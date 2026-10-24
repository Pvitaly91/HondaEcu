"""Invented scalar admission tests; no runner, ROM or CPU invocation."""
from copy import deepcopy
import unittest

from . import corpus


class CorpusTests(unittest.TestCase):
    def test_closed32_case_coverage_and_retirements(self):
        found = corpus.coverage()
        self.assertEqual(found['cases'], 32)
        self.assertEqual(found['paths'], dict.fromkeys('ABCD', 8))
        self.assertEqual(found['retirements'], 624)
        self.assertEqual(found['initialP2Values'], [0, 15, 165, 240, 255])
        self.assertEqual(found['scbs'], list(range(8)))
        self.assertEqual(len(found['incomingFlagVectors']), 16)
        self.assertTrue({0, 191, 192, 193, 255, 256, 65535} <= set(found['words']))

    def test_sf_pairs_keep_the_same_initial_latch_and_aliases(self):
        cases = list(corpus.iter_cases())
        for left, right in zip(cases[::2], cases[1::2]):
            self.assertFalse(left['internal_sf']); self.assertTrue(right['internal_sf'])
            self.assertEqual(left['p2_snapshot'], right['p2_snapshot'])
            self.assertEqual(left['entry'], right['entry'])
            self.assertEqual(left['data'], right['data'])

    def test_closed_initial_mode_alias_and_budget_refusals(self):
        original = next(corpus.iter_cases())
        mutations = [('p2_snapshot', 'p2io', 0), ('p2_snapshot', 'p2sf', 0xFF),
            ('p2_snapshot', 'p2sf', 0), ('p2_snapshot', 'value', True),
            ('p2_snapshot', 'provenance', 'ObservedNative'), ('entry', 'pc', 0x55C5),
            ('entry', 'scb', 9), ('entry', 'al', original['entry']['al'] ^ 1)]
        for group, key, value in mutations:
            with self.subTest(group=group, key=key, value=value):
                altered = deepcopy(original); altered[group][key] = value
                with self.assertRaises(ValueError):
                    corpus.validate_case(altered)
        for key, value in [('budget', 16), ('budget', 18), ('budget', True),
                           ('path', 'JbrAlternate'), ('native_input_claimed', True)]:
            altered = deepcopy(original); altered[key] = value
            with self.assertRaises(ValueError):
                corpus.validate_case(altered)

    def test_invented_program_domain_and_p2_not_in_ram_seed(self):
        for case in corpus.iter_cases():
            wire = corpus.wire_case(case, 'public_fixture')
            self.assertEqual(wire['entry']['pc'], 0x6400)
            self.assertEqual(wire['p2_snapshot'], case['p2_snapshot'])
            self.assertNotIn('36', wire['data'])
            self.assertEqual(wire['budget'], case['budget'])
            self.assertNotIn('mode', wire)


if __name__ == '__main__':
    unittest.main()
