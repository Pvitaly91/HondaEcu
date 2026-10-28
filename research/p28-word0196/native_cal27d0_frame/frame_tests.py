"""New small frame-specific controls; no old corpus or actual CPU execution."""
from copy import deepcopy
from hashlib import sha256
import unittest

from .analysis import (EXPECTED_CONTRACT, canonical, canonical_records, curated_cases,
    event, example, read_contract, validate_contract, verify_case)
from .frame_model import evaluate, geometry
from .reference_oracle import reference_geometry, reference_case
from .helper_frame import analyze_helper_frames, frame_assessment, reviewed_write_inventory
from .ssp_lineage import reviewed_ssp_lineage, prior_2777_helper
from .cal_rt_semantics import semantics_contract, memory_applicability


def negative_controls():
    rows = []
    def blocked(name, mutate, incoming=0x047E, kind='Conditional24F8'):
        case = example(name, incoming, kind); mutate(case)
        rows.append((name, 'ConstraintRefusal', case, None))
    def invalid(name, mutate):
        case = example(name); mutate(case); rows.append((name, 'InputRefusal', case, None))
    def false_claim(name, mutate, case=None):
        case = example(name) if case is None else case
        claim = evaluate(case); mutate(claim); rows.append((name, 'FabricatedEffectRefusal', case, claim))
    blocked('Frame0382FinalStore', lambda c: None, 0x0382, 'InventedHostOnly')
    blocked('Frame0006AccumulatorAlias', lambda c: None, 0x0006, 'InventedHostOnly')
    blocked('Frame0216SourceBufferRmw', lambda c: None, 0x0216, 'InventedHostOnly')
    false_claim('Frame011ECopyOwnershipHazard', lambda r: r.update(sourceBufferEffect='NoSelectedBufferCollision'),
        example('frame-011e', 0x011E, 'InventedHostOnly'))
    blocked('FrameAliasesArchitectureControl', lambda c: None, 0x0000, 'InventedHostOnly')
    blocked('FrameHighByteOnlyWrite', lambda c: c['events'].append(event(c, address=0x047F, value=0x27, width=1)))
    invalid('WrongCallerPC', lambda c: c['call'].update(pc=0x4069))
    invalid('WrongReturnPC', lambda c: c['call'].update(returnPc=0x406C))
    invalid('WrongCalLength', lambda c: c['call'].update(length=2))
    invalid('WrongTarget', lambda c: c['call'].update(target=0x5C86))
    invalid('WrongRtPC', lambda c: c['consumer'].update(pc=0x5CCD))
    invalid('RtiSubstituted', lambda c: c['consumer'].update(form='RTI'))
    blocked('StalePreexistingWord', lambda c: c['consumer'].update(creator='model:stale:old-return-word'))
    blocked('WrongFrameCreator', lambda c: c['consumer'].update(creator='model:another:CAL27D0'))
    invalid('CrossMachineFrameImport', lambda c: c['consumer'].update(machine='model:another-machine'))
    false_claim('WrongSspAlignment', lambda r: r.update(frameAddress=0x047F),
        example('odd-alignment', 0x047F, 'InventedHostOnly'))
    wrong = geometry(0); wrong['arithmeticSspAfterCAL'] = 0
    rows.append(('Incorrect16BitWrapping', 'GeometryClaimRefusal', 0, wrong))
    blocked('SspModifiedInsideHelper', lambda c: c['events'].append(event(c, address=0x0000, value=0x0478)))
    blocked('MissingEarlier276AReturn', lambda c: c['source']['conditions'].update(cal276A=None))
    blocked('Missing2777Return', lambda c: c['source']['conditions'].update(cal2777=None))
    blocked('MissingIncomingSspOwner', lambda c: c['source'].update(kind='Unknown', ownerId=None))
    false_claim('Host047EPromotedToNativeSource', lambda r: r.update(sourceClassification='SspCodeOwnedUnderExplicitConditions'),
        example('host-047e', 0x047E, 'InventedHostOnly'))
    blocked('InterruptedSourceHistory', lambda c: c['helper'].update(normalReturn='Interrupted'))
    blocked('UnprovedFlagBranchRelation', lambda c: c['helper'].update(normalReturn='UnknownPredicate'))
    false_claim('UnknownIndirectDeclaredDisjoint', lambda r: r.update(aliasClassification='ProvedDisjointWithinReviewedSoftwareContext'),
        _extra_unknown('indirect', 'UnknownIndirect'))
    false_claim('NestedIrqSilentlyIgnored', lambda r: r.update(conditionalReturnedPC=0x27D3), _extra_unknown('irq', 'NestedIrq'))
    blocked('SameValueGenerationDeduplicated', lambda c: c['events'].append(event(c, address=0x047E, value=0x27D3, kind='SameValueWrite')))
    false_claim('AccumulatorStackAliasIgnored', lambda r: r.update(conditionalReturnedPC=0x27D3), _stack_unknown())
    false_claim('UnknownSourceDefaultedA5OrZero', lambda r: r.update(incomingSSP=0, frameAddress=0xA5),
        example('unknown-source', None, 'Unknown'))
    false_claim('ActualWriteOrdinalFabricated', lambda r: r.update(actualAllNativeWriteOrdinal=7))
    false_claim('InventedRtPromotedToNative', lambda r: r.update(actualCpuExecutions=1))
    changed = deepcopy(EXPECTED_CONTRACT); changed['baseSourceFingerprintSha256'] = '0' * 64
    rows.append(('OldProtectedSourceShaRewritten', 'ContractIdentityRefusal', changed, None))
    rows.append(('UnapprovedSourceAddedToResearchProjection', 'CiProjectionRefusal', None, None))
    return rows


def _extra_unknown(name, kind):
    case = example(name); case['events'].append(event(case, address=None, value=None, kind=kind))
    return case


def _stack_unknown():
    case = example('unknown-stack-mode'); case['context']['accumulatorMode'] = 'Unknown'
    return case


class FrameTests(unittest.TestCase):
    def test_closed_contract_and_no_runtime_authority(self):
        self.assertEqual(read_contract(), EXPECTED_CONTRACT)
        self.assertFalse(EXPECTED_CONTRACT['runtimeAdmissionGranted'])
        self.assertIsNone(EXPECTED_CONTRACT['actualAllNativeWriteOrdinal'])

    def test_twelve_new_complete_independent_cases(self):
        cases = curated_cases(); self.assertEqual(len(cases), 12)
        results = [verify_case(case) for case in cases]
        self.assertEqual([r['conditionalReturnedPC'] for r in results[:4]], [0x27D3] * 4)
        self.assertEqual(results[4]['frameAddress'], None)
        self.assertEqual(results[5]['writeValue'], 0x0500)
        self.assertEqual(results[6]['registerEffects']['aAfterCal'], 0x27D3)
        self.assertEqual(results[-1]['frameGenerationStatus'], 'ReplacedByModelEvent')

    def test_33_negative_requirement_categories(self):
        rows = negative_controls()
        self.assertEqual(len(rows), 33); self.assertEqual(len({r[0] for r in rows}), 33)
        for name, kind, case, claim in rows:
            with self.subTest(name=name, kind=kind):
                if kind == 'InputRefusal':
                    with self.assertRaises(ValueError):
                        evaluate(case)
                    with self.assertRaises(ValueError):
                        reference_case(case, reviewed_write_inventory())
                elif kind == 'ConstraintRefusal':
                    result = verify_case(case)
                    self.assertIsNone(result['conditionalReturnedPC'])
                    self.assertIsNotNone(result['firstMissingObligation'])
                elif kind == 'FabricatedEffectRefusal':
                    with self.assertRaises(ValueError):
                        verify_case(case, claim)
                elif kind == 'GeometryClaimRefusal':
                    self.assertNotEqual(canonical(claim), canonical(reference_geometry(case)))
                elif kind == 'ContractIdentityRefusal':
                    with self.assertRaises(ValueError):
                        validate_contract(case)
                else:
                    self.check_unapproved_ci_path()

    def check_unapproved_ci_path(self):
        from pathlib import Path
        from original_rom_boundary.source_guard import Blob, tree, contents
        from . import ci_contract, ci_projection
        root = Path(__file__).resolve().parents[3]
        inventory = tree(root, ci_contract.BASE); raw = contents(root, (inventory,))
        base = {name: Blob(mode, raw[oid]) for name, (mode, oid) in inventory.items()}
        current = dict(base)
        for name in ci_projection.NEW_PATHS:
            current[name] = Blob('100644', b'{}\n' if name.endswith('.json') else b'# Invented policy control.\n')
        approved = ci_projection.new_source_fingerprint(current)
        current[ci_contract.WORKFLOW] = Blob('100644', ci_contract.make_workflow(base[ci_contract.WORKFLOW].data, approved))
        current['research/p28-word0196/native_cal27d0_frame/unapproved.py'] = Blob('100644', b'pass\n')
        decision = ci_projection.classify_changes(base, current, approved)
        self.assertTrue(decision['full_qa']); self.assertFalse(decision['research_only'])

    def test_geometry_boundaries_and_odd_ssp_are_separate_from_alias_safety(self):
        for s in (0, 1, 2, 3, 0x047E, 0x047F, 0xFFFE, 0xFFFF):
            with self.subTest(ssp=s):
                self.assertEqual(geometry(s), reference_geometry(s))
        self.assertEqual(geometry(0)['arithmeticSspAfterCAL'], 0xFFFE)
        self.assertEqual(geometry(1)['arithmeticSspAfterCAL'], 0xFFFF)
        odd = verify_case(example('odd', 0x047F, 'InventedHostOnly'))
        self.assertEqual((odd['frameAddress'], odd['sspAfterCAL'], odd['sspAfterRT']), (0x047E, 0x047D, 0x047F))

    def test_ssp_lrb_psw_control_aliases_block_ordinary_architecture_claims(self):
        for address, role in ((0, 'SSP'), (2, 'LRB'), (4, 'PSW')):
            result = verify_case(example('control-' + role, address, 'InventedHostOnly'))
            self.assertEqual(result['firstMissingObligation'], 'CALControlAlias:' + role)
            self.assertIsNone(result['conditionalReturnedPC']); self.assertIsNone(result['rtReadAddress'])
        self.assertIsNone(verify_case(example('self-ssp', 0, 'InventedHostOnly'))['sspAfterCAL'])

    def test_accumulator_frame_store_changes_a_before_mandatory_clrb(self):
        result = verify_case(example('frame-a', 6, 'InventedHostOnly'))
        self.assertEqual(result['registerEffects']['aAfterCal'], 0x27D3)
        self.assertEqual(result['registerEffects']['firstClrbA'], 0x2700)
        self.assertEqual((result['writeAddress'], result['writeWidth'], result['writeValue']), (6, 8, 0))
        self.assertEqual(result['candidateOverwritePC'], 0x5F45)

    def test_0382_final_word_is_incompatible_for_both_conditional_values(self):
        for final in (0x0500, 0x0700):
            case = example('final-' + str(final), 0x0382, 'InventedHostOnly'); case['helper']['finalA'] = final
            result = verify_case(case)
            self.assertEqual((result['candidateOverwritePC'], result['writeWidth'], result['writeValue']), (0x60E3, 16, final))
            self.assertNotEqual(final, 0x27D3)

    def test_frame047e_disjoint_for_every_scb_without_physical_mapping_claim(self):
        for scb in (None, *range(8)):
            case = example('bank-' + str(scb), kind='Conditional24F8' if scb == 0 else 'InventedHostOnly')
            case['context']['scb'] = scb
            result = verify_case(case)
            self.assertEqual(result['mustOverlapPCs'], []); self.assertEqual(result['mayOverlapPCs'], [])
            self.assertEqual(result['conditionalReturnedPC'], 0x27D3)
        unknown = example('mapping'); unknown['context']['mapping'] = 'UnknownAsic'
        self.assertEqual(verify_case(unknown)['firstMissingObligation'], 'ApplicableAsicWritableRetainedFrameMemory')
        self.assertFalse(memory_applicability()['actual047EWritableAndRetainedEstablished'])

    def test_unknown_scb_does_not_turn_some_bank_alias_into_must_write(self):
        case = example('unknown-bank-dp', 0x0084, 'InventedHostOnly'); case['context']['scb'] = None
        result = verify_case(case)
        self.assertEqual(result['mustOverlapPCs'], []); self.assertTrue(result['mayOverlapPCs'])
        case['context']['scb'] = 0
        self.assertTrue(verify_case(case)['mustOverlapPCs'])

    def test_source_buffers_are_distinct_from_local_return_feasibility(self):
        for address in (0x011A, 0x011E, 0x0212):
            result = verify_case(example('buffer-' + str(address), address, 'InventedHostOnly'))
            self.assertEqual(result['conditionalReturnedPC'], 0x27D3)
            self.assertNotEqual(result['sourceBufferEffect'], 'NoSelectedBufferCollision')
        self.assertIsNone(verify_case(example('source-0216', 0x0216, 'InventedHostOnly'))['conditionalReturnedPC'])

    def test_each_injected_control_register_write_invalidates_return_address_relation(self):
        for address, role in ((0, 'SSP'), (2, 'LRB'), (4, 'PSW')):
            case = example('mutate-' + role); case['events'].append(event(case, address=address, value=0x0123))
            result = verify_case(case)
            self.assertEqual(result['firstMissingObligation'], 'ModelControlRegisterWrite:' + role)
            self.assertIsNone(result['rtReadAddress'])

    def test_same_value_and_high_byte_writes_create_fresh_generations(self):
        for address, width, value in ((0x047E, 2, 0x27D3), (0x047F, 1, 0x27)):
            case = example('same-' + str(width)); case['events'].append(event(case, address=address, value=value, width=width, kind='SameValueWrite'))
            result = verify_case(case)
            self.assertEqual(result['frameGenerationStatus'], 'ReplacedByModelEvent')
            self.assertIsNone(result['conditionalReturnedPC'])
            self.assertEqual(result['modelEvents'][-1]['generationRole'], 'OverlappingFreshGeneration')

    def test_odd_word_event_records_effective_address_and_retains_raw_input(self):
        case = example('odd-event'); case['events'].append(event(case, address=0x047F, value=0x27D3))
        result = verify_case(case)
        self.assertEqual(case['events'][0]['address'], 0x047F)
        self.assertEqual(result['writeAddress'], 0x047E)
        self.assertEqual(result['modelEvents'][1]['address'], 0x047E)

    def test_unknown_or_nested_writes_are_not_declared_definite_observations(self):
        for kind in ('UnknownIndirect', 'NestedIrq'):
            case = example('uncertain-' + kind); case['events'].append(event(case, address=0x047E, value=0x27D3, kind=kind))
            result = verify_case(case)
            self.assertEqual(result['frameGenerationStatus'], 'MayBeReplaced')
            self.assertIsNone(result['rtReadAddress'])

    def test_host_reseed_is_forbidden_even_when_frame_bytes_are_disjoint(self):
        case = example('host'); case['events'].append(event(case, address=0x1000, value=1, kind='HostReseed'))
        result = verify_case(case)
        self.assertEqual(result['firstMissingObligation'], 'HostReseedAfterCALForbidden')
        self.assertIsNone(result['conditionalReturnedPC'])

    def test_prior_returns_and_numeric_ssp_owner_cannot_be_assumed_balanced(self):
        for field in ('ram2689', 'ram268D', 'cal276A', 'cal2777'):
            case = example('missing-' + field); case['source']['conditions'][field] = None
            result = verify_case(case)
            self.assertEqual(result['sourceClassification'], 'ReturnPathBlockedByEarlierCaller')
            self.assertEqual(result['firstMissingObligation'], 'SourceCondition:' + field)
        case = example('number-without-owner', 0x047E, 'Unknown')
        self.assertEqual(verify_case(case)['firstMissingObligation'], 'IncomingSspOwner')
        for spliced_scb in (None, 2, 7):
            case = example('spliced-scb-' + str(spliced_scb)); case['context']['scb'] = spliced_scb
            with self.assertRaises(ValueError):
                evaluate(case)
            with self.assertRaises(ValueError):
                reference_case(case, reviewed_write_inventory())

    def test_program_bit_side_effect_retains_semantics_but_not_storage_generation(self):
        for bit in (0, 1):
            case = example('bit-' + str(bit)); case['helper']['programBit'] = bit
            effect = verify_case(case)['producerBitEffects']
            self.assertEqual(effect['conditionalBitAfter5F6B'], bit)
            self.assertEqual(effect['conditionalBitAfter6039'], bit)
            self.assertNotEqual(effect['producerStorageGeneration'], effect['laterStorageGeneration'])
            self.assertIsNone(effect['wholeByteValue']); self.assertIsNone(effect['actualNativeWriteOrdinal'])

    def test_raw_inventory_is_independently_classified_for_selected_matrix(self):
        self.assertEqual(len(reviewed_write_inventory()), 238)
        for address in (0x0084, 0x011A, 0x011E, 0x0212, 0x0216, 0x0356, 0x0382, 0x047E):
            case = example('matrix-' + str(address), address, 'InventedHostOnly'); case['context']['scb'] = None
            result, matrix = verify_case(case), frame_assessment(address)
            self.assertEqual(result['mustOverlapPCs'], sorted({r['pc'] for r in matrix['mustOverlap']}))
            self.assertEqual(result['mayOverlapPCs'], sorted({r['pc'] for r in matrix['mayOverlap']} - set(result['mustOverlapPCs'])))

    def test_new_ssp_context_and_2777_predicates_are_not_actual_returns(self):
        lineage = reviewed_ssp_lineage(); helper = prior_2777_helper()
        self.assertEqual(lineage['producerContext']['conditionalScb'], 0)
        self.assertEqual(lineage['producerContext']['conditionalDpBefore27D0'], 0x0373)
        self.assertEqual((helper['entry'], helper['normalReturn'], helper['faultExit']), (0x5CD9, 0x5CF9, 0x5CF8))
        self.assertEqual(helper['errorRoute']['counterAfter'], 0)
        self.assertFalse(helper['actualReturnObserved']); self.assertFalse(lineage['nativeIncomingSspEstablished'])

    def test_refined_paths_are_static_bounds_with_unowned_live_sources(self):
        helper = analyze_helper_frames()
        self.assertEqual(helper['termination']['privateSourceBoundConservativePathCount'], 4)
        self.assertEqual(helper['termination']['privateSourceBoundConservativeInstructionEnvelope'], [146, 149])
        sources = helper['termination']['remainingLiveBranchSources']
        self.assertEqual({r['address'] for r in sources}, {None, 0x03CF})
        self.assertEqual(sources[0]['possibleInputAddress'], 0x03C7)
        self.assertFalse(helper['termination']['actualTerminationObserved'])
        self.assertFalse(semantics_contract()['alignment']['oddSSPGloballyRejectedByManufacturerEvidence'])

    def test_all_native_ordinals_null_and_canonical_fields_preserved(self):
        records = canonical_records()
        self.assertEqual(len(records), 17); self.assertEqual(len({r['caseId'] for r in records}), 17)
        for record in records[5:]:
            result = record['data']['result']
            for key in ('actualNativeInstructionIndex', 'actualLogicalWriteOrdinal', 'actualRawByteWriteOrdinals', 'actualAllNativeWriteOrdinal'):
                self.assertIsNone(result[key])
            self.assertEqual(result['actualCpuExecutions'], 0); self.assertFalse(result['runtimeAdmissionGranted'])
        self.assertEqual(canonical(records), canonical(__import__('json').loads(canonical(records))))
        self.assertEqual(len(sha256(canonical(records)).hexdigest()), 64)


if __name__ == '__main__':
    unittest.main()
