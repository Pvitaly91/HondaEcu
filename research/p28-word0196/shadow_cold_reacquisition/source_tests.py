"""Independent canonical, ordering, frame and blocked-authority controls."""
import unittest

from . import corpus, reference_oracle
from .adc_generation_timeline import cold_adc_generation_timeline, data03d1_reaching_definitions
from .analysis import OPERATIONS, canonical, record, validate_authority
from .helper_5cd9 import helper_5cd9, rt5cf9_obligations
from .wire import AUTHORITY


def _iteration(identity, index, previous=None):
    return {'kind': 'Acquisition', 'iterationId': identity, 'p2': index << 5,
            'adcr1h': 0x33, 'adcr0h': 0x74, 'adcr1Generation': identity + '.a1',
            'adcr0Generation': identity + '.a0', 'fromIteration': previous,
            'repeatBranch': None if previous is None else True, 'return276d': None if previous is None else True,
            'prefixEstablished': True}


def _timeline(*events, cb=None, d1=None):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': 'M2cyIndexedTimelineV1',
            'initial': {name: {'value': None, 'generation': None, 'iterationId': None} for name in ('03CB', '03D1')},
            'events': list(events), 'requested': {'03CB': cb, '03D1': d1}, 'claim': 'ConditionalOnly',
            'premises': dict.fromkeys(('noInterference', 'loopExit', 'indexedReturn', 'helperEntry'), True)}


class SourceEquivalenceTests(unittest.TestCase):
    def test_full_canonical_stream_matches_independent_reference(self):
        seen, operations = set(), set()
        for case in corpus.cases():
            identity = case['id']
            self.assertNotIn(identity, seen)
            seen.add(identity)
            operations.add(case['operation'])
            with self.subTest(case=identity):
                self.assertTrue(canonical(record(case)) == canonical(reference_oracle.record(case)),
                                'CompleteCanonicalMismatch')
        self.assertEqual(operations, set(OPERATIONS))

    def test_index_three_and_five_cannot_own_both_slots_in_one_iteration(self):
        for index in range(8):
            with self.subTest(index=index):
                output = cold_adc_generation_timeline(_timeline(_iteration('One', index)))
                self.assertEqual(output['status'], 'CompleteConditional')
                self.assertEqual([row['address'] for row in output['orderedWrites']], [0x03CE + index, 0x03C6 + index])
                owners = output['state']['lastSlots']
                self.assertEqual(owners['03CB']['iterationId'], 'One' if index == 5 else None)
                self.assertEqual(owners['03D1']['iterationId'], 'One' if index == 3 else None)

    def test_distinct_repeated_iterations_and_same_value_overwrite(self):
        one, two = _iteration('One', 5), _iteration('Two', 3, 'One')
        output = cold_adc_generation_timeline(_timeline(one, two, cb='One.a0', d1='Two.a1'))
        self.assertIs(output['state']['mixedIterationSource'], True)
        self.assertEqual(output['state']['requestedRetention'], {'03CB': True, '03D1': True})
        stale = cold_adc_generation_timeline(_timeline(one, two, _iteration('Three', 5, 'Two'), cb='One.a0'))
        self.assertEqual(stale['reason'], 'RequestedGenerationNotCurrent')
        self.assertIs(stale['orderedWrites'][-1]['trackedChanges']['03CB']['sameValue'], True)
        self.assertIsNone(stale['state']['requestedRetention']['03CB'])
        withheld = cold_adc_generation_timeline(_timeline(one, {**two, 'return276d': None}))
        self.assertEqual(withheld['reason'], 'MissingIndexedReturnOrRepeatProof')
        self.assertEqual(len(withheld['orderedWrites']), 2)

    def test_usp_and_aligned_frame_aliases_update_the_correct_byte(self):
        start = _iteration('Start', 5)
        usp = {'kind': 'Usp27B2', 'usp': 0x0419, 'uspGeneration': 'UspNow', 'dd': 0, 'value': 0x72,
               'generation': 'UspWrite', 'pathEstablished': True}
        overwrite = cold_adc_generation_timeline(_timeline(start, usp, cb='Start.a0'))
        self.assertEqual(overwrite['orderedWrites'][-1]['address'], 0x03CB)
        self.assertEqual(overwrite['state']['lastSlots']['03CB']['generation'], 'UspWrite')
        unknown = cold_adc_generation_timeline(_timeline(start, {**usp, 'usp': None}, cb='Start.a0'))
        self.assertEqual(unknown['reason'], 'Usp27b2AddressOrDescriptorUnbound')
        self.assertIsNone(unknown['state']['requestedRetention']['03CB'])
        frame = {'kind': 'Frame', 'callerPc': 0x2777, 'ssp': 0x03CB, 'generation': 'LaterFrame',
                 'pathEstablished': True}
        overlapped = cold_adc_generation_timeline(_timeline(start, frame, cb='Start.a0'))
        self.assertEqual(overlapped['orderedWrites'][-1]['address'], 0x03CA)
        self.assertEqual(overlapped['state']['lastSlots']['03CB']['value'], 0x27)

    def test_helper_read_needs_current_index_three_generation_and_return(self):
        query = _timeline(_iteration('D1', 3), d1='D1.a1')
        admitted = data03d1_reaching_definitions(query)
        self.assertEqual(admitted['reason'], 'ConditionalIndexedGenerationAt5cdc')
        self.assertEqual([row['pc'] for row in admitted['reads']], [0x5CDC])
        query['premises']['indexedReturn'] = None
        withheld = data03d1_reaching_definitions(query)
        self.assertEqual(withheld['reason'], 'HelperEntryOrIndexedReturnUnestablished')
        self.assertFalse(withheld['reads'])

    def test_runtime_promotion_is_rejected_in_nested_records(self):
        for field in ('actualCallExecution', 'actualFramePop', 'actualIeWrite', 'actualIrqDelivery',
                      'actualPeripheralWrite', 'actualBufferWrite', 'actualCpuExecutions', 'firmwareReady'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'UnadmittedExecutionAuthority'):
                validate_authority({'wrapped': {'deeper': [{**AUTHORITY, field: 1}]}})

    def test_c8_disagreement_retains_prefix_without_fault_or_return(self):
        fault = helper_5cd9(corpus.helper_query())
        self.assertEqual(fault['stopBoundary'], 'STOP_BEFORE_BRK_5CF8')
        self.assertEqual([event['address'] for event in fault['orderedWrites']], [0x0084, 0x00AF, 0x00F7, 0x00F5])
        self.assertEqual(fault['state']['counterF7']['value'], 0)
        self.assertIsNone(fault['actualReturnExecution'])
        contested = helper_5cd9(corpus.helper_query(adcr1h=0xB6))
        self.assertEqual(contested['stopBoundary'], 'STOP_BEFORE_JGT_5CDF')
        self.assertIsNone(contested['branchOutcome'][0]['taken'])
        self.assertEqual([event['address'] for event in contested['orderedWrites']], [0x0084])

    def test_fault_boundary_cannot_satisfy_ordinary_helper_frame(self):
        query = corpus.helper_frame_query()
        good = rt5cf9_obligations(query)
        self.assertEqual(good['state']['formalReturnedPc'], 0x277A)
        fault = rt5cf9_obligations({**query, 'helperBoundary': 0x5CF8})
        self.assertEqual(fault['reason'], 'FaultBoundaryIsNotNormalReturn')
        self.assertIsNone(fault['state']['formalReturnedPc'])
        self.assertIsNone(fault['actualFramePop'])
