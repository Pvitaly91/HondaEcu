"""Verify the full output and isolate authority and frame regression controls."""
import json
from pathlib import Path
import unittest

from enclosing_caller_return.indexed_caller import indexed_acquisition_caller

from . import corpus, reference_oracle
from .analysis import OPERATIONS, canonical, record, validate_authority
from .return_obligations import indexed_return_obligations
from .suffix import indexed_suffix_post_ie
from .wire import AUTHORITY


class SourceEquivalenceTests(unittest.TestCase):
    def test_suffix_inventory_extents_and_boundaries(self):
        nodes = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())['nodes']
        self.assertEqual([(int(row['pc'], 16), row['lengthBytes']) for row in nodes], [
            (0x5CB7, 2), (0x5CB9, 2), (0x5CBB, 3), (0x5CBE, 4), (0x5CC2, 4),
            (0x5CC6, 3), (0x5CC9, 2), (0x5CCB, 2), (0x5CCD, 1),
        ])
        for left, right in zip(nodes[:-1], nodes[1:], strict=True):
            self.assertEqual(left['next'], right['pc'])
            self.assertEqual(int(left['pc'], 16) + left['lengthBytes'], int(right['pc'], 16))

    def test_every_canonical_record_matches_independent_reference(self):
        seen, operations = set(), set()
        for case in corpus.cases():
            identity = case['id']
            self.assertNotIn(identity, seen)
            seen.add(identity)
            operations.add(case['operation'])
            with self.subTest(case=identity):
                observed = record(case)
                expected = reference_oracle.record(case)
                self.assertTrue(canonical(observed) == canonical(expected), 'CompleteCanonicalMismatch')
        self.assertEqual(operations, set(OPERATIONS))

    def test_composition_retains_the_frozen_prefix_and_stops_before_ie(self):
        admitted = 0
        for case in corpus.cases():
            if case['operation'] != 'indexed_suffix_composition':
                continue
            query = case['input']
            prefix = indexed_acquisition_caller(query['prefixQuery'])
            output = record(case)['output']
            self.assertTrue(canonical(output['frozenPrefixResult']) == canonical(prefix))
            self.assertIs(output['postIeComposed'], False)
            self.assertIsNone(output['actualIeWrite'])
            pre = output['preIeResult']
            if pre is not None and pre['stopBoundary'] == 'STOP_BEFORE_IE_WRITE_5CB9':
                admitted += 1
                self.assertTrue(canonical(prefix['state']['generations']) == canonical(pre['state']['generations']))
                self.assertTrue(canonical(prefix['journal']) == canonical(output['orderedWrites']))
        self.assertGreater(admitted, 0)

    def test_return_candidates_require_separate_frames_and_no_generation_reuse(self):
        passing = {}
        for case in corpus.cases():
            if case['operation'] != 'indexed_return_obligations':
                continue
            query = case['input']
            output = indexed_return_obligations(query)
            self.assertIsNone(output['actualReturnExecution'])
            self.assertIsNone(output['actualFramePop'])
            self.assertEqual(output['orderedWrites'], [])
            self.assertEqual(output['reads'], [])
            if output['status'] == 'CompleteConditional':
                passing[output['state']['callerPc']] = output['state']['formalReturnedPc']
                stale = indexed_return_obligations({**query, 'expectedFrameGeneration': 'DifferentFrame'})
                self.assertEqual(stale['reason'], 'StaleFrameGeneration')
                self.assertIsNone(stale['state']['formalReturnedPc'])
        self.assertEqual(passing, {0x276A: 0x276D, 0x2B64: 0x2B67})

    def test_promoted_hardware_claims_fail_even_in_nested_children(self):
        for field in ('actualCpuExecutions', 'cpuInstructionRetirements', 'actualIeWrite', 'actualIrqDelivery',
                      'actualHardwareObservation', 'actualReturnExecution', 'actualFramePop',
                      'actualBufferWrite', 'actualTransmission', 'actualPeripheralWrite', 'firmwareReady'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'UnadmittedExecutionAuthority'):
                validate_authority({'state': [{'nested': {**AUTHORITY, field: 1}}]})

    def test_disconnected_suffix_keeps_same_value_store_and_no_ie_write(self):
        query = corpus.post_query(p2=0xE0, tm2=0x6733)
        output = indexed_suffix_post_ie(query)
        self.assertEqual(output['stopBoundary'], 'STOP_BEFORE_RT_5CCD')
        self.assertEqual([row['pc'] for row in output['orderedWrites']], [0x5CBB, 0x5CBE, 0x5CC2, 0x5CC6])
        intent, store = output['orderedWrites'][1:3]
        self.assertEqual((intent['kind'], intent['value']), ('P2WriteIntent', 0))
        self.assertIsNone(intent['actualHardwareObservation'])
        self.assertEqual((store['address'], store['widthBits']), (0x025A, 16))
        self.assertIs(store['sameValue'], True)
        self.assertNotEqual(store['generation'], store['priorGeneration'])
        self.assertIsNone(output['ieIntent']['actualPeripheralWrite'])
        self.assertIsNone(output['state']['registers']['cf'])
        self.assertIsNone(output['state']['registers']['hc'])
        no_tm2 = indexed_suffix_post_ie({**query, 'tm2': None})
        self.assertFalse(any(event['pc'] >= 0x5CC2 for event in no_tm2['orderedWrites']))
        before_ie = indexed_suffix_post_ie({**query, 'secondIeBoundary': None})
        self.assertEqual(before_ie['stopBoundary'], 'STOP_BEFORE_IE_WRITE_5CCB')
        self.assertTrue(canonical(before_ie['orderedWrites']) == canonical(output['orderedWrites']))

    def test_no_record_produces_an_actual_effect_or_reaches_blocked_data(self):
        for case in corpus.cases():
            observed = record(case)
            self.assertEqual(observed['executionAuthority'], AUTHORITY)
            for event in observed['reads'] + observed['orderedWrites']:
                self.assertNotIn(event.get('address'), (0x4700, '4700', 'DATA4700'))
                self.assertNotEqual(event.get('pc'), 0x2995)
