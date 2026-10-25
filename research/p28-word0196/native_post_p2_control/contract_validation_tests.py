"""Semantic contract mutations are static refusals, not execution evidence."""
from copy import deepcopy
import unittest
from . import contract_validation as validation


class ContractValidationTests(unittest.TestCase):
    def test_independent_closed_facts_and_counts(self):
        value = validation.validate_contract()
        self.assertTrue(value['passed'])
        self.assertEqual(value['retirementsPerMode'], 680)
        self.assertEqual(value['actualCpuExecutions'], 0)
        self.assertFalse(value['initialNativeControlOwnerEstablished'])

    def test_state_effect_timing_and_authority_mutations_refused(self):
        original = validation.facts()
        mutations = [(('program', 'entryPc'), 0x55C8), (('program', 'segmentBytes'), 211),
            (('program', 'instructionNodes'), 26), (('control', 'tcon0Zf'), 'NewBit2'),
            (('control', 'tcon0NativeReads'), 1), (('control', 'trnsitRead'), 'RawLowNibble'),
            (('control', 'trnsitStoredResult'), 'WholeByte'), (('control', 'sameValueWritesCreateGeneration'), False),
            (('control', 'alias006'), 'RawRam'), (('control', 'timerEvolutionModeled'), True),
            (('control', 'irqDeliveryInjected'), True), (('entry', 'noMidExecutionReseed'), False),
            (('entry', 'unownedRamInitial'), 0), (('paths', 'A', 'budget'), 22),
            (('paths', 'B', 'stopBeforePc'), 0x559E), (('trace', 'canonicalFieldExclusions'), ['psw']),
            (('cycleAccounting', 'softwareDiagnosticCounterDelta'), 7),
            (('cycleAccounting', 'timingEquivalenceEstablished'), True),
            (('delivery', 'privateRomInCi'), True), (('delivery', 'strictHistoricalPreservationPass'), True)]
        for path, value in mutations:
            changed = deepcopy(original)
            target = changed
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                validation.validate_contract(changed)

    def test_historical_source_pins_cannot_be_replaced_by_json(self):
        rows = deepcopy(validation.facts()['sourceBindings'])
        rows[0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            validation.validate_contract(source_bindings=rows)
