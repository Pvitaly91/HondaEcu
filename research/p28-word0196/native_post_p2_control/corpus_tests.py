"""Closed invented input relations; never a runtime or native owner witness."""
from copy import deepcopy
import unittest
from . import corpus


class CorpusTests(unittest.TestCase):
    def test_exact_32_case_and_680_retirement_coverage(self):
        value = corpus.coverage()
        self.assertEqual(value['cases'], 32)
        self.assertEqual(value['paths'], dict.fromkeys('ABCD', 8))
        self.assertEqual(value['retirements'], 680)
        self.assertEqual(value['tcon0Values'], [0x83, 0x87, 0x8B, 0x8F])
        self.assertEqual(value['trnsitFlags'], list(range(16)))
        self.assertEqual(value['scbs'], list(range(8)))
        self.assertEqual(len(value['incomingFlagVectors']), 16)
        self.assertFalse(value['initialNativeControlOwnerEstablished'])

    def test_old_bit_and_same_value_domains_are_independently_varied(self):
        for path in 'ABCD':
            selected = [case for case in corpus.iter_cases() if case['path'] == path]
            self.assertEqual({case['control_snapshot']['tcon0'] for case in selected}, {0x83, 0x87, 0x8B, 0x8F})
            self.assertEqual({bool(case['control_snapshot']['trnsit_implemented_flags'] & 4) for case in selected}, {False, True})
            self.assertEqual({case['internal_sf'] for case in selected}, {False, True})

    def test_closed_control_entry_budget_and_provenance_refusals(self):
        original = next(corpus.iter_cases())
        mutations = [('control_snapshot', 'tcon0', 0), ('control_snapshot', 'tcon0', 0x93),
            ('control_snapshot', 'tcon0', 0x43), ('control_snapshot', 'tcon0', True),
            ('control_snapshot', 'trnsit_implemented_flags', 0xF0),
            ('control_snapshot', 'trnsit_implemented_flags', True),
            ('control_snapshot', 'provenance', 'ObservedNative'), ('entry', 'pc', 0x55C8),
            ('entry', 'pc', 0x5599), ('p2_snapshot', 'p2io', 0), ('p2_snapshot', 'p2sf', 0)]
        for group, field, value in mutations:
            altered = deepcopy(original)
            altered[group][field] = value
            with self.subTest(group=group, field=field, value=value), self.assertRaises(ValueError):
                corpus.validate_case(altered)
        for field, value in [('budget', 17), ('budget', True), ('native_input_claimed', True)]:
            altered = deepcopy(original)
            altered[field] = value
            with self.assertRaises(ValueError):
                corpus.validate_case(altered)
        for field in ['timer_ticks', 'irq', 'startup_owner', 'host_reseed']:
            with self.assertRaises(ValueError):
                corpus.validate_case({**original, field: 1})

    def test_peripheral_snapshots_are_not_ram_seeds(self):
        for case in corpus.iter_cases():
            wire = corpus.wire_case(case, 'public_fixture')
            self.assertEqual(wire['entry']['pc'], 0x6400)
            self.assertEqual(wire['control_snapshot'], case['control_snapshot'])
            self.assertFalse({'36', '64', '70', '6'} & set(wire['data']))
            self.assertEqual(wire['budget'], case['budget'])


if __name__ == '__main__':
    unittest.main()
