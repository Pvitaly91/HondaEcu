"""Independent full records and explicit semantic refusal checks."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest

from cold_return_c8_writer_proof.competing_writers import usp27b2_alias_proof
from cold_return_c8_writer_proof.corpus import usp_query

from . import analysis, reference_oracle
from .corpus import cases, frame_query


class SourceTests(unittest.TestCase):
    def test_all_complete_records_match_independent_expectations(self):
        functions = analysis.operations()
        seen = set()
        for case in cases():
            identifier = case['id']
            with self.subTest(case=identifier):
                self.assertNotIn(identifier, seen)
                seen.add(identifier)
                actual = analysis.record(case, functions[case['operation']](deepcopy(case['input'])))
                expected = analysis.record(case, reference_oracle.expected(case))
                self.assertTrue(analysis.canonical(actual) == analysis.canonical(expected),
                                'IndependentCanonicalMismatch')
        self.assertTrue(seen)

    def test_both_ie_barriers_and_fault_stop_without_execution(self):
        functions = analysis.operations()
        for row in cases():
            if row['id'] not in ('frame-ie-first5cb9', 'frame-ie-second5ccb', 'frame-fault'):
                continue
            actual = functions[row['operation']](row['input'])
            self.assertTrue(actual['stopBoundary'].startswith(('STOP_BEFORE_IE_WRITE_', 'STOP_BEFORE_BRK_')))
            self.assertIsNone(actual['actualFramePop'])
            self.assertIs(actual['sourcePathEstablished'], False)

    def test_unknown_flag_observation_is_not_defaulted(self):
        row = next(row for row in cases() if row['id'] == 'route-unknown-is-not-zero')
        result = analysis.operations()[row['operation']](row['input'])
        routes = result['hypotheses'][1]['routes']
        self.assertEqual(len(routes), 5)
        self.assertEqual({(entry['cf'], entry['zf']) for route in routes for entry in route['branchFlags']
                          if entry['pc'] == 0x5CE7}, {(1, 0), (0, 1), (0, 0)})
        self.assertIsNone(result['nativeBranchTaken'])

    def test_usp_0419_never_proves_disjointness(self):
        result = usp27b2_alias_proof(usp_query(0x0419))
        self.assertIs(result['state']['overlap03cb'], True)
        self.assertEqual(result['state']['qualifiedAddress'], 0x03CB)

    def test_actual_authority_and_private_payload_rejected_by_closed_shape(self):
        model = analysis.operations()['helper_rt_frame_lifetime']
        query = frame_query(0x2777, 'Invented')
        for forbidden in ('actualIeWrite', 'actualBufferWrite', 'actualCpuExecutions', 'privatePayload'):
            with self.subTest(field=forbidden), self.assertRaises(ValueError):
                model({**query, forbidden: True})
        self.assertIsNone(analysis.AUTHORITY['actualIeWrite'])
        self.assertIsNone(analysis.AUTHORITY['actualBufferWrite'])
        self.assertEqual(analysis.AUTHORITY['cpuInstructionRetirements'], 0)
        self.assertIsNone(analysis.AUTHORITY['actualIrqDelivery'])

    def test_frozen_contract_authority_and_source_changes_refused(self):
        baseline = analysis.load_contract()
        mutant = deepcopy(baseline)
        mutant['authority']['firmwareReady'] = True
        with self.assertRaisesRegex(ValueError, 'ExactSourceContractRequired'):
            analysis.validate_contract(mutant)
        mutant = deepcopy(baseline)
        source = min(mutant['sources'])
        mutant['sources'][source] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
            analysis.validate_contract(mutant)

    def test_reference_does_not_import_models_or_emit_diagnostics(self):
        modules = (reference_oracle, analysis)
        for module in modules:
            tree = ast.parse(Path(module.__file__).read_bytes())
            self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                                 and node.func.id == 'print' for node in ast.walk(tree)))
            if module is reference_oracle:
                self.assertFalse(any(isinstance(node, ast.ImportFrom)
                                     and node.module in ('frames', 'lineage', 'helper', 'analysis')
                                     for node in ast.walk(tree)))
