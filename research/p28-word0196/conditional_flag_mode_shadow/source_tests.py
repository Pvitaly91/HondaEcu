"""Independent source-to-model controls; expected values never call the model."""
from copy import deepcopy
from hashlib import sha256
import unittest

from . import flag, mode
from .corpus import ADDRESSES, cases, fixture
from . import reference_oracle as reference

IMPLEMENTED = {'status_clear': flag.status_clear, 'flag_body': flag.flag_body,
               'flag_path': flag.flag_path, 'initial_pair': mode.initial_pair,
               'mode_switch': mode.mode_switch, 'consistency_check': mode.consistency_check,
               'mask_hypotheses': mode.mask_hypotheses}
FROZEN_EXPECTED_SHA256 = '854b1fee40de9de91f78c2235eca7c870a8788fa63b1915c7ff244736b429e83'
FROZEN_EXPECTED_BYTES = 27741832


def actual_records():
    for case in cases():
        yield {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
               'output': IMPLEMENTED[case['operation']](case['input'])}


def changed_bit(state, key, bit, value):
    state['memory'][key] = (state['memory'][key] & ~(1 << bit)) | (value << bit)


def changed_word(state, key, value):
    state['memory'][key] = None if value is None else value % 256
    state['memory'][f'{int(key, 16) + 1:04X}'] = None if value is None else value // 256


def from_state(before, transformed):
    return {'inputClass': before['inputClass'], 'assumptions': deepcopy(before['assumptions']),
            **deepcopy(transformed)}


class ReferenceComparison(unittest.TestCase):
    def equal_full(self, name, snapshot):
        preserved = deepcopy(snapshot)
        expected = reference.OPERATIONS[name](snapshot)
        actual = IMPLEMENTED[name](snapshot)
        self.assertEqual(snapshot, preserved)
        self.assertEqual(reference.canonical(actual), reference.canonical(expected))
        return actual


class FlagTests(ReferenceComparison):
    def test_all_256_flags_by_six_r6_boundaries_match_full_independent_reference(self):
        examined = 0
        for value in range(256):
            for prior in (0, 1, 15, 127, 128, 255):
                state = fixture('flag')
                state['memory'].update({'0055': value, '03F6': prior})
                out = self.equal_full('flag_path', state)
                self.assertEqual(out['outcome'], 'FlagWritten')
                self.assertEqual(out['state']['memory']['03F6'], (value + prior) % 256)
                self.assertEqual(out['state']['registers']['cf'], int(value + prior >= 256))
                self.assertEqual(out['state']['registers']['al'], value)
                self.assertEqual(out['state']['registers']['ah'], state['registers']['ah'])
                self.assertEqual([out['state']['registers'][key] for key in ('zf', 'hc', 'dd')], [0, 0, 0])
                examined += 1
        self.assertEqual(examined, 1536)

    def test_even_and_odd_boundary_flags_both_reach_the_flag_store(self):
        for value in (0, 1, 2, 0x7F, 0x80, 0xFF):
            state = fixture('flag')
            state['memory']['0055'] = value
            out = self.equal_full('flag_body', state)
            self.assertEqual(out['state']['memory']['03F3'], value)
            self.assertEqual(out['outcome'], 'FlagWritten')

    def test_five_ordered_full_path_writes_have_byte_width_and_distinct_generations(self):
        out = self.equal_full('flag_path', fixture('flag'))
        self.assertEqual([(row['pc'], row['address'], row['widthBits']) for row in out['journal']],
                         [(0x0222, 0x0356, 8), (0x0269, 0x03F3, 8), (0x026D, 0x03F6, 8),
                          (0x026F, 0x03F5, 8), (0x0270, 0x03F7, 8)])
        self.assertEqual([row['ordinal'] for row in out['journal']], [1, 2, 3, 4, 5])
        self.assertEqual(len({row['afterGeneration'] for row in out['journal']}), 5)
        self.assertEqual(len(out['intermediateStates']), 5)

    def test_same_value_status_flag_and_r7_stores_are_not_deduplicated(self):
        state = fixture('flag')
        state['memory']['03F3'] = state['memory']['0055']
        out = self.equal_full('flag_path', state)
        for pc in (0x0222, 0x0269, 0x0270):
            event = next(row for row in out['journal'] if row['pc'] == pc)
            self.assertIs(event['sameValue'], True)
            self.assertNotEqual(event['beforeGeneration'], [event['afterGeneration']])

    def test_increment_overwrites_addition_zero_and_halfcarry_but_retains_carry(self):
        state = fixture('flag')
        state['memory'].update({'0055': 1, '03F6': 255})
        out = self.equal_full('flag_body', state)
        add = next(row for row in out['steps'] if row['pc'] == 0x026D)['afterRegisters']
        inc = next(row for row in out['steps'] if row['pc'] == 0x026F)['afterRegisters']
        self.assertEqual((add['cf'], add['zf'], add['hc']), (1, 1, 1))
        self.assertEqual((inc['cf'], inc['zf'], inc['hc']), (1, 0, 0))

    def test_unknown_flag_or_checksum_never_defaults_to_zero(self):
        for key in ('0055', '03F6'):
            state = fixture('flag')
            state['memory'][key] = None
            state['inputClass'] = 'SymbolicInput'
            out = self.equal_full('flag_body', state)
            self.assertIsNone(out['state']['memory']['03F6'])
            self.assertIsNone(out['state']['registers']['cf'])
            self.assertEqual((out['state']['registers']['zf'], out['state']['registers']['hc']), (0, 0))
            self.assertIsNone(next(row for row in out['journal'] if row['pc'] == 0x026D)['sameValue'])

    def test_unknown_ah_and_other_psw_are_preserved(self):
        state = fixture('flag')
        state['registers'].update(ah=None, otherPsw=None)
        out = self.equal_full('flag_path', state)
        self.assertIsNone(out['state']['registers']['ah'])
        self.assertIsNone(out['state']['registers']['otherPsw'])

    def test_direct_body_r5_not_two_keeps_read_compare_prefix_and_stops_before_r4(self):
        for count in (0, 1, 3, 255):
            state = fixture('flag')
            state['memory']['03F5'] = count
            out = self.equal_full('flag_body', state)
            self.assertEqual((out['status'], out['boundary']), ('OutsideVerifiedScope', 0x026C))
            self.assertEqual(out['journal'], [])
            self.assertEqual(out['state']['registers']['al'], state['memory']['0055'])
            self.assertEqual([r['pc'] for r in out['reads']], [0x0262, 0x0264])

    def test_unknown_body_count_has_no_fabricated_selection_or_store(self):
        state = fixture('flag')
        state['memory']['03F5'] = None
        out = self.equal_full('flag_body', state)
        self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', 0x0267))
        self.assertEqual(out['journal'], [])
        self.assertIsNone(out['steps'][-1]['next'])

    def test_dispatch_header_length_checksum_paths_do_not_read_the_flag(self):
        for key, value, destination in (('03F7', 0, 0x0275), ('03F5', 1, 0x027F), ('03F5', 3, 0x0284)):
            state = fixture('flag')
            state['memory'][key] = value
            out = self.equal_full('flag_path', state)
            self.assertEqual(out['boundary'], destination)
            self.assertNotIn(0x0262, [r['pc'] for r in out['reads']])
            self.assertEqual([r['pc'] for r in out['journal']], [0x0222])

    def test_dispatch_mode_zero_uses_exact_029d_relative_target(self):
        state = fixture('flag')
        state['memory']['0356'] = 0
        out = self.equal_full('flag_path', state)
        self.assertEqual(out['boundary'], 0x029D)
        self.assertEqual(out['journal'], [])

    def test_old_error_is_cleared_before_the_outside_error_branch(self):
        state = fixture('flag')
        state['memory']['0356'] |= 0x40
        out = self.equal_full('flag_path', state)
        self.assertEqual(out['boundary'], 0x0227)
        self.assertEqual(out['state']['memory']['0356'], 2)
        self.assertEqual([r['pc'] for r in out['journal']], [0x0222])

    def test_status_clear_is_a_separate_effect_and_retains_ready_bit(self):
        for raw in (0, 0x40, 0x80, 0xC0, None):
            state = fixture('flag')
            state['memory']['0356'] = raw
            out = self.equal_full('status_clear', state)
            self.assertEqual(out['outcome'], 'StatusCleared')
            self.assertEqual(len(out['journal']), 1)
            if raw is not None:
                self.assertEqual(out['state']['memory']['0356'] & 0x80, raw & 0x80)
            else:
                self.assertIsNone(out['state']['memory']['0356'])
                self.assertEqual(out['state']['knownBits']['0356.6'], 0)

    def test_partial_status_uses_known_control_bits_and_preserves_unknown_neighbors(self):
        state = fixture('flag')
        state['memory']['0356'] = None
        state['knownBits'] = {'0356.1': 1, '0356.6': 0, '0356.7': 1}
        out = self.equal_full('flag_path', state)
        self.assertEqual(out['outcome'], 'FlagWritten')
        self.assertIsNone(out['state']['memory']['0356'])
        self.assertEqual(out['state']['knownBits'], state['knownBits'])

    def test_unknown_mode_or_error_stops_at_its_own_predicate(self):
        for bits, boundary, writes in (({}, 0x021F, 0), ({'0356.1': 1}, 0x0225, 1)):
            state = fixture('flag')
            state['memory']['0356'] = None
            state['knownBits'] = bits
            out = self.equal_full('flag_path', state)
            self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', boundary))
            self.assertEqual(len(out['journal']), writes)

    def test_byte_load_premise_refusal_preserves_already_computed_prefix(self):
        state = fixture('flag')
        state['assumptions']['ordinaryByteSemantics'] = False
        body = self.equal_full('flag_body', state)
        path = self.equal_full('flag_path', state)
        self.assertEqual((body['boundary'], len(body['journal'])), (0x0262, 0))
        self.assertEqual((path['boundary'], len(path['journal'])), (0x0255, 1))

    def test_wrong_or_unknown_local_bank_is_not_mapped_to_03f3(self):
        for lrb in (None, 0x0040):
            state = fixture('flag')
            state['registers']['lrb'] = lrb
            out = self.equal_full('flag_body', state)
            self.assertEqual(out['reason'], 'UnsupportedContext')
            self.assertEqual((out['journal'], out['reads'], out['steps']), ([], [], []))

    def test_incoming_dd_does_not_override_lb_selecting_byte_mode(self):
        for dd in (0, 1, None):
            state = fixture('flag')
            state['registers']['dd'] = dd
            self.assertEqual(self.equal_full('flag_body', state)['state']['registers']['dd'], 0)


class ModeTests(ReferenceComparison):
    def test_pair_a_exact_order_is_not_atomic(self):
        state = fixture('mode')
        changed_bit(state, '0217', 2, 1)
        changed_word(state, '001A', 0xA9A3)
        changed_word(state, '00F8', 0xA9A3)
        changed_word(state, '00FA', 0x00A0)
        out = self.equal_full('mode_switch', state)
        self.assertEqual(out['outcome'], 'PairA')
        self.assertEqual([r['pc'] for r in out['journal'] if r['pc'] in (0x3F14, 0x3F16, 0x3F18, 0x3F1D)],
                         [0x3F14, 0x3F16, 0x3F18, 0x3F1D])
        direct = next(r for r in out['intermediateStates'] if r['pc'] == 0x3F14)['state']
        self.assertEqual(direct['memory']['001A'], 0xAB)
        self.assertEqual(direct['memory']['00F8'], 0xA3)
        self.assertEqual(direct['memory']['0217'] & 4, 4)

    def test_pair_b_retains_all_extra_bit_writes_and_two_tcon_generations(self):
        state = fixture('mode')
        changed_bit(state, '0212', 3, 1)
        out = self.equal_full('mode_switch', state)
        self.assertEqual(out['outcome'], 'PairB')
        pcs = [r['pc'] for r in out['journal']]
        self.assertEqual([p for p in pcs if 0x3F28 <= p <= 0x3F3D],
                         [0x3F28, 0x3F2A, 0x3F2C, 0x3F31, 0x3F34, 0x3F37, 0x3F3A, 0x3F3D])
        tcon = [r for r in out['journal'] if r['address'] == 0x0043]
        self.assertEqual(len(tcon), 2)
        self.assertNotEqual(tcon[0]['afterGeneration'], tcon[1]['afterGeneration'])
        self.assertEqual(tcon[1]['beforeGeneration'], [tcon[0]['afterGeneration']])

    def test_threshold_equality_uses_cf_across_unknown_zf_mask(self):
        state = fixture('mode')
        changed_bit(state, '0217', 2, 1)
        state['memory']['01AD'] = 0x29
        out = self.equal_full('mode_switch', state)
        masked = next(row for row in out['steps'] if row['pc'] == 0x3F09)['afterRegisters']
        self.assertIsNone(masked['zf'])
        self.assertEqual(masked['cf'], 0)
        self.assertEqual(out['outcome'], 'PairA')

    def test_first_gate_suppresses_threshold_read_and_its_usp_requirement(self):
        state = fixture('mode')
        changed_bit(state, '0212', 3, 1)
        changed_bit(state, '0217', 2, 1)
        state['registers']['usp'] = None
        state['memory']['01AD'] = None
        out = self.equal_full('mode_switch', state)
        self.assertEqual(out['outcome'], 'NoSwitch')
        self.assertNotIn(0x3F05, [r['pc'] for r in out['reads']])
        self.assertEqual(out['state']['registers']['cf'], state['registers']['cf'])

    def test_usp_refusal_occurs_only_at_the_reached_indirect_site(self):
        for gate, point in ((0, 0x3F05), (1, 0x3F34)):
            state = fixture('mode')
            changed_bit(state, '0212', 3, gate)
            state['registers']['usp'] = None
            out = self.equal_full('mode_switch', state)
            self.assertEqual(out['boundary'], point)
            self.assertEqual(out['reason'], 'NamedUSPAddressNotEstablished')
            self.assertTrue(out['journal'])
            self.assertNotIn(point, [r['pc'] for r in out['reads']])

    def test_optional_irq_high_prelude_controls_inactive_bank_rmw(self):
        for old_bit in (0, 1):
            state = fixture('mode')
            changed_bit(state, '0019', 7, old_bit)
            out = self.equal_full('mode_switch', state)
            pcs = [r['pc'] for r in out['journal']]
            self.assertIn(0x3EF7, pcs)
            self.assertEqual(0x3EFC in pcs, old_bit == 1)
            self.assertEqual(0x3EFF in pcs, old_bit == 1)

    def test_unknown_irq_high_bit_stops_after_clear_not_before_or_after_extra_writes(self):
        state = fixture('mode')
        state['memory']['0019'] = None
        out = self.equal_full('mode_switch', state)
        self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', 0x3EFA))
        self.assertEqual(out['state']['knownBits']['0019.7'], 0)
        self.assertNotIn(0x3EFC, [r['pc'] for r in out['journal']])

    def test_unknown_control_and_threshold_stop_at_distinct_boundaries(self):
        for address, boundary in (('0212', 0x3EF1), ('0217', 0x3EF4), ('01AD', 0x3F0C)):
            state = fixture('mode')
            state['memory'][address] = None
            out = self.equal_full('mode_switch', state)
            self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', boundary))
            self.assertNotIn(0x3F14, [r['pc'] for r in out['journal']])

    def test_partial_mode_and_gate_bits_select_without_inventing_neighbor_bits(self):
        state = fixture('mode')
        state['memory'].update({'0212': None, '0217': None})
        state['knownBits'] = {'0212.3': 1, '0217.2': 0}
        out = self.equal_full('mode_switch', state)
        self.assertEqual(out['outcome'], 'PairB')
        self.assertIsNone(out['state']['memory']['0217'])
        self.assertEqual(out['state']['knownBits']['0217.2'], 1)

    def test_pswh_self_destination_keeps_zf_unknown_until_the_tail_load(self):
        out = self.equal_full('mode_switch', fixture('mode'))
        for row in out['steps']:
            if row['pc'] in (0x3EEE, 0x3F02, 0x3F09, 0x3F40):
                self.assertIsNone(row['afterRegisters']['zf'])
        self.assertEqual(out['state']['registers']['zf'], 0)
        for row in out['journal']:
            if row['space'] == 'REGISTER':
                self.assertEqual((row['address'], row['widthBits'], row['afterBytes']), (5, 8, [None]))

    def test_partial_word_tail_load_uses_proven_nonzero_byte_for_zf(self):
        for lo, hi, zf in ((0xAB, None, 0), (0, None, None), (0, 0, 1)):
            state = fixture('mode')
            state['memory'].update({'00F8': lo, '00F9': hi})
            out = self.equal_full('mode_switch', state)
            self.assertEqual(out['outcome'], 'NoSwitch')
            self.assertEqual((out['state']['registers']['al'], out['state']['registers']['ah']), (lo, hi))
            self.assertEqual(out['state']['registers']['zf'], zf)
            self.assertEqual(out['state']['memory']['001A'], lo)
            self.assertEqual(out['state']['memory']['001B'], hi)

    def test_no_switch_does_not_repair_a_mismatched_shadow(self):
        state = fixture('mode')
        changed_word(state, '00F8', 0x1234)
        out = self.equal_full('mode_switch', state)
        self.assertEqual(out['outcome'], 'NoSwitch')
        self.assertEqual((out['state']['memory']['001A'], out['state']['memory']['001B']), (0x34, 0x12))
        self.assertNotIn(0x3F14, [r['pc'] for r in out['journal']])

    def test_initial_pair_includes_trnsit_irq_tcon_writes_and_no_mode_writer(self):
        state = fixture('mode')
        out = self.equal_full('initial_pair', state)
        self.assertEqual([r['pc'] for r in out['journal']], [0x54DD, 0x54E5, 0x54E7, 0x54EA, 0x54ED, 0x54F0])
        self.assertEqual([r['widthBits'] for r in out['journal']], [16, 16, 8, 16, 8, 16])
        self.assertEqual(out['state']['memory']['0217'], state['memory']['0217'])
        self.assertEqual(out['state']['memory']['0046'], 0)
        self.assertEqual((out['state']['memory']['0018'], out['state']['memory']['0019']), (0, 0))

    def test_initial_word_literal_is_dd_independent_before_load_forces_dd1(self):
        for dd in (0, 1, None):
            state = fixture('mode')
            state['registers']['dd'] = dd
            out = self.equal_full('initial_pair', state)
            self.assertEqual(out['intermediateStates'][0]['state']['registers']['dd'], dd)
            self.assertEqual(out['state']['registers']['dd'], 1)

    def test_initial_partial_tcon_uses_old_bit_and_keeps_other_bits_unknown(self):
        for old_bit in (0, 1, None):
            state = fixture('mode')
            state['memory']['0040'] = None
            if old_bit is not None:
                state['knownBits']['0040.2'] = old_bit
            out = self.equal_full('initial_pair', state)
            self.assertEqual(out['state']['registers']['zf'], None if old_bit is None else 1 - old_bit)
            self.assertIsNone(out['state']['memory']['0040'])
            self.assertEqual(out['state']['knownBits']['0040.2'], 0)

    def test_wrong_page_or_active_bank_is_refused_instead_of_ignoring_aliases(self):
        for field, value in (('lrb', 0x007E), ('lrb', None), ('scb', 6), ('scb', None)):
            state = fixture('mode')
            state['registers'][field] = value
            out = self.equal_full('mode_switch', state)
            self.assertEqual(out['reason'], 'UnsupportedContext')
            self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))

    def test_missing_input_generations_do_not_create_native_owners(self):
        state = fixture('mode')
        state['generations'] = {key: None for key in ADDRESSES}
        out = self.equal_full('mode_switch', state)
        self.assertIsNone(out['actualHardwareObservation'])
        self.assertFalse(out['firmwareReady'])
        self.assertEqual(out['journal'][0]['beforeGeneration'], [None, None])
        self.assertTrue(all(row['afterGeneration'].startswith('ConditionalEffect:') for row in out['journal']))


class ConsistencyTests(ReferenceComparison):
    def matching(self, selected):
        state = fixture('mode')
        changed_bit(state, '0217', 2, selected)
        changed_word(state, '001A', 0x2BAB if selected == 0 else 0xA9A3)
        changed_word(state, '00F8', 0x2BAB if selected == 0 else 0xA9A3)
        changed_word(state, '00FA', 0x02A0 if selected == 0 else 0x00A0)
        return state

    def test_success_reads_all_three_words_and_keeps_one_or_two_x1_writes(self):
        for selected in (0, 1):
            out = self.equal_full('consistency_check', self.matching(selected))
            self.assertEqual((out['outcome'], out['boundary']), ('Consistent', 0x3EA7))
            pointers = [r for r in out['journal'] if r['kind'] == 'PointerStore']
            self.assertEqual([r['pc'] for r in pointers], [0x3E84] if selected == 0 else [0x3E84, 0x3E8D])
            self.assertIn(0x3E9A, [r['pc'] for r in out['reads']])

    def test_first_shadow_mismatch_shortcircuits_ie_and_fa_reads(self):
        state = self.matching(0)
        state['memory']['00F8'] ^= 1
        out = self.equal_full('consistency_check', state)
        self.assertEqual((out['outcome'], out['boundary']), ('Inconsistent', 0x24E0))
        pcs = [r['pc'] for r in out['reads']]
        self.assertNotIn(0x3E95, pcs)
        self.assertNotIn(0x3E9B, pcs)
        self.assertEqual(out['journal'][-1]['address'], 0x00F5)
        self.assertEqual(out['journal'][-1]['after'], 0x4F)

    def test_ie_and_fa_mismatches_have_their_own_last_comparison(self):
        for address, last_pc in (('001A', 0x3E95), ('00FA', 0x3E9B)):
            state = self.matching(1)
            state['memory'][address] ^= 1
            out = self.equal_full('consistency_check', state)
            self.assertEqual(out['outcome'], 'Inconsistent')
            self.assertEqual(out['reads'][-1]['pc'], last_pc)

    def test_unknown_mode_keeps_initial_x1_write_but_never_reads_a_mask(self):
        state = fixture('mode')
        state['memory']['0217'] = None
        out = self.equal_full('consistency_check', state)
        self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', 0x3E87))
        self.assertEqual([r['pc'] for r in out['journal']], [0x3E84])
        self.assertNotIn(0x3E90, [r['pc'] for r in out['reads']])

    def test_partial_word_compare_stops_conservatively_without_fabricated_failure(self):
        state = self.matching(0)
        state['memory']['00F9'] = None
        out = self.equal_full('consistency_check', state)
        self.assertEqual((out['status'], out['boundary']), ('IndeterminateBranch', 0x3E93))
        self.assertEqual((out['state']['registers']['cf'], out['state']['registers']['zf']), (None, None))
        self.assertNotIn(0x3EA0, [r['pc'] for r in out['journal']])

    def test_same_value_x1_pointer_store_is_a_separate_event(self):
        state = self.matching(0)
        changed_word(state, '0080', 0x02A0)
        out = self.equal_full('consistency_check', state)
        self.assertIs(out['journal'][0]['sameValue'], True)
        self.assertEqual(out['journal'][0]['afterGeneration'], 'ConditionalEffect:consistency_check:3E84:1')

    def test_partial_mode_bit_and_unknown_generations_do_not_block_software_equalities(self):
        state = self.matching(1)
        state['memory']['0217'] = None
        state['knownBits']['0217.2'] = 1
        state['generations'] = {key: None for key in ADDRESSES}
        out = self.equal_full('consistency_check', state)
        self.assertEqual(out['outcome'], 'Consistent')
        self.assertIsNone(out['actualHardwareObservation'])

    def test_nonatomic_pair_prefix_can_fail_then_completed_pair_can_pass(self):
        state = self.matching(1)
        changed_bit(state, '0212', 3, 0)
        state['memory']['01AD'] = 0x29
        switched = self.equal_full('mode_switch', state)
        direct = next(row for row in switched['intermediateStates'] if row['pc'] == 0x3F14)
        core_done = next(row for row in switched['intermediateStates'] if row['pc'] == 0x3F1D)
        self.assertEqual(self.equal_full('consistency_check', from_state(state, direct['state']))['outcome'], 'Inconsistent')
        self.assertEqual(self.equal_full('consistency_check', from_state(state, core_done['state']))['outcome'], 'Consistent')


class BoundaryAndCanonicalTests(ReferenceComparison):
    def test_no_interference_is_a_premise_not_a_fabricated_fact(self):
        for name, kind, entry in (('flag_path', 'flag', 0x021F), ('mode_switch', 'mode', 0x3EEA), ('consistency_check', 'mode', 0x3E81)):
            for value in (False, None):
                state = fixture(kind)
                state['assumptions']['noInterference'] = value
                out = self.equal_full(name, state)
                self.assertEqual((out['reason'], out['boundary']), ('NoInterferencePremiseNotEstablished', entry))
                self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))

    def test_polarity_hypotheses_preserve_conflict_and_never_claim_delivery(self):
        state = fixture('mode')
        state['registers']['mie'] = 1
        out = self.equal_full('mask_hypotheses', state)
        one, zero = out['hypotheses']
        self.assertEqual((one['hypothesis'], one['faRx'], one['f8Rx']), ('Set1', 0, 1))
        self.assertEqual((zero['hypothesis'], zero['faRx'], zero['f8Rx']), ('Set0', 1, 0))
        self.assertTrue(all(row['actualIrqDelivery'] is None for row in out['hypotheses']))

    def test_partial_high_byte_does_not_hide_known_rx_bit_and_interpretation_needs_no_context(self):
        state = fixture('mode')
        for key in ('001B', '00FB', '00F9'):
            state['memory'][key] = None
        state['registers'].update(lrb=None, scb=None)
        state['assumptions']['noInterference'] = None
        out = self.equal_full('mask_hypotheses', state)
        self.assertEqual([row['ieRx'] for row in out['hypotheses']], [1, 0])

    def test_all_three_input_classes_are_labels_not_actual_hardware_authority(self):
        for classification in ('SyntheticTestInput', 'SymbolicInput', 'ManufacturerSourceQualifiedState'):
            state = fixture('flag')
            state['inputClass'] = classification
            out = self.equal_full('flag_body', state)
            self.assertEqual(out['inputClass'], classification)
            self.assertIsNone(out['actualHardwareObservation'])
            self.assertEqual(out['cpuInstructionRetirements'], 0)
            self.assertEqual(out['executionStatus'], 'EXECUTION_BLOCKED')

    def test_malformed_types_ranges_unknown_keys_and_contradictory_bits_are_refused(self):
        baseline = fixture('flag')
        mutations = []
        for bad in (True, -1, 256, '0', [], {}):
            item = deepcopy(baseline)
            item['memory']['0055'] = bad
            mutations.append(item)
        for bad in (True, -1, 2, '0', [], {}):
            item = deepcopy(baseline)
            item['registers']['cf'] = bad
            mutations.append(item)
        for replacement in ({'FFFF.7': 1}, {'0356.6': True}, {'0356.1': 0}):
            item = deepcopy(baseline)
            item['knownBits'] = replacement
            mutations.append(item)
        item = deepcopy(baseline)
        item['registers']['otherPsw'] = 1
        mutations.append(item)
        item = deepcopy(baseline)
        del item['memory']['0356']
        mutations.append(item)
        item = deepcopy(baseline)
        item['generations']['0055'] = ''
        mutations.append(item)
        for item in mutations:
            with self.subTest(input=item), self.assertRaises(ValueError):
                flag.flag_body(item)

    def test_actual_owner_runtime_or_hardware_input_promotions_are_refused(self):
        for key, value in (('actualHardwareObservation', {}), ('cpuInstructionRetirements', 8), ('firmwareReady', True)):
            state = fixture('flag')
            state[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                flag.flag_body(state)

    def test_corpus_is_closed_unique_and_contains_every_flag_by_boundary_cross(self):
        inventory = list(cases())
        self.assertEqual(len(inventory), 1744)
        self.assertEqual(len({row['id'] for row in inventory}), 1744)
        full = [row for row in inventory if row['id'].startswith('flag-f')]
        self.assertEqual(len(full), 1536)
        self.assertEqual({(row['input']['memory']['0055'], row['input']['memory']['03F6']) for row in full},
                         {(f, r) for f in range(256) for r in (0, 1, 15, 127, 128, 255)})

    def test_complete_canonical_bytes_equal_independent_frozen_reference(self):
        expected = reference.canonical_bytes()
        actual = b''.join(reference.canonical(row) for row in actual_records())
        self.assertEqual(len(expected), FROZEN_EXPECTED_BYTES)
        self.assertEqual(sha256(expected).hexdigest(), FROZEN_EXPECTED_SHA256)
        self.assertEqual(actual, expected)

    def test_complete_comparison_detects_write_loss_reordering_flag_error_and_unknown_loss(self):
        state = fixture('flag')
        state['memory']['0055'] = None
        expected = reference.flag_path(state)
        mutated = []
        item = deepcopy(expected)
        item['journal'].pop()
        mutated.append(item)
        item = deepcopy(expected)
        item['journal'][0], item['journal'][1] = item['journal'][1], item['journal'][0]
        mutated.append(item)
        item = deepcopy(expected)
        item['state']['registers']['al'] = 0
        mutated.append(item)
        item = deepcopy(expected)
        item['state']['registers']['hc'] = 1
        mutated.append(item)
        item = deepcopy(expected)
        item['journal'][0]['widthBits'] = 16
        mutated.append(item)
        item = deepcopy(expected)
        item['actualHardwareObservation'] = {'invented': True}
        mutated.append(item)
        self.equal_full('flag_path', state)
        original_bytes = reference.canonical(expected)
        for item in mutated:
            self.assertNotEqual(reference.canonical(item), original_bytes)


if __name__ == '__main__':
    unittest.main()
