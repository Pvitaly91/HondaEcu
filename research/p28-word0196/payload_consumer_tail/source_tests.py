"""Independent source expectations, partial knowledge and authority controls."""
from copy import deepcopy
import hashlib
import unittest

from . import reference_oracle as oracle
from .consumer_model import payload_consumer
from .corpus import ADDRESSES, DP_ADDRESSES, PREMISES, cases, fixture, partial, rti_query, timeline
from .rti_obligations import rti_obligations
from .tail import parser_step_with_tail, post_checksum_tail
from .writer_lineage import last_writer_at_conditional_boundary

OPERATIONS = {'payload_consumer': payload_consumer, 'post_checksum_tail': post_checksum_tail,
    'parser_step_with_tail': parser_step_with_tail,
    'last_writer_at_conditional_boundary': last_writer_at_conditional_boundary, 'rti_obligations': rti_obligations}
EXPECTED_COUNT = 1060
EXPECTED_BYTES = 13926741
EXPECTED_SHA256 = '1ac24eaea5a279d653c8cf5dc39a73c85fefac2885ab5ff9d064a6f09f8d4624'


class SourceTests(unittest.TestCase):
    def assertIndependent(self, operation, value):
        original = deepcopy(value)
        actual = OPERATIONS[operation](value)
        self.assertEqual(value, original)
        self.assertEqual(actual, oracle.OPERATIONS[operation](original))
        return actual

    def test_full_canonical_stream_equals_independent_premodel_freeze(self):
        digest, count, size = hashlib.sha256(), 0, 0
        for case in cases():
            with self.subTest(case=case['id']):
                raw = oracle.canonical({'caseId': case['id'], 'operation': case['operation'],
                    'input': deepcopy(case['input']), 'output': self.assertIndependent(case['operation'], case['input'])})
                digest.update(raw)
                count += 1
                size += len(raw)
        self.assertEqual((count, size, digest.hexdigest()), (EXPECTED_COUNT, EXPECTED_BYTES, EXPECTED_SHA256))

    def test_snapshot_has_all_46_bytes_and_retains_unwritten_storage(self):
        value = fixture()
        out = self.assertIndependent('payload_consumer', value)
        self.assertEqual(len(out['state']['memory']), 46)
        self.assertEqual(set(out['state']['memory']), set(ADDRESSES))
        changed = {'0084', '0085', '03F2'}
        for key in set(ADDRESSES) - changed:
            self.assertEqual(out['state']['memory'][key], value['memory'][key])
            self.assertEqual(out['state']['generations'][key], value['generations'][key])

    def test_consumer_uses_payload_03f4_not_flag_03f3(self):
        value = fixture()
        value['memory'].update({'03F4': 0x80, '03F3': 1})
        out = self.assertIndependent('payload_consumer', value)
        self.assertEqual(out['state']['memory']['03F2'], 0x83)
        self.assertEqual(out['state']['memory']['03F3'], 1)
        self.assertEqual([r['address'] for r in out['reads'] if r['space'] == 'DATA'], [0x3F4])

    def test_consumer_exact_six_source_steps_and_stop_before_2980(self):
        out = self.assertIndependent('payload_consumer', fixture())
        self.assertEqual([row['pc'] for row in out['steps']], [0x28D8, 0x28DB, 0x28DC, 0x28DE, 0x297C, 0x297F])
        self.assertEqual(out['boundary'], 0x2980)
        self.assertEqual(out['steps'][3]['kind'], 'Jump')
        self.assertEqual(out['steps'][3]['next'], 0x297C)

    def test_consumer_has_two_dp_word_writes_and_one_data_byte_store(self):
        out = self.assertIndependent('payload_consumer', fixture())
        self.assertEqual([row['pc'] for row in out['journal']], [0x28D8, 0x297C, 0x297F])
        self.assertEqual([row['widthBits'] for row in out['journal']], [16, 16, 8])
        self.assertEqual([row['kind'] for row in out['journal']], ['PointingRegisterWrite', 'PointingRegisterWrite', 'Store'])
        self.assertEqual([row['after'] for row in out['journal'][:2]], [0x3F4, 0x3F2])

    def test_consumer_address_dependencies_are_separate_from_functional_reads(self):
        out = self.assertIndependent('payload_consumer', fixture())
        self.assertEqual([row['space'] for row in out['reads']], ['ARCHITECTURAL_ADDRESS_DEPENDENCY', 'DATA', 'ARCHITECTURAL_ADDRESS_DEPENDENCY'])
        self.assertEqual([row['accessRole'] for row in out['reads']], ['PointingRegisterAlias', 'FunctionalOperand', 'PointingRegisterAlias'])
        self.assertFalse(any(row['address'] == 0x3F2 and row['space'] == 'DATA' for row in out['reads']))

    def test_consumer_pointer_read_generations_follow_the_two_distinct_writers(self):
        out = self.assertIndependent('payload_consumer', fixture())
        self.assertEqual(out['reads'][0]['generations'], [out['journal'][0]['afterGeneration']] * 2)
        self.assertEqual(out['reads'][2]['generations'], [out['journal'][1]['afterGeneration']] * 2)
        self.assertNotEqual(out['reads'][0]['generations'], out['reads'][2]['generations'])

    def test_consumer_all_eight_scb_banks_are_explicit(self):
        for bank in range(8):
            value = fixture()
            value['registers']['scb'] = bank
            out = self.assertIndependent('payload_consumer', value)
            self.assertEqual(out['journal'][0]['address'], 0x84 + bank * 8)
            self.assertEqual(out['pointerState']['dataAddress'], 0x84 + bank * 8)
            self.assertEqual(out['pointerState']['value'], 0x3F2)

    def test_consumer_bank6_updates_the_shared_b4_b5_alias(self):
        value = fixture()
        value['registers']['scb'] = 6
        partial(value, '00B4', {0: 1})
        out = self.assertIndependent('payload_consumer', value)
        self.assertEqual(out['state']['memory']['00B4'], 0xF2)
        self.assertEqual(out['state']['memory']['00B5'], 3)
        self.assertNotIn('00B4.0', out['state']['knownBits'])
        self.assertEqual(out['state']['generations']['00B4'], out['journal'][1]['afterGeneration'])

    def test_consumer_unknown_scb_refuses_without_defaulting_bank_zero(self):
        value = fixture()
        value['registers']['scb'] = None
        out = self.assertIndependent('payload_consumer', value)
        self.assertEqual(out['reason'], 'PointerBankNotEstablished')
        self.assertEqual(out['journal'], [])
        self.assertEqual(out['reads'], [])
        self.assertIsNone(out['pointerState']['dataAddress'])

    def test_consumer_does_not_require_parser_lrb_context(self):
        for lrb in (None, 0, 0x40, 0xFFFF):
            value = fixture()
            value['registers']['lrb'] = lrb
            out = self.assertIndependent('payload_consumer', value)
            self.assertEqual(out['outcome'], 'PayloadReadAddThreeStored')
            self.assertEqual(out['state']['registers']['lrb'], lrb)

    def test_consumer_mov_retains_incoming_dd_until_lb_establishes_zero(self):
        for dd in (0, 1, None):
            value = fixture()
            value['registers']['dd'] = dd
            out = self.assertIndependent('payload_consumer', value)
            self.assertEqual(out['steps'][0]['afterRegisters']['dd'], dd)
            self.assertEqual(out['state']['registers']['dd'], 0)

    def test_consumer_unqualified_byte_load_keeps_only_first_dp_write(self):
        value = fixture()
        value['assumptions']['ordinaryByteSemantics'] = None
        out = self.assertIndependent('payload_consumer', value)
        self.assertEqual(out['boundary'], 0x28DB)
        self.assertEqual(len(out['journal']), 1)
        self.assertEqual(out['reads'], [])
        self.assertEqual(out['pointerState']['value'], 0x3F4)

    def test_consumer_add_three_flags_cover_zero_carry_and_halfcarry(self):
        for byte in (0x0C, 0x0D, 0xFC, 0xFD, 0xFE, 0xFF):
            value = fixture()
            value['memory']['03F4'] = byte
            out = self.assertIndependent('payload_consumer', value)
            regs = out['state']['registers']
            self.assertEqual((regs['al'], regs['cf'], regs['zf'], regs['hc']),
                ((byte + 3) % 256, int(byte + 3 > 255), int((byte + 3) % 256 == 0), int((byte & 15) + 3 > 15)))

    def test_consumer_ah_and_unrelated_registers_are_retained(self):
        value = fixture()
        value['registers']['ah'] = 0xC7
        out = self.assertIndependent('payload_consumer', value)
        for key in ('ah', 'mie', 'otherPsw', 'lrb', 'scb', 'usp', 'ssp'):
            self.assertEqual(out['state']['registers'][key], value['registers'][key])

    def test_consumer_same_value_pointer_and_destination_stores_remain_events(self):
        value = fixture()
        value['memory'].update({'0084': 0xF4, '0085': 3, '03F2': 0x82})
        out = self.assertIndependent('payload_consumer', value)
        self.assertTrue(out['journal'][0]['sameValue'])
        self.assertTrue(out['journal'][2]['sameValue'])
        self.assertEqual(len(out['journal']), 3)
        self.assertEqual(len({r['afterGeneration'] for r in out['journal']}), 3)

    def test_consumer_unknown_input_is_not_zero_or_flag_substitution(self):
        value = partial(fixture(), '03F4', {})
        out = self.assertIndependent('payload_consumer', value)
        for key in ('al', 'cf', 'zf', 'hc'):
            self.assertIsNone(out['state']['registers'][key])
        self.assertIsNone(out['state']['memory']['03F2'])

    def test_consumer_partial_even_input_proves_odd_result_and_nonzero(self):
        value = partial(fixture(), '03F4', {0: 0})
        out = self.assertIndependent('payload_consumer', value)
        self.assertIsNone(out['state']['registers']['al'])
        self.assertEqual(out['state']['registerKnownBits']['AL.0'], 1)
        self.assertEqual(out['state']['registers']['zf'], 0)
        self.assertEqual(out['state']['knownBits']['03F2.0'], 1)

    def test_consumer_partial_low_nibble_exact_halfcarry(self):
        value = partial(fixture(), '03F4', dict.fromkeys(range(4), 1))
        out = self.assertIndependent('payload_consumer', value)
        self.assertEqual(out['state']['registers']['hc'], 1)
        self.assertEqual(out['state']['registers']['zf'], 0)
        self.assertEqual({key: out['state']['knownBits'][key] for key in ('03F2.0', '03F2.1', '03F2.2', '03F2.3')},
                         {'03F2.0': 0, '03F2.1': 1, '03F2.2': 0, '03F2.3': 0})

    def test_unique_bit_domain_infers_load_without_rewriting_source_memory(self):
        value = partial(fixture(), '03F4', {bit: (0xFD >> bit) & 1 for bit in range(8)})
        out = self.assertIndependent('payload_consumer', value)
        self.assertIsNone(out['state']['memory']['03F4'])
        self.assertIsNone(out['reads'][1]['value'])
        self.assertEqual(out['reads'][1]['bytes'], [None])
        self.assertEqual(out['state']['registers']['al'], 0)
        self.assertEqual(out['state']['memory']['03F2'], 0)

    def test_consumer_generation_label_does_not_confirm_native_reaching_definition(self):
        value = fixture()
        value['generations']['03F4'] = 'ConditionalEffect:generic_payload_body:026C:1'
        out = self.assertIndependent('payload_consumer', value)
        self.assertIn('Specific026CGenerationReachingConsumerNotEstablished', out['unresolvedConstraints'])
        self.assertIsNone(out['actualHardwareObservation'])

    def test_tail_word_read_mask_and_word_store_order(self):
        out = self.assertIndependent('post_checksum_tail', fixture('tail'))
        self.assertEqual([r['pc'] for r in out['steps']], [0x295, 0x297, 0x29A])
        self.assertEqual([(r['pc'], r['widthBits']) for r in out['reads']], [(0x295, 16), (0x297, 8)])
        self.assertEqual([(r['space'], r['address'], r['widthBits']) for r in out['journal']], [('REGISTER', 5, 8), ('DATA', 0x1A, 16)])
        self.assertEqual(out['boundary'], 0x29C)

    def test_tail_copies_low_and_high_shadow_bytes_to_ie(self):
        value = fixture('tail')
        value['memory'].update({'00F8': 0x34, '00F9': 0xA5})
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertEqual((out['state']['memory']['001A'], out['state']['memory']['001B']), (0x34, 0xA5))
        self.assertEqual((out['state']['registers']['al'], out['state']['registers']['ah']), (0x34, 0xA5))
        self.assertEqual(out['state']['registers']['dd'], 1)

    def test_tail_has_no_lrb_scb_or_byte_load_premise_dependency(self):
        value = fixture('tail')
        value['registers'].update(lrb=None, scb=None)
        value['assumptions']['ordinaryByteSemantics'] = False
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertEqual(out['outcome'], 'PreRtiTailSpecified')
        self.assertIsNone(out['pointerState']['dataAddress'])

    def test_tail_mie_clear_does_not_determine_pswh_self_destination_zf(self):
        value = fixture('tail')
        value['registers'].update(mie=1, cf=1, hc=1)
        out = self.assertIndependent('post_checksum_tail', value)
        regs = out['state']['registers']
        self.assertEqual((regs['mie'], regs['cf'], regs['hc'], regs['dd']), (0, 1, 1, 1))
        self.assertIsNone(regs['zf'])
        self.assertIn('PswhSelfDestinationZfOrderNotEstablished', out['unresolvedConstraints'])

    def test_tail_known_zero_shadow_sets_load_zf_then_mask_makes_it_unknown(self):
        value = fixture('tail')
        value['memory'].update({'00F8': 0, '00F9': 0})
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertEqual(out['steps'][0]['afterRegisters']['zf'], 1)
        self.assertIsNone(out['steps'][1]['afterRegisters']['zf'])

    def test_tail_partial_word_known_one_proves_nonzero_load(self):
        value = partial(partial(fixture('tail'), '00F8', {}), '00F9', {7: 1})
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertEqual(out['steps'][0]['afterRegisters']['zf'], 0)
        self.assertIsNone(out['state']['registers']['zf'])
        self.assertEqual(out['state']['knownBits']['001B.7'], 1)

    def test_tail_partial_shadow_masks_copy_without_default_bits(self):
        value = partial(partial(fixture('tail'), '00F8', {0: 1}), '00F9', {7: 0})
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertIsNone(out['state']['memory']['001A'])
        self.assertIsNone(out['state']['memory']['001B'])
        self.assertEqual({k: v for k, v in out['state']['knownBits'].items() if k[:4] in ('001A', '001B')}, {'001A.0': 1, '001B.7': 0})
        self.assertEqual(out['state']['registerKnownBits'], {'AL.0': 1, 'AH.7': 0})

    def test_tail_unknown_shadow_remains_unknown_ie_word(self):
        value = partial(partial(fixture('tail'), '00F8', {}), '00F9', {})
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertIsNone(out['state']['memory']['001A'])
        self.assertIsNone(out['state']['memory']['001B'])
        self.assertEqual(out['state']['registerKnownBits'], {})

    def test_tail_same_value_ie_word_is_a_new_generation(self):
        value = fixture('tail')
        value['memory'].update({'001A': 0x34, '001B': 0x12})
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertTrue(out['journal'][-1]['sameValue'])
        self.assertEqual(out['state']['generations']['001A'], out['journal'][-1]['afterGeneration'])
        self.assertNotEqual(out['state']['generations']['001A'], value['generations']['00F8'])

    def test_tail_missing_f8_generation_does_not_fabricate_native_ownership(self):
        value = fixture('tail')
        value['generations']['00F8'] = None
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertIn('F8GenerationNotEstablished', out['unresolvedConstraints'])
        self.assertEqual(out['reads'][0]['generations'][0], None)
        self.assertEqual(out['state']['memory']['001A'], 0x34)

    def test_tail_does_not_read_ie_destination_or_restore_stack(self):
        value = fixture('tail')
        value['registers']['ssp'] = None
        out = self.assertIndependent('post_checksum_tail', value)
        self.assertFalse(any(row['address'] == 0x1A for row in out['reads']))
        self.assertIsNone(out['state']['registers']['ssp'])
        self.assertEqual(out['rtiObligations']['reads'], [])
        self.assertEqual(out['rtiObligations']['journal'], [])
        self.assertIsNone(out['rtiObligations']['state']['actualReturnObservation'])

    def test_tail_register_mask_read_keeps_frozen_five_flag_knowledge(self):
        out = self.assertIndependent('post_checksum_tail', fixture('tail'))
        row = out['reads'][1]
        self.assertEqual(row['accessRole'], 'RegisterOperand')
        self.assertEqual(row['generations'], [None])
        self.assertTrue(set(row['knownBits']) <= {'0005.0', '0005.4', '0005.5', '0005.6', '0005.7'})

    def test_parser_completed_header_length_flag_and_generic_have_new_jump_to_tail(self):
        for role in ('Header', 'Length', 'Flag', 'Generic'):
            out = self.assertIndependent('parser_step_with_tail', fixture(role))
            jump = [step for step in out['steps'] if step['pc'] == 0x272]
            self.assertEqual(len(jump), 1)
            self.assertEqual(jump[0]['next'], 0x295)
            self.assertEqual(out['outcome'], 'PreRtiTailSpecified')

    def test_parser_checksum_acceptance_falls_into_tail_without_0272_jump(self):
        out = self.assertIndependent('parser_step_with_tail', fixture('Checksum'))
        self.assertFalse(any(step['pc'] == 0x272 for step in out['steps']))
        self.assertEqual(out['state']['memory']['03F7'], 0)
        self.assertEqual(out['boundary'], 0x29C)

    def test_parser_rejected_checksum_uses_tail_but_keeps_r7_two(self):
        value = fixture('Checksum')
        value['memory']['0055'] = 0
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['state']['memory']['03F7'], 2)
        self.assertTrue(any(step['pc'] == 0x272 for step in out['steps']))
        self.assertEqual(out['boundary'], 0x29C)

    def test_parser_outside_mode_and_error_do_not_force_tail(self):
        for status, boundary in ((0, 0x29D), (0x42, 0x227)):
            value = fixture('Generic')
            value['memory']['0356'] = status
            out = self.assertIndependent('parser_step_with_tail', value)
            self.assertEqual(out['boundary'], boundary)
            self.assertFalse(any(step['pc'] == 0x295 for step in out['steps']))
            self.assertIsNone(out['rtiObligations'])

    def test_parser_indeterminate_prefix_does_not_apply_tail(self):
        value = fixture('Generic')
        value['memory']['03F2'] = None
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['status'], 'IndeterminateBranch')
        self.assertEqual(out['boundary'], 0x260)
        self.assertIsNone(out['rtiObligations'])

    def test_parser_unsupported_new_partial_knowledge_refuses_before_effects(self):
        value = partial(fixture('Generic'), '0055', {0: 1})
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['reason'], 'UnsupportedPartialParserKnowledge')
        self.assertEqual(out['journal'], [])
        self.assertEqual(out['reads'], [])

    def test_parser_extra_dp_and_f8_partial_knowledge_is_retained(self):
        value = partial(partial(fixture('Generic'), '0084', {7: 1}), '00F8', {0: 1})
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['state']['knownBits']['0084.7'], 1)
        self.assertEqual(out['state']['knownBits']['001A.0'], 1)
        self.assertIsNone(out['state']['memory']['0084'])

    def test_parser_prefix_labels_and_tail_labels_have_distinct_exact_owners(self):
        out = self.assertIndependent('parser_step_with_tail', fixture('Generic'))
        self.assertTrue(out['journal'][0]['afterGeneration'].startswith('ConditionalEffect:parser_step@M2cqPrefix:'))
        self.assertTrue(out['journal'][-1]['afterGeneration'].startswith('ConditionalEffect:parser_step_with_tail:'))
        self.assertEqual([r['ordinal'] for r in out['journal']], list(range(1, len(out['journal']) + 1)))

    def test_parser_read_generations_are_captured_before_prefix_rmw(self):
        value = fixture('Generic')
        out = self.assertIndependent('parser_step_with_tail', value)
        status_reads = [r for r in out['reads'] if r['pc'] == 0x222]
        self.assertEqual(status_reads[0]['generations'], [value['generations']['0356']])
        self.assertNotEqual(status_reads[0]['generations'][0], out['state']['generations']['0356'])

    def test_parser_initial_prefix_namespace_is_refused_without_double_effects(self):
        value = fixture('Generic')
        value['generations']['0084'] = 'ConditionalEffect:parser_step@M2cqPrefix:0222:1'
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['reason'], 'EffectNamespaceAlreadyPresent')
        self.assertEqual(out['journal'], [])

    def test_parser_namespace_guard_precedes_unsupported_partial_knowledge(self):
        value = partial(fixture('Generic'), '0055', {0: 1})
        value['generations']['0084'] = 'ConditionalEffect:parser_step_with_tail:029A:1'
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['reason'], 'EffectNamespaceAlreadyPresent')

    def test_parser_partial_knowledge_guard_precedes_inherited_lrb_gate(self):
        value = partial(fixture('Generic'), '0055', {0: 1})
        value['registers']['lrb'] = None
        out = self.assertIndependent('parser_step_with_tail', value)
        self.assertEqual(out['reason'], 'UnsupportedPartialParserKnowledge')

    def test_timeline_retains_three_writers_and_each_boundary(self):
        out = self.assertIndependent('last_writer_at_conditional_boundary', timeline(2))
        self.assertEqual(len(out['journal']), 3)
        self.assertEqual(len(out['reads']), 3)
        self.assertEqual(len(out['intermediateStates']), 6)
        self.assertEqual([r['value'] for r in out['reads']], [2, 3, 3])
        self.assertEqual([r['generation'] for r in out['reads']], ['G1', 'G2', 'G3'])

    def test_timeline_same_value_replacement_has_new_identity(self):
        out = self.assertIndependent('last_writer_at_conditional_boundary', timeline())
        self.assertTrue(out['journal'][-1]['sameTrackedByteValue'])
        self.assertEqual(out['journal'][-1]['beforeGeneration'], 'G2')
        self.assertEqual(out['journal'][-1]['afterGeneration'], 'G3')

    def test_timeline_stale_request_does_not_recover_previous_writer(self):
        value = timeline()
        value['events'][-1]['requestedGeneration'] = 'G2'
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reads'][-1]['relation'], 'StaleOrUnboundRequestedGeneration')
        self.assertEqual(out['state']['lastGeneration'], 'G3')

    def test_timeline_unknown_value_can_retain_a_conditional_generation(self):
        value = timeline(None)
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertIsNone(out['reads'][0]['value'])
        self.assertEqual(out['reads'][0]['relation'], 'ConditionalLastWriterAtBoundary')

    def test_timeline_missing_generation_is_not_replaced_by_value(self):
        value = timeline()
        value['events'][0]['generation'] = None
        value['events'][1]['requestedGeneration'] = None
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reads'][0]['relation'], 'MissingProducerGeneration')

    def test_timeline_unknown_writer_destroys_tracking_without_fake_store_address(self):
        value = timeline()
        value['events'].insert(-1, {'kind': 'UnknownWriter', 'id': 'unknown'})
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reads'][-1]['relation'], 'UnknownInterveningWriter')
        self.assertIsNone(out['journal'][-1]['address'])
        self.assertIsNone(out['journal'][-1]['targetOverlap'])

    def test_timeline_no_interference_is_never_defaulted_true(self):
        for premise in (False, None):
            value = timeline()
            value['noInterference'] = premise
            out = self.assertIndependent('last_writer_at_conditional_boundary', value)
            self.assertTrue(all(row['relation'] == 'InterferenceNotExcluded' for row in out['reads']))

    def test_timeline_wrong_producer_context_preserves_only_applied_prefix(self):
        value = timeline()
        value['events'][2]['lrb'] = 0x40
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reason'], 'ProducerContextNotEstablished')
        self.assertEqual(out['boundary'], 2)
        self.assertEqual(len(out['journal']), 1)
        self.assertEqual(len(out['intermediateStates']), 2)

    def test_timeline_reused_generation_refuses_before_event(self):
        value = timeline()
        value['events'][4]['generation'] = 'G1'
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reason'], 'WriterGenerationReused')
        self.assertEqual(out['boundary'], 4)
        self.assertEqual(out['state']['lastGeneration'], 'G2')

    def test_timeline_initial_generation_cannot_be_reused(self):
        value = timeline()
        value['events'][0]['generation'] = value['initial']['generation']
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reason'], 'WriterGenerationReused')
        self.assertEqual(out['journal'], [])

    def test_timeline_null_generation_labels_may_repeat_without_owner_promotion(self):
        value = timeline()
        for event in value['events']:
            event['generation' if event['kind'] == 'GenericStore' else 'requestedGeneration'] = None
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertEqual(len(out['journal']), 3)
        self.assertTrue(all(row['relation'] == 'MissingProducerGeneration' for row in out['reads']))

    def test_timeline_producer_context_guard_precedes_generation_collision(self):
        value = timeline()
        value['events'][2].update(lrb=0x40, generation='G1')
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reason'], 'ProducerContextNotEstablished')

    def test_timeline_nonoverlap_writer_still_reserves_its_generation(self):
        value = timeline()
        value['events'].insert(0, {'kind': 'AlternateStore', 'id': 'other', 'address': 0x3F3,
            'widthBits': 8, 'value': 0, 'generation': 'G2'})
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reason'], 'WriterGenerationReused')
        self.assertEqual(out['boundary'], 3)
        self.assertFalse(out['journal'][0]['targetOverlap'])

    def test_timeline_word_alias_normalizes_effective_address_before_overlap(self):
        for address, overlaps, byte in ((0x3F3, False, 0x7F), (0x3F5, True, 0x5A)):
            value = timeline()
            value['events'] = [value['events'][0], {'kind': 'AlternateStore', 'id': 'word',
                'address': address, 'widthBits': 16, 'value': 0xA55A, 'generation': 'W'}]
            out = self.assertIndependent('last_writer_at_conditional_boundary', value)
            self.assertEqual(out['journal'][-1]['address'], address & 0xFFFE)
            self.assertEqual(out['journal'][-1]['targetOverlap'], overlaps)
            self.assertEqual(out['state']['lastValue'], byte)

    def test_timeline_alternate_writer_is_not_026c_even_with_matching_label(self):
        value = timeline()
        value['events'] = [{'kind': 'AlternateStore', 'id': 'alt', 'address': 0x3F4,
            'widthBits': 16, 'value': 0xA55A, 'generation': 'W'},
            {'kind': 'ConsumerBoundary', 'id': 'c', 'requestedGeneration': 'W'}]
        out = self.assertIndependent('last_writer_at_conditional_boundary', value)
        self.assertEqual(out['reads'][0]['relation'], 'AlternateWriterNot026C')

    def test_timeline_unsupported_confirmed_array_fifo_and_execution_claims_refuse(self):
        for claim in ('Confirmed026CConsumer', 'PayloadArray', 'Fifo', 'ActualExecution'):
            value = timeline()
            value['claim'] = claim
            out = self.assertIndependent('last_writer_at_conditional_boundary', value)
            self.assertEqual(out['reason'], 'UnestablishedAuthorityClaim')
            self.assertEqual(out['journal'], [])
            self.assertEqual(out['reads'], [])

    def test_timeline_duplicate_event_ids_and_bool_bytes_are_malformed(self):
        for mode in ('ids', 'byte'):
            value = timeline()
            if mode == 'ids':
                value['events'][1]['id'] = value['events'][0]['id']
            else:
                value['events'][0]['value'] = True
            with self.assertRaises(ValueError):
                last_writer_at_conditional_boundary(value)

    def test_rti_increment_first_read_roles_and_geometry(self):
        out = self.assertIndependent('rti_obligations', rti_query(0x07F0, True))
        self.assertEqual([row['role'] for row in out['obligationReads']], ['psw', 'lrb', 'a', 'pc'])
        self.assertEqual([row['numericSspAfterIncrement'] for row in out['obligationReads']], [0x07F2, 0x07F4, 0x07F6, 0x07F8])
        self.assertEqual(out['state']['hypotheticalRestores']['ssp'], 0x07F8)
        self.assertEqual(out['status'], 'CompleteConditional')

    def test_rti_odd_numeric_ssp_is_not_rounded_but_word_addresses_are(self):
        out = self.assertIndependent('rti_obligations', rti_query(1, True))
        self.assertEqual([row['numericSspAfterIncrement'] for row in out['obligationReads']], [3, 5, 7, 9])
        self.assertEqual([row['effectiveWordAddress'] for row in out['obligationReads']], [2, 4, 6, 8])
        self.assertEqual(out['state']['hypotheticalRestores']['ssp'], 9)
        self.assertIn('OddSspPhysicalSafetyNotEstablished', out['missingPremises'])

    def test_rti_word_geometry_wraps_at_16bit_boundary(self):
        out = self.assertIndependent('rti_obligations', rti_query(0xFFFE, True))
        self.assertEqual([row['numericSspAfterIncrement'] for row in out['obligationReads']], [0, 2, 4, 6])
        self.assertEqual(out['state']['hypotheticalRestores']['ssp'], 6)

    def test_rti_unknown_ssp_and_pc_are_not_seeded(self):
        out = self.assertIndependent('rti_obligations', rti_query())
        self.assertTrue(all(row['effectiveWordAddress'] is None for row in out['obligationReads']))
        self.assertIsNone(out['state']['hypotheticalRestores']['ssp'])
        self.assertIsNone(out['state']['hypotheticalRestores']['pc'])
        self.assertEqual(out['status'], 'IndeterminateObligation')

    def test_rti_missing_generation_is_an_explicit_obligation(self):
        value = rti_query(0x07F0, True)
        value['frameGenerations']['pc'] = None
        out = self.assertIndependent('rti_obligations', value)
        self.assertIn('FrameGenerationUnknown:pc', out['missingPremises'])
        self.assertEqual(out['status'], 'IndeterminateObligation')

    def test_rti_requires_all_eight_distinct_conditional_premises(self):
        for premise in PREMISES:
            value = rti_query(0x07F0, True)
            value['premises'][premise] = None
            out = self.assertIndependent('rti_obligations', value)
            self.assertIn('PremiseUnknown:' + premise, out['missingPremises'])
            self.assertEqual(out['status'], 'IndeterminateObligation')

    def test_rti_frame_mismatch_precedes_declared_false_premise(self):
        value = rti_query(0x07F0, True)
        value['premises'].update(matchingEntrySsp=0, integrity=False)
        out = self.assertIndependent('rti_obligations', value)
        self.assertEqual(out['reason'], 'MatchingEntryFrameMismatch')
        self.assertEqual(len(out['obligationReads']), 4)

    def test_rti_declared_control_alias_unsafe_is_not_success(self):
        value = rti_query(0x16, True)
        value['premises']['noControlAlias'] = False
        out = self.assertIndependent('rti_obligations', value)
        self.assertEqual(out['reason'], 'DeclaredFramePremiseFalse')
        self.assertEqual(out['obligationReads'][0]['effectiveWordAddress'], 0x18)

    def test_rti_execution_claim_suppresses_even_hypothetical_operations(self):
        value = rti_query(0x07F0, True)
        value['executionClaim'] = True
        out = self.assertIndependent('rti_obligations', value)
        self.assertEqual(out['reason'], 'ActualRtiExecutionNotAuthorized')
        self.assertEqual(out['obligationReads'], [])
        self.assertEqual(out['missingPremises'], [])
        self.assertTrue(all(value is None for value in out['state']['hypotheticalRestores'].values()))

    def test_rti_does_not_restore_ie_pr_ram_parser_ram_or_assign_sf(self):
        out = self.assertIndependent('rti_obligations', rti_query(0x07F0, True))
        self.assertFalse(out['state']['ieRestoredByRti'])
        self.assertFalse(out['state']['pointingRegisterRamRestored'])
        self.assertFalse(out['state']['parserRamRestored'])
        self.assertEqual(out['state']['sfAssignment'], 'NotEstablished')
        self.assertIsNone(out['state']['actualReturnObservation'])

    def test_rti_restored_dd_does_not_change_formal_word_width(self):
        for psw in (0, 0x1007):
            value = rti_query(0x07F0, True)
            value['frameWords']['psw'] = psw
            out = self.assertIndependent('rti_obligations', value)
            self.assertTrue(all(row['widthBits'] == 16 for row in out['obligationReads']))
            self.assertEqual(out['state']['hypotheticalRestores']['scb'], psw & 7)

    def test_rti_host_foreground_pc_field_is_not_admitted(self):
        value = rti_query()
        value['foregroundPc'] = 0x1234
        with self.assertRaises(ValueError):
            rti_obligations(value)

    def test_snapshot_contradictory_bits_missing_alias_and_actual_claim_are_invalid(self):
        for kind in ('bits', 'alias', 'claim'):
            value = fixture()
            if kind == 'bits':
                value['knownBits']['03F4.0'] = 0
            elif kind == 'alias':
                value['memory'].pop(DP_ADDRESSES[0])
            else:
                value['inputClass'] = 'ObservedNative'
            with self.assertRaises(ValueError):
                payload_consumer(value)

    def test_no_interference_and_namespace_guards_apply_before_source_effects(self):
        for operation, kind in (('payload_consumer', 'consumer'), ('post_checksum_tail', 'tail'), ('parser_step_with_tail', 'Generic')):
            value = fixture(kind)
            value['assumptions']['noInterference'] = None
            value['generations']['03F4'] = 'ConditionalEffect:' + operation + ':0000:1'
            out = self.assertIndependent(operation, value)
            self.assertEqual(out['reason'], 'NoInterferencePremiseNotEstablished')
            self.assertEqual(out['journal'], [])
            self.assertEqual(out['reads'], [])

    def test_all_five_operations_preserve_zero_execution_and_source_scope(self):
        for operation, value in (('payload_consumer', fixture()), ('post_checksum_tail', fixture('tail')),
                                 ('parser_step_with_tail', fixture('Generic')),
                                 ('last_writer_at_conditional_boundary', timeline()), ('rti_obligations', rti_query())):
            out = self.assertIndependent(operation, value)
            self.assertTrue(out['sourceScope'])
            self.assertEqual(out['unresolvedConstraints'][:5], list(oracle.COMMON))
            self.assertIsNone(out['actualHardwareObservation'])
            self.assertEqual(out['cpuInstructionRetirements'], 0)
            self.assertEqual(out['executionStatus'], 'EXECUTION_BLOCKED')
            self.assertFalse(out['firmwareReady'])


if __name__ == '__main__':
    unittest.main()
