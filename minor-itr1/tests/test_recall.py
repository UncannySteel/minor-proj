import datetime as dt
import tempfile
import unittest

from mem import index, recall, schema
from mem.store import Store

NOW = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)


def ago(days):
    return NOW - dt.timedelta(days=days)


class RecallTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name).init()

    def episode(self, title, days, **over):
        when = ago(days)
        return self.store.create("episodic", title, when=when,
                                 occurred=schema.now_iso(when),
                                 body="## What happened\n\n%s\n" % title, **over)

    def data(self):
        return index.build(self.store)


class RankingTests(RecallTestCase):
    def test_lexical_match_wins(self):
        self.store.create("semantic", "Git hooks need LF endings",
                          body="## Claim\n\nCRLF breaks the shebang.\n",
                          evidence=["ep-1"], tags=["git-hooks"])
        self.store.create("semantic", "Coffee machine is on floor three",
                          body="## Claim\n\nUnrelated.\n", evidence=["ep-2"])
        hits = recall.search(self.store, "git hook line endings", now=NOW,
                             data=self.data())
        self.assertEqual(hits[0].id, "se-git-hooks-need-lf-endings")

    def test_non_matching_records_are_gated_out(self):
        self.store.create("semantic", "Something else entirely",
                          salience=1.0, confidence=1.0, evidence=["ep-1"])
        self.assertEqual(recall.search(self.store, "quantum tunnelling",
                                       now=NOW, data=self.data()), [])

    def test_recent_episode_outranks_an_older_twin(self):
        self.episode("Deploy hook failed", 2, tags=["deploy"], outcome="failure")
        self.episode("Deploy hook failed", 200, tags=["deploy"], outcome="failure")
        hits = recall.search(self.store, "deploy hook failed", now=NOW,
                             layers=("episodic",), data=self.data())
        self.assertEqual(len(hits), 2)
        self.assertGreater(hits[0].parts["recency"], hits[1].parts["recency"])
        self.assertGreater(hits[0].score, hits[1].score)

    def test_a_proven_procedure_outranks_an_unproven_twin(self):
        self.store.create("procedural", "Restart the widget service alpha",
                          trigger="widget service hangs", runs=6, successes=6,
                          confidence=0.9, status="active", links=["se-x"])
        self.store.create("procedural", "Restart the widget service beta",
                          trigger="widget service hangs", runs=6, successes=1,
                          failures=5, confidence=0.3, status="active", links=["se-x"])
        hits = recall.search(self.store, "restart widget service", now=NOW,
                             layers=("procedural",), data=self.data())
        self.assertEqual(hits[0].id, "pr-restart-the-widget-service-alpha")
        self.assertEqual(hits[0].parts["reliability"], 1.0)

    def test_deprecated_records_are_pushed_down(self):
        self.store.create("semantic", "Widget policy current", evidence=["ep-1"])
        self.store.create("semantic", "Widget policy old", evidence=["ep-1"],
                          status="deprecated")
        hits = recall.search(self.store, "widget policy", now=NOW, data=self.data())
        self.assertEqual(hits[0].id, "se-widget-policy-current")


class SpreadingTests(RecallTestCase):
    def test_a_linked_record_surfaces_without_matching(self):
        self.episode("Pipeline exploded on Tuesday", 1, tags=["pipeline"],
                     outcome="failure")
        self.store.create("procedural", "Recover the widget conveyor",
                          trigger="conveyor stops",
                          body="## Steps\n\n1. do it\n\n## Verification\n\nit runs\n",
                          links=["ep-20260831-pipeline-exploded-on-tuesday"])
        hits = recall.search(self.store, "pipeline exploded", now=NOW,
                             data=self.data())
        ids = [h.id for h in hits]
        self.assertIn("pr-recover-the-widget-conveyor", ids)
        linked = next(h for h in hits if h.id == "pr-recover-the-widget-conveyor")
        self.assertEqual(linked.via, "ep-20260831-pipeline-exploded-on-tuesday")
        self.assertLess(linked.score, hits[0].score)


class WorkingSetTests(RecallTestCase):
    def test_budget_is_spread_across_layers(self):
        for i in range(5):
            self.episode("Deploy hook failed run %d" % i, i + 1, tags=["deploy"],
                         outcome="failure")
        self.store.create("semantic", "Deploy hooks need LF", evidence=["ep-1"],
                          body="## Claim\n\nDeploy hook line endings matter.\n")
        self.store.create("procedural", "Fix the deploy hook",
                          trigger="deploy hook fails",
                          body="## Steps\n\n1. fix hook\n\n## Verification\n\nhook runs\n")
        hits = recall.working_set(self.store, "deploy hook", budget=6, now=NOW,
                                  data=self.data())
        layers = {h.layer for h in hits}
        self.assertEqual(layers, {"episodic", "semantic", "procedural"})
        self.assertLessEqual(len(hits), 6)
        self.assertEqual(len({h.id for h in hits}), len(hits))


class RenderTests(RecallTestCase):
    def test_empty_render_is_explicit(self):
        self.assertEqual(recall.render([]), "(no memories matched)")

    def test_explain_lists_components(self):
        self.store.create("semantic", "Widget facts", evidence=["ep-1"])
        hits = recall.search(self.store, "widget", now=NOW, data=self.data())
        text = recall.render(hits, explain=True)
        self.assertIn("lex=", text)
        self.assertIn("recency=", text)


if __name__ == "__main__":
    unittest.main()
