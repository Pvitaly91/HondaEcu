"""Exact records, full byte arithmetic, and stop-before regressions."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest

from . import analysis, path_reference, reference_oracle
from .checksum import byte_effect
from .corpus import cases, context, snapshot


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.functions = analysis.operations()

    def result(self, identity):
        row = next(item for item in cases() if item['id'] == identity)
        return self.functions[row['operation']](deepcopy(row['input']))

    def test_complete_records_match_independent_oracle(self):
        seen = set()
        for row in cases():
            with self.subTest(case=row['id']):
                self.assertNotIn(row['id'], seen)
                seen.add(row['id'])
                actual = self.functions[row['operation']](deepcopy(row['input']))
                self.assertTrue(analysis.canonical(analysis.record(row, actual)) ==
                                analysis.canonical(analysis.record(row, reference_oracle.expected(row))),
                                'IndependentCanonicalMismatch')
        self.assertTrue(seen)

    def test_full_add_domain_and_all_negated_r6_bytes(self):
        for left in range(256):
            for right in range(256):
                self.assertEqual(byte_effect('Add', left, right), reference_oracle.reference_byte('Add', left, right))
        for right in range(256):
            self.assertEqual(byte_effect('Subtract', 0, right), reference_oracle.reference_byte('Subtract', 0, right))
        self.assertEqual(byte_effect('Add', None, 1), dict(value=None, cf=None, zf=None, hc=None))
        self.assertIsNone(self.result('checksum-0252-1-4')['result'])

    def test_distinct_source_routes_and_hard_boundaries(self):
        literal = self.result('path-r2-selection')
        table = self.result('path-table-read')
        complement = self.result('path-equal-length')
        epilogue = self.result('path-greater-length')
        self.assertEqual([literal['boundary'], table['boundary'], complement['boundary'], epilogue['boundary']],
                         [0x023E, 0x023E, 0x023E, 0x0244])
        self.assertEqual([item['pc'] for item in literal['journal']], [0x023C])
        self.assertEqual([item['pc'] for item in table['journal']], [0x0237, 0x023A, 0x023C])
        self.assertEqual([item['widthBits'] for item in table['journal']], [16, 16, 8])
        self.assertFalse(complement['journal'])
        self.assertFalse(epilogue['journal'])
        for result in (literal, table, complement, epilogue):
            self.assertFalse({0x023E, 0x0244, 0x2995} & {step['pc'] for step in result['steps']})
        for result in (literal, table, complement):
            intent = result['prospectiveStbufIntent']
            self.assertEqual(intent['value'], result['state']['registers']['al'])
            self.assertEqual(intent['address'], 0x0051)
            self.assertIsNone(intent['actualWrite'])
        self.assertIsNone(epilogue['prospectiveStbufIntent'])
        self.assertEqual(complement['state']['registers']['al'], 0xFF)
        self.assertEqual(complement['state']['memory']['03F6'], 1)
        self.assertEqual(table['state']['memory']['03F6'], 0)

    def test_same_value_is_a_fresh_write_and_selected_pointer_alias_is_live(self):
        result = self.result('path-r2-same-value')
        write, = result['journal']
        self.assertIs(write['sameValue'], True)
        self.assertNotEqual(write['afterGeneration'], write['beforeGeneration'][0])
        alias = self.result('path-pointer-alias')
        self.assertEqual(alias['state']['registers']['al'], 0x84)
        self.assertEqual([item['pc'] for item in alias['journal']], [0x0237, 0x023A, 0x023C])
        self.assertNotEqual(alias['journal'][0]['afterGeneration'], alias['journal'][1]['afterGeneration'])
        collision = snapshot(r5=2, r2=0, r6=0x80)
        collision['generations']['03F6'] = 'ConditionalEffect:alternate_response_selector:023C:1'
        result = self.functions['alternate_response_selector']({'snapshot': collision, 'context': context()})
        self.assertEqual(result['boundary'], 0x023C)
        self.assertEqual(result['reason'], 'WriterGenerationCollision')
        self.assertFalse(result['journal'])
        self.assertEqual(result['state']['memory']['03F6'], 0x80)

    def test_unqualified_reads_stop_before_access_without_fabricated_response(self):
        for name in ('sfr-write-only', 'sfr-read-sensitive', 'external-unbound'):
            with self.subTest(case=name):
                result = self.result('path-' + name)
                self.assertEqual(result['boundary'], 0x023B)
                self.assertFalse(any(row['pc'] == 0x023B and row['widthBits'] == 8 for row in result['reads']))
                self.assertFalse(any(row['pc'] == 0x023C for row in result['journal']))
        self.assertEqual(self.result('path-missing-program')['boundary'], 0x0238)
        self.assertEqual(self.result('path-unknown-scb')['boundary'], 0x0237)
        self.assertFalse(self.result('memory-write-only')['allowed'])
        self.assertFalse(self.result('memory-sfr-side-effect')['allowed'])
        self.assertFalse(self.result('memory-wrong-space')['allowed'])
        self.assertIsNone(self.result('address-wrong-width')['dataAddress'])

    def test_unknown_flags_and_detached_entries_never_select_arbitrary_targets(self):
        unknown = self.result('path-unknown-r5')
        self.assertEqual(unknown['boundary'], 0x022B)
        self.assertEqual(unknown['status'], 'IndeterminateBranch')
        self.assertEqual(self.result('aux-unknown-predicate')['boundary'], 0x024F)
        self.assertEqual(self.result('aux-conditional-not-equal')['boundary'], 0x0244)
        self.assertEqual(self.result('aux-r2-entry')['entryQualification'], 'DetachedAuxiliaryEntry')
        self.assertEqual(self.result('path-r2-selection')['entryQualification'], 'DetachedConditionalSourcePath')
        partial = self.result('path-partial-r5')
        self.assertEqual(partial['boundary'], 0x0244)
        self.assertIsNone(partial['state']['registers']['al'])

    def test_composition_retains_frozen_rmw_and_exact_generation(self):
        for name in ('table', 'partial-taken', 'epilogue', 'blocked-read'):
            with self.subTest(case=name):
                result = self.result('composition-' + name)
                self.assertIs(result['handoff']['reseeded'], False)
                self.assertEqual(result['orderedWrites'][0]['event']['pc'], 0x0222)
                self.assertEqual(result['handoff']['clearedStatusGeneration'],
                                 result['alternate']['state']['generations']['0356'])
        for name in ('old-bit-clear', 'mode-clear', 'unknown-bit', 'wrong-bank',
                     'wrong-generation', 'unknown-generation'):
            with self.subTest(case=name):
                result = self.result('composition-' + name)
                self.assertIsNone(result['handoff'])
                self.assertIsNone(result['alternate'])
        self.assertEqual(self.result('composition-unknown-bit')['boundary'], 0x0225)
        clear = self.result('composition-old-bit-clear')
        self.assertIs(clear['prefix']['journal'][0]['sameValue'], True)

    def test_unproved_entries_and_peripheral_claims_are_refused(self):
        model = self.functions['alternate_response_selector']
        q = {'snapshot': snapshot(), 'context': context()}
        for field in ('entryPc', 'sourceInstruction', 'actualStbufWrite', 'actualTxReady', 'actualTxCompletion',
                      'actualTransmission', 'actualIrqDelivery', 'actualCpuExecutions', 'rawSource'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                model({**q, field: True})
        with self.assertRaises(ValueError):
            self.functions['alternate_auxiliary_024c_0253']({**q, 'entryPc': 0x0244})
        self.assertIsNone(analysis.AUTHORITY['actualStbufWrite'])
        self.assertIsNone(analysis.AUTHORITY['actualTransmission'])
        self.assertIsNone(analysis.AUTHORITY['actualTxReady'])
        self.assertEqual(analysis.AUTHORITY['stbufStopBoundary'], 'STOP_BEFORE_STBUF_2995')

    def test_reviewed_source_inventory_stops_and_frozen_contract(self):
        source = json.loads(Path(analysis.__file__).with_name('source_inventory.json').read_bytes())
        entries = {row['pc']: row for row in source['sites']}
        self.assertEqual(len(entries), 23)
        self.assertEqual(entries['0227']['form'], 'CLR A')
        self.assertEqual(entries['0227']['length'], 1)
        self.assertEqual(entries['022B']['successors'], ['024C', '022D'])
        self.assertEqual(entries['022E']['successors'], ['024F', '0230'])
        self.assertEqual(entries['024F']['successors'], ['0244', '0251'])
        self.assertEqual(entries['023E']['successors'], [])
        self.assertEqual(entries['0244']['successors'], [])
        baseline = analysis.load_contract()
        modified = deepcopy(baseline)
        modified['authority']['firmwareReady'] = True
        with self.assertRaisesRegex(ValueError, 'ExactSourceContractRequired'):
            analysis.validate_contract(modified)
        modified = deepcopy(baseline)
        modified['sources'][min(modified['sources'])] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
            analysis.validate_contract(modified)

    def test_oracle_does_not_import_new_models(self):
        for module in (path_reference, reference_oracle):
            for node in ast.walk(ast.parse(Path(module.__file__).read_bytes())):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, ('path', 'addressing', 'checksum', 'analysis', 'composition'))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, 'print')
