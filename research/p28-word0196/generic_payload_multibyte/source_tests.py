"""Independent source assertions and full-field conditional model comparisons."""
from copy import deepcopy
import hashlib
import unittest

from . import reference_oracle as oracle
from .composition import compose
from .corpus import RETAINED, cases, fixture, sequence
from .counter import counter_route
from .dispatch import dispatch, parser_step
from .payload import data_body, generic_payload_body

OPERATIONS = {'generic_payload_body': generic_payload_body, 'data_body': data_body,
              'dispatch': dispatch, 'parser_step': parser_step,
              'counter_route': counter_route, 'compose': compose}
EXPECTED_COUNT = 2017
EXPECTED_BYTES = 75842754
EXPECTED_SHA256 = '8c6dafbd4fce5f762fdcba42dee7883e26cad3910676c02b9ad9bf3289da9753'


def write_pcs(output):
    return [event['pc'] for event in output['journal']]


def read_addresses(output):
    return [event['address'] for event in output['reads']]


class SourceTests(unittest.TestCase):
    def assertIndependent(self, operation, value):
        original = deepcopy(value)
        actual = OPERATIONS[operation](value)
        self.assertEqual(value, original)
        self.assertEqual(actual, oracle.OPERATIONS[operation](original))
        return actual

    def test_complete_canonical_stream_matches_frozen_independent_bytes(self):
        count, size, digest = 0, 0, hashlib.sha256()
        for case in cases():
            with self.subTest(case=case['id']):
                encoded = oracle.canonical({'caseId': case['id'], 'operation': case['operation'],
                    'input': deepcopy(case['input']), 'output': self.assertIndependent(case['operation'], case['input'])})
                digest.update(encoded)
                size += len(encoded)
                count += 1
        self.assertEqual((count, size, digest.hexdigest()), (EXPECTED_COUNT, EXPECTED_BYTES, EXPECTED_SHA256))

    def test_direct_store_uses_al_without_reading_0055(self):
        value = fixture()
        value['registers']['al'], value['memory']['0055'] = 0xA6, 0x17
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['memory']['03F4'], 0xA6)
        self.assertEqual(read_addresses(out), [0x3F6, 0x3F5])

    def test_direct_store_byte_destination_preserves_flag_and_neighbor(self):
        value = fixture()
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['memory']['03F3'], value['memory']['03F3'])
        self.assertEqual(out['journal'][0]['address'], 0x3F4)
        self.assertEqual(out['journal'][0]['widthBits'], 8)
        self.assertEqual(out['intermediateStates'][0]['state']['memory']['03F5'], value['memory']['03F5'])

    def test_direct_store_rejects_wrong_or_unknown_dd_before_any_effect(self):
        for dd in (1, None):
            value = fixture()
            value['registers']['dd'] = dd
            out = self.assertIndependent('generic_payload_body', value)
            self.assertEqual(out['reason'], 'ByteStoreDdContextNotEstablished')
            self.assertEqual(out['boundary'], 0x26C)
            self.assertEqual(out['reads'], [])
            self.assertEqual(out['journal'], [])
            self.assertEqual(out['state']['registers']['dd'], dd)

    def test_direct_store_does_not_need_lb_premise(self):
        for premise in (False, None):
            value = fixture()
            value['assumptions']['ordinaryByteSemantics'] = premise
            out = self.assertIndependent('generic_payload_body', value)
            self.assertEqual(out['outcome'], 'GenericWritten')

    def test_direct_counter_two_does_not_fabricate_flag_selection(self):
        value = fixture()
        value['memory']['03F5'] = 2
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['outcome'], 'GenericWritten')
        self.assertEqual(write_pcs(out), [0x26C, 0x26D, 0x26F, 0x270])
        self.assertEqual(out['state']['memory']['03F3'], value['memory']['03F3'])

    def test_direct_unknown_counter_keeps_store_and_unknown_increment(self):
        value = fixture()
        value['memory']['03F5'] = None
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['memory']['03F4'], value['registers']['al'])
        self.assertIsNone(out['state']['memory']['03F5'])
        self.assertIsNone(out['state']['registers']['zf'])
        self.assertIsNone(out['state']['registers']['hc'])

    def test_direct_unknown_al_is_not_default_zero(self):
        value = fixture()
        value['registers']['al'] = None
        out = self.assertIndependent('generic_payload_body', value)
        self.assertIsNone(out['state']['memory']['03F4'])
        self.assertIsNone(out['state']['memory']['03F6'])
        self.assertIsNone(out['state']['registers']['cf'])
        self.assertEqual(out['state']['memory']['03F5'], 4)

    def test_join_sum_does_not_change_al_or_ah(self):
        value = fixture()
        value['registers'].update(al=0x80, ah=0xD7)
        value['memory']['03F6'] = 0x90
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['memory']['03F6'], 0x10)
        self.assertEqual(out['state']['registers']['al'], 0x80)
        self.assertEqual(out['state']['registers']['ah'], 0xD7)
        self.assertEqual(out['state']['registers']['cf'], 1)

    def test_join_counter_ff_wrap_is_modulo256(self):
        value = fixture()
        value['memory'].update({'03F5': 255, '03F6': 255})
        value['registers']['al'] = 1
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['memory']['03F5'], 0)
        self.assertEqual(out['state']['registers']['zf'], 1)
        self.assertEqual(out['state']['registers']['hc'], 1)
        self.assertEqual(out['state']['registers']['cf'], 1)

    def test_increment_overwrites_sum_zf_hc_but_retains_cf(self):
        value = fixture()
        value['memory'].update({'03F5': 3, '03F6': 255})
        value['registers']['al'] = 1
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['registers']['cf'], 1)
        self.assertEqual(out['state']['registers']['zf'], 0)
        self.assertEqual(out['state']['registers']['hc'], 0)

    def test_join_counter_low_nibble_halfcarry(self):
        value = fixture()
        value['memory']['03F5'] = 15
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['state']['memory']['03F5'], 16)
        self.assertEqual(out['state']['registers']['hc'], 1)

    def test_same_value_store_sum_and_r7_writes_remain_distinct(self):
        value = fixture()
        value['registers']['al'] = 0
        value['memory']['03F4'] = 0
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(len(out['journal']), 4)
        self.assertTrue(out['journal'][0]['sameValue'])
        self.assertTrue(out['journal'][1]['sameValue'])
        self.assertTrue(out['journal'][-1]['sameValue'])
        self.assertEqual(len({event['afterGeneration'] for event in out['journal']}), 4)

    def test_ordered_byte_effects_are_not_merged(self):
        out = self.assertIndependent('generic_payload_body', fixture())
        self.assertEqual([event['address'] for event in out['journal']], [0x3F4, 0x3F6, 0x3F5, 0x3F7])
        self.assertEqual([event['kind'] for event in out['journal']], ['Store', 'RMW', 'RMW', 'ImmediateStore'])
        self.assertTrue(all(event['widthBits'] == 8 for event in out['journal']))
        self.assertEqual(out['boundary'], 0x272)

    def test_data_counter_two_writes_flag_without_generic_store(self):
        value = fixture()
        value['memory']['03F5'] = 2
        out = self.assertIndependent('data_body', value)
        self.assertEqual(out['outcome'], 'FlagWritten')
        self.assertEqual(write_pcs(out), [0x269, 0x26D, 0x26F, 0x270])
        self.assertEqual(out['state']['memory']['03F4'], value['memory']['03F4'])

    def test_data_non_two_writes_generic_without_flag_store(self):
        for counter in (0, 1, 3, 4, 254, 255):
            value = fixture()
            value['memory']['03F5'] = counter
            out = self.assertIndependent('data_body', value)
            self.assertEqual(out['outcome'], 'GenericWritten')
            self.assertEqual(write_pcs(out)[0], 0x26C)
            self.assertEqual(out['state']['memory']['03F3'], value['memory']['03F3'])

    def test_data_unknown_counter_stops_before_both_stores(self):
        value = fixture()
        value['memory']['03F5'] = None
        out = self.assertIndependent('data_body', value)
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['boundary'], 0x267)
        self.assertEqual(read_addresses(out), [0x55, 0x3F5])
        self.assertEqual(out['journal'], [])

    def test_data_unknown_byte_stays_unknown_through_generic_join(self):
        value = fixture()
        value['memory']['0055'] = None
        out = self.assertIndependent('data_body', value)
        self.assertEqual(out['outcome'], 'GenericWritten')
        self.assertIsNone(out['state']['memory']['03F4'])
        self.assertIsNone(out['state']['memory']['03F6'])
        self.assertEqual(out['state']['memory']['03F5'], 4)

    def test_data_lb_establishes_dd0_from_any_incoming_dd(self):
        for dd in (0, 1, None):
            value = fixture()
            value['registers']['dd'] = dd
            out = self.assertIndependent('data_body', value)
            self.assertEqual(out['state']['registers']['dd'], 0)
            self.assertEqual(out['state']['registers']['ah'], value['registers']['ah'])

    def test_data_lb_premise_is_checked_at_0262(self):
        value = fixture()
        value['assumptions']['ordinaryByteSemantics'] = None
        out = self.assertIndependent('data_body', value)
        self.assertEqual(out['boundary'], 0x262)
        self.assertEqual(out['reads'], [])
        self.assertEqual(out['journal'], [])

    def test_dispatch_data_label_is_not_automatic_flag_store(self):
        value = fixture()
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['outcome'], 'DataSelected')
        self.assertEqual(out['boundary'], 0x262)
        self.assertNotIn(0x55, read_addresses(out))
        self.assertEqual(out['journal'], [])

    def test_dispatch_length_priority_precedes_checksum_equality(self):
        value = fixture()
        value['memory'].update({'03F5': 1, '03F2': 2})
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['outcome'], 'LengthSelected')
        self.assertNotIn(0x3F2, read_addresses(out))

    def test_dispatch_checksum_preempts_flag_at_length3(self):
        value = fixture('Flag')
        value['memory']['03F2'] = 3
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['outcome'], 'ChecksumSelected')
        self.assertNotIn(0x55, read_addresses(out))

    def test_parser_adds_separate_status_store_to_generic(self):
        out = self.assertIndependent('parser_step', fixture())
        self.assertEqual(out['outcome'], 'GenericWritten')
        self.assertEqual(write_pcs(out), [0x222, 0x26C, 0x26D, 0x26F, 0x270])

    def test_parser_mode_zero_keeps_no_writes_and_029d_boundary(self):
        value = fixture()
        value['memory']['0356'] = 0
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x29D)
        self.assertEqual(out['journal'], [])

    def test_parser_old_error_is_cleared_before_outside_branch(self):
        value = fixture()
        value['memory']['0356'] = 0x42
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x227)
        self.assertEqual(write_pcs(out), [0x222])
        self.assertEqual(out['state']['memory']['0356'], 2)

    def test_parser_unknown_length_does_not_consume_payload(self):
        value = fixture()
        value['memory']['03F2'] = None
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x260)
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertNotIn(0x55, read_addresses(out))

    def test_parser_subrole_mismatch_stops_before_selected_store(self):
        for counter, requested, boundary in ((2, 'Generic', 0x269), (3, 'Flag', 0x26C)):
            value = fixture()
            value['memory'].update({'03F5': counter, '03F2': 8})
            actual = parser_step(value, stage_id='x', required_role=requested)
            expected = oracle.parser_step(value, stage_id='x', required_role=requested)
            self.assertEqual(actual, expected)
            self.assertEqual(actual['reason'], 'DeclaredRoleDoesNotMatchDataSelection')
            self.assertEqual(actual['boundary'], boundary)
            self.assertEqual(write_pcs(actual), [0x222])
            self.assertIn(0x55, read_addresses(actual))

    def test_counter_all_lengths_match_independent_first_frontier_formula(self):
        for length in range(256):
            out = self.assertIndependent('counter_route', {'length': length, 'maxDataStages': 512})
            expected = 255 if length == 2 else (length - 3) % 256
            self.assertEqual(out['dataStageCount'], expected)
            self.assertEqual(out['boundary']['counter'], (2 + expected) % 256)
            self.assertEqual(out['checksumReachable'], length != 2)

    def test_counter_short_lengths_have_exact_flag_generic_counts(self):
        for length in range(3, 9):
            out = self.assertIndependent('counter_route', {'length': length, 'maxDataStages': 512})
            self.assertEqual(out['totalStageCount'], length)
            self.assertEqual(out['flagStageCount'], int(length >= 4))
            self.assertEqual(out['genericStageCount'], max(0, length - 4))

    def test_counter_zero_one_and_ff_have_distinct_long_frontiers(self):
        for length, count, total, counter in ((0, 253, 256, 255), (1, 254, 257, 0), (255, 252, 255, 254)):
            out = self.assertIndependent('counter_route', {'length': length, 'maxDataStages': 512})
            self.assertEqual((out['dataStageCount'], out['totalStageCount'], out['boundary']['counter']), (count, total, counter))

    def test_counter_length2_reentry_does_not_append_checksum_or_length_body(self):
        out = self.assertIndependent('counter_route', {'length': 2, 'maxDataStages': 512})
        self.assertEqual(out['outcome'], 'LengthReentrySelected')
        self.assertEqual(out['totalStageCount'], 257)
        self.assertEqual(out['boundary'], {'counter': 1, 'sourcePC': 0x27F})
        self.assertNotIn('Checksum', out['stageOrder'])
        self.assertEqual(out['stageOrder'].count('Length'), 1)

    def test_counter_terminal_predicate_precedes_equal_resource_bound(self):
        for length, bound in ((3, 0), (4, 1), (0, 253), (1, 254), (2, 255)):
            out = self.assertIndependent('counter_route', {'length': length, 'maxDataStages': bound})
            self.assertEqual(out['status'], 'CompleteConditional')

    def test_counter_resource_bound_preserves_only_completed_math_history(self):
        out = self.assertIndependent('counter_route', {'length': 8, 'maxDataStages': 2})
        self.assertEqual(out['status'], 'OutsideVerifiedScope')
        self.assertEqual(out['reason'], 'SyntheticResourceBound_NotProtocolLimit')
        self.assertEqual(out['stageOrder'], ['Header', 'Length', 'Flag', 'Generic'])
        self.assertEqual(out['boundary'], {'counter': 4, 'sourcePC': 0x262})
        self.assertIsNone(out['checksumReachable'])

    def test_counter_unknown_length_does_not_zero_seed_or_generate_history(self):
        out = self.assertIndependent('counter_route', {'length': None, 'maxDataStages': 512})
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['counterHistory'], [])
        self.assertEqual(out['stageOrder'], ['Header', 'Length'])
        self.assertEqual(out['boundary'], {'counter': 2, 'sourcePC': 0x260})

    def test_counter_candidate_slot_is_not_checksum_body_execution(self):
        out = self.assertIndependent('counter_route', {'length': 3, 'maxDataStages': 0})
        self.assertEqual(out['stageOrder'], ['Header', 'Length', 'Checksum'])
        self.assertEqual(out['boundary']['sourcePC'], 0x284)
        self.assertEqual(out['reads'], [])
        self.assertEqual(out['journal'], [])
        self.assertEqual(out['cpuInstructionRetirements'], 0)

    def test_counter_boolean_and_unbounded_inputs_are_rejected(self):
        for value in ({'length': True, 'maxDataStages': 1}, {'length': 256, 'maxDataStages': 1},
                      {'length': 2, 'maxDataStages': True}, {'length': 2, 'maxDataStages': 513},
                      {'length': 2, 'maxDataStages': -1}):
            with self.assertRaises(ValueError):
                counter_route(value)

    def test_compose_short_lengths_keep_exact_stage_order(self):
        for length in range(3, 9):
            out = self.assertIndependent('compose', sequence(length=length))
            roles = [stage['role'] for stage in out['stages']]
            expected = ['Header', 'Length'] + ([] if length == 3 else ['Flag'] + ['Generic'] * (length - 4)) + ['Checksum']
            self.assertEqual(roles, expected)
            self.assertEqual(out['checksumOutcome'], 'ChecksumAccepted')

    def test_compose_multibyte_r4_is_last_generic_without_array_advance(self):
        value = sequence(length=6, data=[2, 0xA5, 0x5A])
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['finalState']['memory']['03F3'], 2)
        self.assertEqual(out['finalState']['memory']['03F4'], 0x5A)
        generic = [row for row in out['journal'] if row['event']['pc'] == 0x26C]
        self.assertEqual([row['event']['address'] for row in generic], [0x3F4, 0x3F4])
        self.assertNotEqual(generic[0]['event']['afterGeneration'], generic[1]['event']['afterGeneration'])

    def test_compose_accumulator_history_includes_every_data_byte_once(self):
        out = self.assertIndependent('compose', sequence(length=6, data=[2, 0xA5, 0x5A]))
        sums = [row['output']['state']['memory']['03F6'] for row in out['stages']]
        self.assertEqual(sums, [0x21, 0x27, 0x29, 0xCE, 0x28, 0x28])
        self.assertEqual(len(out['journal']), 29)

    def test_compose_length1_proves_counter_wrap_only_conditionally(self):
        out = self.assertIndependent('compose', sequence(length=1))
        self.assertEqual(len(out['stages']), 257)
        data = out['stages'][-2]['output']
        self.assertEqual(data['state']['memory']['03F5'], 0)
        self.assertEqual(data['state']['registers']['zf'], 1)
        self.assertEqual(data['state']['registers']['hc'], 1)
        self.assertEqual(out['checksumOutcome'], 'ChecksumAccepted')

    def test_compose_long_length2_reentry_uses_explicit_new_length(self):
        out = self.assertIndependent('compose', sequence(length=2, reentry_length=3))
        self.assertEqual(len(out['stages']), 259)
        self.assertEqual(out['stages'][-2]['role'], 'Length')
        self.assertEqual(out['stages'][-2]['output']['state']['memory']['03F2'], 3)
        self.assertEqual(out['stages'][-2]['output']['state']['memory']['03F5'], 2)
        self.assertEqual(out['checksumOutcome'], 'ChecksumAccepted')
        self.assertEqual(len(out['journal']), 1294)

    def test_compose_missing_checksum_is_complete_prefix_with_explicit_constraint(self):
        value = sequence()
        value['stages'], value['transfers'] = value['stages'][:-1], value['transfers'][:-1]
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertIsNone(out['checksumOutcome'])
        self.assertIn('ChecksumNotReachedWithinRequestedSequence', out['unresolvedConstraints'])

    def test_compose_checksum_rejected_is_not_outside_scope(self):
        out = self.assertIndependent('compose', sequence(checksum=0))
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertEqual(out['checksumOutcome'], 'ChecksumRejected')
        self.assertEqual(out['boundary']['sourcePC'], 0x272)
        self.assertEqual(out['finalState']['memory']['03F7'], 2)

    def test_compose_unknown_generic_byte_reaches_unknown_checksum_prefix(self):
        out = self.assertIndependent('compose', sequence(data=[2, None]))
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['boundary']['sourcePC'], 0x287)
        self.assertIsNone(out['finalState']['memory']['03F4'])
        self.assertIsNone(out['finalState']['memory']['03F6'])

    def test_compose_prefix_inputs_do_not_fabricate_0055_writes_or_receive(self):
        value = sequence(length=6)
        out = self.assertIndependent('compose', value)
        self.assertEqual(len(out['boundaryInputs']), 6)
        self.assertTrue(all(row['address'] == 0x55 for row in out['boundaryInputs']))
        self.assertFalse(any(row['event']['address'] == 0x55 for row in out['journal']))
        self.assertTrue(all(row['classification'] == 'ExplicitSymbolicBoundaryInput_NotPeripheralObservation' for row in out['boundaryInputs']))

    def test_compose_incoming_registers_are_explicit_without_rti_restore(self):
        value = sequence()
        out = self.assertIndependent('compose', value)
        for request, observed in zip(value['stages'], out['stages']):
            self.assertEqual(observed['output']['state']['registers']['ah'], request['snapshot']['registers']['ah'])
        self.assertGreater(len({row['snapshot']['registers']['ah'] for row in value['stages']}), 1)

    def test_compose_boundaries_and_branch_decisions_preserve_every_stage_prefix(self):
        out = self.assertIndependent('compose', sequence())
        self.assertEqual(len(out['stageBoundaries']), len(out['stages']))
        expected = [{'stageId': row['id'], 'pc': step['pc'], 'next': step['next'], 'branchTaken': step['branchTaken']}
                    for row in out['stages'] for step in row['output']['steps'] if step['kind'] == 'Branch']
        self.assertEqual(out['branchDecisions'], expected)

    def test_compose_local_and_global_write_ordinals_are_retained(self):
        out = self.assertIndependent('compose', sequence())
        self.assertEqual([row['globalOrdinal'] for row in out['journal']], list(range(1, 25)))
        for stage in out['stages']:
            self.assertEqual(stage['output']['procedure'], 'parser_step@' + stage['id'])
            local = stage['output']['journal']
            self.assertEqual([event['ordinal'] for event in local], list(range(1, len(local) + 1)))

    def test_compose_unknown_ready_preserves_partial_bits(self):
        value = sequence()
        for stage in value['stages']:
            stage['snapshot']['memory']['0356'] = None
            stage['snapshot']['knownBits'] = {'0356.1': 1, '0356.6': 0}
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['checksumOutcome'], 'ChecksumAccepted')
        self.assertIsNone(out['finalState']['memory']['0356'])
        self.assertEqual(out['finalState']['knownBits']['0356.7'], 1)
        self.assertIsNone(out['finalState']['registers']['zf'])

    def test_compose_same_value_overwritten_generation_is_refused(self):
        value = sequence()
        value['stages'][3]['snapshot']['generations']['03F6'] = 'SameValueOtherWriter'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'PersistentStateOverwritten')
        self.assertEqual(len(out['rejectedTransfers']), 1)
        self.assertEqual(len(out['stages']), 3)

    def test_compose_missing_writer_cannot_be_replaced_by_numeric_value(self):
        value = sequence()
        value['transfers'][2]['retainedGenerations']['03F6'] = None
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'WriterLineageNotEstablished')
        self.assertEqual(out['rejectedTransfers'][0]['transfer'], value['transfers'][2])

    def test_compose_native_reentry_claim_is_not_an_allowed_handoff(self):
        value = sequence()
        value['transfers'][2]['relation'] = 'Native0272To021FReceiveCompletion'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'MissingVerifiedInterBlockRelation')
        self.assertEqual(out['rejectedTransfers'][0]['classification'], 'RefusedConditionalHandoff_NotRuntimeEvent')

    def test_compose_unknown_no_interference_does_not_evaluate_next_stage(self):
        value = sequence()
        value['transfers'][2]['noInterference'] = None
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'NoInterferencePremiseNotEstablished')
        self.assertEqual(len(out['boundaryInputs']), 3)
        self.assertIsNone(out['boundary']['sourcePC'])

    def test_compose_context_change_refuses_handoff(self):
        value = sequence()
        value['stages'][3]['snapshot']['registers']['lrb'] = 0x40
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'IncompatibleHandoffContext')

    def test_compose_premature_checksum_keeps_accepted_transfer_and_local_prefix(self):
        value = sequence(length=6)
        value['stages'][3]['role'] = 'Checksum'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'DeclaredRoleDoesNotMatchDispatch')
        self.assertEqual(out['boundary']['sourcePC'], 0x262)
        self.assertEqual(out['rejectedTransfers'], [])
        self.assertEqual(len(out['transfers']), 3)
        self.assertEqual(write_pcs(out['stages'][-1]['output']), [0x222])

    def test_compose_first_role_and_initial_namespace_fail_without_transfer_events(self):
        for category in ('role', 'namespace'):
            value = sequence()
            if category == 'role':
                value['stages'][0]['role'] = 'Generic'
            else:
                value['stages'][0]['snapshot']['generations']['03F4'] = 'ConditionalEffect:parser_step@p000:026C:2'
            out = self.assertIndependent('compose', value)
            self.assertEqual(out['stages'], [])
            self.assertEqual(out['rejectedTransfers'], [])

    def test_compose_duplicate_ids_and_samples_reject_upfront(self):
        for field in ('id', 'sampleId'):
            value = sequence()
            value['stages'][1][field] = value['stages'][0][field]
            with self.assertRaises(ValueError):
                compose(value)

    def test_compose_synthetic_stage_limit_refuses_513_inputs(self):
        value = sequence()
        stage = value['stages'][0]
        value['stages'] = [{**deepcopy(stage), 'id': 'h' + str(index), 'sampleId': 's' + str(index)} for index in range(513)]
        transfer = value['transfers'][0]
        value['transfers'] = [{**deepcopy(transfer), 'from': 'h' + str(index), 'to': 'h' + str(index + 1)} for index in range(512)]
        with self.assertRaises(ValueError):
            compose(value)

    def test_unsupported_bank_and_absent_interference_refuse_without_writes(self):
        for change in ('bank', 'interference'):
            value = fixture()
            if change == 'bank':
                value['registers']['lrb'] = None
            else:
                value['assumptions']['noInterference'] = None
            out = self.assertIndependent('generic_payload_body', value)
            self.assertEqual(out['journal'], [])
            self.assertEqual(out['status'], 'OutsideVerifiedScope')

    def test_invalid_native_authority_or_boolean_byte_is_not_coerced(self):
        for category in ('authority', 'byte'):
            value = fixture()
            if category == 'authority':
                value['inputClass'] = 'ObservedNative'
            else:
                value['registers']['al'] = True
            with self.assertRaises(ValueError):
                generic_payload_body(value)

    def test_unknown_initial_generation_is_reported_without_fabricated_native_owner(self):
        value = fixture()
        value['generations']['03F4'] = None
        out = self.assertIndependent('generic_payload_body', value)
        self.assertEqual(out['journal'][0]['beforeGeneration'], [None])
        self.assertTrue(out['journal'][0]['afterGeneration'].startswith('ConditionalEffect:'))

    def test_every_new_operation_keeps_zero_execution_and_common_constraints(self):
        for operation, value in (('generic_payload_body', fixture()), ('data_body', fixture()),
                                 ('dispatch', fixture()), ('parser_step', fixture()),
                                 ('counter_route', {'length': 5, 'maxDataStages': 512}), ('compose', sequence())):
            out = self.assertIndependent(operation, value)
            self.assertIsNone(out['actualHardwareObservation'])
            self.assertEqual(out['cpuInstructionRetirements'], 0)
            self.assertEqual(out['executionStatus'], 'EXECUTION_BLOCKED')
            self.assertFalse(out['firmwareReady'])
            self.assertEqual(out['unresolvedConstraints'][:4], list(oracle.COMMON))


if __name__ == '__main__':
    unittest.main()
