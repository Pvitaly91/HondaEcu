"""Closed invented input relations; never a runtime or native owner witness."""
from copy import deepcopy
import unittest
from . import corpus


class CorpusTests(unittest.TestCase):
    def test_exact_16_case_and_624_retirement_coverage(self):
        value = corpus.coverage()
        self.assertEqual(value['cases'], 16)
        self.assertEqual(value['paths'], {'A': 16})
        self.assertEqual(value['retirements'], 624)
        self.assertEqual(value['tcon0Values'], [0x83, 0x87, 0x8B, 0x8F])
        self.assertEqual(value['trnsitFlags'], list(range(8)))
        self.assertEqual(value['scbs'], list(range(8)))
        self.assertEqual(len(value['incomingFlagVectors']), 8)
        self.assertEqual(value['words'], [0, 1, 2, 0x3F, 0x7F, 0x80, 0xBE, 0xBF])
        self.assertFalse(value['initialNativeControlOwnerEstablished'])

    def test_new_canaries_are_pre_entry_unowned_not_ready_values(self):
        for case in corpus.iter_cases():
            self.assertEqual(len(case['data']), 23)
            self.assertTrue(all(case['data'][str(a)] == 0xA5 for a in corpus.NEW_CANARIES))
            for address in corpus.NEW_CANARIES:
                changed = deepcopy(case); changed['data'][str(address)] = 1
                with self.assertRaises(ValueError): corpus.validate_case(changed)
        self.assertEqual({c['internal_sf'] for c in corpus.iter_cases()}, {False, True})
        self.assertEqual({bool(c['data'][str(0x012A)] & 128) for c in corpus.iter_cases()}, {False, True})

    def test_not_below_and_canary_alias_scopes_refuse(self):
        case = next(corpus.iter_cases())
        for word in (0xC0, 0x100, 0xFFFF):
            changed = deepcopy(case)
            changed['data'][str(0x0196)], changed['data'][str(0x0197)] = word & 255, word >> 8
            with self.assertRaises(ValueError): corpus.validate_case(changed)
        for address in corpus.NEW_CANARIES:
            self.assertEqual(corpus.PUBLIC_DATA.get(address, address), address)
        old_mapped = {corpus.PUBLIC_DATA.get(a, a) for a in corpus.previous.INVENTORY}
        self.assertFalse(old_mapped & set(corpus.NEW_CANARIES))

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
