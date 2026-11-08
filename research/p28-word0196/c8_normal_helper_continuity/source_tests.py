"""Exercise full source equivalence and distinguish live from dead stack slots."""
import unittest

from cold_return_c8_writer_proof.corpus import return_path_query

from . import corpus, reference_oracle
from .analysis import OPERATIONS, canonical, record, validate_authority
from .frame_graph import cold_frame_generation_chain
from .helper_continuity import c8_source_feasibility, helper_normal_continuation
from .wire import AUTHORITY


def frame_chain(*writes, first_ie=True, second_ie=True):
    return {'inputClass': 'SyntheticTestInput', 'frameQuery': return_path_query(), 'ie5cb9': first_ie,
            'ie5ccb': second_ie, 'writes': list(writes), 'claim': 'ConditionalOnly'}


def store(stage, address, generation='NewStore', width=8):
    return {'stage': stage, 'address': address, 'widthBits': width, 'generation': generation, 'pathEstablished': True}


class SourceTests(unittest.TestCase):
    def test_full_canonical_stream_matches_independent_reference(self):
        seen, operations = set(), set()
        for case in corpus.cases():
            identifier = case['id']
            self.assertNotIn(identifier, seen)
            seen.add(identifier)
            operations.add(case['operation'])
            with self.subTest(case=identifier):
                self.assertTrue(canonical(record(case)) == canonical(reference_oracle.record(case)),
                                'CompleteCanonicalMismatch')
        self.assertEqual(operations, set(OPERATIONS))

    def test_same_slot_write_is_safe_only_between_the_two_frame_lifetimes(self):
        query = frame_chain()
        nested = query['frameQuery']['indexedFrame']['frameQuery']
        address = nested['incomingSsp'] & 0xFFFE
        result = cold_frame_generation_chain(frame_chain(store('BetweenCalls', address + 1, width=16)))
        self.assertEqual(result['state']['formalIndexedPc'], 0x276D)
        self.assertEqual(result['state']['formalHelperPc'], 0x277A)
        self.assertIs(result['state']['sameAlignedAddress'], True)
        self.assertEqual(result['intermediateStates'][0]['alignedAddress'], address)
        self.assertFalse(result['orderedWrites'])
        self.assertIsNone(result['actualFramePop'])
        for stage, blocked in (('IndexedLive', 'STOP_BEFORE_RT_5CCD'), ('HelperLive', 'STOP_BEFORE_RT_5CF9')):
            with self.subTest(stage=stage):
                conflict = cold_frame_generation_chain(frame_chain(store(stage, address + 1)))
                self.assertEqual(conflict['reason'], 'LiveFrameGenerationOverwritten')
                self.assertEqual(conflict['stopBoundary'], blocked)
                self.assertIsNone(conflict['state']['formalHelperPc'])

    def test_independent_ie_gates_and_unknown_competing_write(self):
        first = cold_frame_generation_chain(frame_chain(first_ie=None))
        second = cold_frame_generation_chain(frame_chain(second_ie=False))
        unknown = cold_frame_generation_chain(frame_chain(store('IndexedLive', None)))
        self.assertEqual(first['stopBoundary'], 'STOP_BEFORE_IE_WRITE_5CB9')
        self.assertEqual(second['stopBoundary'], 'STOP_BEFORE_IE_WRITE_5CCB')
        self.assertEqual(unknown['reason'], 'CompetingFrameWriteUnqualified')
        for output in (first, second, unknown):
            self.assertIsNone(output['actualIeWrite'])
            self.assertIsNone(output['state']['formalIndexedPc'])

    def test_mode_proof_is_detached_and_full_entry_never_claims_mode(self):
        detached = connected = 0
        for case in corpus.cases():
            if case['operation'] == 'data03cb_to_60cc_source_proof':
                output = record(case)['output']
                if output['status'] == 'CompleteConditional':
                    detached += 1
                    self.assertEqual(output['stopBoundary'], 'STOP_BEFORE_RT_60E4')
                    self.assertIsNone(output['actualReturnExecution'])
            if case['operation'] == 'cold_normal_mode_source_join':
                connected += 1
                output = record(case)['output']
                self.assertIs(output['connectedModeRead'], False)
                self.assertIsNone(output['nativeModeOwner'])
        self.assertGreater(detached, 0)
        self.assertGreater(connected, 0)

    def test_exact_first_compare_excludes_generic_greater_consensus(self):
        complete = c8_source_feasibility(corpus.c8_feasibility_query())
        printed, comparative = complete['state']['domains']
        self.assertEqual({(row['cf'], row['zf']) for row in printed['rows']}, {(0, 1), (1, 0)})
        self.assertTrue(all(row['taken'] for row in printed['rows']))
        self.assertTrue(all(not row['taken'] for row in comparative['rows']))
        generic_greater = c8_source_feasibility(corpus.c8_feasibility_query(cf=0, zf=0))
        self.assertTrue(all(not row['rows'] for row in generic_greater['state']['domains']))
        self.assertIsNone(complete['state']['nativeBranchTaken'])

    def test_second_detached_jge_preserves_unproved_full_helper_path(self):
        query = corpus.helper_continuation_query()
        normal = helper_normal_continuation(query)
        self.assertEqual(normal['stopBoundary'], 'STOP_BEFORE_RT_5CF9')
        self.assertIs(normal['detachedNormalFrontier'], True)
        self.assertIs(normal['fullNormalFrontier'], False)
        self.assertEqual(normal['candidatePairs'], [{'cf': 0, 'zf': 1}])
        query['helperQuery']['thresholds']['5CE9'] = 0x52
        fault = helper_normal_continuation(query)
        self.assertEqual(fault['stopBoundary'], 'STOP_BEFORE_ERROR_MARKER_5CED')
        self.assertEqual(fault['orderedWrites'], normal['orderedWrites'])
        self.assertIsNone(fault['actualReturnExecution'])

    def test_native_promotion_in_nested_children_is_refused(self):
        for field in ('actualCallExecution', 'actualFramePop', 'actualIeWrite', 'actualIrqDelivery',
                      'actualPeripheralWrite', 'actualBufferWrite', 'actualCpuExecutions', 'firmwareReady'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'UnadmittedExecutionAuthority'):
                validate_authority({'wrapped': {'deeper': [{**AUTHORITY, field: 1}]}})
