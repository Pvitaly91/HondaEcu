"""Invented corpus/admission checks; no CPU, ROM or runtime observations."""
from copy import deepcopy
import unittest

from native_entry_continuity import corpus


class CorpusTests(unittest.TestCase):
    def test_closed_balanced_32_positive_states(self):
        cases = list(corpus.iter_cases())
        self.assertEqual(len({case["case_id"] for case in cases}), 32)
        counts = corpus.coverage(cases)
        self.assertEqual(counts["paths"], dict.fromkeys("ABCD", 8))
        self.assertEqual(counts["retirements"], 592)
        self.assertEqual(len(counts["incomingFlagVectors"]), 16)
        self.assertEqual(counts["scbs"], list(range(8)))
        self.assertTrue({0, 191, 192, 193, 255, 256, 65535} <= set(counts["words"]))
        self.assertTrue(all(case["data"][str(0x0128)] & 4 for case in cases))
        self.assertTrue(all(case["data"][str(0x0117)] != 15 for case in cases))

    def test_host_sf_pairs_have_identical_other_inputs(self):
        cases = list(corpus.iter_cases())
        for first, second in zip(cases[::2], cases[1::2]):
            left, right = deepcopy(first), deepcopy(second)
            self.assertFalse(left.pop("internal_sf"))
            self.assertTrue(right.pop("internal_sf"))
            left.pop("case_id")
            right.pop("case_id")
            self.assertEqual(left, right)

    def test_public_mapping_is_explicit_and_distinct(self):
        for case in corpus.iter_cases():
            public = corpus.wire_case(case, "public_fixture")
            self.assertEqual(public["entry"]["pc"], 0x6200)
            self.assertNotIn(str(0x0128), public["data"])
            self.assertEqual(public["data"][str(0x0130)], case["data"][str(0x0128)])
            self.assertNotIn("native_input_claimed", public)

    def test_alternates_are_not_positive_routes(self):
        controls = list(corpus.iter_branch_controls())
        self.assertEqual([case["path"] for case in controls], ["JbrAlternate", "JneAlternate"])
        self.assertEqual([case["budget"] for case in controls], [1, 6])

    def test_meaningful_domain_and_authority_refusals(self):
        original = next(corpus.iter_cases())
        mutations = [
            lambda v: v.update(mode="NativeScheduledExecution"),
            lambda v: v.update(native_input_claimed=True),
            lambda v: v.update(budget=22),
            lambda v: v.update(path="D"),
            lambda v: v["entry"].update(pc=0x556F),
            lambda v: v["entry"].update(lrb=0x20),
            lambda v: v["entry"].update(psw=v["entry"]["psw"] & ~0x0008),
            lambda v: v["entry"].update(ah=v["entry"]["ah"] ^ 1),
            lambda v: v["entry"]["local_r"].__setitem__(2, v["entry"]["local_r"][2] ^ 1),
            lambda v: v["entry"]["sf"].update(value=0),
            lambda v: v["data"].__setitem__(str(0x0128), v["data"][str(0x0128)] & ~4),
            lambda v: v["data"].__setitem__(str(0x0117), 15),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                value = deepcopy(original)
                mutate(value)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    corpus.validate_case(value)
        self.assertEqual(original, next(corpus.iter_cases()))


if __name__ == "__main__":
    unittest.main()
