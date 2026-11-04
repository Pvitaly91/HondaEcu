"""Source-qualified independent expectations for conditional M2co transforms.

No target CPU, PROGRAM fetch, receive event, IRQ or native execution is invoked.
The author froze these expectations before importing the implementation under
test. Complete canonical equality checks all fields, not only final byte values.
"""
from copy import deepcopy
import hashlib
import unittest

from conditional_flag_mode_shadow.reference_oracle import flag_path as prior_flag_path
from . import reference_oracle as oracle
from .checksum import checksum_body
from .corpus import RETAINED, cases, fixture, request
from .dataflow import compose
from .dispatch import dispatch, parser_step
from .header import header_body
from .length import length_body

OPERATIONS = {'header_body': header_body, 'length_body': length_body,
              'checksum_body': checksum_body, 'dispatch': dispatch,
              'parser_step': parser_step, 'compose': compose}
EXPECTED_COUNT = 2034
EXPECTED_SHA256 = '03efc06ca74a5900fb09180789e34f62fe1eee54d8c29e6cf6ed2dc9110f513e'
EXPECTED_BYTES = 41225964


def pcs(output):
    return [event['pc'] for event in output['journal']]


def read_addresses(output):
    return [event['address'] for event in output['reads']]


class SourceTests(unittest.TestCase):
    def assertIndependent(self, operation, value):
        before = deepcopy(value)
        actual = OPERATIONS[operation](value)
        self.assertEqual(value, before)
        self.assertEqual(actual, oracle.OPERATIONS[operation](before))
        return actual

    def test_full_canonical_records_equal_frozen_independent_stream(self):
        digest, total, count = hashlib.sha256(), 0, 0
        for case in cases():
            with self.subTest(case=case['id']):
                record = {'caseId': case['id'], 'operation': case['operation'],
                          'input': deepcopy(case['input']),
                          'output': self.assertIndependent(case['operation'], case['input'])}
                encoded = oracle.canonical(record)
                digest.update(encoded)
                total += len(encoded)
                count += 1
        self.assertEqual(count, EXPECTED_COUNT)
        self.assertEqual(total, EXPECTED_BYTES)
        self.assertEqual(digest.hexdigest(), EXPECTED_SHA256)

    def test_header_copies_old_header_before_new_input(self):
        value = fixture('Header')
        out = self.assertIndependent('header_body', value)
        self.assertEqual(out['state']['memory']['03F0'], 0x77)
        self.assertEqual(out['state']['memory']['03F1'], 0x21)
        self.assertEqual(pcs(out), [0x275, 0x279, 0x27A, 0x27B, 0x270])
        self.assertEqual(read_addresses(out)[:2], [0x3F1, 0x55])

    def test_header_seed_counter_and_sum_are_distinct_byte_writes(self):
        out = self.assertIndependent('header_body', fixture('Header'))
        self.assertEqual([event['address'] for event in out['journal']], [0x3F0, 0x3F1, 0x3F6, 0x3F5, 0x3F7])
        self.assertTrue(all(event['widthBits'] == 8 for event in out['journal']))
        self.assertEqual(out['state']['memory']['03F5'], 1)
        self.assertEqual(out['state']['memory']['03F7'], 2)

    def test_header_preserves_adjacent_length_flag_and_other_state(self):
        value = fixture('Header')
        out = self.assertIndependent('header_body', value)
        for address in ('03F2', '03F3', '03F4', '00F8'):
            self.assertEqual(out['state']['memory'][address], value['memory'][address])
            self.assertEqual(out['state']['generations'][address], value['generations'][address])

    def test_header_mov_is_dd_independent(self):
        for dd in (0, 1, None):
            value = fixture('Header')
            value['registers']['dd'] = dd
            out = self.assertIndependent('header_body', value)
            self.assertEqual(out['steps'][0]['afterRegisters']['dd'], dd)
            self.assertEqual(out['state']['registers']['dd'], 0)

    def test_header_preserves_ah_cf_hc(self):
        value = fixture('Header')
        value['registers'].update(ah=0xC7, cf=1, hc=1)
        out = self.assertIndependent('header_body', value)
        self.assertEqual({key: out['state']['registers'][key] for key in ('ah', 'cf', 'hc')}, {'ah': 0xC7, 'cf': 1, 'hc': 1})

    def test_header_zero_byte_sets_zf_but_not_r7_zero(self):
        value = fixture('Header')
        value['memory']['0055'] = 0
        out = self.assertIndependent('header_body', value)
        self.assertEqual(out['state']['registers']['zf'], 1)
        self.assertEqual(out['state']['memory']['03F7'], 2)

    def test_header_same_value_store_is_retained(self):
        value = fixture('Header')
        value['memory']['03F0'] = value['memory']['03F1']
        out = self.assertIndependent('header_body', value)
        self.assertTrue(out['journal'][0]['sameValue'])
        self.assertNotEqual(out['journal'][0]['beforeGeneration'][0], out['journal'][0]['afterGeneration'])

    def test_header_unknown_old_header_is_not_zero_seeded(self):
        value = fixture('Header')
        value['memory']['03F1'] = None
        out = self.assertIndependent('header_body', value)
        self.assertIsNone(out['state']['memory']['03F0'])
        self.assertIsNone(out['journal'][0]['sameValue'])

    def test_header_unknown_input_preserves_known_counter(self):
        value = fixture('Header')
        value['memory']['0055'] = None
        out = self.assertIndependent('header_body', value)
        self.assertIsNone(out['state']['memory']['03F1'])
        self.assertIsNone(out['state']['memory']['03F6'])
        self.assertEqual(out['state']['memory']['03F5'], 1)

    def test_header_unqualified_lb_keeps_prior_mov_prefix(self):
        value = fixture('Header')
        value['assumptions']['ordinaryByteSemantics'] = None
        out = self.assertIndependent('header_body', value)
        self.assertEqual(out['boundary'], 0x277)
        self.assertEqual(pcs(out), [0x275])
        self.assertEqual(read_addresses(out), [0x3F1])

    def test_length_uses_sum_destination_without_changing_al(self):
        value = fixture('Length')
        value['memory'].update({'0055': 0x80, '03F6': 0x90})
        out = self.assertIndependent('length_body', value)
        self.assertEqual(out['state']['memory']['03F6'], 0x10)
        self.assertEqual(out['state']['registers']['al'], 0x80)
        self.assertEqual(out['state']['registers']['cf'], 1)

    def test_length_direct_counter_ff_wraps(self):
        value = fixture('Length')
        value['memory']['03F5'] = 0xFF
        out = self.assertIndependent('length_body', value)
        self.assertEqual(out['state']['memory']['03F5'], 0)
        self.assertEqual(out['state']['registers']['zf'], 1)
        self.assertEqual(out['state']['registers']['hc'], 1)

    def test_length_increment_overwrites_add_zf_and_hc(self):
        value = fixture('Length')
        value['memory'].update({'0055': 1, '03F6': 255, '03F5': 1})
        out = self.assertIndependent('length_body', value)
        self.assertEqual(out['state']['registers']['cf'], 1)
        self.assertEqual(out['state']['registers']['zf'], 0)
        self.assertEqual(out['state']['registers']['hc'], 0)

    def test_length_increment_preserves_add_carry(self):
        for prior, byte in ((0, 0), (255, 1)):
            value = fixture('Length')
            value['memory'].update({'0055': byte, '03F6': prior, '03F5': 15})
            out = self.assertIndependent('length_body', value)
            self.assertEqual(out['state']['registers']['cf'], int(prior + byte > 255))
            self.assertEqual(out['state']['registers']['hc'], 1)

    def test_length_byte_store_does_not_overwrite_flag_neighbor(self):
        value = fixture('Length')
        value['memory']['03F3'] = 0xAB
        out = self.assertIndependent('length_body', value)
        self.assertEqual(out['state']['memory']['03F3'], 0xAB)
        self.assertEqual(out['journal'][0]['address'], 0x3F2)
        self.assertEqual(out['journal'][0]['widthBits'], 8)

    def test_length_order_and_same_value_r7_are_not_deduplicated(self):
        out = self.assertIndependent('length_body', fixture('Length'))
        self.assertEqual(pcs(out), [0x281, 0x26D, 0x26F, 0x270])
        self.assertTrue(out['journal'][-1]['sameValue'])

    def test_length_unknown_sum_is_conservative(self):
        value = fixture('Length')
        value['memory']['03F6'] = None
        out = self.assertIndependent('length_body', value)
        self.assertIsNone(out['state']['memory']['03F6'])
        self.assertIsNone(out['state']['registers']['cf'])
        self.assertEqual(out['state']['memory']['03F2'], 4)

    def test_length_unknown_counter_does_not_assume_one(self):
        value = fixture('Length')
        value['memory']['03F5'] = None
        out = self.assertIndependent('length_body', value)
        self.assertIsNone(out['state']['memory']['03F5'])
        self.assertIsNone(out['state']['registers']['zf'])
        self.assertIsNone(out['state']['registers']['hc'])

    def test_length_all_byte_inputs_remain_local_without_range_claim(self):
        for byte in (0, 1, 3, 4, 255):
            value = fixture('Length')
            value['memory']['0055'] = byte
            out = self.assertIndependent('length_body', value)
            self.assertEqual(out['state']['memory']['03F2'], byte)
            self.assertEqual(out['outcome'], 'LengthWritten')

    def test_checksum_modular_zero_acceptance_all_sums(self):
        for prior in range(256):
            value = fixture('Checksum')
            value['memory'].update({'03F6': prior, '0055': (-prior) % 256})
            out = self.assertIndependent('checksum_body', value)
            self.assertEqual(out['outcome'], 'ChecksumAccepted')

    def test_checksum_every_masked_header_class(self):
        for header in range(256):
            value = fixture('Checksum')
            value['memory']['03F1'] = header
            out = self.assertIndependent('checksum_body', value)
            self.assertEqual(out['outcome'], 'ChecksumAccepted' if header & 0xE0 == 0x20 else 'ChecksumRejected')

    def test_checksum_wrong_sum_suppresses_header_and_ready_reads(self):
        value = fixture('Checksum')
        value['memory']['0055'] = 0
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(read_addresses(out), [0x55, 0x3F6])
        self.assertEqual(pcs(out), [0x270])
        self.assertEqual(out['boundary'], 0x272)

    def test_checksum_never_stores_sum_or_counter(self):
        value = fixture('Checksum')
        out = self.assertIndependent('checksum_body', value)
        for address in ('03F6', '03F5'):
            self.assertEqual(out['state']['memory'][address], value['memory'][address])
            self.assertEqual(out['state']['generations'][address], value['generations'][address])

    def test_checksum_success_zf_comes_from_old_ready(self):
        for ready in (0, 1):
            value = fixture('Checksum')
            value['memory']['0356'] = 2 | (ready << 7)
            out = self.assertIndependent('checksum_body', value)
            self.assertEqual(out['state']['registers']['zf'], 1 - ready)
            self.assertEqual(out['journal'][0]['sameValue'], bool(ready))

    def test_checksum_clrb_does_not_force_zf_one(self):
        value = fixture('Checksum')
        value['memory']['0356'] = 0x82
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(out['state']['memory']['03F7'], 0)
        self.assertEqual(out['state']['registers']['zf'], 0)
        self.assertEqual(pcs(out), [0x290, 0x293])

    def test_checksum_preserves_halfcarry_from_add(self):
        value = fixture('Checksum')
        value['memory'].update({'0055': 0xF1, '03F6': 0x0F})
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(out['state']['registers']['hc'], 1)
        self.assertEqual(out['state']['registers']['cf'], 0)
        self.assertEqual(out['state']['registers']['al'], 0x20)

    def test_checksum_rejection_does_not_clear_stale_ready(self):
        value = fixture('Checksum')
        value['memory'].update({'0055': 0, '0356': 0x82})
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(out['state']['memory']['0356'], 0x82)
        self.assertNotIn(0x356, [event['address'] for event in out['journal']])

    def test_checksum_unknown_sum_stops_before_header_read(self):
        value = fixture('Checksum')
        value['memory']['03F6'] = None
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['boundary'], 0x287)
        self.assertEqual(out['journal'], [])
        self.assertNotIn(0x3F1, read_addresses(out))

    def test_checksum_unknown_header_stops_before_ready_write(self):
        value = fixture('Checksum')
        value['memory']['03F1'] = None
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(out['boundary'], 0x28E)
        self.assertEqual(out['journal'], [])

    def test_checksum_unknown_ready_forces_only_ready_bit(self):
        value = fixture('Checksum')
        value['memory']['0356'] = None
        value['knownBits'] = {'0356.1': 1, '0356.6': 0}
        out = self.assertIndependent('checksum_body', value)
        self.assertEqual(out['outcome'], 'ChecksumAccepted')
        self.assertIsNone(out['state']['registers']['zf'])
        self.assertIsNone(out['state']['memory']['0356'])
        self.assertEqual(out['state']['knownBits'], {'0356.1': 1, '0356.6': 0, '0356.7': 1})

    def test_dispatch_zero_r7_short_circuits_other_fields(self):
        value = fixture('Header')
        value['memory'].update({'03F5': None, '03F2': None, '0055': None})
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['outcome'], 'HeaderSelected')
        self.assertEqual(read_addresses(out), [0x3F7])

    def test_dispatch_length_short_circuits_r2(self):
        value = fixture('Length')
        value['memory']['03F2'] = None
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['outcome'], 'LengthSelected')
        self.assertNotIn(0x3F2, read_addresses(out))

    def test_dispatch_increment_wraps_modulo_byte(self):
        value = fixture('Flag')
        value['memory'].update({'03F5': 255, '03F2': 0})
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['outcome'], 'ChecksumSelected')

    def test_dispatch_does_not_consume_input_or_modify_memory(self):
        value = fixture('Flag')
        value['memory']['0055'] = None
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['state']['memory'], value['memory'])
        self.assertEqual(out['journal'], [])
        self.assertNotIn(0x55, read_addresses(out))

    def test_dispatch_unknown_predicate_does_not_choose_role(self):
        value = fixture('Flag')
        value['memory']['03F7'] = None
        out = self.assertIndependent('dispatch', value)
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['boundary'], 0x256)
        self.assertIsNone(out['outcome'])

    def test_parser_mode_zero_stops_at_029d(self):
        value = fixture('Header')
        value['memory']['0356'] = 0
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x29D)
        self.assertEqual(out['journal'], [])

    def test_parser_old_error_is_cleared_but_branch_uses_old_bit(self):
        value = fixture('Header')
        value['memory']['0356'] = 0x42
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x227)
        self.assertEqual(pcs(out), [0x222])
        self.assertEqual(out['state']['memory']['0356'], 2)

    def test_parser_prefix_status_store_is_separate_from_header(self):
        out = self.assertIndependent('parser_step', fixture('Header'))
        self.assertEqual(pcs(out), [0x222, 0x275, 0x279, 0x27A, 0x27B, 0x270])
        self.assertTrue(out['journal'][0]['sameValue'])

    def test_parser_inherited_flag_is_exact_prior_reference(self):
        value = fixture('Flag')
        out = self.assertIndependent('parser_step', value)
        expected = prior_flag_path(value)
        expected['procedure'] = 'parser_step'
        def rename(item):
            if isinstance(item, dict):
                return {key: rename(value) for key, value in item.items()}
            if isinstance(item, list):
                return [rename(value) for value in item]
            return item.replace('ConditionalEffect:flag_path:', 'ConditionalEffect:parser_step:') if isinstance(item, str) else item
        self.assertEqual(out, rename(expected))

    def test_parser_data_frontier_does_not_write_r4(self):
        value = fixture('Flag')
        value['memory'].update({'03F5': 3, '03F2': 5})
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x26C)
        self.assertEqual(pcs(out), [0x222])
        self.assertEqual(out['state']['memory']['03F4'], 0x44)

    def test_parser_unknown_error_keeps_partial_status_prefix(self):
        value = fixture('Header')
        value['memory']['0356'] = None
        value['knownBits'] = {'0356.1': 1}
        out = self.assertIndependent('parser_step', value)
        self.assertEqual(out['boundary'], 0x225)
        self.assertEqual(out['state']['knownBits']['0356.6'], 0)

    def test_compose_four_stages_preserve_writer_lineage(self):
        out = self.assertIndependent('compose', request())
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertEqual([row['role'] for row in out['stages']], ['Header', 'Length', 'Flag', 'Checksum'])
        self.assertEqual(out['finalState']['memory']['03F6'], 0x27)
        self.assertEqual(out['finalState']['memory']['03F7'], 0)
        self.assertEqual(len(out['journal']), 19)

    def test_compose_qualified_three_read_length3_path(self):
        out = self.assertIndependent('compose', request(length=3, roles=['Header', 'Length', 'Checksum']))
        self.assertEqual(out['stages'][-1]['output']['outcome'], 'ChecksumAccepted')
        self.assertEqual(out['finalState']['memory']['03F3'], 2)
        self.assertEqual(len(out['journal']), 14)

    def test_compose_declared_flag_never_forces_length3_branch(self):
        out = self.assertIndependent('compose', request(length=3))
        self.assertEqual(out['reason'], 'DeclaredRoleDoesNotMatchDispatch')
        self.assertEqual(out['boundary'], {'stageId': 'f', 'sourcePC': 0x284})
        self.assertEqual(pcs(out['stages'][-1]['output']), [0x222])

    def test_compose_invalid_length_frontier_preserves_partial_stage(self):
        out = self.assertIndependent('compose', request(length=5))
        self.assertEqual(out['boundary'], {'stageId': 'k', 'sourcePC': 0x262})
        self.assertEqual(out['reason'], 'DeclaredRoleDoesNotMatchDispatch')
        self.assertEqual(len(out['stages']), 4)

    def test_compose_boundary_inputs_are_not_data_writers(self):
        out = self.assertIndependent('compose', request())
        self.assertEqual(len(out['boundaryInputs']), 4)
        self.assertTrue(all(row['address'] == 0x55 for row in out['boundaryInputs']))
        self.assertFalse(any(row['event']['address'] == 0x55 for row in out['journal']))
        self.assertTrue(all(row['classification'] == 'ExplicitSymbolicBoundaryInput_NotPeripheralObservation' for row in out['boundaryInputs']))

    def test_compose_global_and_local_ordinals_are_both_preserved(self):
        out = self.assertIndependent('compose', request())
        self.assertEqual([row['globalOrdinal'] for row in out['journal']], list(range(1, 20)))
        for row in out['stages']:
            self.assertEqual([event['ordinal'] for event in row['output']['journal']], list(range(1, len(row['output']['journal']) + 1)))
            self.assertEqual(row['output']['procedure'], 'parser_step@' + row['id'])

    def test_compose_same_value_other_writer_is_refused(self):
        value = request()
        value['stages'][1]['snapshot']['generations']['03F6'] = 'SameValueOtherWriter'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'PersistentStateOverwritten')
        self.assertEqual(len(out['stages']), 1)

    def test_compose_missing_retained_writer_is_refused(self):
        value = request()
        value['transfers'][0]['retainedGenerations']['03F6'] = None
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'WriterLineageNotEstablished')

    def test_compose_changed_persistent_value_is_refused(self):
        value = request()
        value['stages'][1]['snapshot']['memory']['03F6'] ^= 1
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'PersistentStateOverwritten')

    def test_compose_native_cfg_claim_does_not_authorize_handoff(self):
        value = request()
        value['transfers'][0]['relation'] = 'NativeCfgEdge'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'MissingVerifiedInterBlockRelation')

    def test_compose_wrong_from_to_are_semantic_refusals(self):
        for field in ('from', 'to'):
            value = request()
            value['transfers'][0][field] = 'wrong'
            out = self.assertIndependent('compose', value)
            self.assertEqual(out['reason'], 'MissingVerifiedInterBlockRelation')

    def test_compose_unknown_interference_blocks_unevaluated_stage(self):
        value = request()
        value['transfers'][0]['noInterference'] = None
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'NoInterferencePremiseNotEstablished')
        self.assertEqual(len(out['boundaryInputs']), 1)
        self.assertEqual(out['boundary'], {'stageId': 'l', 'sourcePC': None})

    def test_compose_missing_header_origin(self):
        value = request(roles=['Header'])
        value['stages'][0]['role'] = 'Flag'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'CompositionRequiresHeaderOrigin')
        self.assertEqual(out['journal'], [])

    def test_compose_initial_namespace_collision_is_refused(self):
        value = request()
        value['stages'][0]['snapshot']['generations']['03F3'] = 'ConditionalEffect:parser_step@f:0269:2'
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['reason'], 'GenerationNamespaceCollision')

    def test_compose_later_prior_namespace_is_legitimate(self):
        value = request()
        self.assertTrue(value['stages'][1]['snapshot']['generations']['03F6'].startswith('ConditionalEffect:parser_step@h:'))
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['status'], 'CompleteConditional')

    def test_compose_context_qualifications_are_preserved(self):
        for category in ('class', 'lrb', 'assumptions'):
            value = request()
            if category == 'class':
                value['stages'][1]['snapshot']['inputClass'] = 'SymbolicInput'
            elif category == 'lrb':
                value['stages'][1]['snapshot']['registers']['lrb'] = None
            else:
                value['stages'][1]['snapshot']['assumptions']['ordinaryByteSemantics'] = None
            out = self.assertIndependent('compose', value)
            self.assertEqual(out['reason'], 'IncompatibleHandoffContext')

    def test_compose_separate_incoming_ah_is_not_inferred_rti(self):
        value = request()
        out = self.assertIndependent('compose', value)
        self.assertNotEqual(value['stages'][0]['snapshot']['registers']['ah'], value['stages'][1]['snapshot']['registers']['ah'])
        self.assertEqual(out['stages'][1]['output']['state']['registers']['ah'], value['stages'][1]['snapshot']['registers']['ah'])

    def test_compose_unknown_checksum_keeps_actual_mathematical_prefix(self):
        value = request()
        value['stages'][-1]['snapshot']['memory']['0055'] = None
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['boundary'], {'stageId': 'k', 'sourcePC': 0x287})
        self.assertEqual(pcs(out['stages'][-1]['output']), [0x222])

    def test_compose_first_local_partial_write_is_retained(self):
        value = request()
        value['stages'][0]['snapshot']['assumptions']['ordinaryByteSemantics'] = None
        out = self.assertIndependent('compose', value)
        self.assertEqual(out['boundary'], {'stageId': 'h', 'sourcePC': 0x255})
        self.assertEqual(len(out['stages']), 1)
        self.assertEqual(pcs(out['stages'][0]['output']), [0x222])

    def test_duplicate_stage_id_and_sample_id_are_malformed(self):
        for field in ('id', 'sampleId'):
            value = request()
            value['stages'][1][field] = value['stages'][0][field]
            with self.assertRaises(ValueError):
                compose(value)
            with self.assertRaises(ValueError):
                oracle.compose(value)

    def test_invalid_role_cardinality_and_keys_are_malformed(self):
        for modify in (lambda value: value['stages'][0].update(role='Data'),
                       lambda value: value.update(extra=True),
                       lambda value: value['transfers'][0]['retainedGenerations'].pop('03F6'),
                       lambda value: value['stages'].clear()):
            value = request()
            modify(value)
            with self.assertRaises(ValueError):
                compose(value)
            with self.assertRaises(ValueError):
                oracle.compose(value)

    def test_invalid_boolean_byte_is_never_coerced(self):
        value = fixture('Header')
        value['memory']['0055'] = True
        with self.assertRaises(ValueError):
            header_body(value)

    def test_actual_native_input_class_is_rejected(self):
        value = fixture('Header')
        value['inputClass'] = 'ObservedNative'
        with self.assertRaises(ValueError):
            header_body(value)

    def test_all_outputs_keep_execution_and_firmware_blocked(self):
        for operation, role in (('header_body', 'Header'), ('length_body', 'Length'),
                                ('checksum_body', 'Checksum'), ('dispatch', 'Flag'), ('parser_step', 'Flag')):
            out = self.assertIndependent(operation, fixture(role))
            self.assertIsNone(out['actualHardwareObservation'])
            self.assertEqual(out['cpuInstructionRetirements'], 0)
            self.assertEqual(out['executionStatus'], 'EXECUTION_BLOCKED')
            self.assertFalse(out['firmwareReady'])
        out = self.assertIndependent('compose', request())
        self.assertEqual(out['cpuInstructionRetirements'], 0)
        self.assertFalse(out['firmwareReady'])

    def test_wrong_or_unknown_lrb_refuses_before_effects(self):
        for operation, role in (('header_body', 'Header'), ('length_body', 'Length'), ('checksum_body', 'Checksum')):
            for lrb in (None, 0x0040):
                value = fixture(role)
                value['registers']['lrb'] = lrb
                out = self.assertIndependent(operation, value)
                self.assertEqual(out['reason'], 'UnsupportedContext')
                self.assertEqual(out['journal'], [])


if __name__ == '__main__':
    unittest.main()
