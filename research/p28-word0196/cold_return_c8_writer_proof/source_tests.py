"""Check canonical equivalence, source boundaries and authority refusals."""
import unittest

from indexed_suffix_ie_provenance.corpus import return_query
from shadow_cold_reacquisition.corpus import helper_frame_query, helper_query

from . import corpus, reference_oracle
from .analysis import OPERATIONS, canonical, record, validate_authority
from .c8_helper import c8_branch_consensus, helper_5cd9_extended
from .cold_source_join import cold_caller_mode_source_join, cold_return_path_obligations
from .competing_writers import data03cb_competing_writer_exclusion, usp27b2_alias_proof
from .wire import AUTHORITY


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

    def test_c8_unsigned_domain_cannot_have_consensus_fallthrough(self):
        for pc, fallthrough in ((0x5CDF, 0x5CE1), (0x5CE7, 0x5CE9)):
            for cf, zf, expected in ((0, 0, 'ConsensusTaken'), (0, 1, 'Disagreement'), (1, 0, 'Disagreement')):
                query = {'inputClass': 'SyntheticTestInput', 'pc': pc, 'target': 0x5CED, 'fallthrough': fallthrough,
                         'conditionCode': 0xC8, 'authority': 'OKI_MSM66201_3_66_3_67', 'cf': cf, 'zf': zf,
                         'producer': 'UnsignedByteCompare'}
                with self.subTest(pc=pc, cf=cf, zf=zf):
                    result = c8_branch_consensus(query)
                    self.assertEqual(result['classification'], expected)
                    if expected == 'Disagreement':
                        self.assertIsNone(result['branchOutcome'][0]['next'])
            impossible = c8_branch_consensus({**query, 'cf': 1, 'zf': 1})
            self.assertEqual(impossible['reason'], 'UnsignedCompareFlagPairImpossible')
            raw = c8_branch_consensus({**query, 'cf': 1, 'zf': 1, 'producer': 'ExplicitFlags'})
            self.assertEqual(raw['classification'], 'ConsensusNotTaken')

    def test_detached_normal_frontier_never_joins_full_entry(self):
        query = helper_query(adcr1h=0xB6)
        query['thresholds'].update({'5CDD': 0xB6, '5CE1': 0xB6})
        full = helper_5cd9_extended({'entry': 'Full', 'detachedHandoff': None, 'helperQuery': query})
        self.assertEqual(full['stopBoundary'], 'STOP_BEFORE_JGT_5CDF')
        separate = helper_5cd9_extended({'entry': 'Detached5CE1', 'detachedHandoff': True, 'helperQuery': query})
        self.assertEqual(separate['stopBoundary'], 'STOP_BEFORE_RT_5CF9')
        self.assertIs(separate['detachedNormalFrontier'], True)
        self.assertIs(separate['connectedNormalFrontier'], False)
        self.assertIsNone(separate['actualReturnExecution'])

    def test_frame_reuse_and_unbalanced_intercall_pointer_are_refused(self):
        indexed, helper = return_query(), helper_frame_query()
        indexed['expectedFrameGeneration'] = 'FirstFrame'
        indexed['frameQuery']['frame']['generation'] = 'FirstFrame'
        helper['expectedFrameGeneration'] = 'SecondFrame'
        helper['frameQuery']['frame']['generation'] = 'SecondFrame'
        query = {'inputClass': 'SyntheticTestInput', 'indexedFrame': indexed, 'helperFrame': helper,
                 'indexedIeBoundary': True, 'helperNormalBoundary': True, 'stackContinuity': True,
                 'claim': 'ConditionalOnly'}
        result = cold_return_path_obligations(query)
        self.assertEqual(result['state']['formalIndexedPc'], 0x276D)
        self.assertEqual(result['state']['formalHelperPc'], 0x277A)
        self.assertIsNone(result['actualFramePop'])
        helper['expectedFrameGeneration'] = 'FirstFrame'
        helper['frameQuery']['frame']['generation'] = 'FirstFrame'
        reused = cold_return_path_obligations(query)
        self.assertEqual(reused['reason'], 'ColdFrameGenerationReused')
        self.assertIsNone(reused['state']['formalHelperPc'])
        mismatch = cold_return_path_obligations({**query, 'helperFrame': helper_frame_query(ssp=0x0460)})
        self.assertEqual(mismatch['reason'], 'IntercallStackPointerMismatch')
        self.assertIsNone(mismatch['state']['formalHelperPc'])

    def test_cold_join_preserves_unmodified_counter_and_off_page_state(self):
        query = corpus.source_join_query()
        query['helperArgs']['thresholds']['5CDD'] = query['coldQuery']['prefixQuery']['snapshot']['memory']['03D1']
        output = cold_caller_mode_source_join(query)
        self.assertEqual(output['stopBoundary'], 'STOP_BEFORE_JGT_5CDF')
        previous = output['frozenColdResult']['state']
        self.assertTrue(output['state']['offPage'] == previous['offPage'])
        self.assertTrue(output['state']['counterF7'] == previous['counterF7'])
        self.assertEqual(output['generations']['00F7'], previous['counterF7']['generation'])
        self.assertFalse(output['modeConsumerReached'])

    def test_usp_alias_is_qualified_separately_from_numeric_candidate(self):
        qualified = usp27b2_alias_proof(corpus.usp_query())
        self.assertEqual(qualified['state']['qualifiedAddress'], 0x03CB)
        self.assertIs(qualified['state']['overlap03cb'], True)
        self.assertEqual(qualified['orderedWrites'][0]['widthBits'], 8)
        stale = corpus.usp_query()
        stale['currentUsp']['generation'] = 'DifferentUsp'
        unqualified = usp27b2_alias_proof(stale)
        self.assertEqual(unqualified['state']['numericAddressCandidate'], 0x03CB)
        self.assertIsNone(unqualified['state']['qualifiedAddress'])
        self.assertFalse(unqualified['orderedWrites'])

    def test_equal_repeat_and_aligned_frame_both_replace_generation(self):
        disjoint = data03cb_competing_writer_exclusion(corpus.writer_query([corpus.indexed_event(index=3)]))
        self.assertEqual(disjoint['state']['retention'], 'ConditionalGenerationRetained')
        equal = data03cb_competing_writer_exclusion(corpus.writer_query([corpus.indexed_event(index=5)]))
        self.assertEqual(equal['state']['retention'], 'CompetingWriterPresent')
        self.assertTrue(equal['orderedWrites'][0]['sameValue'])
        self.assertNotEqual(equal['generations']['candidate'], equal['generations']['lastEstablished'])
        frame = data03cb_competing_writer_exclusion(corpus.writer_query([corpus.frame_event()]))
        self.assertEqual(frame['orderedWrites'][0]['address'], 0x03CA)
        self.assertEqual(frame['state']['lastEstablishedSlot']['value'], 0x27)
        self.assertIsNone(frame['generations']['retained'])

    def test_blocked_execution_promotion_is_rejected_inside_nested_results(self):
        for field in ('actualCallExecution', 'actualFramePop', 'actualIeWrite', 'actualIrqDelivery',
                      'actualPeripheralWrite', 'actualBufferWrite', 'actualCpuExecutions', 'firmwareReady'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'UnadmittedExecutionAuthority'):
                validate_authority({'wrapped': {'deeper': [{**AUTHORITY, field: 1}]}})
