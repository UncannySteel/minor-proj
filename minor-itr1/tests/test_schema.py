import unittest

from mem import schema


class DefaultsTests(unittest.TestCase):
    def test_episodic_defaults_are_valid(self):
        meta = schema.default_meta("episodic", "Something happened")
        meta["id"] = "ep-20260101-something-happened"
        errors, _ = schema.validate(meta, schema.TEMPLATES["episodic"])
        self.assertEqual(errors, [])

    def test_semantic_and_procedural_defaults_are_valid(self):
        for layer, rec_id in (("semantic", "se-a-fact"), ("procedural", "pr-a-move")):
            meta = schema.default_meta(layer, "A thing")
            meta["id"] = rec_id
            if layer == "procedural":
                meta["trigger"] = "when x happens"
            errors, _ = schema.validate(meta, schema.TEMPLATES[layer])
            self.assertEqual(errors, [], layer)

    def test_unknown_layer_raises(self):
        with self.assertRaises(ValueError):
            schema.default_meta("muscle", "nope")


class ValidateTests(unittest.TestCase):
    def base(self, layer="semantic", **over):
        meta = schema.default_meta(layer, "A claim")
        meta["id"] = {"semantic": "se-a-claim", "episodic": "ep-20260101-a-claim",
                      "procedural": "pr-a-claim"}[layer]
        if layer == "procedural":
            meta["trigger"] = "when x"
        meta.update(over)
        return meta

    def test_missing_required_field_is_an_error(self):
        meta = self.base()
        del meta["kind"]
        errors, _ = schema.validate(meta, schema.TEMPLATES["semantic"])
        self.assertIn("missing required field: kind", errors)

    def test_id_prefix_must_match_layer(self):
        errors, _ = schema.validate(self.base(id="pr-a-claim"), "## Claim")
        self.assertTrue(any("disagrees with layer" in e for e in errors))

    def test_confidence_must_be_a_unit_interval(self):
        errors, _ = schema.validate(self.base(confidence=1.4), "## Claim")
        self.assertTrue(any("outside [0,1]" in e for e in errors))

    def test_enum_is_enforced(self):
        errors, _ = schema.validate(self.base(kind="vibes"), "## Claim")
        self.assertTrue(any("not in" in e for e in errors))

    def test_missing_body_section_is_only_a_warning(self):
        errors, warnings = schema.validate(self.base(evidence=["ep-1"]), "no headings")
        self.assertEqual(errors, [])
        self.assertTrue(any("## Claim" in w for w in warnings))

    def test_evidence_free_semantic_warns(self):
        _, warnings = schema.validate(self.base(), "## Claim")
        self.assertTrue(any("no evidence" in w for w in warnings))

    def test_bad_timestamp_is_an_error(self):
        errors, _ = schema.validate(self.base(created="last tuesday"), "## Claim")
        self.assertTrue(any("ISO-8601" in e for e in errors))

    def test_run_counts_that_exceed_runs_warn(self):
        meta = self.base("procedural", runs=1, successes=2, failures=1)
        _, warnings = schema.validate(meta, schema.TEMPLATES["procedural"])
        self.assertTrue(any("exceeds runs" in w for w in warnings))


class HelperTests(unittest.TestCase):
    def test_slugify_truncates_and_normalises(self):
        self.assertEqual(schema.slugify("Deploy Hook: FAILED (again!)"),
                         "deploy-hook-failed-again")
        self.assertEqual(schema.slugify("a b c d e f g h"), "a-b-c-d-e-f")
        self.assertEqual(schema.slugify("!!!"), "untitled")

    def test_parse_ts_accepts_z_and_date_only(self):
        self.assertIsNotNone(schema.parse_ts("2026-01-01T00:00:00Z"))
        self.assertIsNotNone(schema.parse_ts("2026-01-01"))
        self.assertIsNone(schema.parse_ts("nope"))


if __name__ == "__main__":
    unittest.main()
