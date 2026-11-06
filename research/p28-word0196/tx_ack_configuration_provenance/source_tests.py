"""Source-qualified independent comparisons; implementation imports are deferred to tests."""
from copy import deepcopy
import importlib
import unittest

from . import reference_oracle as reference
from .corpus import (fixture, reaching_query, ack_query, join_query, cases, partial,
    partial_slot, register_partial, SOURCE_BINDING, READBACK_KEYS, READER_SITES,
    PRODUCER_SITES, PATHS)

MODULES = {'tx_configuration_reader': 'reader_cfg', 'mode_bit1_producer': 'mode_producer',
    'tx_configuration_reaching_definitions': 'reaching_definitions',
    'tx_ack_documentary_obligations': 'tx_ack_rules',
    'stbuf2995_configuration_provenance': 'source_join'}


def resolve(operation):
    return getattr(importlib.import_module('.' + MODULES[operation], __package__), operation)


class SourceTests(unittest.TestCase):
    def check(self, operation, query):
        expected = reference.OPERATIONS[operation](deepcopy(query))
        actual = resolve(operation)(deepcopy(query))
        self.assertEqual(reference.canonical(expected), reference.canonical(actual))
        return actual

    def reader(self, query=None):
        return self.check('tx_configuration_reader', fixture() if query is None else query)

    def producer(self, query=None):
        return self.check('mode_bit1_producer', fixture('Compare3cb') if query is None else query)

    def reaching(self, query=None):
        return self.check('tx_configuration_reaching_definitions', reaching_query() if query is None else query)

    def ack(self, query=None):
        return self.check('tx_ack_documentary_obligations', ack_query() if query is None else query)

    def join(self, query=None):
        return self.check('stbuf2995_configuration_provenance', join_query() if query is None else query)

    def malformed(self, operation, query):
        with self.assertRaises(ValueError): resolve(operation)(deepcopy(query))
        with self.assertRaises(ValueError): reference.OPERATIONS[operation](deepcopy(query))

    def test_full_canonical_corpus_exact_equality(self):
        ids = set()
        for case in cases():
            self.assertNotIn(case['id'], ids); ids.add(case['id'])
            expected = reference.record(case, reference.evaluate(case))
            actual = reference.record(case, resolve(case['operation'])(deepcopy(case['input'])))
            self.assertEqual(reference.canonical(expected), reference.canonical(actual), case['id'])

    def test_all_inputs_are_immutable(self):
        values = [('tx_configuration_reader', fixture()), ('mode_bit1_producer', fixture('Compare3cb')),
            ('mode_bit1_producer', partial(fixture('SymbolicCarryTail'), '0356', {1: 1})),
            ('tx_configuration_reaching_definitions', reaching_query()),
            ('tx_ack_documentary_obligations', ack_query()), ('stbuf2995_configuration_provenance', join_query())]
        for operation, query in values:
            before = deepcopy(query)
            resolve(operation)(query)  # The original object is essential to detect mutation.
            self.assertEqual(reference.canonical(before), reference.canonical(query))

    def test_reader_all_match_exact_path(self):
        value = self.reader()
        self.assertEqual([step['pc'] for step in value['steps']], list(READER_SITES))
        self.assertEqual((value['boundary'], value['outcome']), (0x3FF7, 'AllConfigurationChecksMatch'))

    def test_reader_bypass_preserves_registers(self):
        query = fixture(); query['memory']['0356'] = 0
        value = self.reader(query)
        self.assertEqual(len(value['steps']), 3)
        for key in ('al', 'ah', 'zf', 'hc', 'dd', 'mie', 'lrb', 'ssp', 'usp'):
            self.assertEqual(value['state']['registers'][key], query['registers'][key])
        self.assertEqual(value['state']['registers']['cf'], 0)

    def test_reader_bypass_suppresses_all_sfr_reads(self):
        query = fixture(); query['memory']['0356'] = 0
        value = self.reader(query)
        self.assertFalse(any(row['space'] == 'SYMBOLIC_SFR_READBACK' for row in value['reads']))

    def test_reader_unknown_guard_prefix(self):
        query = partial(fixture(), '0356', {})
        value = self.reader(query)
        self.assertEqual((value['status'], value['boundary']), ('IndeterminateBranch', 0x3FD9))
        self.assertEqual(value['steps'][-1]['next'], None)
        self.assertEqual(len(value['journal']), 1)

    def test_reader_partial_known_guard(self):
        for bit in (0, 1):
            value = self.reader(partial(fixture(), '0356', {1: bit}))
            self.assertEqual(len(value['steps']), 3 if bit == 0 else 15)

    def test_reader_sttmc_failure_short_circuits(self):
        query = fixture(); query['sfrReadbacks']['004A']['value'] = 0
        value = self.reader(query)
        self.assertEqual((value['outcome'], len(value['steps'])), ('MismatchSTTMC', 7))
        self.assertEqual([r['address'] for r in value['reads'] if r['space'] == 'SYMBOLIC_SFR_READBACK'], [0x4A])

    def test_reader_stcon_failure_short_circuits(self):
        query = fixture(); query['sfrReadbacks']['0050']['value'] = 0
        value = self.reader(query)
        self.assertEqual((value['outcome'], len(value['steps'])), ('MismatchSTCON', 11))
        self.assertEqual([r['address'] for r in value['reads'] if r['space'] == 'SYMBOLIC_SFR_READBACK'], [0x4A, 0x50])

    def test_reader_srcon_failure_keeps_al(self):
        query = fixture(); query['sfrReadbacks']['0054']['value'] = 0
        value = self.reader(query)
        self.assertEqual((value['outcome'], len(value['steps'])), ('MismatchSRCON', 13))
        self.assertEqual(value['state']['registers']['al'], 0x1C)

    def test_reader_sttmr_failure_keeps_al(self):
        query = fixture(); query['sfrReadbacks']['0049']['value'] = 0
        value = self.reader(query)
        self.assertEqual((value['outcome'], len(value['steps'])), ('MismatchSTTMR', 15))
        self.assertEqual(value['state']['registers']['al'], 0x1C)

    def test_reader_ignores_sttmc_read_one_positions(self):
        for byte in (0x12, 0x16, 0x1A, 0x1E):
            query = fixture(); query['sfrReadbacks']['004A']['value'] = byte
            self.assertEqual(self.reader(query)['outcome'], 'AllConfigurationChecksMatch')

    def test_reader_stcon_bit7_masked_not_tx_permission(self):
        query = fixture(); query['sfrReadbacks']['0050']['value'] = 0x9C
        self.assertEqual(self.reader(query)['outcome'], 'AllConfigurationChecksMatch')

    def test_reader_does_not_inject_read_one_bits(self):
        query = fixture(); query['sfrReadbacks']['004A']['value'] = 0x12
        value = self.reader(query)
        row = next(r for r in value['reads'] if r['space'] == 'SYMBOLIC_SFR_READBACK')
        self.assertEqual((row['value'], row['bytes']), (0x12, [0x12]))

    def test_reader_partial_mask_can_establish_equality(self):
        query = fixture(); partial_slot(query['sfrReadbacks']['004A'],
            {bit: (0x12 >> bit) & 1 for bit in (0, 1, 4, 5, 6, 7)})
        self.assertEqual(self.reader(query)['outcome'], 'AllConfigurationChecksMatch')

    def test_reader_partial_compare_independent_cf_and_zf(self):
        query = fixture(); partial_slot(query['sfrReadbacks']['0054'], {7: 0})
        value = self.reader(query)
        self.assertEqual(value['outcome'], 'MismatchSRCON')
        self.assertEqual((value['state']['registers']['cf'], value['state']['registers']['zf']), (1, 0))

    def test_reader_unknown_match_does_not_guess_branch(self):
        query = fixture(); partial_slot(query['sfrReadbacks']['004A'], {4: 1})
        value = self.reader(query)
        self.assertEqual((value['status'], value['boundary']), ('IndeterminateBranch', 0x3FE1))

    def test_reader_unknown_raw_with_full_bits_stays_raw_unknown(self):
        query = fixture(); partial_slot(query['sfrReadbacks']['0050'], {bit: (0x1C >> bit) & 1 for bit in range(8)})
        value = self.reader(query)
        self.assertIsNone(value['state']['sfrReadbacks']['0050']['value'])
        row = next(r for r in value['reads'] if r['address'] == 0x50)
        self.assertIsNone(row['value']); self.assertEqual(value['state']['registers']['al'], 0x1C)

    def test_reader_intent_does_not_replace_supplied_readback(self):
        query = fixture(); query['configurationIntents']['0050']['value'] = 0x1C
        query['sfrReadbacks']['0050']['value'] = 0x31
        self.assertEqual(self.reader(query)['outcome'], 'MismatchSTCON')

    def test_reader_no_lrb_or_usp_gate(self):
        query = fixture(); query['registers'].update(lrb=None, usp=None)
        self.assertEqual(self.reader(query)['outcome'], 'AllConfigurationChecksMatch')

    def test_reader_unknown_scb_refuses_before_write(self):
        query = fixture(); query['registers']['scb'] = None
        value = self.reader(query)
        self.assertEqual(value['reason'], 'PointerBankNotEstablished'); self.assertEqual(value['journal'], [])

    def test_reader_bank6_pointer_word_alias(self):
        query = fixture(); query['registers']['scb'] = 6
        value = self.reader(query)
        self.assertEqual(value['journal'][0]['address'], 0xB4)
        self.assertEqual((value['state']['memory']['00B4'], value['state']['memory']['00B5']), (0x56, 3))

    def test_reader_ordinary_premise_only_on_reached_lb(self):
        query = fixture(); query['assumptions']['ordinaryByteSemantics'] = False
        value = self.reader(query)
        self.assertEqual((value['boundary'], len(value['journal']), len(value['steps'])), (0x3FDB, 1, 3))
        self.assertFalse(any(row['space'] == 'SYMBOLIC_SFR_READBACK' for row in value['reads']))
        query['memory']['0356'] = 0
        self.assertEqual(self.reader(query)['outcome'], 'GuardBypass')

    def test_reader_preserves_hc_ah_other_psw(self):
        query = fixture(); query['registers'].update(hc=1, ah=0xAA, otherPsw=0x0EF8)
        query['registerKnownBits'].update({'AH.' + str(bit): (0xAA >> bit) & 1 for bit in range(8)})
        value = self.reader(query)
        for key in ('hc', 'ah', 'otherPsw'): self.assertEqual(value['state']['registers'][key], query['registers'][key])

    def test_reader_namespace_in_intent_refuses(self):
        query = fixture(); query['configurationIntents']['0050']['generation'] = 'ConditionalEffect:tx_configuration_reader:earlier'
        self.assertEqual(self.reader(query)['reason'], 'EffectNamespaceAlreadyPresent')

    def test_reader_namespace_in_readback_refuses(self):
        query = fixture(); query['sfrReadbacks']['004A']['generation'] = 'ConditionalEffect:tx_configuration_reader:earlier'
        self.assertEqual(self.reader(query)['reason'], 'EffectNamespaceAlreadyPresent')

    def test_producer_compare_exact_five_sites_four_writers(self):
        value = self.producer()
        self.assertEqual([step['pc'] for step in value['steps']], list(PRODUCER_SITES))
        self.assertEqual([event['pc'] for event in value['journal']], [0x60C9, 0x60CF, 0x60D2, 0x60D5])

    def test_producer_tail_exact_two_sites(self):
        value = self.producer(fixture('SymbolicCarryTail'))
        self.assertEqual([step['pc'] for step in value['steps']], [0x60D2, 0x60D5])
        self.assertEqual(len(value['journal']), 2); self.assertEqual(value['sourceScope'], list(PRODUCER_SITES))

    def test_producer_compare_threshold_and_inversion(self):
        for byte in (0, 0x7F, 0x80, 0x81, 0xFF):
            query = fixture('Compare3cb'); query['memory']['03CB'] = byte
            value = self.producer(query)
            self.assertEqual(value['state']['registers']['cf'], int(byte >= 0x80))
            self.assertEqual((value['state']['memory']['0356'] >> 1) & 1, int(byte >= 0x80))

    def test_producer_mb_retains_all_tail_flags(self):
        query = fixture('SymbolicCarryTail'); query['registers'].update(cf=1, zf=1, hc=1, dd=1, mie=1)
        value = self.producer(query)
        self.assertEqual(value['state']['registers'], query['registers'])

    def test_producer_compare_zf_alias_order_not_claimed(self):
        value = self.producer()
        self.assertIsNone(value['state']['registers']['zf'])
        self.assertIn('PswhSelfDestinationZfPrecedenceNotEstablished', value['unresolvedConstraints'])

    def test_producer_tail_does_not_add_xor_ambiguity(self):
        value = self.producer(fixture('SymbolicCarryTail'))
        self.assertNotIn('PswhSelfDestinationZfPrecedenceNotEstablished', value['unresolvedConstraints'])

    def test_producer_retains_dd_including_unknown(self):
        for entry in ('Compare3cb', 'SymbolicCarryTail'):
            for dd in (0, 1, None):
                query = fixture(entry); query['registers']['dd'] = dd
                self.assertEqual(self.producer(query)['state']['registers']['dd'], dd)

    def test_producer_no_lrb_usp_or_ordinary_gate(self):
        query = fixture('Compare3cb'); query['registers'].update(lrb=None, usp=None)
        query['assumptions']['ordinaryByteSemantics'] = False
        self.assertEqual(self.producer(query)['status'], 'CompleteConditional')

    def test_producer_partial_compare_high_bit_suffices_for_cf(self):
        for bit in (0, 1):
            value = self.producer(partial(fixture('Compare3cb'), '03CB', {7: bit}))
            self.assertEqual(value['state']['registers']['cf'], bit)
            self.assertEqual(value['state']['memory']['0356'], bit << 1)

    def test_producer_unknown_carry_forgets_old_target_bit(self):
        query = fixture('SymbolicCarryTail'); query['registers']['cf'] = None
        value = self.producer(query)
        self.assertIsNone(value['state']['memory']['0356'])
        self.assertNotIn('0356.1', value['state']['knownBits'])
        self.assertEqual({key: bit for key, bit in value['state']['knownBits'].items() if key.startswith('0356.')},
                         {'0356.' + str(bit): 0 for bit in (0, 2, 3, 4, 5, 6, 7)})

    def test_producer_partial_status_preserves_other_bits(self):
        query = partial(fixture('SymbolicCarryTail'), '0356', {0: 1, 1: 0, 6: 1}); query['registers']['cf'] = 1
        value = self.producer(query)
        self.assertEqual({key: bit for key, bit in value['state']['knownBits'].items() if key.startswith('0356.')},
                         {'0356.0': 1, '0356.1': 1, '0356.6': 1})

    def test_producer_same_value_write_is_retained(self):
        query = fixture('SymbolicCarryTail'); query['registers']['cf'] = 1
        value = self.producer(query)
        self.assertTrue(value['journal'][-1]['sameValue'])
        self.assertNotEqual(value['journal'][-1]['beforeGeneration'][0], value['journal'][-1]['afterGeneration'])

    def test_producer_register_xor_event_is_not_data(self):
        value = self.producer(); event = value['journal'][1]
        self.assertEqual((event['space'], event['address'], event['kind']), ('REGISTER', 5, 'RegisterXor'))
        self.assertIsNone(event['after']); self.assertEqual(event['beforeGeneration'], [None])

    def test_producer_pointer_read_and_data_read_distinct(self):
        value = self.producer()
        rows = [row for row in value['reads'] if row['pc'] == 0x60CC]
        self.assertEqual([row['space'] for row in rows], ['ARCHITECTURAL_ADDRESS_DEPENDENCY', 'DATA'])

    def test_producer_preserves_partial_al_ah(self):
        query = register_partial(register_partial(fixture('Compare3cb'), 'AL', {1: 1}), 'AH', {7: 0})
        value = self.producer(query)
        self.assertEqual(value['state']['registerKnownBits'], query['registerKnownBits'])

    def test_producer_namespace_before_first_writer(self):
        query = fixture('Compare3cb'); query['generations']['03CB'] = 'ConditionalEffect:mode_bit1_producer:old'
        value = self.producer(query)
        self.assertEqual(value['reason'], 'EffectNamespaceAlreadyPresent'); self.assertEqual(value['journal'], [])

    def test_reaching_local_windows_conditionally_retained(self):
        for path in ('ConfigurationSuffix', 'ReaderWindow'):
            value = self.reaching(reaching_query(path))
            self.assertEqual(value['state']['reachingDefinitions']['relation'], 'ConditionalWriterRetained')

    def test_reaching_missing_cfg_not_created_by_no_interference(self):
        for path in ('ProducerToConfiguration', 'ConfigurationTo2995', 'ReaderTo2995'):
            value = self.reaching(reaching_query(path))
            self.assertEqual((value['status'], value['reason']), ('IndeterminateObligation', 'SourceCfgEdgeNotEstablished'))

    def test_reaching_stale_generation(self):
        query = reaching_query(); query['requestedGeneration'] = 'Earlier'
        self.assertEqual(self.reaching(query)['reason'], 'StaleRequestedGeneration')

    def test_reaching_entry_generation_replaced(self):
        query = reaching_query(); query['entryGeneration'] = 'Earlier'
        self.assertEqual(self.reaching(query)['reason'], 'EntryGenerationReplaced')

    def test_reaching_missing_generation(self):
        query = reaching_query(); query['entryGeneration'] = None
        self.assertEqual(self.reaching(query)['reason'], 'MissingGenerationObligation')

    def test_reaching_unknown_writer_not_owner(self):
        query = reaching_query(); query['timelineQuery']['events'] = [{'kind': 'UnknownWriter', 'id': 'u'}]
        self.assertEqual(self.reaching(query)['reason'], 'InterferenceNotExcluded')

    def test_reaching_competing_same_value_writer(self):
        query = reaching_query(); query['timelineQuery']['events'] = [{'kind': 'AlternateIntent', 'id': 'other',
            'address': 0x50, 'widthBits': 8, 'value': 0x1C, 'generation': 'Other', 'dd': 0}]
        self.assertEqual(self.reaching(query)['reason'], 'CompetingConfigurationWriter')

    def test_reaching_native_claim_refused(self):
        query = reaching_query(); query['claim'] = 'NativeOwner'
        self.assertEqual(self.reaching(query)['status'], 'OutsideVerifiedScope')

    def test_ack_documented_and_unknown_rules_distinct(self):
        for rule, row in reference.ACK_RULES.items():
            query = ack_query(rule); value = self.ack(query)
            self.assertEqual(value['state']['relationship'], row)
            self.assertEqual(value['status'], 'CompleteConditional')

    def test_ack_generic_entry_not_stbuf_write_ack(self):
        generic = self.ack(ack_query('GENERIC_QUALIFIED_INTERRUPT_ENTRY_ACK'))
        write = self.ack(ack_query('STBUF_WRITE_ACK'))
        self.assertEqual(generic['state']['relationship']['classification'], 'SourceQualifiedConditional')
        self.assertEqual(write['state']['relationship']['classification'], 'Unknown')

    def test_ack_transmit_allocation_separate_from_rx(self):
        value = self.ack()['state']
        self.assertEqual((value['txReadyVector'], value['txReadyBit'], value['rxReadyVector'], value['rxReadyBit']), (12, 2, 10, 1))
        self.assertEqual((value['txBrgVector'], value['txBrgBit']), (36, 14))

    def test_ack_ie_conflict_not_resolved(self):
        value = self.ack(ack_query('IE_POLARITY'))
        self.assertEqual(value['state']['relationship']['classification'], 'SourceConflict')
        self.assertIsNone(value['state']['iePolarityResolution'])

    def test_ack_no_ack_event_created(self):
        value = self.ack()
        self.assertEqual((value['journal'], value['reads'], value['steps']), ([], [], []))
        self.assertIsNone(value['state']['actualPendingGeneration']); self.assertIsNone(value['state']['actualAcknowledge'])

    def test_ack_fifo_completion_and_runtime_claims_refused(self):
        for claim in ('ActualAck', 'ActualTx', 'Fifo', 'TxCompleteIrq', 'RuntimeAdmission'):
            query = ack_query(); query['claim'] = claim
            self.assertEqual(self.ack(query)['status'], 'OutsideVerifiedScope')

    def test_ack_actual_ecu_applicability_refused(self):
        query = ack_query(); query['applicability'] = 'ActualEcuVerified'
        self.assertEqual(self.ack(query)['status'], 'OutsideVerifiedScope')

    def test_join_all_local_success_never_native_admission(self):
        value = self.join()
        self.assertEqual((value['status'], value['reason']), ('IndeterminateObligation', 'ConfigurationTo2995PathNotEstablished'))
        self.assertFalse(value['state']['continuousCfgEstablished'])

    def test_join_keeps_all_nested_results_on_global_refusal(self):
        query = join_query(); query['claim'] = 'ActualTx'
        value = self.join(query)
        self.assertEqual(set(value['state']), {'reader', 'producer', 'reaching', 'ack', 'stbuf',
            'actualNativeConfigurationOwner', 'actualTxReadiness', 'continuousCfgEstablished'})

    def test_join_does_not_use_producer_output_to_seed_reader(self):
        query = join_query(); query['readerQuery']['memory']['0356'] = 0
        query['producerQuery']['memory']['03CB'] = 0xFF
        value = self.join(query)
        self.assertEqual(value['state']['reader']['outcome'], 'GuardBypass')
        self.assertEqual(value['state']['producer']['state']['memory']['0356'], 2)

    def test_join_nested_outside_refuses(self):
        query = join_query(); query['ackQuery']['claim'] = 'ActualAck'
        self.assertEqual(self.join(query)['reason'], 'NestedSourceObligationRefused')

    def test_join_nested_unknown_preserves_obligation(self):
        query = join_query(); query['readerQuery']['memory']['0356'] = None
        self.assertEqual(self.join(query)['reason'], 'NestedConditionalPremisesNotEstablished')

    def test_canonical_has_exact_sixteen_keys_and_generations(self):
        case = {'id': 'schema', 'operation': 'tx_configuration_reader', 'input': fixture()}
        value = reference.record(case, self.reader())
        self.assertEqual(len(value), 16)
        self.assertEqual(set(value['generations']), {'data', 'softwareIntents', 'suppliedReadbacks', 'writerEvents', 'reachingDefinitions'})
        self.assertEqual(value['state'], value['output']['state'])

    def test_authority_is_blocked_recursively(self):
        value = self.join()
        for item in (value, *(value['state'][key] for key in ('reader', 'producer', 'reaching', 'ack'))):
            self.assertEqual(item['executionStatus'], 'EXECUTION_BLOCKED'); self.assertFalse(item['firmwareReady'])
            for key in ('cpuInstructionRetirements', 'actualPeripheralOperations'):
                self.assertIs(type(item[key]), int); self.assertEqual(item[key], 0)
            for key in ('actualHardwareObservation', 'actualBufferWrite', 'actualTransmission',
                        'actualTxCompletion', 'actualTxIrqDelivery', 'actualPeripheralClockEvent'):
                self.assertIsNone(item[key])
        # Frozen M2cr keeps peripheral observations in its state, not its envelope.
        stbuf = value['state']['stbuf']
        self.assertEqual(stbuf['executionStatus'], 'EXECUTION_BLOCKED'); self.assertFalse(stbuf['firmwareReady'])
        self.assertIs(type(stbuf['cpuInstructionRetirements']), int)
        self.assertEqual(stbuf['cpuInstructionRetirements'], 0)
        self.assertIsNone(stbuf['actualHardwareObservation'])
        for key in ('actualBufferWrite', 'actualAcceptance', 'actualTransmission', 'actualCompletion', 'actualTxIrq'):
            self.assertIsNone(stbuf['state'][key])
        for key in ('reads', 'journal', 'steps'):
            self.assertEqual(stbuf[key], [])

    def test_all_step_register_views_are_full(self):
        for value in (self.reader(), self.producer()):
            for step in value['steps']:
                self.assertEqual(set(step['afterRegisters']), set(fixture()['registers']))

    def test_malformed_snapshot_and_added_data_refused(self):
        query = fixture(); query['memory'].pop('03CB')
        self.malformed('tx_configuration_reader', query)
        query = fixture(); query['memory']['9999'] = 0
        self.malformed('tx_configuration_reader', query)

    def test_contradictory_partial_and_boolean_bytes_refused(self):
        query = fixture(); query['knownBits']['03CB.7'] = 0
        self.malformed('tx_configuration_reader', query)
        query = fixture(); query['sfrReadbacks']['004A']['value'] = False
        self.malformed('tx_configuration_reader', query)

    def test_wrong_closed_query_claim_and_source_types_refused(self):
        query = ack_query(); query['claim'] = 'Rx000ATx'
        self.malformed('tx_ack_documentary_obligations', query)
        query = ack_query(); query['sourceBinding'] = False
        self.malformed('tx_ack_documentary_obligations', query)

    def test_binding_missing_and_mismatch_remain_distinct(self):
        for maker, method in ((ack_query, self.ack), (reaching_query, self.reaching), (join_query, self.join)):
            query = maker(); query['sourceBinding'] = None
            self.assertEqual(method(query)['reason'], 'SourceBindingMissing')
            query['sourceBinding'] = {**SOURCE_BINDING, 'baseSha': False}
            self.assertEqual(method(query)['reason'], 'SourceBindingMismatch')

    def test_nested_input_classes_must_match(self):
        query = join_query(); query['readerQuery']['inputClass'] = 'SymbolicInput'
        self.malformed('stbuf2995_configuration_provenance', query)

    def test_producer_shape_does_not_accept_arbitrary_entry(self):
        query = fixture('Other')
        self.malformed('mode_bit1_producer', query)

    def test_documented_fields_never_become_hardware_permission(self):
        from stbuf_stcon_transmit_source.reference_oracle import transmit_configuration_hypotheses
        from stbuf_stcon_transmit_source.corpus import hypotheses_query
        from .stcon_allocation import UNKNOWN_ENCODINGS, REGISTER_INVENTORY, INHERITED_FACT_IDS, UNKNOWN_FACT_IDS
        for raw in range(256):
            query = hypotheses_query(); query['configurationIntents']['0050']['value'] = raw
            value = transmit_configuration_hypotheses(query)
            decoded = value['state']['decoded']
            self.assertIsNone(decoded['stconBit7Meaning']); self.assertIsNone(decoded['effectiveBaudRate'])
            self.assertIsNone(value['state']['actualReady'])
            self.assertEqual(decoded['serialMode'], 'Synchronous' if raw & 2 else 'UART')
            self.assertEqual(decoded['paritySelectionBit5'], (raw >> 5) & 1)
            self.assertEqual(decoded['bit6MeaningfulWhenBit5One'], bool(raw & 0x20))
            if raw & 2:
                self.assertEqual(decoded['synchronousClockRole'], 'Master' if raw & 0x10 else 'Slave')
                self.assertIsNone(decoded['uartProtocol'])
            else:
                self.assertEqual(decoded['uartProtocol'], 'Multiprocessor' if raw & 1 else 'Normal')
                self.assertEqual(decoded['uartStopLengthCode'], (raw >> 4) & 1)
                if raw & 1:
                    self.assertEqual(decoded['multiprocessorDataAddress'], 'Address' if raw & 4 else 'Data')
                    self.assertTrue(decoded['multiprocessorBit3Ignored'])
                else:
                    self.assertEqual(decoded['normalLengthCode'], (raw >> 2) & 3)
            query = hypotheses_query(); query['configurationIntents']['004A']['value'] = raw
            decoded = transmit_configuration_hypotheses(query)['state']['decoded']
            self.assertEqual(decoded['baudGeneratorModeCode'], raw & 3)
            self.assertEqual(decoded['baudGeneratorRunBit'], (raw >> 4) & 1)
            self.assertEqual(decoded['baudGeneratorClockDivisor'], (2, 4, 8, 16, 32, 128, 512, 512)[raw >> 5])
        reset = next(row for row in REGISTER_INVENTORY if row['address'] == 0x50)
        self.assertEqual((reset['resetValue'], reset['resetClassification']), (0x80, 'ManufacturerResetValue_NotCurrentState'))
        self.assertEqual(UNKNOWN_ENCODINGS['bit7'], 'Unknown')
        self.assertEqual(UNKNOWN_ENCODINGS['parityPresencePolarity'], 'Unknown')
        self.assertEqual(UNKNOWN_ENCODINGS['oddEvenPolarity'], 'Unknown')
        self.assertEqual((len(INHERITED_FACT_IDS), len(UNKNOWN_FACT_IDS)), (17, 15))

    def test_primary_ack_rows_are_exact_frozen_source_rows(self):
        from .stcon_allocation import ACK_RULES
        self.assertEqual(reference.canonical(ACK_RULES), reference.canonical(reference.ACK_RULES))
        self.assertEqual(len(ACK_RULES), 14)


if __name__ == '__main__':
    unittest.main()
