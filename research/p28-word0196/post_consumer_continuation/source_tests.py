"""Source-derived controls; actual implementations are imported only on use."""
from copy import deepcopy
import importlib
import unittest

from . import reference_oracle as reference
from .corpus import fixture, partial, register_partial, stbuf_query, lineage_query, cases, SITES, PREMISES
from payload_consumer_tail.reference_oracle import payload_consumer as frozen_reference


def actual(operation, value):
    module = {'post_consumer_continuation': 'continuation', 'consumer_with_continuation': 'continuation',
              'stbuf_boundary_obligations': 'stbuf_obligations', 'continuation_lineage': 'lineage'}[operation]
    return getattr(importlib.import_module('.' + module, __package__), operation)(deepcopy(value))


class SourceTests(unittest.TestCase):
    def body(self, value=None):
        return actual('post_consumer_continuation', fixture() if value is None else value)

    def composed(self, value=None):
        return actual('consumer_with_continuation', fixture(True) if value is None else value)

    def formal(self, value=None):
        return actual('stbuf_boundary_obligations', stbuf_query(True) if value is None else value)

    def lineage(self, value=None):
        return actual('continuation_lineage', lineage_query() if value is None else value)

    def test_full_independent_canonical_records(self):
        seen = set()
        for case in cases():
            self.assertNotIn(case['id'], seen)
            seen.add(case['id'])
            expected = reference.evaluate(case)
            observed = actual(case['operation'], case['input'])
            self.assertEqual(reference.canonical(expected), reference.canonical(observed), case['id'])

    def test_input_immutability_all_four_operations(self):
        for op, value in (('post_consumer_continuation', fixture()), ('consumer_with_continuation', fixture(True)),
                          ('stbuf_boundary_obligations', stbuf_query()), ('continuation_lineage', lineage_query())):
            before = deepcopy(value)
            actual(op, value)
            self.assertEqual(value, before)

    def test_exact_ten_site_straightline(self):
        out = self.body()
        self.assertEqual([x['pc'] for x in out['steps']], list(SITES))
        self.assertEqual([x['next'] for x in out['steps']], [*SITES[1:], 0x2995])
        self.assertTrue(all(x['kind'] == 'Linear' and x['branchTaken'] is None for x in out['steps']))

    def test_seven_ordered_mixed_width_writes(self):
        out = self.body()
        self.assertEqual([x['pc'] for x in out['journal']], [0x2980, 0x2983, 0x2985, 0x298A, 0x298B, 0x2991, 0x2994])
        self.assertEqual([x['widthBits'] for x in out['journal']], [16, 8, 16, 8, 16, 16, 8])
        self.assertEqual([x['ordinal'] for x in out['journal']], list(range(1, 8)))

    def test_intermediate_state_after_every_writer(self):
        out = self.body()
        self.assertEqual(len(out['intermediateStates']), 7)
        self.assertEqual([x['afterOrdinal'] for x in out['intermediateStates']], list(range(1, 8)))
        self.assertEqual(out['intermediateStates'][0]['state']['memory']['0084'], 0x56)
        self.assertEqual(out['intermediateStates'][1]['state']['memory']['0356'], 0x42)
        self.assertEqual(out['intermediateStates'][-1]['state'], out['state'])

    def test_reads_have_separate_pointer_dependencies(self):
        reads = self.body()['reads']
        self.assertEqual([x['pc'] for x in reads], [0x2983, 0x2983, 0x298A, 0x298E, 0x298E, 0x2994])
        self.assertEqual([x['address'] for x in reads if x['space'] == 'DATA'], [0x356, 0x3F1])
        self.assertEqual(sum(x['space'] == 'ARCHITECTURAL_ADDRESS_DEPENDENCY' for x in reads), 4)

    def test_literal_operands_are_not_data_reads(self):
        out = self.body()
        self.assertFalse(any(x['pc'] in (0x2988, 0x298F) for x in out['reads']))
        self.assertFalse(any(x['space'] == 'DATA' and x['address'] in (2, 31) for x in out['reads']))

    def test_full_H_sweep_mask_and_flags(self):
        for h in range(256):
            value = fixture(); value['memory']['03F1'] = h
            out = self.body(value); r = out['state']['registers']
            self.assertEqual((r['al'], r['zf'], r['dd'], out['state']['memory']['03F6']), (h & 31, int(h & 31 == 0), 0, h & 31))

    def test_full_G_sweep_retains_consumer_carry_halfcarry(self):
        for g in range(256):
            value = fixture(True); value['memory']['03F4'] = g
            out = self.composed(value); r = out['state']['registers']
            self.assertEqual((r['cf'], r['hc']), (int(g + 3 > 255), int((g & 15) + 3 > 15)))
            self.assertEqual(out['state']['memory']['03F2'], (g + 3) & 255)
            self.assertEqual(r['al'], 1)

    def test_direct_carry_and_halfcarry_retained_including_unknown(self):
        for cf, hc in ((0, 0), (1, 1), (1, 0), (None, 1), (0, None), (None, None)):
            value = fixture(); value['registers'].update(cf=cf, hc=hc)
            out = self.body(value)
            self.assertEqual((out['state']['registers']['cf'], out['state']['registers']['hc']), (cf, hc))

    def test_status_set_complements_old_bit_only(self):
        for old in (0x02, 0x42):
            value = fixture(); value['memory']['0356'] = old
            out = self.body(value)
            self.assertEqual(out['steps'][1]['afterRegisters']['zf'], 1 - ((old >> 6) & 1))
            self.assertEqual(out['state']['memory']['0356'], old | 0x40)

    def test_unknown_status_propagates_without_fake_branch(self):
        out = self.body(partial(fixture(), '0356', {1: 1}))
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertIsNone(out['steps'][1]['afterRegisters']['zf'])
        self.assertIsNone(out['state']['memory']['0356'])
        self.assertEqual(out['state']['knownBits']['0356.6'], 1)

    def test_same_value_writes_keep_identity_and_generation(self):
        value = fixture(); value['memory'].update({'0356': 0x42, '0084': 0x56, '0085': 3})
        out = self.body(value)
        self.assertTrue(out['journal'][0]['sameValue'])
        self.assertTrue(out['journal'][1]['sameValue'])
        self.assertTrue(out['journal'][3]['sameValue'])
        self.assertTrue(out['journal'][-1]['sameValue'])
        self.assertEqual(len({x['afterGeneration'] for x in out['journal']}), 7)

    def test_scb_banks_are_physical_memory_aliases(self):
        for bank in range(8):
            value = fixture(); value['registers']['scb'] = bank
            out = self.body(value); addr = 0x84 + bank * 8
            self.assertEqual([x['address'] for x in out['journal'] if x['widthBits'] == 16], [addr] * 4)
            self.assertEqual(out['pointerState']['value'], 0x3F6)
            self.assertEqual(out['state']['memory'][f'{addr:04X}'], 0xF6)

    def test_scb6_overwrites_real_B4_B5_partial_knowledge(self):
        value = fixture(); value['registers']['scb'] = 6
        partial(value, '00B4', {0: 1}); partial(value, '00B5', {7: 1})
        out = self.body(value)
        self.assertEqual((out['state']['memory']['00B4'], out['state']['memory']['00B5']), (0xF6, 3))
        self.assertFalse(any(k.startswith(('00B4.', '00B5.')) for k in out['state']['knownBits']))

    def test_unknown_scb_never_defaults_to_bank_zero(self):
        value = fixture(); value['registers']['scb'] = None
        out = self.body(value)
        self.assertEqual(out['reason'], 'PointerBankNotEstablished')
        self.assertEqual(out['journal'], []); self.assertEqual(out['reads'], [])

    def test_no_false_lrb_or_usp_gate(self):
        value = fixture(); value['registers'].update(lrb=None, usp=None)
        out = self.body(value)
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertIsNone(out['state']['registers']['lrb'])

    def test_incoming_dd_unknown_or_word_is_accepted_until_lb(self):
        for dd in (0, 1, None):
            value = fixture(); value['registers']['dd'] = dd
            out = self.body(value)
            self.assertEqual(out['steps'][2]['afterRegisters']['dd'], dd)
            self.assertEqual(out['steps'][3]['afterRegisters']['dd'], 0)

    def test_unknown_H_preserves_masked_partial_bits(self):
        out = self.body(partial(fixture(), '03F1', {}))
        self.assertIsNone(out['state']['registers']['al']); self.assertIsNone(out['state']['registers']['zf'])
        self.assertIsNone(out['state']['memory']['03F6'])
        self.assertEqual({k: v for k, v in out['state']['knownBits'].items() if k.startswith('03F6.')}, {'03F6.5': 0, '03F6.6': 0, '03F6.7': 0})

    def test_partial_H_lower_one_proves_nonzero(self):
        out = self.body(partial(fixture(), '03F1', {0: 1}))
        self.assertIsNone(out['state']['registers']['al'])
        self.assertEqual(out['state']['registers']['zf'], 0)

    def test_partial_H_lower_zero_proves_zero(self):
        out = self.body(partial(fixture(), '03F1', dict.fromkeys(range(5), 0)))
        self.assertEqual((out['state']['registers']['al'], out['state']['registers']['zf']), (0, 1))

    def test_register_partial_AL_is_retained_before_literal_overwrite(self):
        value = register_partial(fixture(), 'al', {0: 1, 7: 0})
        out = self.body(value)
        for step in out['steps'][:3]:
            self.assertIsNone(step['afterRegisters']['al'])
            self.assertEqual(step['afterRegisterKnownBits']['AL.0'], 1)
        self.assertEqual(out['steps'][3]['afterRegisters']['al'], 2)

    def test_partial_AH_raw_none_is_never_filled(self):
        bits = {bit: (0xA5 >> bit) & 1 for bit in range(8)}
        out = self.body(register_partial(fixture(), 'ah', bits))
        self.assertIsNone(out['state']['registers']['ah'])
        self.assertEqual({k: v for k, v in out['state']['registerKnownBits'].items() if k.startswith('AH.')}, {'AH.' + str(k): v for k, v in bits.items()})

    def test_scalar_known_register_subset_is_not_augmented_initially(self):
        value = fixture(); value['registerKnownBits'] = {'AH.0': value['registers']['ah'] & 1}
        out = self.body(value)
        self.assertEqual(out['steps'][0]['afterRegisterKnownBits'], value['registerKnownBits'])
        self.assertEqual({k: v for k, v in out['state']['registerKnownBits'].items() if k.startswith('AH.')}, value['registerKnownBits'])

    def test_no_interference_refuses_before_first_writer(self):
        value = fixture(); value['assumptions']['noInterference'] = None
        out = self.body(value)
        self.assertEqual(out['reason'], 'NoInterferencePremiseNotEstablished')
        self.assertEqual(out['journal'], []); self.assertIsNone(out['stbufObligations'])

    def test_ordinary_byte_refusal_retains_reached_prefix(self):
        value = fixture(); value['assumptions']['ordinaryByteSemantics'] = False
        out = self.body(value)
        self.assertEqual((out['boundary'], out['reason']), (0x2988, 'OrdinaryByteSemanticsNotEstablished'))
        self.assertEqual(len(out['journal']), 3); self.assertEqual(len(out['steps']), 3)
        self.assertEqual([x['pc'] for x in out['reads']], [0x2983, 0x2983])

    def test_existing_own_namespace_refuses_no_deduplicated_events(self):
        value = fixture(); value['generations']['03F1'] = 'ConditionalEffect:post_consumer_continuation:298F:1'
        out = self.body(value)
        self.assertEqual(out['reason'], 'EffectNamespaceAlreadyPresent'); self.assertEqual(out['journal'], [])

    def test_F2_F4_are_retained_without_reads_or_writes(self):
        value = fixture(); value['memory'].update({'03F2': None, '03F4': 0xFA})
        out = self.body(value)
        self.assertIsNone(out['state']['memory']['03F2'])
        self.assertEqual(out['state']['memory']['03F4'], 0xFA)
        self.assertFalse(any(x['address'] in (0x3F2, 0x3F4) for x in out['reads'] + out['journal']))

    def test_composed_prefix_is_byte_exact_including_labels(self):
        value = fixture(True); prefix = frozen_reference(value); out = self.composed(value)
        self.assertEqual(out['journal'][:3], prefix['journal'])
        self.assertEqual(out['reads'][:3], prefix['reads'])
        self.assertEqual(out['steps'][:6], prefix['steps'])
        self.assertEqual(out['intermediateStates'][:3], prefix['intermediateStates'])

    def test_composed_has_no_extra_fallthrough_step_or_counter_reset(self):
        out = self.composed()
        self.assertEqual(len(out['steps']), 16); self.assertEqual(len(out['journal']), 10)
        self.assertEqual(out['steps'][5]['next'], 0x2980)
        self.assertEqual(out['steps'][6]['pc'], 0x2980)
        self.assertEqual(out['journal'][3]['afterGeneration'], 'ConditionalEffect:consumer_with_continuation:2980:4')

    def test_composed_partial_prefix_register_bits_transferred(self):
        value = partial(fixture(True), '03F4', {0: 1, 1: 0})
        out = self.composed(value); prefix = frozen_reference(value)
        for step in out['steps'][6:9]:
            self.assertEqual(step['afterRegisterKnownBits'], prefix['state']['registerKnownBits'])
        self.assertEqual(out['state']['generations']['03F2'], prefix['state']['generations']['03F2'])

    def test_composed_refusal_is_unchanged_parent_prefix(self):
        value = fixture(True); value['assumptions']['ordinaryByteSemantics'] = None
        expected = frozen_reference(value); expected['stbufObligations'] = None
        self.assertEqual(self.composed(value), expected)

    def test_composed_own_namespace_retains_successful_prefix(self):
        value = fixture(True); value['generations']['03F1'] = 'ConditionalEffect:consumer_with_continuation:0000:1'
        out = self.composed(value)
        self.assertEqual((out['boundary'], out['reason']), (0x2980, 'EffectNamespaceAlreadyPresent'))
        self.assertEqual(len(out['journal']), 3); self.assertEqual(len(out['steps']), 6)

    def test_overwritten_original_own_namespace_cannot_escape_admission(self):
        for bank, address in ((0, '0084'), (0, '03F2'), (6, '00B4')):
            value = fixture(True); value['registers']['scb'] = bank
            value['generations'][address] = 'ConditionalEffect:consumer_with_continuation:0000:1'
            out = self.composed(value)
            self.assertEqual((out['boundary'], out['reason']), (0x2980, 'EffectNamespaceAlreadyPresent'))
            self.assertEqual(len(out['journal']), 3)
            self.assertEqual(out['state'], frozen_reference(value)['state'])

    def test_final_boundary_never_retires_STBUF(self):
        for out in (self.body(), self.composed()):
            self.assertEqual(out['boundary'], 0x2995)
            self.assertFalse(any(x['pc'] == 0x2995 or x['address'] == 0x51 for x in out['journal']))
            self.assertEqual(out['cpuInstructionRetirements'], 0)
            self.assertIsNone(out['actualHardwareObservation'])

    def test_nested_hardware_obligations_do_not_undo_completion(self):
        out = self.body(); obligation = out['stbufObligations']
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertEqual(obligation['status'], 'IndeterminateObligation')
        self.assertEqual(obligation['missingPremises'], ['PremiseUnknown:' + key for key in PREMISES])

    def test_stbuf_all_hypothetical_facts_never_make_observation(self):
        out = self.formal()
        self.assertEqual(out['status'], 'CompleteConditional')
        for key in ('actualBufferWrite', 'actualAcceptance', 'actualTransmission', 'actualCompletion', 'actualTxIrq'):
            self.assertIsNone(out['state'][key])
        self.assertEqual(out['journal'], []); self.assertEqual(out['reads'], [])

    def test_stbuf_claims_refuse_actual_side_effects(self):
        for claim in ('ActualBufferWrite', 'ActualTransmit', 'TxComplete', 'IRQ', 'CpuExecution'):
            query = stbuf_query(True); query['claim'] = claim
            out = self.formal(query)
            self.assertEqual(out['reason'], 'PeripheralExecutionNotAuthorized')
            self.assertIsNone(out['state']['actualTransmission']); self.assertEqual(out['steps'], [])

    def test_stbuf_word_descriptor_does_not_silently_write_byte(self):
        query = stbuf_query(True); query['dd'] = 1
        out = self.formal(query)
        self.assertEqual(out['reason'], 'WordStoreInterpretationNotByteStbuf')
        self.assertEqual(out['state']['descriptorDD'], 1); self.assertEqual(out['journal'], [])

    def test_stbuf_wrong_pc_does_not_advance_or_inject_boundary(self):
        query = stbuf_query(True); query['pc'] = 0x2997
        out = self.formal(query)
        self.assertEqual(out['reason'], 'WrongStbufBoundary'); self.assertEqual(out['steps'], [])

    def test_stbuf_missing_and_wrong_source_identity(self):
        for source, reason in ((None, 'SourceBindingMissing'), ({}, 'SourceBindingMismatch')):
            query = stbuf_query(True); query['sourceBinding'] = source
            self.assertEqual(self.formal(query)['reason'], reason)

    def test_source_binding_type_confusion_does_not_bind_descriptor(self):
        for operation, maker in (('stbuf_boundary_obligations', stbuf_query), ('continuation_lineage', lineage_query)):
            for key, value in (('boundaryDD', False), ('entry', float(0x2980)), ('sites', tuple(SITES))):
                query = maker(); query['sourceBinding'][key] = value
                self.assertEqual(actual(operation, query)['reason'], 'SourceBindingMismatch')

    def test_stbuf_unknown_operand_is_not_zero(self):
        query = stbuf_query(True); query['prospectiveAL']['value'] = None
        out = self.formal(query)
        self.assertIsNone(out['state']['prospectiveAL']['value'])
        self.assertIn('ProspectiveAlUnknown', out['missingPremises'])

    def test_stbuf_unique_partial_byte_stays_raw_symbolic(self):
        query = stbuf_query(True); query['prospectiveAL'].update(value=None, knownBits=dict.fromkeys(map(str, range(8)), 0))
        out = self.formal(query)
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertIsNone(out['state']['prospectiveAL']['value']); self.assertIsNone(out['state']['actualAcceptance'])

    def test_stbuf_missing_generation_is_not_fabricated(self):
        query = stbuf_query(True); query['prospectiveAL']['generation'] = None
        self.assertIn('ProspectiveAlGenerationUnknown', self.formal(query)['missingPremises'])

    def test_stbuf_false_or_unknown_hardware_premise(self):
        for key in PREMISES:
            query = stbuf_query(True); query['premises'][key] = False
            self.assertEqual(self.formal(query)['reason'], 'DeclaredPeripheralPremiseFalse')
            query['premises'][key] = None
            self.assertEqual(self.formal(query)['missingPremises'], ['PremiseUnknown:' + key])

    def test_stbuf_missing_order_and_precedence(self):
        query = stbuf_query(); query.update(pc=None, dd=None, softwareReached=None, softwareNoInterference=None)
        query['prospectiveAL'].update(value=None, generation=None)
        out = self.formal(query)
        self.assertEqual(out['missingPremises'][:6], ['UnknownBoundaryPc', 'UnknownByteDescriptor', 'SoftwareBoundaryNotEstablished',
            'SoftwareInterferenceNotExcluded', 'ProspectiveAlUnknown', 'ProspectiveAlGenerationUnknown'])
        query['claim'] = 'ActualTransmit'; query['sourceBinding'] = None
        self.assertEqual(self.formal(query)['reason'], 'PeripheralExecutionNotAuthorized')

    def test_stbuf_false_software_premise_is_separate(self):
        query = stbuf_query(True); query['softwareReached'] = False
        self.assertEqual(self.formal(query)['reason'], 'DeclaredSoftwarePremiseFalse')

    def test_lineage_no_access_window_is_not_observed_read(self):
        out = self.lineage()
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertEqual(out['reads'], []); self.assertEqual(out['journal'], [])
        self.assertFalse(out['state']['native026CReachingDefinitionEstablished'])
        self.assertTrue(out['state']['endpointEqualityIsNotAnObservation'])

    def test_lineage_aliases_are_explicitly_bank_conditional(self):
        rows = self.lineage()['state']['relations']
        self.assertEqual(rows[0]['aliasesIfLocalBank03F0'], ['r2', 'er1.low'])
        self.assertEqual(rows[1]['aliasesIfLocalBank03F0'], ['r4', 'er2.low'])
        self.assertTrue(all('aliases' not in row for row in rows))

    def test_lineage_generation_change_cannot_be_hidden_by_same_value(self):
        query = lineage_query(); query['after']['03F2']['generation'] = 'OtherSameValueWriter'
        out = self.lineage(query)
        self.assertEqual(out['reason'], 'FrameConditionViolated')
        self.assertEqual(out['state']['relations'][0]['relation'], 'GenerationChanged')

    def test_lineage_different_values_are_frame_conflict(self):
        query = lineage_query(); query['after']['03F4']['value'] ^= 1
        out = self.lineage(query)
        self.assertEqual(out['state']['relations'][1]['relation'], 'ValueContradictsFrame')
        self.assertEqual(out['status'], 'OutsideVerifiedScope')

    def test_lineage_stale_requested_writer_refuses(self):
        query = lineage_query(); query['requestedGenerations']['03F2'] = 'EarlierWriter'
        self.assertEqual(self.lineage(query)['state']['relations'][0]['relation'], 'StaleRequestedGeneration')

    def test_lineage_unknown_generation_is_not_native_owner(self):
        query = lineage_query(); query['before']['03F4']['generation'] = None
        out = self.lineage(query)
        self.assertEqual(out['status'], 'IndeterminateLineage')
        self.assertEqual(out['state']['relations'][1]['relation'], 'GenerationNotEstablished')

    def test_lineage_equal_numeric_domains_do_not_hide_raw_map_change(self):
        query = lineage_query(); raw = query['after']['03F2']['value']
        query['after']['03F2'].update(value=None, knownBits={str(bit): (raw >> bit) & 1 for bit in range(8)})
        out = self.lineage(query)
        self.assertEqual(out['state']['relations'][0]['relation'], 'KnowledgeChangedWithoutObservation')
        self.assertEqual(out['status'], 'IndeterminateLineage')

    def test_lineage_no_interference_missing_does_not_prove_retention(self):
        query = lineage_query(); query['noInterference'] = None
        out = self.lineage(query)
        self.assertEqual(out['reason'], 'InterferenceNotExcluded')
        self.assertTrue(all(x['relation'] == 'InterferenceNotExcluded' for x in out['state']['relations']))

    def test_lineage_cannot_promote_F2_to_length_or_native_owner(self):
        for claim in ('ParserLength', 'ContinuationReadsF2', 'Native026COwner', 'ActualTransmit'):
            query = lineage_query(); query['claim'] = claim
            out = self.lineage(query)
            self.assertEqual(out['reason'], 'UnestablishedLineageAuthorityClaim')
            self.assertFalse(out['state']['parserLengthEstablished'])

    def test_unknown_equal_lineage_values_are_not_invented(self):
        query = lineage_query()
        for field in ('before', 'after'):
            query[field]['03F4']['value'] = None
        out = self.lineage(query)
        self.assertEqual(out['state']['relations'][1]['relation'], 'ConditionalRetainedNotRead')
        self.assertIsNone(out['state']['relations'][1]['after']['value'])

    def test_no_hardware_or_execution_promotion_in_any_record(self):
        for case in cases():
            out = actual(case['operation'], case['input'])
            self.assertEqual(out['executionStatus'], 'EXECUTION_BLOCKED')
            self.assertFalse(out['firmwareReady']); self.assertEqual(out['cpuInstructionRetirements'], 0)
            self.assertIsNone(out['actualHardwareObservation'])

    def test_malformed_extended_snapshot_shape_refuses(self):
        value = fixture(); value.pop('registerKnownBits')
        with self.assertRaises(ValueError): self.body(value)

    def test_contradictory_register_knowledge_refuses(self):
        value = fixture(); value['registerKnownBits']['AH.0'] = 1 - (value['registers']['ah'] & 1)
        with self.assertRaises(ValueError): self.body(value)

    def test_register_bit_bool_or_out_of_range_refuses(self):
        for key, value in (('AL.0', True), ('AL.8', 0), ('DP.0', 1)):
            state = fixture(); state['registerKnownBits'][key] = value
            with self.assertRaises(ValueError): self.body(state)

    def test_wrong_memory_scope_or_type_refuses(self):
        value = fixture(); value['memory']['0051'] = 0
        with self.assertRaises(ValueError): self.body(value)
        value = fixture(); value['memory']['03F1'] = True
        with self.assertRaises(ValueError): self.body(value)

    def test_composed_snapshot_does_not_accept_host_partial_state_reseed(self):
        with self.assertRaises(ValueError): self.composed(fixture())

    def test_host_successor_or_source_scope_override_refuses(self):
        for key, override in (('successor', 0x2997), ('sourceScope', [0x2980, 0x2995])):
            value = fixture(); value[key] = override
            with self.assertRaises(ValueError): self.body(value)

    def test_stbuf_contradictory_operand_or_boolean_descriptor_refuses(self):
        query = stbuf_query(); query['prospectiveAL']['knownBits']['0'] = 0
        with self.assertRaises(ValueError): self.formal(query)
        query = stbuf_query(); query['dd'] = False
        with self.assertRaises(ValueError): self.formal(query)

    def test_formal_queries_reject_fabricated_frame_or_observation_keys(self):
        query = stbuf_query(); query['actualTransmission'] = 1
        with self.assertRaises(ValueError): self.formal(query)
        query = lineage_query(); query['ssp'] = 0x400
        with self.assertRaises(ValueError): self.lineage(query)

    def test_lineage_closed_two_slot_scope_refuses_extra_alias(self):
        query = lineage_query(); query['before']['03F3'] = deepcopy(query['before']['03F2'])
        with self.assertRaises(ValueError): self.lineage(query)


if __name__ == '__main__':
    unittest.main()
