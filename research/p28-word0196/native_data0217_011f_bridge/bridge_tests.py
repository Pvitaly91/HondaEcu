"""New M2cc invented constraints and refusal controls, not old runtime replay."""
from copy import deepcopy
import json
import unittest

from native_data0217_011f_bridge.analysis import (
    EXPECTED_CONTRACT, canonical_records, curated_cases, example,
    minimum_frontier, read_contract, renumber, validate_contract, verify_case,
)
from native_data0217_011f_bridge.constraint_model import solve


def negative_controls():
    cases = []
    def invalid(name, change):
        item = example(name); change(item); cases.append((name, 'InputRefusal', item, None))
    def blocked(name, change):
        item = example(name); change(item); renumber(item)
        cases.append((name, 'ConstraintRefusal', item, None))
    def false_effect(name, change):
        item = example(name); result = solve(item); change(result)
        cases.append((name, 'FabricatedExpectedEffectRefusal', item, result))
    invalid('WrongPROGRAMAddress', lambda x: x['events'][1].update(programAddress=0x60ED))
    invalid('ProgramConfusedWithData', lambda x: x['events'][1].update(sourceSpace='DATA'))
    invalid('WrongSourceBit', lambda x: x['events'][1].update(sourceBit=6))
    invalid('WrongShiftSemantics', lambda x: x['events'][1].update(shift='SRLB A'))
    invalid('HostProvidedCF', lambda x: x['events'][1].update(hostCf=0))
    invalid('IncorrectDD', lambda x: x['events'][1].update(dd=1))
    invalid('WrongLRBPage', lambda x: x['context'].update(copyLrb=0x20))
    blocked('ProducerBypassed', lambda x: x['events'].pop(1))
    blocked('WrongHelperReturnPC', lambda x: x['events'][3].update(returnPc=0x406C))
    blocked('MissingCalFrame', lambda x: x['events'].pop(0))
    blocked('StaleReturnWord', lambda x: x['events'].insert(3,
        {'kind': 'overlapFrame', 'address': x['incoming']['ssp'], 'value': x['callerPc'] + 3}))
    invalid('CrossMachineGeneration', lambda x: x['events'][5].update(machine='invented:another-machine'))
    blocked('CrossRootCfgSplice', lambda x: x['events'][4].update(receiver=0x03ED))
    blocked('IrqFromStaticSoftwareEdge', lambda x: x['events'][4].update(evidence='ListedSoftwareEdge'))
    blocked('NestedFrameOverwriteIgnored', lambda x: x['events'].insert(3,
        {'kind': 'overlapFrame', 'address': x['incoming']['ssp'], 'value': 0x5555}))
    blocked('SourceOverwrittenBeforeCopy', lambda x: x['events'].insert(5,
        {'kind': 'overwriteBuffer', 'pc': 0x7000, 'address': 0x0217, 'bitValue': 0}))
    blocked('TargetOverwrittenAfterCopy', lambda x: x['events'].insert(6,
        {'kind': 'overwriteTarget', 'pc': 0x7000, 'address': 0x011F, 'bitValue': 0}))
    def before_producer(x):
        item = x['events'].pop(5); x['events'].insert(1, item)
    blocked('CopyBeforeProducer', before_producer)
    blocked('CopyAccumulatorMutated', lambda x: x['events'][5].update(accumulatorMutated=True))
    invalid('WrongHighByteMapping', lambda x: x['events'][5].update(sourceWord=0x0217))
    false_effect('InventedFullByteFromBit', lambda x: x['target'].update(byteValue=0))
    false_effect('UnknownNeighborsDefaultA5', lambda x: x['source'].update(byteValue=0xA5))
    blocked('Wrong012AContext', lambda x: x['context'].update(context012A='unrelated-caller'))
    invalid('OldSelectorGenerationImported', lambda x: x['context'].update(selectorGeneration='historical:M2bz'))
    invalid('OriginalRomByteInPublicFixture', lambda x: x.update(sourceIdentity='original-rom:private-byte'))
    false_effect('StaticTraceAsCpuExecution', lambda x: x.update(actualCpuExecutions=1))
    invalid('FabricatedWriteOrdinal', lambda x: x['events'][5].update(ordinal=999))
    contract = deepcopy(EXPECTED_CONTRACT); contract['baseSha'] = '0' * 40
    cases.append(('UnreviewedHistoricalFingerprint', 'ContractIdentityRefusal', contract, None))
    return cases


class BridgeTests(unittest.TestCase):
    def test_closed_contract_and_no_runtime_authority(self):
        self.assertEqual(read_contract(), EXPECTED_CONTRACT)
        self.assertFalse(EXPECTED_CONTRACT['selectedBitProofAdmitsActualByteRead'])

    def test_full_new_curated_model_and_independent_oracle(self):
        cases = curated_cases(); self.assertEqual(len(cases), 12)
        results = [verify_case(case) for case in cases]
        self.assertTrue(all(r['solverResult'] == 'SatisfiableUnderExplicitAssumptions' for r in results[:8]))
        self.assertEqual([r['solverResult'] for r in results[8:]], [
            'BlockedByExternalInterruptDelivery', 'BlockedByMissingReturnFrame',
            'BlockedByAliasUncertainty', 'UnsatisfiableWithinReviewedCFG'])

    def test_28_new_negative_requirements(self):
        rows = negative_controls(); self.assertEqual(len(rows), 28)
        self.assertEqual(len({r[0] for r in rows}), 28)
        for name, kind, case, claim in rows:
            with self.subTest(name=name, kind=kind):
                if kind == 'InputRefusal':
                    with self.assertRaises(ValueError):
                        solve(case)
                elif kind == 'ConstraintRefusal':
                    self.assertNotEqual(verify_case(case)['solverResult'], 'SatisfiableUnderExplicitAssumptions')
                elif kind == 'ContractIdentityRefusal':
                    with self.assertRaises(ValueError):
                        validate_contract(case)
                else:
                    with self.assertRaises(ValueError):
                        verify_case(case, claim)

    def test_selected_bit_lineage_does_not_require_unknown_neighbors(self):
        result = verify_case(example())
        self.assertIsNone(result['source']['byteValue']); self.assertIsNone(result['target']['byteValue'])
        self.assertEqual(result['target']['bitValue'], 0)
        self.assertEqual(result['target']['owner'], 'OwnerConditional')
        self.assertEqual(result['solverResult'], 'SatisfiableUnderExplicitAssumptions')
        self.assertEqual(result['wholeByteClassification'], 'WholeByteValueNotFullyOwned')
        self.assertFalse(result['actualByteReadAdmitted'])

    def test_later6039_changes_storage_not_selected_semantic_producer(self):
        result = verify_case(example())
        self.assertEqual(result['source']['semanticOrdinal'], 2)
        self.assertEqual(result['source']['storageOrdinal'], 3)
        self.assertEqual(result['target']['semanticOrdinal'], 2)
        self.assertEqual(result['target']['storageOrdinal'], 4)

    def test_same_value_rmw_and_word_copy_have_fresh_storage(self):
        case = example('same-values', root=0x03ED)
        result = verify_case(case)
        self.assertEqual(result['source']['byteValue'], case['incoming']['bufferByte'])
        self.assertEqual(result['target']['byteValue'], case['incoming']['targetByte'])
        self.assertEqual(result['source']['storageOrdinal'], 3)
        self.assertEqual(result['target']['storageOrdinal'], 4)

    def test_callers_require_distinct_matching_return_frames(self):
        p = verify_case(example('caller-p', caller=0x27D0))
        q = verify_case(example('caller-q', caller=0x4069))
        self.assertEqual(p['frame']['expectedReturnPc'], 0x27D3)
        self.assertEqual(q['frame']['expectedReturnPc'], 0x406C)
        self.assertNotEqual(p['machineId'], q['machineId'])
        self.assertEqual(p['frame']['restoredSsp'], 0x07E0)
        case = example(); case['events'].append(deepcopy(case['events'][3])); renumber(case)
        self.assertIn('ReturnRepeatedInSingleInvocation', verify_case(case)['violations'])
        case = example(); case['events'].insert(1, deepcopy(case['events'][0])); renumber(case)
        self.assertIn('MultipleCallsInSingleInvocation', verify_case(case)['violations'])

    def test_same_value_frame_overwrite_loses_original_frame_identity(self):
        case = example(); case['events'].insert(3, {'kind': 'overlapFrame',
            'address': case['incoming']['ssp'], 'value': case['callerPc'] + 3}); renumber(case)
        result = verify_case(case)
        self.assertFalse(result['frame']['validReturn'])
        self.assertNotEqual(result['solverResult'], 'SatisfiableUnderExplicitAssumptions')

    def test_mandatory_final_store_proves_specific_frame_contradiction(self):
        case = example(); case['incoming']['ssp'] = 0x0382
        result = verify_case(case)
        self.assertIn('MandatoryFinalStoreOverwritesReturnFrame', result['violations'])
        self.assertEqual(result['solverResult'], 'UnsatisfiableWithinReviewedCFG')

    def test_accumulator_frame_and_known_alias_domains_cannot_be_assumed_safe(self):
        case = example(); case['incoming']['ssp'] = 0x0006
        result = verify_case(case)
        self.assertIn('MandatoryAccumulatorWritesOverwriteReturnFrame', result['violations'])
        for address in (0x0004, 0x0094, 0x0240, 0x0356):
            case = example(); case['incoming']['ssp'] = address
            self.assertNotEqual(verify_case(case)['solverResult'], 'SatisfiableUnderExplicitAssumptions')

    def test_source_word_alias_of_call_frame_cannot_be_declared_safe(self):
        case = example(); case['incoming']['ssp'] = 0x0216
        result = verify_case(case)
        self.assertFalse(result['frame']['validReturn'])

    def test_late_frame_overlap_cannot_retroactively_break_completed_return(self):
        case = example(); case['events'].append({'kind': 'overlapFrame',
            'address': case['incoming']['ssp'], 'value': 0xAAAA}); renumber(case)
        result = verify_case(case)
        self.assertTrue(result['frame']['validReturn'])
        self.assertEqual(result['solverResult'], 'SatisfiableUnderExplicitAssumptions')

    def test_known_number_without_source_owner_stays_blocked(self):
        case = example(); case['sourceIdentity'] = None
        result = verify_case(case)
        self.assertEqual(result['target']['bitValue'], 0)
        self.assertEqual(result['solverResult'], 'BlockedBySourceOwner')

    def test_trio_flags_cf_transfer_and_ah_preservation(self):
        for byte in (0, 0x80, 0xFF):
            case = example(); case['programByte'] = byte; case['incoming']['dd'] = 1
            result = verify_case(case); states = result['registerEffects']
            self.assertEqual(states['afterLCB']['zf'], int(byte == 0))
            self.assertEqual(states['afterShift']['zf'], int(byte == 0))
            self.assertEqual(states['afterShift']['cf'], byte >> 7)
            self.assertEqual(states['afterShift']['al'], byte << 1 & 255)
            self.assertEqual(states['afterMB'], states['afterShift'])
            self.assertTrue(all(s['ah'] == case['incoming']['ah'] and s['dd'] == 0 for s in states.values()))

    def test_source_consistent_earlier_call_controls_stop_boundary(self):
        case = example(bit=1); case['context'].update(earlierCalls=[0x0611], old012ABit3=1)
        result = verify_case(case); self.assertEqual(result['conditionalStopBefore'], 0x0667)
        case['context'].update(earlierCalls=[0x0611, 0x0635])
        self.assertEqual(verify_case(case)['solverResult'], 'UnsatisfiableWithinReviewedCFG')

    def test_mandatory_later_rmw_and_single_invocation_order(self):
        case = example(); case['events'].pop(2); renumber(case)
        self.assertIn('Mandatory6039Bypassed', verify_case(case)['violations'])
        case = example(); event = case['events'].pop(2); case['events'].insert(1, event); renumber(case)
        self.assertIn('6039BeforeProducer', verify_case(case)['violations'])
        case = example(); case['events'].insert(3, deepcopy(case['events'][2])); renumber(case)
        self.assertIn('6039RepeatedInAcyclicHelper', verify_case(case)['violations'])

    def test_buffer_overwrite_after_copy_does_not_destroy_copied_token(self):
        case = example(); case['events'].insert(6, {'kind': 'overwriteBuffer', 'pc': 0x7000,
            'address': 0x0217, 'bitValue': 1}); renumber(case)
        result = verify_case(case)
        self.assertEqual(result['source']['owner'], 'OwnerUnknown')
        self.assertEqual(result['target']['owner'], 'OwnerConditional')
        self.assertEqual(result['target']['bitValue'], 0)
        self.assertEqual(result['solverResult'], 'SatisfiableUnderExplicitAssumptions')

    def test_missing_assumptions_do_not_become_execution(self):
        case = example(); case['hypotheses']['helperPredicatesSatisfied'] = None
        result = verify_case(case)
        self.assertEqual(result['solverResult'], 'UnknownOutsideReviewedScope')
        self.assertEqual(result['nativeEventIndexes'], [])
        self.assertEqual(result['nativeWriteOrdinals'], [])
        self.assertEqual(result['actualCpuExecutions'], 0)

    def test_receiver_boundary_and_reader_have_closed_order_and_multiplicity(self):
        cases = []
        case = example(); event = case['events'].pop(4); case['events'].insert(0, event); cases.append(renumber(case))
        case = example(); event = case['events'].pop(4); case['events'].append(event); cases.append(renumber(case))
        case = example(); case['events'].append(deepcopy(case['events'][4])); cases.append(renumber(case))
        case = example(); case['events'].pop(); cases.append(renumber(case))
        case = example(); case['events'].append(deepcopy(case['events'][-1])); cases.append(renumber(case))
        for case in cases:
            with self.subTest(events=[e['kind'] for e in case['events']]):
                self.assertEqual(verify_case(case)['solverResult'], 'UnsatisfiableWithinReviewedCFG')
        case = example(); case['events'].pop(4); renumber(case)
        self.assertEqual(verify_case(case)['solverResult'], 'BlockedByExternalInterruptDelivery')

    def test_helper_dominance_with_independent_fixed_point(self):
        from native_data0217_011f_bridge.helper_cfg import reviewed_helper, analyze_helper
        graph = reviewed_helper(); edges = graph['edges']; root, terminal = 0x5F45, 0x60E4
        dom = {node: ({root} if node == root else set(edges)) for node in edges}
        changed = True
        while changed:
            changed = False
            for node in sorted(set(edges) - {root}):
                parents = [p for p in edges if node in edges[p]]
                updated = {node} | set.intersection(*(dom[p] for p in parents))
                if updated != dom[node]:
                    dom[node] = updated; changed = True
        self.assertIn(0x5F6B, dom[terminal]); self.assertIn(0x6039, dom[terminal])
        report = analyze_helper(); self.assertEqual((report['nodeCount'], report['edgeCount']), (226, 253))
        self.assertFalse(report['pathEnvelopeIsActualRetirementCount'])

    def test_real_bridge_analysis_retains_external_gap_and_no_winner(self):
        from native_data0217_011f_bridge.bridge_reachability import analyze_bridges
        report = analyze_bridges()
        self.assertFalse(report['irqInjected']); self.assertEqual(report['actualCpuExecutions'], 0)
        self.assertIsNone(minimum_frontier()['comparison']['provenIntegratedWinner'])

    def test_full_canonical_json_roundtrip_has_no_field_loss(self):
        records = canonical_records(); self.assertEqual(len(records), 16)
        encoded = json.dumps(records, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
        self.assertEqual(records, json.loads(encoded))
        self.assertEqual(encoded, json.dumps(json.loads(encoded), ensure_ascii=True, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    unittest.main()
