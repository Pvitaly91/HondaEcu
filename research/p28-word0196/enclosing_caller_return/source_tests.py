"""Source obligations, bounded effects and full independent canonical comparisons."""

from copy import deepcopy
import unittest

from mode_caller_continuity.corpus import fixture as frozen_fixture
from mode_caller_continuity.data03cb_writers import data03cb_indexed_writer
from mode_caller_continuity.reaching_definitions import data03cb_reaching_definitions

from . import reference_oracle
from .analysis import AUTHORITY, OPERATIONS, canonical, record, validate_authority
from .corpus import MODE_PROOF, case, cases, frame_query, indexed_query, lineage_query, mode_query, program_query
from .corpus import partial_slot


INDEXED = 'indexed_acquisition_caller'
MODE = 'mode_enclosing_caller'
PROGRAM = 'program_table_path'
FRAME = 'call_return_obligations'
LINEAGE = 'indexed_to_mode_reaching_definitions'
CLOBBERS = 'callee_clobber_summary'
FORBIDDEN_STEPS = {0x5CB7, 0x5CCD, 0x5CD2, 0x60E4, 0x2891, 0x3FB5, 0x3FF9, 0x2995}


def clobber_input(caller=0x27D0, phase='ModeCalleeBeforeRt', scb=6, context=True):
    return {'inputClass': 'SyntheticTestInput', 'callerPc': caller, 'phase': phase,
            'scb': scb, 'contextEstablished': context}


class SourceTests(unittest.TestCase):
    def calculate(self, operation, query):
        return OPERATIONS[operation](query)

    def test_full_canonical_corpus_equality(self):
        case_ids, operations = set(), set()
        for item in cases():
            self.assertNotIn(item['id'], case_ids)
            case_ids.add(item['id'])
            operations.add(item['operation'])
            expected = canonical(reference_oracle.record(item))
            actual = canonical(record(item))
            self.assertEqual(actual, expected, item['id'])
        self.assertEqual(operations, set(OPERATIONS))

    def test_closed_inputs_reject_fake_targets_and_contradictory_alias_slots(self):
        query = indexed_query()
        query['calleeTarget'] = 0x5F45
        with self.assertRaises(ValueError):
            self.calculate(INDEXED, query)
        query = indexed_query()
        query['snapshot']['sfrReadbacks']['0019']['knownBits'] = {'4': 0}
        with self.assertRaises(ValueError):
            self.calculate(INDEXED, query)
        query = indexed_query()
        query['inputClass'] = 'ActualHardwareObservation'
        with self.assertRaises(ValueError):
            self.calculate(INDEXED, query)
        query = frame_query()
        query['frame']['hostReturnPc'] = 0x2869
        with self.assertRaises(ValueError):
            self.calculate(FRAME, query)
        query = program_query(MODE_PROOF)
        query['operand']['index'] = True
        with self.assertRaises(ValueError):
            self.calculate(PROGRAM, query)

    def test_nested_and_input_states_are_immutable(self):
        queries = ((INDEXED, indexed_query()), (MODE, mode_query(MODE_PROOF)),
                   (PROGRAM, program_query(MODE_PROOF)), (FRAME, frame_query()),
                   (LINEAGE, lineage_query()), (CLOBBERS, clobber_input()))
        for operation, query in queries:
            with self.subTest(operation=operation):
                before = canonical(query)
                self.calculate(operation, query)
                self.assertEqual(canonical(query), before)

    def test_indexed_caller_identity_and_selected_x1_bank(self):
        for caller, expected_return, listed_dd in ((0x276A, 0x276D, 1), (0x2B64, 0x2B67, 0)):
            for index in range(8):
                with self.subTest(caller=caller, index=index):
                    query = indexed_query(caller)
                    query['snapshot']['registers']['scb'] = index
                    query['snapshot']['sfrReadbacks']['0024']['value'] = index << 5
                    value = self.calculate(INDEXED, query)
                    self.assertEqual(value['caller'], {'callerPc': caller, 'calleeTarget': 0x5C86,
                                                       'returnSiteCandidate': expected_return, 'listedEntryDD': listed_dd})
                    stores = [item['address'] for item in value['journal'] if item['space'] == 'DATA']
                    self.assertEqual(stores, [0x80 + 8 * index, 0x3CE + index, 0x3C6 + index])
                    self.assertEqual(value['state']['registers']['usp'], query['snapshot']['registers']['usp'])
                    self.assertEqual(value['selectedIndex'], index)
                    self.assertIs(value['conditionalData03cbWriterEstablished'], index == 5)
                    self.assertEqual(value['exactStopBoundary'], 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7')

    def test_unknown_irq_bit_retains_symbolic_intent_and_stops_before_adc(self):
        query = indexed_query()
        supplied = query['snapshot']['sfrReadbacks']['0019']
        partial_slot(supplied, {7: 1})
        value = self.calculate(INDEXED, query)
        self.assertEqual(value['boundary'], 0x5CA3)
        self.assertEqual(value['status'], 'IndeterminateBranch')
        self.assertIsNone(value['state']['registers']['zf'])
        self.assertEqual(value['state']['sfrReadbacks']['0019'], supplied)
        self.assertEqual(value['reads'][-1]['space'], 'SYMBOLIC_SFR_READBACK')
        self.assertEqual([item['address'] for item in value['reads']], [0x230, 0x19])
        self.assertEqual(value['journal'], [value['irqhClearIntent']])
        self.assertEqual(value['irqhClearIntent']['knownBitsAfter'], {'4': 0, '7': 1})
        self.assertIsNone(value['irqhClearIntent']['priorBit'])
        self.assertEqual(value['inheritedResults'], [])

    def test_irq_old_zero_branches_to_same_value_marker_before_brk(self):
        query = indexed_query()
        query['snapshot']['sfrReadbacks']['0019']['value'] = 0x80
        query['snapshot']['memory']['00F5'] = 0x4A
        value = self.calculate(INDEXED, query)
        self.assertEqual([(s['pc'], s['next']) for s in value['steps']],
                         [(0x5C86, 0x5CA0), (0x5CA0, 0x5CA3), (0x5CA3, 0x5CCE), (0x5CCE, 0x5CD2)])
        self.assertEqual(value['exactStopBoundary'], 'STOP_BEFORE_BRK_5CD2')
        self.assertEqual(value['state']['registers']['zf'], 1)
        intent, marker = value['journal']
        self.assertEqual((intent['space'], intent['address'], intent['priorBit'], intent['after']),
                         ('SOFTWARE_SFR_INTENT', 0x19, 0, 0x80))
        self.assertIs(intent['sameDeclaredValue'], True)
        self.assertEqual((marker['space'], marker['address'], marker['after']), ('DATA', 0xF5, 0x4A))
        self.assertIs(marker['sameValue'], True)
        self.assertNotEqual(marker['afterGeneration'], query['snapshot']['generations']['00F5'])

    def test_indexed_entry_and_timer_refusals_do_not_bypass_source_guards(self):
        query = indexed_query()
        query['snapshot']['memory']['0230'] = 8
        value = self.calculate(INDEXED, query)
        self.assertEqual(value['exactStopBoundary'], 'STOP_BEFORE_TIMER_IE_PATH_5C89')
        self.assertEqual([read['address'] for read in value['reads']], [0x230])
        self.assertEqual(value['journal'], [])
        self.assertIsNone(value['irqhClearIntent'])
        for field, invalid in (('callerPc', 0x27D0), ('entryEstablished', None)):
            query = indexed_query()
            query[field] = invalid
            value = self.calculate(INDEXED, query)
            self.assertEqual((value['status'], value['reads'], value['steps']), ('OutsideVerifiedScope', [], []))
        query = indexed_query()
        query['snapshot']['registers']['lrb'] = 0x21
        value = self.calculate(INDEXED, query)
        self.assertEqual((value['boundary'], value['reads']), (0x5C86, []))

    def test_unknown_index_and_unknown_scb_cannot_assign_a_writer_address(self):
        query = indexed_query()
        partial_slot(query['snapshot']['sfrReadbacks']['0024'], {})
        value = self.calculate(INDEXED, query)
        self.assertIsNone(value['selectedIndex'])
        self.assertEqual(value['boundary'], 0x5CAF)
        self.assertFalse(any(item['address'] in range(0x3C6, 0x3D6) for item in value['journal']))
        self.assertFalse(any(read['address'] == 0x61 for read in value['reads']))
        query = indexed_query()
        query['snapshot']['registers']['scb'] = None
        value = self.calculate(INDEXED, query)
        self.assertEqual((value['boundary'], value['selectedIndex']), (0x5CAC, 5))
        self.assertIs(value['conditionalData03cbWriterEstablished'], False)
        self.assertEqual(value['journal'], [value['irqhClearIntent']])

    def test_indexed_frozen_child_and_generation_labels_are_not_rewritten(self):
        query = indexed_query()
        query['snapshot']['memory'].update({'03CB': 0x80, '0230': None})
        query['snapshot']['knownBits']['0230.3'] = 0
        value = self.calculate(INDEXED, query)
        expected_input = frozen_fixture()
        expected_input['memory']['03CB'] = 0x80
        expected_input['registers']['zf'] = 0
        expected = data03cb_indexed_writer(expected_input)
        self.assertEqual(canonical(value['inheritedResults']), canonical([expected]))
        for ordinal, event in enumerate(expected['journal'], start=2):
            aggregated = value['journal'][ordinal - 1]
            self.assertEqual(aggregated['ordinal'], ordinal)
            self.assertEqual(aggregated['stageOrdinal'], event['ordinal'])
            self.assertEqual(aggregated['afterGeneration'], event['afterGeneration'])
        self.assertIs(value['journal'][-1]['sameValue'], True)
        self.assertEqual(value['state']['knownBits']['0230.3'], 0)
        self.assertEqual(value['state']['sfrReadbacks']['0019'], query['snapshot']['sfrReadbacks']['0019'])

    def test_mode_prefix_writes_local_r0_from_fixed_program_operand_and_stops(self):
        writer_pcs = [0x5F4B, 0x5F53, 0x5F63, 0x5F6B, 0x5F73, 0x5F7B, 0x5F83,
                      0x5F86, 0x5F89, 0x5F90, 0x5F93, 0x5F97, 0x7DF4]
        for caller, prior, incoming_dd in ((0x27D0, 0x27CE, 0), (0x4069, 0x4068, 1)):
            query = mode_query(MODE_PROOF, caller=caller)
            query['program']['60E6']['slot']['value'] = 0x80
            query['program']['60FB']['slot']['value'] = 0x73
            query['snapshot']['memory']['03C7'] = 0x23
            query['snapshot']['registers'].update(dd=incoming_dd, ah=0x69)
            query['snapshot']['registerKnownBits'] = {}
            value = self.calculate(MODE, query)
            self.assertEqual(value['callerContext']['priorSourceBoundary'], prior)
            self.assertEqual(value['callerContext']['listedIncomingDd'], incoming_dd)
            self.assertEqual((value['boundary'], len(value['steps'])), (0x7DF5, 35))
            self.assertEqual([write['pc'] for write in value['journal']], writer_pcs)
            self.assertEqual((value['state']['memory']['0208'], value['state']['memory']['0209']), (0x73, 0x23))
            self.assertEqual(value['state']['memory']['0216'] & 0x10, 0x10)
            self.assertEqual((value['state']['registers']['ah'], value['state']['registers']['cf']), (0x69, 0))
            self.assertEqual(value['steps'][-1]['pc'], 0x7DF4)
            self.assertEqual(value['inheritedResults'], [])

    def test_mode_entry_missing_program_cannot_borrow_the_detached_suffix(self):
        query = mode_query(MODE_PROOF, caller=0x4069)
        del query['program']['60E6']
        query['snapshot']['registers'].update(al=None, ah=None, zf=None, cf=None)
        query['snapshot']['registerKnownBits'] = {}
        value = self.calculate(MODE, query)
        self.assertEqual((value['boundary'], value['steps'][0]['pc'], value['journal']), (0x5F46, 0x5F45, []))
        self.assertEqual((value['state']['registers']['al'], value['state']['registers']['zf']), (0, 1))
        self.assertIsNone(value['state']['registers']['ah'])
        self.assertIsNone(value['state']['registers']['cf'])
        query = mode_query(MODE_PROOF, entry='At608F')
        query['callerPc'] = 0x27D0
        value = self.calculate(MODE, query)
        self.assertEqual((value['boundary'], value['steps'], value['reads']), (0x608F, [], []))

    def test_mode_detached_r0_zero_short_circuits_program_and_preserves_old_xor_caveat(self):
        query = mode_query(MODE_PROOF, entry='At608F')
        query['snapshot']['memory'].update({'0208': 0, '0217': 0x40, '03CB': 0x80, '0216': 8})
        del query['program']['6104']
        del query['program']['6105']
        value = self.calculate(MODE, query)
        self.assertEqual(value['exactStopBoundary'], 'STOP_BEFORE_RT_60E4')
        self.assertIsNone(value['callerContext'])
        self.assertFalse(any(read['space'] == 'PROGRAM' for read in value['reads']))
        self.assertEqual(value['state']['memory']['0356'] & 2, 2)
        self.assertEqual((value['state']['memory']['0382'], value['state']['memory']['0383']), (0, 7))
        by_pc = {step['pc']: step for step in value['steps']}
        self.assertIsNone(by_pc[0x60CF]['afterRegisters']['zf'])
        self.assertEqual(by_pc[0x60D7]['afterRegisters']['zf'], 0)
        self.assertNotIn(0x60E4, by_pc)

    def test_program_nonzero_r0_uses_fixed_address_and_shift_keeps_zf(self):
        for r0 in (1, 0xFE):
            query = program_query(MODE_PROOF, 0x80)
            query['snapshot']['memory']['0208'] = r0
            value = self.calculate(PROGRAM, query)
            table = [read for read in value['reads'] if read['space'] == 'PROGRAM']
            self.assertEqual([(read['address'], read['widthBits'], read['value']) for read in table],
                             [(0x6105, 8, 0x80)])
            self.assertIsNone(value['programOperandIndex'])
            shifted = next(step['afterRegisters'] for step in value['steps'] if step['pc'] == 0x60C6)
            self.assertEqual((shifted['al'], shifted['cf'], shifted['zf']), (0, 1, 0))
            self.assertEqual(value['state']['memory']['0356'] & 2, 2)
            self.assertEqual(value['boundary'], 0x60E4)

    def test_program_rejects_data_wrong_index_and_oem_claim_before_any_table_read(self):
        controls = (('space', 'DATA'), ('address', 0x6104), ('widthBits', 16),
                    ('index', 1), ('index', 0xFFFF), ('sourceBinding', None),
                    ('sourceBinding', 'InventedWrongSource'), ('valueClass', 'ClaimedOemByte'))
        for field, invalid in controls:
            with self.subTest(field=field, invalid=invalid):
                query = program_query(MODE_PROOF)
                query['operand'][field] = invalid
                value = self.calculate(PROGRAM, query)
                self.assertEqual((value['status'], value['boundary'], value['journal']), ('OutsideVerifiedScope', 0x60C2, []))
                self.assertFalse(any(read['space'] == 'PROGRAM' for read in value['reads']))
                self.assertEqual([step['pc'] for step in value['steps']], [0x60BD, 0x60C0])
                self.assertEqual(value['inheritedResults'][0]['reason'], 'ProgramTableSourceNotAdmitted')

    def test_program_partial_old_bit_and_wrong_dd_preserve_the_exact_prefix(self):
        query = program_query(MODE_PROOF)
        partial_slot(query['operand']['slot'], {7: 1})
        value = self.calculate(PROGRAM, query)
        shift = next(step for step in value['steps'] if step['pc'] == 0x60C6)
        self.assertIsNone(shift['afterRegisters']['al'])
        self.assertEqual((shift['afterRegisters']['cf'], shift['afterRegisters']['zf']), (1, 0))
        self.assertEqual(shift['afterRegisterKnownBits']['AL.0'], 0)
        for dd in (None, 1):
            query = program_query(MODE_PROOF)
            query['snapshot']['registers']['dd'] = dd
            value = self.calculate(PROGRAM, query)
            self.assertEqual((value['boundary'], value['steps'][-1]['pc'], value['journal']), (0x60C6, 0x60C2, []))
            self.assertIs(value['steps'][-1]['afterRegisters']['dd'], dd)
        query = program_query(MODE_PROOF)
        query['snapshot']['memory']['0208'] = None
        value = self.calculate(PROGRAM, query)
        self.assertEqual((value['boundary'], value['status']), (0x60C0, 'IndeterminateBranch'))
        self.assertFalse(any(read['space'] == 'PROGRAM' for read in value['reads']))

    def test_formal_frame_geometry_uses_aligned_word_and_unrounded_ssp(self):
        for caller, candidate in ((0x276A, 0x276D), (0x2B64, 0x2B67), (0x27D0, 0x27D3), (0x4069, 0x406C)):
            query = frame_query(caller, ssp=0x047F)
            value = self.calculate(FRAME, query)
            self.assertEqual(value['status'], 'CompleteConditional')
            self.assertEqual(value['state']['geometry'], {'frameAddress': 0x047E, 'sspAfterCall': 0x047D,
                            'returnReadAddress': 0x047E, 'sspAfterReturn': 0x047F, 'savedPc': candidate})
            self.assertEqual(value['state']['formalReturnedPc'], candidate)
            self.assertEqual([row['widthBits'] for row in value['frameObligations']], [16, 16])
            self.assertEqual((value['reads'], value['journal'], value['steps']), ([], [], []))
            self.assertIsNone(value['actualReturnExecution'])
            self.assertIsNone(value['actualFramePop'])

    def test_formal_frame_refuses_rti_unknown_ssp_and_desired_return_substitution(self):
        controls = (('frame', 'kind', 'Interrupt', 'InterruptFrameCannotReturnViaRt'),
                    ('frame', 'low', None, 'FrameContentsOrOwnerUnknown'),
                    ('frame', 'high', 0x28, 'FrameDoesNotMatchCall'),
                    (None, 'sspBeforeReturn', 0x047E, 'UnbalancedStackPointer'),
                    (None, 'incomingSsp', None, 'StackPointerUnknown'),
                    (None, 'returnPc', 0x2869, 'CallReturnSourceMismatch'),
                    (None, 'claim', 'HostSelectedReturn', 'NonConditionalFrameClaim'))
        for container, key, invalid, reason in controls:
            with self.subTest(container=container, key=key, invalid=invalid):
                query = frame_query()
                (query if container is None else query[container])[key] = invalid
                value = self.calculate(FRAME, query)
                self.assertEqual(value['reason'], reason)
                self.assertIsNone(value['state']['formalReturnedPc'])
                self.assertIsNone(value['actualSavedPcObservation'])
                self.assertEqual((value['journal'], value['steps']), ([], []))

    def test_formal_frame_rejects_source_bound_stack_aliases_despite_all_true_premises(self):
        for ssp, aligned, alias in ((0x03CB, 0x03CA, 'Data03cbAlias'), (0x0357, 0x0356, 'ModeBitAlias'),
                                    (0x0209, 0x0208, 'LocalR0Alias'), (0x0383, 0x0382, 'ModeWordAlias'),
                                    (0x0087, 0x0086, 'PointingBankAlias')):
            value = self.calculate(FRAME, frame_query(ssp=ssp))
            self.assertEqual(value['reason'], 'FrameAliasRequiresIndependentProof')
            self.assertEqual((value['state']['geometry']['frameAddress'], value['state']['alias']), (aligned, alias))
            self.assertFalse(value['state']['nativeFrameOwnerEstablished'])
            self.assertEqual(value['journal'], [])

    def test_clobber_summary_retains_flags_caveats_and_unknown_nested_context(self):
        complete = self.calculate(CLOBBERS, clobber_input())
        self.assertEqual(complete['exactStopBoundary'], 'STOP_BEFORE_RT_60E4')
        self.assertEqual(complete['state']['dpAliasCandidates'], [0xB4])
        self.assertEqual(complete['state']['registerEffects']['DP'], 'ProvenOverwritten')
        self.assertEqual(complete['state']['registerEffects']['USP'], 'ProvenUnchangedWithinReviewedPath')
        self.assertEqual(complete['state']['registerEffects']['HC'], 'ConditionallyOverwritten')
        self.assertEqual(complete['state']['undefinedLogicalPswFlags'], ['CF', 'ZF', 'HC'])
        nested = self.calculate(CLOBBERS, clobber_input(caller=0x4069, phase='CallerPreEntry'))
        self.assertEqual((nested['boundary'], nested['state']['unreviewedPreEntryCallee']), (0x4068, 0x4068))
        self.assertEqual(set(nested['state']['registerEffects'].values()), {'UnknownDueToNestedCallee'})
        missing = self.calculate(CLOBBERS, clobber_input(context=None))
        self.assertEqual(set(missing['state']['registerEffects'].values()), {'UnknownDueToUnreviewedPath'})
        self.assertEqual(missing['journal'], [])

    def test_lineage_requires_matching_frame_and_never_confirms_mode_to_config(self):
        query = lineage_query()
        value = self.calculate(LINEAGE, query)
        self.assertEqual((value['status'], value['boundary']), ('CompleteConditional', 0x60CC))
        self.assertEqual(value['state']['retainedGeneration'], query['localLineage']['requestedGeneration'])
        self.assertIsNone(value['state']['actualNativeData03cbOwner'])
        self.assertIs(value['state']['nativeContinuityEstablished'], False)
        configuration = next(edge for edge in value['sourceEdges'] if (edge['from'], edge['to']) == (0x60E4, 0x2869))
        self.assertEqual(configuration['class'], 'SourceUnbound')
        self.assertEqual(canonical(value['inheritedResults'][0]),
                         canonical(data03cb_reaching_definitions(query['localLineage'])))
        query['indexedReturn']['premises']['frameIntegrity'] = None
        value = self.calculate(LINEAGE, query)
        self.assertEqual((value['reason'], value['boundary']), ('IndexedReturnUnestablished', 0x5CB7))
        self.assertIsNone(value['state']['retainedGeneration'])

    def test_lineage_rejects_missing_handoff_alternate_pair_and_mode_stack_alias(self):
        for premise in (False, None):
            query = lineage_query()
            query['premises']['explicitHandoff'] = premise
            value = self.calculate(LINEAGE, query)
            self.assertEqual(value['reason'], 'LineagePremisesNotEstablished')
            self.assertIsNone(value['state']['retainedGeneration'])
        query = lineage_query()
        query['modeCallerPc'] = 0x4069
        value = self.calculate(LINEAGE, query)
        self.assertEqual(value['reason'], 'CommonCallerPathUnestablished')
        query = lineage_query()
        query['modeIncomingSsp'] = 0x03CB
        value = self.calculate(LINEAGE, query)
        self.assertEqual(value['state']['modeFrameAddress'], 0x03CA)
        self.assertEqual(value['reason'], 'ModeFrameAliasRequiresProof')
        self.assertIsNone(value['state']['retainedGeneration'])

    def test_lineage_cannot_retain_stale_or_same_value_competing_generation(self):
        query = lineage_query()
        query['localLineage']['requestedGeneration'] = 'InventedStale'
        value = self.calculate(LINEAGE, query)
        self.assertEqual(value['reason'], 'LocalWriterNotRetained')
        self.assertEqual(value['inheritedResults'][0]['state']['reachingDefinitions']['relation'], 'StaleGeneration')
        query = lineage_query()
        local = query['localLineage']
        prior_value = local['events'][0]['adcr0h']['value']
        local['events'].append({'kind': 'AlternateStore', 'id': 'word-overlap', 'address': 0x03CB,
                                'widthBits': 16, 'value': (prior_value << 8) | 0x55, 'generation': 'InventedWordWrite'})
        value = self.calculate(LINEAGE, query)
        self.assertIsNone(value['state']['retainedGeneration'])
        child = value['inheritedResults'][0]
        self.assertEqual(child['state']['lastSlot']['generation'], 'InventedWordWrite')
        self.assertEqual(child['journal'][-1]['address'], 0x03CA)
        self.assertIs(child['journal'][-1]['sameDeclaredValue'], True)

    def test_execution_authority_is_checked_on_nested_frozen_results(self):
        item = case('indexed-authority', INDEXED, indexed_query())
        output = record(item)['output']
        self.assertEqual({key: output[key] for key in AUTHORITY}, AUTHORITY)
        for query, operation in ((indexed_query(), INDEXED), (program_query(MODE_PROOF), PROGRAM),
                                 (frame_query(), FRAME), (mode_query(MODE_PROOF), MODE)):
            value = self.calculate(operation, query)
            self.assertFalse(FORBIDDEN_STEPS & {step['pc'] for step in value['steps']})
            self.assertFalse(any(read['address'] == 0x4700 for read in value['reads']))
            validate_authority(value)
        for name, fabricated in (('cpuInstructionRetirements', False), ('actualReturnExecution', {'pc': 0x2869}),
                                  ('actualTxIrqDelivery', True), ('actualBufferWrite', {'pc': 0x2995})):
            injected = deepcopy(output)
            injected['inheritedResults'][0][name] = fabricated
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_authority(injected)


if __name__ == '__main__':
    unittest.main()
