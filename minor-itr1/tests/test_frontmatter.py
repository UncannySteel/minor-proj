import unittest

from mem import frontmatter


class LoadTests(unittest.TestCase):
    def test_no_header_returns_body_untouched(self):
        meta, body = frontmatter.loads("just prose\n")
        self.assertEqual(meta, {})
        self.assertEqual(body, "just prose\n")

    def test_scalars_are_typed(self):
        text = "---\nid: se-x\nsalience: 0.5\nruns: 3\npinned: true\nnote: null\n---\n\nbody\n"
        meta, body = frontmatter.loads(text)
        self.assertEqual(meta["id"], "se-x")
        self.assertEqual(meta["salience"], 0.5)
        self.assertEqual(meta["runs"], 3)
        self.assertIs(meta["pinned"], True)
        self.assertIsNone(meta["note"])
        self.assertEqual(body, "body\n")

    def test_inline_and_block_lists(self):
        text = "---\ntags: [a, b, c]\nlinks:\n  - ep-1\n  - ep-2\nempty: []\nbare:\n---\n\nx\n"
        meta, _ = frontmatter.loads(text)
        self.assertEqual(meta["tags"], ["a", "b", "c"])
        self.assertEqual(meta["links"], ["ep-1", "ep-2"])
        self.assertEqual(meta["empty"], [])
        self.assertEqual(meta["bare"], [])

    def test_quoted_value_keeps_colon(self):
        meta, _ = frontmatter.loads('---\ntitle: "Deploy: it broke"\n---\n\nx\n')
        self.assertEqual(meta["title"], "Deploy: it broke")


class RoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_values(self):
        meta = {"id": "ep-1", "layer": "episodic", "title": "A: b",
                "tags": ["one", "two"], "salience": 0.25, "runs": 0,
                "flag": False, "empty": []}
        text = frontmatter.dumps(meta, "## What happened\n\nthing\n",
                                 order=("id", "layer", "title"))
        back, body = frontmatter.loads(text)
        self.assertEqual(back, meta)
        self.assertIn("## What happened", body)

    def test_key_order_is_honoured(self):
        text = frontmatter.dumps({"z": 1, "id": "se-x", "a": 2},
                                 "body", order=("id", "a"))
        keys = [line.split(":")[0] for line in text.splitlines()[1:4]]
        self.assertEqual(keys, ["id", "a", "z"])

    def test_ambiguous_strings_are_quoted(self):
        text = frontmatter.dumps({"a": "true", "b": "12", "c": "- dash"}, "body")
        meta, _ = frontmatter.loads(text)
        self.assertEqual(meta["a"], "true")
        self.assertEqual(meta["b"], "12")
        self.assertEqual(meta["c"], "- dash")


if __name__ == "__main__":
    unittest.main()
