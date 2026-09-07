import json
import tempfile
import unittest
from pathlib import Path

from mem.errorlog import ErrorLog, fingerprint, render, render_stats
from mem.store import Store


class ErrorLogTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = ErrorLog(self.tmp.name)


class WriteTests(ErrorLogTestCase):
    def test_record_appends_one_json_line(self):
        self.log.record("something broke", kind="test", query="abc")
        lines = Path(self.log.path).read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["message"], "something broke")
        self.assertEqual(entry["kind"], "test")
        self.assertEqual(entry["context"]["query"], "abc")
        self.assertEqual(entry["severity"], "error")

    def test_exception_captures_type_and_traceback(self):
        try:
            raise ValueError("bad value")
        except ValueError as exc:
            entry = self.log.exception(exc, kind="unit")
        self.assertEqual(entry["type"], "ValueError")
        self.assertIn("ValueError: bad value", entry["traceback"])

    def test_unserialisable_context_falls_back_to_repr(self):
        self.log.record("x", obj=object(), nested={"a": [1, object()]})
        entry = self.log.entries()[0]
        self.assertTrue(entry["context"]["obj"].startswith("<object"))
        self.assertEqual(entry["context"]["nested"]["a"][0], 1)

    def test_unknown_severity_is_normalised(self):
        self.assertEqual(self.log.record("x", severity="spicy")["severity"], "error")

    def test_a_broken_log_path_does_not_raise(self):
        log = ErrorLog(self.tmp.name)
        log.dir = Path(self.tmp.name) / "logs"
        log.dir.mkdir(parents=True, exist_ok=True)
        log.path = log.dir  # a directory, so opening it for append fails
        self.assertIsInstance(log.record("still returns an entry"), dict)


class CaptureTests(ErrorLogTestCase):
    def test_capture_logs_and_reraises(self):
        with self.assertRaises(KeyError):
            with self.log.capture("recall", query="q"):
                raise KeyError("missing")
        entry = self.log.entries()[0]
        self.assertEqual(entry["kind"], "recall")
        self.assertEqual(entry["type"], "KeyError")
        self.assertEqual(entry["context"]["query"], "q")

    def test_capture_can_swallow(self):
        with self.log.capture("recall", reraise=False):
            raise RuntimeError("handled")
        self.assertEqual(len(self.log.entries()), 1)

    def test_clean_block_logs_nothing(self):
        with self.log.capture("recall"):
            pass
        self.assertEqual(self.log.entries(), [])


class FingerprintTests(unittest.TestCase):
    def test_instance_noise_is_stripped(self):
        a = fingerprint("io", "OSError", "cannot read C:/tmp/a/ep-1.md at line 42")
        b = fingerprint("io", "OSError", "cannot read D:/other/ep-2.md at line 7")
        self.assertEqual(a, b)

    def test_different_shapes_differ(self):
        self.assertNotEqual(fingerprint("io", "OSError", "cannot read"),
                            fingerprint("io", "ValueError", "cannot read"))
        self.assertNotEqual(fingerprint("io", "OSError", "cannot read"),
                            fingerprint("index", "OSError", "cannot read"))


class ReadTests(ErrorLogTestCase):
    def seed(self):
        for i in range(4):
            self.log.record("parse failed on line %d" % i, kind="index")
        self.log.record("other thing", kind="recall", severity="warning")

    def test_filters(self):
        self.seed()
        self.assertEqual(len(self.log.entries()), 5)
        self.assertEqual(len(self.log.entries(kind="index")), 4)
        self.assertEqual(len(self.log.entries(severity="warning")), 1)
        self.assertEqual(len(self.log.entries(limit=2)), 2)

    def test_since_cutoff_excludes_older(self):
        self.seed()
        self.assertEqual(self.log.entries(since="2099-01-01"), [])
        self.assertEqual(len(self.log.entries(since="2000-01-01")), 5)

    def test_torn_line_loses_one_entry_not_the_log(self):
        self.seed()
        with open(self.log.path, "a", encoding="utf-8") as handle:
            handle.write("{not json\n")
        self.assertEqual(len(self.log.entries()), 5)

    def test_missing_file_reads_empty(self):
        self.assertEqual(self.log.entries(), [])

    def test_stats_group_recurrences(self):
        self.seed()
        data = self.log.stats(min_recurrence=3)
        self.assertEqual(data["total"], 5)
        self.assertEqual(data["by_kind"], {"index": 4, "recall": 1})
        self.assertEqual(data["distinct"], 2)
        self.assertEqual(len(data["recurring"]), 1)
        self.assertEqual(data["recurring"][0]["count"], 4)

    def test_clear_removes_the_file(self):
        self.seed()
        self.assertTrue(self.log.clear())
        self.assertEqual(self.log.entries(), [])
        self.assertFalse(self.log.clear())


class RotationTests(ErrorLogTestCase):
    def test_rotation_starts_a_new_file(self):
        log = ErrorLog(self.tmp.name, max_bytes=200)
        for i in range(20):
            log.record("padding entry number %d with some text" % i)
        self.assertTrue(log.path.with_suffix(".1.jsonl").exists())
        self.assertLess(len(log.entries()), 20)


class RenderTests(ErrorLogTestCase):
    def test_empty_render_is_explicit(self):
        self.assertEqual(render([]), "(no errors logged)")

    def test_verbose_includes_traceback(self):
        try:
            raise ValueError("boom")
        except ValueError as exc:
            self.log.exception(exc, kind="unit")
        rows = self.log.entries()
        self.assertNotIn("Traceback", render(rows))
        self.assertIn("Traceback", render(rows, verbose=True))

    def test_stats_render_calls_out_recurrences(self):
        for _ in range(3):
            self.log.record("same shape", kind="index")
        text = render_stats(self.log.stats(), min_recurrence=3)
        self.assertIn("recurring", text)
        self.assertIn("3x", text)


class StoreIntegrationTests(unittest.TestCase):
    def test_an_unreadable_record_is_logged_not_swallowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp).init()
            store.create("semantic", "A fact", evidence=["ep-1"])
            bad = Path(store.memory) / "semantic" / "se-broken.md"
            bad.write_bytes(b"---\nid: se-broken\n---\n\n\xff\xfe not utf-8\n")
            self.assertEqual(len(list(store.records())), 1)
            entries = store.errors.entries(kind="store.load")
            self.assertEqual(len(entries), 1)
            self.assertIn("se-broken", entries[0]["context"]["path"])


if __name__ == "__main__":
    unittest.main()
