"""Independent source obligations and substantive refusal controls."""
from copy import deepcopy
import importlib
from itertools import zip_longest
import unittest

from . import reference_oracle as reference
from .corpus import (fixture, slots, slot, partial, partial_slot, hypotheses_query,
    lineage_query, lifecycle_query, join_query, cases, SFR_KEYS, CONFIG_SITES)
from post_consumer_continuation.reference_oracle import stbuf_boundary_obligations as frozen_stbuf


def actual(operation, value):
    module = {'stcon_configuration': 'configuration', 'transmit_configuration_hypotheses': 'configuration',
        'stcon_writer_lineage': 'lineage', 'tx_lifecycle_obligations': 'tx_obligations',
        'stbuf2995_source_join': 'tx_obligations'}[operation]
    return getattr(importlib.import_module('.' + module, __package__), operation)(deepcopy(value))


class SourceTests(unittest.TestCase):
    def config(self, value=None): return actual('stcon_configuration', fixture() if value is None else value)
    def hypothesis(self, query=None): return actual('transmit_configuration_hypotheses', hypotheses_query() if query is None else query)
    def lineage(self, query=None): return actual('stcon_writer_lineage', lineage_query() if query is None else query)
    def lifecycle(self, query=None): return actual('tx_lifecycle_obligations', lifecycle_query() if query is None else query)
    def join(self, query=None): return actual('stbuf2995_source_join', join_query() if query is None else query)

    def test_all_sixteen_canonical_fields_against_independent_stream(self):
        producer = importlib.import_module('.analysis', __package__).canonical_records()
        expected = (reference.record(case, reference.evaluate(case)) for case in cases())
        sentinel = object()
        for index, (left, right) in enumerate(zip_longest(expected, producer, fillvalue=sentinel)):
            self.assertIsNot(left, sentinel, index); self.assertIsNot(right, sentinel, index)
            self.assertEqual(reference.canonical(left), reference.canonical(right), left['caseId'])
            self.assertEqual(len(right), 16)

    def test_all_inputs_are_immutable(self):
        for operation, query in (('stcon_configuration', fixture()), ('stcon_writer_lineage', lineage_query()),
            ('transmit_configuration_hypotheses', hypotheses_query()), ('tx_lifecycle_obligations', lifecycle_query()),
            ('stbuf2995_source_join', join_query())):
            module = {'stcon_configuration': 'configuration', 'transmit_configuration_hypotheses': 'configuration',
                'stcon_writer_lineage': 'lineage', 'tx_lifecycle_obligations': 'tx_obligations',
                'stbuf2995_source_join': 'tx_obligations'}[operation]
            function = getattr(importlib.import_module('.' + module, __package__), operation)
            saved = deepcopy(query)
            function(query)
            self.assertEqual(query, saved)

    def test_default_exact_path_and_software_intents(self):
        out = self.config()
        self.assertEqual([s['pc'] for s in out['steps']], [0x286D, 0x286F, 0x2871, 0x2873, 0x2876, 0x2878, 0x2880, 0x2882, 0x2884, 0x2888, 0x2889, 0x288B, 0x288C])
        self.assertEqual([out['state']['configurationIntents'][key]['value'] for key in SFR_KEYS], [0xDF, 0xDF, 0x12, 0x1C, 0x8C])
        self.assertEqual(len(out['journal']), 8)

    def test_alternate_exact_path_keeps_overwritten_local_events(self):
        value = fixture(); value['memory']['0356'] = 0
        out = self.config(value)
        self.assertEqual([s['pc'] for s in out['steps']], list(CONFIG_SITES))
        self.assertEqual([out['state']['configurationIntents'][key]['value'] for key in SFR_KEYS], [0xFB, 0xFB, 0x12, 0x31, 0xA1])
        self.assertEqual([e['after'] for e in out['journal'] if e['address'] == 0x208], [0x1C, 0x31])
        self.assertEqual(len(out['journal']), 10)

    def test_full_status_domain_selects_only_source_bit_one(self):
        for byte in range(256):
            value = fixture(); value['memory']['0356'] = byte
            out = self.config(value); bit = (byte >> 1) & 1
            self.assertEqual(out['state']['configurationIntents']['0050']['value'], 0x1C if bit else 0x31)
            self.assertEqual(out['state']['registers']['cf'], bit)
            self.assertEqual(out['state']['memory']['0356'], byte)

    def test_unknown_branch_keeps_prefix_without_intents(self):
        out = self.config(partial(fixture(), '0356', {}))
        self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', 0x2878))
        self.assertEqual(len(out['journal']), 3); self.assertEqual(len(out['steps']), 6)
        self.assertEqual(out['steps'][-1]['next'], None)
        self.assertFalse(any(e['space'] == 'SOFTWARE_SFR_INTENT' for e in out['journal']))

    def test_partial_known_selector_does_not_zero_fill_status(self):
        out = self.config(partial(fixture(), '0356', {1: 1, 7: 0}))
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertIsNone(out['state']['memory']['0356'])
        self.assertEqual(out['state']['knownBits']['0356.7'], 0)

    def test_local_bank_must_be_exact_and_not_mask_equivalent(self):
        for lrb in (None, 0x40, 0x7E, 0x2041):
            value = fixture(); value['registers']['lrb'] = lrb
            out = self.config(value)
            self.assertEqual(out['reason'], 'LocalBank0208NotEstablished'); self.assertEqual(out['journal'], [])

    def test_scb_unknown_refuses_only_at_reached_pointer(self):
        value = fixture(); value['registers']['scb'] = None
        out = self.config(value)
        self.assertEqual((out['boundary'], out['reason']), (0x2873, 'PointerBankNotEstablished'))
        self.assertEqual(len(out['steps']), 3); self.assertEqual(len(out['journal']), 2)
        self.assertEqual(out['state']['registers']['al'], 0xDF)

    def test_ordinary_byte_unknown_preserves_two_initial_writes(self):
        value = fixture(); value['assumptions']['ordinaryByteSemantics'] = None
        out = self.config(value)
        self.assertEqual(out['boundary'], 0x2871)
        self.assertEqual([e['address'] for e in out['journal']], [0x208, 0x209])
        self.assertEqual(out['reads'], [])

    def test_no_interference_refuses_before_local_writes(self):
        value = fixture(); value['assumptions']['noInterference'] = False
        out = self.config(value)
        self.assertEqual(out['reason'], 'NoInterferencePremiseNotEstablished'); self.assertEqual(out['journal'], [])

    def test_scb6_aliases_B4_B5_without_shadow_pointer(self):
        value = fixture(); value['registers']['scb'] = 6
        partial(value, '00B4', {0: 1}); partial(value, '00B5', {7: 1})
        out = self.config(value)
        self.assertEqual((out['state']['memory']['00B4'], out['state']['memory']['00B5']), (0x56, 3))
        self.assertEqual(out['pointerState']['dataAddress'], 0xB4)
        self.assertEqual(out['pointerState']['value'], 0x356)

    def test_all_scb_pointer_word_writes_are_distinct_from_intents(self):
        for bank in range(8):
            value = fixture(); value['registers']['scb'] = bank
            out = self.config(value)
            pointer = [e for e in out['journal'] if e['kind'] == 'PointingRegisterWrite']
            self.assertEqual([(e['address'], e['widthBits']) for e in pointer], [(0x84 + bank * 8, 16)])
            self.assertEqual(len([e for e in out['journal'] if e['space'] == 'SOFTWARE_SFR_INTENT']), 5)

    def test_incoming_dd_does_not_change_literal_movb_width(self):
        for dd in (None, 0, 1):
            value = fixture(); value['registers']['dd'] = dd
            out = self.config(value)
            self.assertEqual(out['steps'][1]['afterRegisters']['dd'], dd)
            self.assertEqual(out['steps'][2]['afterRegisters']['dd'], 0)
            self.assertEqual([e['widthBits'] for e in out['journal'][:2]], [8, 8])

    def test_AH_and_HC_retained_without_physical_SF_assignment(self):
        value = fixture(); value['registers'].update(ah=None, hc=None)
        value['registerKnownBits'] = {key: bit for key, bit in value['registerKnownBits'].items() if not key.startswith('AH.')}
        value['registerKnownBits']['AH.6'] = 1
        out = self.config(value)
        self.assertIsNone(out['state']['registers']['ah']); self.assertIsNone(out['state']['registers']['hc'])
        self.assertEqual(out['state']['registerKnownBits']['AH.6'], 1)
        self.assertNotIn('sf', out['state']['registers'])

    def test_same_declared_intents_remain_separate_generations(self):
        value = fixture(); value['configurationIntents'] = slots(True)
        out = self.config(value); events = [e for e in out['journal'] if e['space'] == 'SOFTWARE_SFR_INTENT']
        self.assertEqual(len(events), 5); self.assertTrue(all(e['sameDeclaredValue'] is True for e in events))
        self.assertTrue(all('sameValue' not in e for e in events))
        self.assertEqual(len({e['afterGeneration'] for e in events}), 5)

    def test_declared_before_is_not_readback_and_bits_preserved_in_journal(self):
        value = fixture(); partial_slot(value['configurationIntents']['0050'], {0: 0, 7: 1})
        out = self.config(value); event = next(e for e in out['journal'] if e['address'] == 0x50)
        self.assertIsNone(event['before']); self.assertIsNone(event['sameDeclaredValue'])
        self.assertEqual(event['knownBitsBefore'], {'0': 0, '7': 1}); self.assertEqual(event['knownBitsAfter'], {})
        self.assertFalse(any(r['address'] in (0x48, 0x49, 0x4A, 0x50, 0x54) and r['space'] == 'DATA' for r in out['reads']))

    def test_every_writer_has_full_after_state(self):
        out = self.config()
        self.assertEqual(len(out['intermediateStates']), len(out['journal']))
        for event, state in zip(out['journal'], out['intermediateStates']):
            self.assertEqual(event['ordinal'], state['afterOrdinal'])
            if event['space'] == 'SOFTWARE_SFR_INTENT':
                self.assertEqual(state['state']['configurationIntents'][f"{event['address']:04X}"]['generation'], event['afterGeneration'])

    def test_own_namespace_in_overwritten_data_and_intent_is_refused(self):
        for address in ('0208', '0084'):
            value = fixture(); value['generations'][address] = 'ConditionalEffect:stcon_configuration:0000:1'
            self.assertEqual(self.config(value)['reason'], 'EffectNamespaceAlreadyPresent')
        value = fixture(); value['configurationIntents']['0050']['generation'] = 'ConditionalEffect:stcon_configuration:0000:1'
        self.assertEqual(self.config(value)['journal'], [])

    def test_no_instruction_or_intent_after_config_boundary(self):
        out = self.config()
        self.assertEqual((out['boundary'], out['stopBoundary']), (0x288E, 'STOP_BEFORE_DATA4700_288E'))
        self.assertEqual(out['steps'][-1]['next'], 0x288E)
        self.assertFalse(any(e['address'] in (0x51, 0x4700) for e in out['journal']))
        self.assertEqual(out['stbufStopBoundary'], 'STOP_BEFORE_STBUF_2995')

    def test_configuration_reads_only_selector_and_local_registers(self):
        out = self.config()
        self.assertEqual([r['address'] for r in out['reads'] if r['space'] == 'DATA'], [0x356, 0x208, 0x209])
        self.assertEqual([r['pc'] for r in out['reads']], [0x2876, 0x2876, 0x2888, 0x288B])

    def test_status0356_not_a_native_owned_mode_by_assumption(self):
        value = fixture(); value['generations']['0356'] = None
        out = self.config(value)
        read = next(r for r in out['reads'] if r['address'] == 0x356)
        self.assertEqual(read['generations'], [None])
        self.assertIn('NativeConfigurationOwnerNotEstablished', out['unresolvedConstraints'])

    def test_STCON_full_byte_sweep_uses_only_intact_field_relations(self):
        for byte in range(256):
            query = hypotheses_query(); query['configurationIntents']['0050']['value'] = byte
            decoded = self.hypothesis(query)['state']['decoded']
            self.assertEqual(decoded['serialMode'], 'Synchronous' if byte & 2 else 'UART')
            self.assertIsNone(decoded['stconBit7Meaning']); self.assertIsNone(decoded['effectiveBaudRate'])
            self.assertNotIn('parityEnabled', decoded); self.assertNotIn('dataBitCount', decoded)

    def test_STTMC_full_byte_sweep_has_corrected_mode_table(self):
        modes = ('AutoReloadTimer', 'TransmissionBaudGenerator', 'TransmissionReceivingBaudGenerator', 'TransmissionReceivingBaudGenerator')
        divisors = (2, 4, 8, 16, 32, 128, 512, 512)
        for byte in range(256):
            query = hypotheses_query(); query['configurationIntents']['004A']['value'] = byte
            decoded = self.hypothesis(query)['state']['decoded']
            self.assertEqual(decoded['baudGeneratorMode'], modes[byte & 3])
            self.assertEqual(decoded['baudGeneratorClockDivisor'], divisors[byte >> 5])

    def test_intent12_is_combined_BRG_not_current_running_clock(self):
        out = self.hypothesis(); d = out['state']['decoded']
        self.assertEqual((d['baudGeneratorModeCode'], d['baudGeneratorMode'], d['baudGeneratorRunBit']), (2, 'TransmissionReceivingBaudGenerator', 1))
        self.assertEqual(d['sttmcDocumentedReadBits'], {'2': 1, '3': 1})
        self.assertEqual(out['state']['configurationIntents']['004A']['value'], 0x12)
        self.assertIsNone(out['actualPeripheralClockEvent'])

    def test_partial_mode_or_divisor_can_have_consensus_without_code(self):
        query = hypotheses_query(); partial_slot(query['configurationIntents']['004A'], {1: 1})
        d = self.hypothesis(query)['state']['decoded']
        self.assertIsNone(d['baudGeneratorModeCode']); self.assertEqual(d['baudGeneratorMode'], 'TransmissionReceivingBaudGenerator')
        partial_slot(query['configurationIntents']['004A'], {7: 1, 6: 1})
        d = self.hypothesis(query)['state']['decoded']
        self.assertIsNone(d['baudGeneratorClockCode']); self.assertEqual(d['baudGeneratorClockDivisor'], 512)

    def test_STCON_normal_multiprocessor_sync_fields_not_conflated(self):
        for byte, protocol in ((0x1C, 'Normal'), (0x31, 'Multiprocessor')):
            query = hypotheses_query(); query['configurationIntents']['0050']['value'] = byte
            d = self.hypothesis(query)['state']['decoded']; self.assertEqual(d['uartProtocol'], protocol)
            self.assertEqual(d['multiprocessorBit3Ignored'], protocol == 'Multiprocessor')
        query = hypotheses_query(); query['configurationIntents']['0050']['value'] = 0x12
        d = self.hypothesis(query)['state']['decoded']; self.assertEqual(d['synchronousClockRole'], 'Master')
        self.assertIsNone(d['uartStopLengthCode']); self.assertIsNone(d['uartProtocol'])

    def test_STCON_parity_polarity_and_bit7_remain_unknown(self):
        query = hypotheses_query(); query['configurationIntents']['0050']['value'] = 0xFF
        d = self.hypothesis(query)['state']['decoded']
        self.assertEqual(d['paritySelectionBit5'], 1); self.assertTrue(d['bit6MeaningfulWhenBit5One'])
        self.assertIsNone(d['stconBit7Meaning']); self.assertNotIn('parityOdd', d)

    def test_receiver_permission_not_transferred_to_transmitter(self):
        query = hypotheses_query(); query['configurationIntents']['0054']['value'] = 0x80
        d = self.hypothesis(query)['state']['decoded']
        self.assertEqual(d['srconReceivingPermission'], 'ReceivingAllowed'); self.assertIsNone(d['stconBit7Meaning'])
        self.assertNotIn('transmitterEnabled', d)

    def test_counter_reload_equality_is_declared_candidate_relationship(self):
        query = hypotheses_query(); self.assertTrue(self.hypothesis(query)['state']['decoded']['baudCounterAndReloadDeclaredEqual'])
        query['configurationIntents']['0048']['value'] = 0
        self.assertFalse(self.hypothesis(query)['state']['decoded']['baudCounterAndReloadDeclaredEqual'])
        partial_slot(query['configurationIntents']['0048'], {})
        self.assertIsNone(self.hypothesis(query)['state']['decoded']['baudCounterAndReloadDeclaredEqual'])

    def test_reader_predicates_mask_read_one_bits_without_performing_reads(self):
        query = hypotheses_query(); query['configurationIntents']['004A']['value'] = 0x1E
        out = self.hypothesis(query); predicates = out['state']['reviewedMaskedPredicates']
        self.assertEqual([p['sourcePc'] for p in predicates], [0x3FDF, 0x3FE7, 0x3FEB, 0x3FF1])
        self.assertTrue(all(p['matches'] for p in predicates))
        self.assertTrue(all(p['requiredGuard'] == 'DATA0356.1=1_NotObserved' for p in predicates))
        self.assertEqual(out['reads'], []); self.assertEqual(out['steps'], [])

    def test_partial_hypothesis_bytes_preserve_raw_none_and_unknown_fields(self):
        query = hypotheses_query(); partial_slot(query['configurationIntents']['0050'], {1: 0})
        out = self.hypothesis(query)
        self.assertIsNone(out['state']['configurationIntents']['0050']['value'])
        self.assertEqual(out['state']['decoded']['serialMode'], 'UART')
        self.assertIn('UnknownDeclaredByte:0050', out['state']['unknownFields'])

    def test_manufacturer_reset_never_assigns_current_configuration(self):
        query = hypotheses_query(); query['configurationIntents'] = slots()
        out = self.hypothesis(query)
        self.assertTrue(all(s['value'] is None for s in out['state']['configurationIntents'].values()))
        self.assertIsNone(out['state']['actualReady']); self.assertIsNone(out['state']['actualConfigurationOwner'])

    def test_all_seven_lifecycle_lists_are_independent_source_catalog(self):
        for situation, expected in reference.SITUATIONS.items():
            state = self.lifecycle(lifecycle_query(situation))['state']
            self.assertEqual(state['documentedRules'], expected['documentedRules'])
            self.assertEqual(state['unknownRules'], expected['unknownRules'])

    def test_TX_READY_at_start_is_not_TX_complete_interrupt(self):
        state = self.lifecycle()['state']
        self.assertIn('TX_READY_AT_START_IRQ_BIT2', state['documentedRules'])
        end = self.lifecycle(lifecycle_query('Completion'))['state']
        self.assertIn('TX_COMPLETE_INTERRUPT', end['unknownRules'])

    def test_buffered_next_start_does_not_define_full_queue_collision(self):
        state = self.lifecycle(lifecycle_query('BusyWrite'))['state']
        self.assertIn('BUFFERED_NEXT_START_RAISES_TX_READY', state['documentedRules'])
        self.assertIn('FULL_HOLDING_BUFFER_WRITE_COLLISION', state['unknownRules'])
        self.assertNotIn('fifoDepth', state)

    def test_TX_RX_and_BRG_allocations_are_separate(self):
        state = self.lifecycle()['state']
        self.assertEqual((state['txReadyVector'], state['txReadyBit']), (0xC, 2))
        self.assertEqual((state['rxReadyVector'], state['rxReadyBit']), (0xA, 1))
        self.assertEqual((state['txBrgVector'], state['txBrgBit']), (0x24, 14))
        self.assertIsNone(state['iePolarityResolution'])

    def test_ACK_reassertion_collision_not_invented(self):
        for situation, unknown in (('Acknowledge', 'STBUF_WRITE_SPECIFIC_ACK'),
            ('Reassertion', 'LEVEL_REASSERT_WITHOUT_NEW_DATA'), ('Collision', 'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY')):
            state = self.lifecycle(lifecycle_query(situation))['state']
            self.assertIn(unknown, state['unknownRules']); self.assertIsNone(state['actualPendingGeneration'])

    def test_TX_mode_change_does_not_borrow_receiver_safe_rule(self):
        state = self.lifecycle(lifecycle_query('ModeChange'))['state']
        self.assertIn('RX_MODE_CHANGE_REQUIRES_SREN_ZERO', state['documentedRules'])
        self.assertIn('TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER', state['unknownRules'])

    def test_lifecycle_authority_and_old_RX000A_TX_claims_refuse(self):
        for claim in ('ActualTx', 'Fifo', 'TxCompleteIrq', 'AckByWrite', 'Rx000ATx'):
            query = lifecycle_query(); query['claim'] = claim
            out = self.lifecycle(query); self.assertEqual(out['reason'], 'UnestablishedTransmitAuthorityClaim')
            self.assertEqual(out['journal'], []); self.assertIsNone(out['actualTxIrqDelivery'])

    def test_actual_ECU_applicability_is_not_selected_by_claim(self):
        query = lifecycle_query(); query['applicability'] = 'ActualEcuVerified'
        out = self.lifecycle(query)
        self.assertEqual(out['status'], 'OutsideVerifiedScope'); self.assertIsNone(out['state']['physicalApplicability'])

    def test_configuration_claim_refusal_retains_documentary_decoding(self):
        query = hypotheses_query(); query['claim'] = 'ActualOwner'
        out = self.hypothesis(query)
        self.assertEqual(out['status'], 'OutsideVerifiedScope')
        self.assertEqual(out['state']['decoded']['baudGeneratorModeCode'], 2)
        self.assertIsNone(out['state']['actualConfigurationOwner'])

    def test_lineage_config_writer_source_value_and_descriptor(self):
        query = lineage_query(); out = self.lineage(query)
        self.assertEqual(out['configurationChecks'][-1]['relation'], 'ConditionalConfigurationWriterAtBoundary')
        self.assertEqual(out['journal'][0]['sourcePc'], 0x2889)
        for field, value, reason in (('value', 0x1D, 'ConfigurationSourceValueMismatch'), ('dd', 1, 'ByteDescriptorNotEstablished')):
            query = lineage_query(); query['events'][0][field] = value
            out = self.lineage(query); self.assertEqual(out['reason'], reason)
            self.assertEqual(out['boundary'], 0); self.assertEqual(out['journal'], [])

    def test_lineage_unknown_literal_cannot_prove_config_path(self):
        query = lineage_query(); query['events'][0]['value'] = None
        self.assertEqual(self.lineage(query)['reason'], 'ConfigurationSourceValueMismatch')

    def test_lineage_same_value_writer_has_new_distinct_label(self):
        query = lineage_query(); query['initial'] = slot(0x1C, 'Earlier')
        out = self.lineage(query)
        self.assertTrue(out['journal'][0]['sameDeclaredValue'])
        self.assertEqual(out['state']['lastSlot']['generation'], 'Config1')

    def test_lineage_repeated_same_value_events_are_not_deduplicated(self):
        query = lineage_query(); query['events'].insert(1, {'kind': 'ConfigIntent', 'id': 'second',
            'path': 'Bit1Set', 'value': 0x1C, 'generation': 'Config2', 'dd': 0})
        query['events'][-1]['requestedGeneration'] = 'Config2'
        out = self.lineage(query)
        self.assertEqual(len(out['journal']), 2); self.assertTrue(out['journal'][-1]['sameDeclaredValue'])
        self.assertEqual(out['configurationChecks'][-1]['currentSlot']['generation'], 'Config2')

    def test_lineage_requested_alternate_does_not_become_reviewed_writer(self):
        query = lineage_query(); query['events'].insert(1, {'kind': 'AlternateIntent', 'id': 'alternate',
            'address': 0x50, 'widthBits': 8, 'value': 0x1C, 'generation': 'Alt', 'dd': 0})
        query['events'][-1]['requestedGeneration'] = 'Alt'
        self.assertEqual(self.lineage(query)['configurationChecks'][-1]['relation'], 'AlternateWriterNotReviewedConfiguration')

    def test_lineage_word_0051_aligns_to_0050_without_STBUF_latch(self):
        query = lineage_query(); query['events'].insert(1, {'kind': 'AlternateIntent', 'id': 'word',
            'address': 0x51, 'widthBits': 16, 'value': 0xABCD, 'generation': 'Alt', 'dd': 1})
        out = self.lineage(query)
        self.assertEqual(out['state']['lastSlot']['value'], 0xCD)
        self.assertEqual(out['journal'][-1]['address'], 0x50)
        self.assertNotIn('0051', out['state']); self.assertIsNone(out['actualBufferWrite'])

    def test_lineage_nonoverlap_preserves_target_but_reserves_generation(self):
        query = lineage_query(); query['events'].insert(1, {'kind': 'AlternateIntent', 'id': 'other',
            'address': 0x54, 'widthBits': 8, 'value': 0, 'generation': 'Other', 'dd': 0})
        query['events'].insert(2, {'kind': 'ConfigIntent', 'id': 'reuse', 'path': 'Bit1Set', 'value': 0x1C, 'generation': 'Other', 'dd': 0})
        out = self.lineage(query)
        self.assertEqual((out['boundary'], out['reason']), (2, 'WriterGenerationReused'))
        self.assertEqual(len(out['journal']), 2); self.assertEqual(out['state']['lastSlot']['generation'], 'Config1')

    def test_lineage_initial_label_reuse_refuses(self):
        query = lineage_query(); query['events'][0]['generation'] = query['initial']['generation']
        self.assertEqual(self.lineage(query)['reason'], 'WriterGenerationReused')

    def test_lineage_stale_missing_and_unknown_writer_are_separate(self):
        query = lineage_query(); query['events'][-1]['requestedGeneration'] = 'Old'
        self.assertEqual(self.lineage(query)['configurationChecks'][-1]['relation'], 'StaleRequestedGeneration')
        query = lineage_query(); query['events'][0]['generation'] = None
        self.assertEqual(self.lineage(query)['configurationChecks'][-1]['relation'], 'MissingConfigurationGeneration')
        query = lineage_query(); query['events'].insert(1, {'kind': 'UnknownWriter', 'id': 'unknown'})
        self.assertEqual(self.lineage(query)['configurationChecks'][-1]['relation'], 'UnknownInterveningWriter')

    def test_lineage_no_interference_is_obligation_not_event(self):
        query = lineage_query(); query['noInterference'] = None
        out = self.lineage(query)
        self.assertEqual(out['configurationChecks'][-1]['relation'], 'InterferenceNotExcluded')
        self.assertEqual(out['reads'], []); self.assertEqual(out['steps'], [])

    def test_lineage_history_includes_boundaries_zero_based(self):
        out = self.lineage()
        self.assertEqual([row['eventIndex'] for row in out['intermediateStates']], [0, 1])
        self.assertEqual([row['ordinal'] for row in out['journal']], [1])
        self.assertIsNone(out['boundary'])

    def test_lineage_global_refusal_does_not_process_writers(self):
        query = lineage_query(); query['claim'] = 'ResetOwner'
        out = self.lineage(query)
        self.assertEqual(out['state']['lastSlot'], query['initial']); self.assertEqual(out['journal'], [])
        self.assertEqual(out['intermediateStates'], [])

    def test_all_true_join_remains_conditional_without_observations(self):
        out = self.join()
        self.assertEqual(out['status'], 'CompleteConditional')
        self.assertIsNone(out['state']['actualNativeConfigurationOwner']); self.assertIsNone(out['state']['actualTxReadiness'])
        self.assertIsNone(out['actualBufferWrite']); self.assertEqual(out['actualPeripheralOperations'], 0)

    def test_join_preserves_all_four_nested_results_exactly(self):
        query = join_query(); out = self.join(query)
        self.assertEqual(out['state']['configuration'], self.hypothesis(query['configurationQuery']))
        self.assertEqual(out['state']['lineage'], self.lineage(query['lineageQuery']))
        self.assertEqual(out['state']['lifecycle'], self.lifecycle(query['lifecycleQuery']))
        self.assertEqual(out['state']['stbuf'], frozen_stbuf(query['stbufQuery']))

    def test_join_global_refusal_keeps_full_nested_results(self):
        query = join_query(); query['claim'] = 'RuntimeAdmission'
        out = self.join(query)
        self.assertEqual(out['reason'], 'UnestablishedTransmitAuthorityClaim')
        self.assertEqual(out['state']['stbuf'], frozen_stbuf(query['stbufQuery']))
        self.assertTrue(out['state']['lineage']['configurationChecks'])

    def test_join_raw_bits_and_generation_mismatch_are_not_hidden(self):
        for field, value in (('value', 0x31), ('knownBits', {'0': 0}), ('generation', 'Other')):
            query = join_query(); query['configurationQuery']['configurationIntents']['0050'][field] = value
            self.assertEqual(self.join(query)['reason'], 'ConfigurationLineageMismatch')

    def test_join_requires_current_requested_configuration_generation(self):
        query = join_query(); query['lineageQuery']['events'][-1]['requestedGeneration'] = 'Earlier'
        self.assertEqual(self.join(query)['reason'], 'ConfigurationWriterAt2995NotEstablished')

    def test_join_no_boundary_check_is_not_current_owner(self):
        query = join_query(); query['lineageQuery']['events'].pop()
        self.assertEqual(self.join(query)['reason'], 'ConfigurationWriterAt2995NotEstablished')

    def test_join_unknown_hardware_prerequisites_remain_unestablished(self):
        query = join_query()
        from post_consumer_continuation.corpus import stbuf_query
        query['stbufQuery'] = stbuf_query()
        self.assertEqual(self.join(query)['reason'], 'StbufPrerequisitesNotEstablished')

    def test_join_nested_byte_word_refusal_is_not_repaired(self):
        query = join_query(); query['stbufQuery']['dd'] = 1
        out = self.join(query)
        self.assertEqual(out['reason'], 'NestedSourceObligationRefused')
        self.assertEqual(out['state']['stbuf']['state']['descriptorDD'], 1)

    def test_all_authority_fields_are_null_and_counters_zero(self):
        for op, value in (('stcon_configuration', fixture()), ('stcon_writer_lineage', lineage_query()),
            ('transmit_configuration_hypotheses', hypotheses_query()), ('tx_lifecycle_obligations', lifecycle_query()), ('stbuf2995_source_join', join_query())):
            out = actual(op, value)
            for key in ('actualHardwareObservation', 'actualBufferWrite', 'actualTransmission', 'actualTxCompletion', 'actualTxIrqDelivery', 'actualPeripheralClockEvent'):
                self.assertIsNone(out[key])
            self.assertIs(type(out['actualPeripheralOperations']), int); self.assertEqual(out['actualPeripheralOperations'], 0)
            self.assertEqual(out['executionStatus'], 'EXECUTION_BLOCKED'); self.assertFalse(out['firmwareReady'])

    def test_missing_wrong_and_type_confused_source_bindings_refuse(self):
        for operation, maker in (('stcon_writer_lineage', lineage_query), ('transmit_configuration_hypotheses', hypotheses_query),
            ('tx_lifecycle_obligations', lifecycle_query), ('stbuf2995_source_join', join_query)):
            for binding, reason in ((None, 'SourceBindingMissing'), ({}, 'SourceBindingMismatch'), ({'baseSha': False}, 'SourceBindingMismatch')):
                query = maker(); query['sourceBinding'] = binding
                self.assertEqual(actual(operation, query)['reason'], reason)

    def test_closed_configuration_state_rejects_fake_STBUF_memory(self):
        value = fixture(); value['memory']['0051'] = 0
        with self.assertRaises(ValueError): self.config(value)

    def test_closed_SFR_slots_reject_extra_or_contradictory_knowledge(self):
        query = hypotheses_query(); query['configurationIntents']['0051'] = slot(1)
        with self.assertRaises(ValueError): self.hypothesis(query)
        query = hypotheses_query(); query['configurationIntents']['0050']['knownBits']['0'] = 1
        with self.assertRaises(ValueError): self.hypothesis(query)

    def test_register_partial_knowledge_contradiction_refuses(self):
        value = fixture(); raw = value['registers']['ah']; value['registerKnownBits']['AH.0'] = 1 - (raw & 1)
        with self.assertRaises(ValueError): self.config(value)

    def test_timeline_duplicate_ids_bounds_and_wrong_descriptor_types(self):
        query = lineage_query(); query['events'][1]['id'] = query['events'][0]['id']
        with self.assertRaises(ValueError): self.lineage(query)
        query = lineage_query(); query['events'] = []
        with self.assertRaises(ValueError): self.lineage(query)
        query = lineage_query(); query['events'][0]['dd'] = False
        with self.assertRaises(ValueError): self.lineage(query)

    def test_global_refusal_still_validates_closed_event_shapes(self):
        query = lineage_query(); query['claim'] = 'ActualTx'; query['events'][0]['extra'] = 1
        with self.assertRaises(ValueError): self.lineage(query)

    def test_join_global_claim_does_not_hide_malformed_nested_input(self):
        query = join_query(); query['claim'] = 'ActualTx'; query['stbufQuery']['desiredHostPC'] = 0x2997
        with self.assertRaises(ValueError): self.join(query)

    def test_join_nested_input_class_cannot_be_substituted(self):
        query = join_query(); query['configurationQuery']['inputClass'] = 'SymbolicInput'
        with self.assertRaises(ValueError): self.join(query)

    def test_lifecycle_has_no_physical_observation_input(self):
        query = lifecycle_query(); query['actualTransmission'] = 1
        with self.assertRaises(ValueError): self.lifecycle(query)


if __name__ == '__main__':
    unittest.main()
