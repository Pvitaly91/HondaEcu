"""Meaningful contract/input relation mutations, never runtime proof."""
from copy import deepcopy
import unittest

from original_rom_execution.verify import strict_json
from . import contract_validation as validation


class ContractValidationTests(unittest.TestCase):
    def test_actual_closed_contract_and_explicit_no_runtime_claim(self):
        result = validation.validate_contract()
        self.assertTrue(result['passed'])
        self.assertEqual(result['retirementsPerMode'], 624)
        self.assertEqual(result['actualCpuExecutions'], 0)
        self.assertFalse(result['initialNativeP2OwnerEstablished'])

    def test_instruction_context_ownership_and_effect_relation_mutations_refused(self):
        original = strict_json(validation.PATH.read_bytes())
        mutations = [(('program', 'entryPc'), 0x5596), (('program', 'segmentBytes'), 208),
            (('p2', 'p2io'), 0), (('p2', 'p2sf'), 0xFF), (('p2', 'width'), 16),
            (('p2', 'initialNativeOwner'), 'ObservedNative'), (('p2', 'initialSnapshotCreatesNativeGeneration'), True),
            (('p2', 'sameValueWriteCreatesFreshGeneration'), False), (('paths', 'A', 'budget'), 16),
            (('paths', 'B', 'stopBeforePc'), 0x55C8), (('paths', 'A', 'operation'), 'AND'),
            (('entry', 'oneCpuBusPerCase'), False), (('entry', 'nativeProducer05ebExecuted'), True),
            (('trace', 'globalLogicalWriteOrdinalIncludes48Seeds'), False), (('trace', 'canonicalFieldExclusions'), ['psw']),
            (('cycleAccounting', 'softwareDiagnosticCounterDelta'), 7),
            (('cycleAccounting', 'primaryManualIntCycles'), 6),
            (('cycleAccounting', 'timingEquivalenceEstablished'), True),
            (('cycleAccounting', 'semanticOrCanonicalFieldsOmitted'), ['cycles']),
            (('corpus', 'priorRuntimeResultsCountedAsNew'), True), (('delivery', 'privateRomInCi'), True),
            (('delivery', 'strictHistoricalPreservationPass'), True)]
        for path, value in mutations:
            altered = deepcopy(original); target = altered
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                validation.validate_contract(altered)

    def test_current_source_bindings_cannot_be_replaced_by_metadata(self):
        rows = [{'path': path, 'bytes': size, 'sha256': digest} for path, size, digest in validation.SOURCES]
        rows[0]['sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            validation.validate_contract(source_bindings=rows)


if __name__ == '__main__':
    unittest.main()
