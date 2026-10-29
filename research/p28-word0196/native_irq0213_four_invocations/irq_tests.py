"""Bounded invented relation tests against the pre-model frozen M2ch oracle."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from native_irq0213_four_invocations import analysis
from native_irq0213_four_invocations.invocation_lineage import lineage_analysis
from native_irq0213_four_invocations.irq_frame import frame_layout, irq_analysis
from native_irq0213_four_invocations.reference_oracle import (
    ACTUAL, REASONS, curated_controls, independent_check, reference_case, reviewed_case,
)


class Irq0213FourInvocationTests(unittest.TestCase):
    maxDiff = None

    def compare(self, case, reason=None):
        expected = reference_case(case)
        self.assertEqual(expected['firstMismatch'], reason)
        self.assertEqual(analysis.evaluate_case(case), expected)
        return expected

    def test_complete_44_control_results_match_independent_oracle(self):
        controls = curated_controls()
        self.assertEqual(len(controls), 44)
        self.assertEqual(len({row['caseId'] for row in controls}), 44)
        self.assertEqual([row['caseId'].removeprefix('negative-') for row in controls[5:]], list(REASONS))
        for row in controls:
            with self.subTest(caseId=row['caseId']):
                reason = row['caseId'].removeprefix('negative-') if row['caseId'].startswith('negative-') else None
                self.compare(row['input'], reason)

    def test_five_positive_witnesses_keep_full_ram_and_19_writers(self):
        for row in curated_controls()[:5]:
            with self.subTest(caseId=row['caseId']):
                case = row['input']
                result = self.compare(case)
                stages = result['modeledStages']
                self.assertEqual([len(stage['orderedPersistentWrites']) for stage in stages], [6, 5, 5, 3])
                self.assertEqual(result['persistentWriteCount'], 19)
                self.assertEqual(stages[0]['ramAfter']['r0'], case['initialRam']['r1'])
                self.assertNotEqual(stages[0]['ramAfter']['r0'], 0x21)
                self.assertEqual(stages[-1]['ramAfter']['r3'], case['srbuf']['reads'][2]['value'])
                self.assertEqual(stages[-1]['ramAfter']['r7'], 0)
                self.assertEqual(stages[-1]['ramAfter']['r6'], stages[-2]['ramAfter']['r6'])
                self.assertEqual(stages[-1]['ramAfter']['status0356'], case['initialRam']['status0356'] | 0x80)
                for earlier, later in zip(stages, stages[1:]):
                    self.assertEqual(earlier['ramAfter'], later['ramBefore'])

    def test_checksum_carry_zero_and_one_are_independently_covered(self):
        for flag, expected_cf in ((1, 1), (219, 0)):
            with self.subTest(flag=flag):
                result = self.compare(reviewed_case(flag=flag))
                final = result['modeledStages'][-1]
                self.assertIs(type(final['checksumZF']), int)
                self.assertIs(type(final['checksumCF']), int)
                self.assertEqual(final['checksumZF'], 1)
                self.assertEqual(final['checksumCF'], expected_cf)

    def test_odd_ssp_frame_word_alignment_and_raw_ssp_parity(self):
        expected = [('PC', 0x027E), ('A', 0x027C), ('LRB', 0x027A), ('PSW', 0x0278)]
        layout = frame_layout(0x027F)
        self.assertEqual(layout['incomingSSP'], 0x027F)
        self.assertEqual(layout['sspAfterEntry'], 0x0277)
        self.assertEqual(layout['sspAfterRti'], 0x027F)
        self.assertEqual([(row['role'], row['wordAddress']) for row in layout['entryWordSlots']], expected)
        self.assertEqual([row['role'] for row in layout['rtiWordReads']], ['PSW', 'LRB', 'A', 'PC'])
        self.assertEqual(sorted(layout['byteFootprint']), list(range(0x0278, 0x0280)))
        self.assertTrue(layout['parityPreserved'])
        for value in (True, -1, 0x10000, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                frame_layout(value)

    def test_matching_rti_restores_its_own_context_not_instruction_pc(self):
        case = reviewed_case()
        result = self.compare(case)
        self.assertEqual(len({row['creator'] for row in result['modeledFrames']}), 4)
        for given, observed in zip(case['frames'], result['modeledFrames']):
            self.assertEqual(observed['restoredContext'], given['savedContext'])
            self.assertEqual(observed['rtInstructionPC'], 0x029C)
            self.assertIsNone(observed['actualRestoredPC'])
            self.assertNotEqual(observed['restoredContext']['PC'], 0x029C)
            self.assertEqual([row['role'] for row in observed['rtiWordReads']], ['PSW', 'LRB', 'A', 'PC'])

    def test_reused_numeric_frame_locations_do_not_merge_creators(self):
        result = self.compare(reviewed_case())
        frames = result['modeledFrames']
        self.assertEqual([row['entryWordSlots'][0]['wordAddress'] for row in frames], [0x047E] * 4)
        self.assertEqual(len({row['creator'] for row in frames}), 4)
        self.assertEqual(len({row['restoredContext']['PC'] for row in frames}), 4)

    def test_parser_bank_frame_overlap_refuses_even_and_odd_ssp(self):
        for ssp in (0x03F6, 0x03F7):
            with self.subTest(ssp=ssp):
                case = reviewed_case()
                case['frames'][0]['incomingSSP'] = ssp
                self.compare(case, 'FrameParserBankOverlap')

    def test_unknown_ssp_never_becomes_a_safe_frame(self):
        case = reviewed_case()
        case['frames'][0]['incomingSSP'] = None
        self.compare(case, 'UnknownSspCannotBeDeclaredSafe')

    def test_sfr_pointing_and_status_frame_aliases_remain_blocked(self):
        for ssp in (0x0055, 0x0097, 0x0357):
            with self.subTest(ssp=ssp):
                case = reviewed_case()
                case['frames'][0]['incomingSSP'] = ssp
                self.compare(case, 'FrameSfrOrPointingRamOverlap')

    def test_source_profile_conflict_is_not_a_universal_tx_assignment(self):
        tx = self.compare(reviewed_case())
        rx = self.compare(reviewed_case(profile='InstructionTable1_1'))
        self.assertEqual(tx['conditionalCause'], 'SerialTransmittingReady')
        self.assertEqual(rx['conditionalCause'], 'SerialReceivingReady')
        self.assertTrue(tx['allocationConflictPreserved'])
        self.assertTrue(rx['allocationConflictPreserved'])
        case = reviewed_case()
        case['irq']['allocationConflictAcknowledged'] = False
        self.compare(case, 'UniversalVectorAllocationClaim')

    def test_four_access_ids_are_not_four_receive_completions(self):
        result = self.compare(reviewed_case())
        self.assertEqual(result['bufferParities'], [1, 0, 1, 0])
        self.assertEqual(result['conditionalContentChangeGaps'], [True, True, True])
        case = reviewed_case()
        case['srbuf']['receiveCompletionCountClaim'] = 4
        self.compare(case, 'InventedSrbufReadCompletion')

    def test_masks_and_mie_window_do_not_create_hardware_events(self):
        result = self.compare(reviewed_case())
        self.assertEqual(result['maskBit1Entry'], 0)
        self.assertEqual(result['maskBit1Tail'], 1)
        self.assertEqual(result['mieWindow']['setPC'], 0x0217)
        self.assertEqual(result['mieWindow']['clearPC'], 0x0297)
        self.assertEqual(result['actual'], ACTUAL)

    def test_same_value_status_and_ready_writes_keep_fresh_generations(self):
        result = self.compare(reviewed_case(status=0x82))
        generations = []
        for stage in result['modeledStages']:
            first = stage['orderedPersistentWrites'][0]
            self.assertEqual(first['pc'], 0x0222)
            self.assertEqual(first['value'], stage['ramBefore']['status0356'])
            generations.append(first['storageGeneration'])
        self.assertEqual(len(set(generations)), 4)
        last = result['modeledStages'][-1]
        ready = last['orderedPersistentWrites'][1]
        self.assertEqual(ready['pc'], 0x0290)
        self.assertEqual(ready['value'], last['ramBefore']['status0356'])
        self.assertEqual(ready['storageGeneration'], result['readyGeneration'])
        self.assertNotIn(result['readyGeneration'], generations)

    def test_rti_does_not_automatically_restore_ie_or_pointer_ram(self):
        for key, reason in (('rtiRestoresIE', 'RtiDoesNotRestoreIE'),
                ('rtiRestoresPointingRam', 'RtiDoesNotRestorePointingRam')):
            with self.subTest(field=key):
                case = reviewed_case()
                case['frameContract'][key] = True
                self.compare(case, reason)

    def test_no_premature_parser_consumption_or_host_handoff(self):
        case = reviewed_case()
        case['foreground']['noPrematureParserConsumptionHypothesis'] = False
        self.compare(case, 'PrematureParserConsumption')
        case = reviewed_case()
        case['foreground']['lrb'] = 0x007E
        self.compare(case, 'WrongParserContext')

    def test_all_actual_authority_stays_zero_or_null_even_on_refusal(self):
        for control in curated_controls():
            with self.subTest(caseId=control['caseId']):
                result = reference_case(control['input'])
                self.assertEqual(result['actual'], ACTUAL)
                self.assertIs(type(result['actual']['irqDeliveries']), int)
                self.assertFalse(result['firmwareReady'])
                self.assertEqual(result['runtimeAdmission'], 'Blocked')
                self.assertTrue(result['allocationConflictPreserved'])
                if not result['valid']:
                    self.assertEqual(result['modeledFrames'], [])
                    self.assertEqual(result['modeledStages'], [])
                    self.assertIsNone(result['readyGeneration'])

    def test_static_source_projections_match_70_frozen_obligations(self):
        result = independent_check(irq_analysis(), lineage_analysis())
        self.assertTrue(result['valid'], result['firstMismatch'])
        self.assertEqual(result['comparedFactCount'], 70)

    def test_independent_source_check_rejects_meaningful_mutations(self):
        irq, lineage = irq_analysis(), lineage_analysis()
        mutations = (
            ('irq', ('sourceProfiles', 'actualSource'), 'SerialTransmittingReady'),
            ('irq', ('frameContract', 'entryRoleOffsets'), [['PC', 0], ['A', -2], ['PSW', -4], ['LRB', -6]]),
            ('irq', ('rtiContract', 'order'), ['PC', 'A', 'LRB', 'PSW']),
            ('irq', ('rtiContract', 'instructionPCIsRestoredReturnPC'), True),
            ('irq', ('rtiContract', 'sfAssignmentInRTIFunction'), 0),
            ('irq', ('actualNative', 'actualIRQDeliveries'), 4),
            ('irq', ('actualNative', 'actualCpuExecutions'), False),
            ('lineage', ('handlerContext', 'lrb'), 0x0041),
            ('lineage', ('maskAndMieChronology', 'entrySourceWord'), 0x00F8),
            ('lineage', ('maskAndMieChronology', 'conditionalMIE'), 0),
            ('lineage', ('readyRetention', 'actualInitialReadyOwner'), 'fabricated:native-owner'),
            ('lineage', ('invocations', 2, 'srbufReadPC'), 0x0277),
            ('lineage', ('invocations', 3, 'actualFrameCreator'), 'fabricated:frame'),
            ('lineage', ('rtiAndForeground', 'parserSCB'), 2),
            ('lineage', ('actualCpuExecutions',), 1),
        )
        for target, path, replacement in mutations:
            with self.subTest(target=target, path=path):
                left, right = deepcopy(irq), deepcopy(lineage)
                value = left if target == 'irq' else right
                for key in path[:-1]:
                    value = value[key]
                value[path[-1]] = replacement
                self.assertFalse(independent_check(left, right)['valid'])

    def test_header_old_r0_effect_cannot_disappear_from_projection(self):
        irq, lineage = irq_analysis(), lineage_analysis()
        effects = lineage['invocations'][0]['orderedDataAndContextEffects']
        selected = [row for row in effects if row['pc'] == 0x0275 and row['address'] == 0x03F0]
        self.assertEqual(len(selected), 1)
        lineage['invocations'][0]['orderedDataAndContextEffects'] = [row for row in effects if row is not selected[0]]
        self.assertFalse(independent_check(irq, lineage)['valid'])

    def test_bad_case_shape_and_false_boolean_execution_count_refuse(self):
        self.compare({}, 'ClosedCaseShapeRequired')
        case = reviewed_case()
        case['actual']['irqDeliveries'] = False
        self.compare(case, 'CurrentIrqExecutionClaimed')


if __name__ == '__main__':
    unittest.main()
