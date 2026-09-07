import datetime as dt
import tempfile
import unittest

from mem import consolidate, index, schema
from mem.store import Store

NOW = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)


def ago(days):
    return NOW - dt.timedelta(days=days)


class ConsolidateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name).init()

    def episode(self, title, days=1, **over):
        when = ago(days)
        return self.store.create("episodic", title, when=when,
                                 occurred=schema.now_iso(when),
                                 body="## What happened\n\n%s\n" % title, **over)

    def report(self, **kw):
        return consolidate.analyze(self.store, data=index.build(self.store),
                                   now=NOW, **kw)


class PromotionTests(ConsolidateTestCase):
    def test_repeated_tag_proposes_a_semantic_record(self):
        for i in range(3):
            self.episode("Hook failed %d" % i, i + 1, tags=["git-hooks"],
                         outcome="failure")
        proposals = self.report()["promote_semantic"]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["tag"], "git-hooks")
        self.assertEqual(proposals[0]["support"], 3)
        self.assertEqual(proposals[0]["suggested_id"], "se-git-hooks")

    def test_repeated_success_proposes_a_procedure(self):
        for i in range(3):
            self.episode("dos2unix fixed it %d" % i, i + 1, tags=["git-hooks"],
                         outcome="success")
        proposals = self.report()["promote_procedural"]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["suggested_id"], "pr-git-hooks")

    def test_failures_alone_do_not_propose_a_procedure(self):
        for i in range(3):
            self.episode("Hook failed %d" % i, i + 1, tags=["git-hooks"],
                         outcome="failure")
        self.assertEqual(self.report()["promote_procedural"], [])

    def test_two_episodes_are_not_yet_a_pattern(self):
        for i in range(2):
            self.episode("Hook failed %d" % i, i + 1, tags=["git-hooks"],
                         outcome="failure")
        self.assertEqual(self.report()["promote_semantic"], [])

    def test_already_cited_episodes_stop_proposing(self):
        ids = [self.episode("Hook failed %d" % i, i + 1, tags=["git-hooks"],
                            outcome="failure").id for i in range(3)]
        self.store.create("semantic", "Hooks need LF", tags=["git-hooks"],
                          evidence=ids, body="## Claim\n\nLF only.\n")
        self.assertEqual(self.report()["promote_semantic"], [])

    def test_min_support_is_tunable(self):
        for i in range(2):
            self.episode("Hook failed %d" % i, i + 1, tags=["git-hooks"],
                         outcome="failure")
        self.assertEqual(len(self.report(min_support=2)["promote_semantic"]), 1)


class HygieneTests(ConsolidateTestCase):
    def test_dangling_link_is_an_error(self):
        self.store.create("semantic", "A fact", evidence=["ep-does-not-exist"],
                          body="## Claim\n\nx\n")
        problems = [h for h in self.report()["hygiene"] if "dangling" in h["detail"]]
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["severity"], "error")

    def test_unevidenced_procedure_warns(self):
        self.store.create("procedural", "A guess", trigger="whenever",
                          body="## Steps\n\n1. x\n\n## Verification\n\ny\n")
        details = [h["detail"] for h in self.report()["hygiene"]]
        self.assertTrue(any("neither evidence nor a run record" in d for d in details))

    def test_schema_errors_are_surfaced(self):
        record = self.store.create("semantic", "Broken", evidence=["ep-1"],
                                   body="## Claim\n\nx\n")
        record.meta["confidence"] = 3.0
        self.store.save(record)
        errors = [h for h in self.report()["hygiene"] if h["severity"] == "error"]
        self.assertTrue(any("outside [0,1]" in h["detail"] for h in errors))


class DecayTests(ConsolidateTestCase):
    def test_old_unloved_episode_is_a_forgetting_candidate(self):
        self.episode("Trivial thing", 400, salience=0.1, tags=["noise"])
        decay = self.report()["decay"]
        self.assertEqual(len(decay), 1)
        self.assertIn("cited by nothing", decay[0]["why"])

    def test_a_cited_episode_is_kept(self):
        rec = self.episode("Trivial thing", 400, salience=0.1, tags=["noise"])
        self.store.create("semantic", "Depends on it", evidence=[rec.id],
                          body="## Claim\n\nx\n")
        self.assertEqual(self.report()["decay"], [])

    def test_a_salient_episode_is_kept(self):
        self.episode("Important thing", 400, salience=0.9, tags=["noise"])
        self.assertEqual(self.report()["decay"], [])


class DuplicateTests(ConsolidateTestCase):
    def test_near_duplicate_semantics_are_merge_candidates(self):
        body = "## Claim\n\nGit hooks on this machine need LF line endings.\n"
        self.store.create("semantic", "Git hooks need LF line endings",
                          evidence=["ep-1"], body=body, confidence=0.8)
        self.store.create("semantic", "Git hooks need LF endings",
                          evidence=["ep-1"], body=body, confidence=0.8)
        self.assertEqual(len(self.report()["merge_semantic"]), 1)

    def test_wide_confidence_gap_reads_as_a_contradiction(self):
        body = "## Claim\n\nGit hooks on this machine need LF line endings.\n"
        self.store.create("semantic", "Git hooks need LF line endings",
                          evidence=["ep-1"], body=body, confidence=0.9)
        self.store.create("semantic", "Git hooks need LF endings",
                          evidence=["ep-1"], body=body, confidence=0.2)
        self.assertEqual(len(self.report()["contradictions"]), 1)
        self.assertEqual(self.report()["merge_semantic"], [])


class RenderTests(ConsolidateTestCase):
    def test_empty_report_renders_every_section(self):
        text = consolidate.render(self.report())
        for heading in ("Promote to semantic", "Promote to procedural",
                        "Merge candidates", "Forgetting candidates", "Hygiene"):
            self.assertIn(heading, text)
        self.assertIn("Nothing above has been written", text)


if __name__ == "__main__":
    unittest.main()
