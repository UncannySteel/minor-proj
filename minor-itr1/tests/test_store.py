import datetime as dt
import tempfile
import unittest
from pathlib import Path

from mem import index, schema
from mem.store import Store


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name).init()


class LayoutTests(StoreTestCase):
    def test_init_creates_every_layer(self):
        for layer in schema.LAYERS:
            self.assertTrue((Path(self.tmp.name) / "memory" / layer).is_dir())

    def test_episodes_bucket_by_month(self):
        when = dt.datetime(2026, 3, 4, tzinfo=dt.timezone.utc)
        record = self.store.create("episodic", "A thing", when=when,
                                   occurred=schema.now_iso(when))
        self.assertIn("2026-03", record.path.parts)

    def test_durable_layers_stay_flat(self):
        record = self.store.create("semantic", "A fact")
        self.assertEqual(record.path.parent.name, "semantic")


class IdTests(StoreTestCase):
    def test_episodic_ids_carry_their_date(self):
        when = dt.datetime(2026, 3, 4, tzinfo=dt.timezone.utc)
        self.assertEqual(self.store.new_id("episodic", "Hook broke", when),
                         "ep-20260304-hook-broke")

    def test_durable_ids_are_addresses(self):
        self.assertEqual(self.store.new_id("semantic", "Hooks need LF"),
                         "se-hooks-need-lf")

    def test_collisions_get_a_suffix(self):
        self.store.create("semantic", "Hooks need LF")
        self.assertEqual(self.store.new_id("semantic", "Hooks need LF"),
                         "se-hooks-need-lf-2")


class RoundTripTests(StoreTestCase):
    def test_create_then_get_preserves_fields(self):
        self.store.create("procedural", "Fix the hook", trigger="hook fails",
                          tags=["deploy"], links=["se-x"], runs=2, successes=2)
        record = self.store.get("pr-fix-the-hook")
        self.assertIsNotNone(record)
        self.assertEqual(record.meta["trigger"], "hook fails")
        self.assertEqual(record.tags, ["deploy"])
        self.assertEqual(record.meta["runs"], 2)

    def test_links_property_unions_every_reference_field(self):
        self.store.create("semantic", "A fact", evidence=["ep-1"],
                          links=["pr-2"], supersedes=["se-old"])
        record = self.store.get("se-a-fact")
        self.assertEqual(sorted(record.links), ["ep-1", "pr-2", "se-old"])

    def test_default_body_uses_the_layer_template(self):
        record = self.store.create("procedural", "Something")
        self.assertIn("## Verification", record.body)

    def test_missing_id_returns_none(self):
        self.assertIsNone(self.store.get("se-not-here"))


class ArchiveTests(StoreTestCase):
    def test_archive_moves_the_file_and_stamps_it(self):
        self.store.create("episodic", "Old noise", outcome="neutral")
        rec_id = next(self.store.records()).id
        archived = self.store.archive_record(rec_id, reason="superseded by se-x")
        self.assertEqual(archived.meta["status"], "archived")
        self.assertEqual(archived.meta["archive_reason"], "superseded by se-x")
        self.assertIn("_archive", archived.path.parts)
        self.assertEqual(list(self.store.records()), [])
        self.assertEqual(len(list(self.store.records(include_archived=True))), 1)

    def test_restore_brings_it_back(self):
        self.store.create("semantic", "A fact")
        self.store.archive_record("se-a-fact")
        restored = self.store.restore("se-a-fact")
        self.assertEqual(restored.meta["status"], "active")
        self.assertNotIn("_archive", restored.path.parts)
        self.assertEqual(len(list(self.store.records())), 1)


class IndexTests(StoreTestCase):
    def test_index_counts_and_files(self):
        self.store.create("semantic", "A fact", tags=["x"], evidence=["ep-1"])
        self.store.create("episodic", "An event", outcome="success", tags=["x"])
        data = index.save(self.store)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["counts_by_layer"], {"semantic": 1, "episodic": 1})
        self.assertTrue((self.store.index_dir / "index.json").exists())
        text = (self.store.index_dir / "MEMORY.md").read_text(encoding="utf-8")
        self.assertIn("## semantic (1)", text)
        self.assertIn("## procedural (0)", text)

    def test_title_terms_outweigh_body_terms(self):
        self.store.create("semantic", "Widget", body="## Claim\n\ngadget gadget\n")
        entry = index.build(self.store)["records"][0]
        self.assertEqual(entry["terms"]["widget"], 3)

    def test_stale_detection(self):
        data = index.save(self.store)
        self.assertFalse(index.is_stale(self.store, data))
        self.store.create("semantic", "New fact")
        self.assertTrue(index.is_stale(self.store, data))


if __name__ == "__main__":
    unittest.main()
