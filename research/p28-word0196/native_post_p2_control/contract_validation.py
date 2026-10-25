"""Independent closed requirements; JSON alone grants no runtime authority."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from original_rom_execution.verify import strict_json
from . import corpus, oracle

ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name('contract.json')
BASE = 'b67ea436870fe591f6ae4daca307341806d6f8eb'
SOURCES = (('research/p28-word0196/native_p2_handoff/contract.json', 6463, '87964bd798cc3d62571b01de26dc1febbf7f162d9ec42e92259f853d426fcf61'), ('research/p28-word0196/native_p2_handoff/corpus.py', 3971, '74f4ab1ac4c8d8bf9efb6ac589cf457f60d22e6bd05f0c0ecbdb3e239174526a'), ('research/p28-word0196/native_p2_handoff/oracle.py', 17277, '5d0722bb61c766c99e178995797e3d6f3d8f56cded86439a9f6fa91209d5800e'), ('research/p28-word0196/native_p2_handoff/admission.py', 2681, '91383ef322dd50fdc2008d30573ae28a0ca55534ec16ec8b4142a8045dbb8a46'), ('research/p28-word0196/native_p2_handoff/resume.py', 36198, 'f9f9aeca8d1cc8013ca527c43d07104772537ac8a718539e6e17e5098bc3892e'), ('research/p28-word0196/native_p2_handoff/checkpoint.py', 2433, '06e0c153d56b3c36bf00b30fac71be37d1828728110fd201e4b876efd78ef671'), ('docs/M2AB_POST_P2_CONTROL_HANDOFF.md', 8471, '53d0ab78eebb0650ff29feef648d7970ba6f6b4c640494c5641dc71bc4093e7f'), ('docs/M2AA_P2_OUTPUT_LATCH_HANDOFF.md', 8442, '14459918ab1b863e00dcc36ff32fd6b2cf53d3cb74ae60248364700a5c85c096'), ('docs/M2BU_NATIVE_ENTRY_CONTINUITY.md', 10808, '9f41342e73aaf7170ca7d252e43b682aa12f65ae33340b5ae87829c53fceb04a'), ('research/p28-word0196/original_rom_boundary/decode.py', 13934, 'ad7079c1894488834fa85d3f24b483e530440853eade244ff54556a3b442ad58'), ('rust/p28-slice-runner/src/post_p2_control.rs', 6066, '35ac4f0e7f14884eda04a127dd5afac4fdcf9834471249ad018cd347a1191deb'))
UNRESOLVED = ['ActualHardwareEcuExecutionNotObserved', 'RecoveredFullEcuSchedulerNotEstablished',
    'PhysicalSFNotEstablished', 'NativeStackSafetyNotEstablished', 'NativeP2InitialOwnershipNotEstablished',
    'NativeTCON0InitialOwnershipNotEstablished', 'NativeTRNSITInitialOwnershipNotEstablished',
    'TimerEvolutionNotModeled', 'IRQDeliveryNotInjected', 'PhysicalTimingEquivalenceNotEstablished',
    'ElectricalOutputNotObserved', 'ActualNativeDownstreamRejoinNotEstablished', 'SafeROMPlacementNotEstablished',
    'TargetProgramEquivalenceNotEstablished', 'FirmwareIntegrationNotEstablished',
    'DiagnosticCycleTimingEquivalenceNotEstablished']


def facts():
    return {'schemaVersion': 1, 'milestone': 'M2bw', 'baseCommit': BASE,
        'classification': 'ClosedPostP2ControlRequirements_NotExecutionEvidence',
        'sourceBindings': [{'path': p, 'bytes': n, 'sha256': h} for p, n, h in SOURCES],
        'manufacturer': {'instructionManualSha256': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
            'peripheralPackageSha256': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf',
            'printedPages': {'ANDB': '3-27', 'SB': '3-127', 'LB': '3-70', 'XORB': '3-175', 'MB': '3-77'},
            'semanticsAuthority': 'PrimaryManualAndReviewedM2ab_NotProductionOutput'},
        'program': {'entryPc': 0x54F5, 'privateEndExclusive': 0x55D2, 'segmentBytes': 221,
            'instructionNodes': 31, 'publicBase': 0x6400, 'publicEndExclusive': 0x64DD,
            'privateSource': 'VerifiedUnmodifiedOriginalImage_NoRelocationOrPadding',
            'publicSource': 'IndependentInventedCodeCells_NotOemByteCopy', 'noArbitraryStepping': True},
        'entry': {'oneCpuBusPerCase': True, 'noHostPcJump': True, 'noMidExecutionReseed': True,
            'noSnapshotImport': True, 'oneTechnicalPeripheralInitializationBeforeFirstInstruction': True,
            'unownedRamInitial': 165, 'unownedRamAuthority': 'ExplicitTechnicalBusCanary_NotNativeOwner',
            'controlSnapshotProvenance': corpus.CONTROL_PROVENANCE, 'historicalGenerationIdsTransferred': False},
        'control': {'tcon0Address': 64, 'tcon0AllowedInitial': [0x83, 0x87, 0x8B, 0x8F],
            'tcon0Operation': 'SetBit2', 'tcon0Zf': 'NotOldBit2', 'tcon0NativeReads': 2,
            'trnsitAddress': 70, 'trnsitImplementedInitial': list(range(16)), 'trnsitRead': 'F0OrImplementedFlags',
            'trnsitOperation': 'AndFB', 'trnsitStoredResult': 'OnlyImplementedLowNibble',
            'trnsitZf': 'WholeByteResultEqualsZero_AlwaysFalseInAdmittedDomain',
            'sameValueWritesCreateGeneration': True, 'permissionsClosedAfterControlInstruction': True,
            'alias006': 'CpuAL_LogicalRead_NoRawRamAccess', 'functionalP2IoSfAccesses': 0,
            'timerEvolutionModeled': False, 'irqDeliveryInjected': False, 'electricalEffectClaimed': False},
        'paths': {p: {'budget': corpus.BUDGETS[p], 'p2Pc': corpus.P2_PCS[p], 'controlPc': corpus.CONTROL_PCS[p],
            'stopBeforePc': corpus.TERMINALS[p], 'controlInstructions': 4 if p == 'A' else 1} for p in 'ABCD'},
        'corpus': {'privateCases': 32, 'publicCases': 32, 'casesPerPathPerMode': 8, 'retirementsPerMode': 680,
            'totalLocalPositiveRetirements': 1360, 'controlRetirementsPerMode': 56,
            'functionalControlReadsPerMode': 40, 'functionalControlWritesPerMode': 32,
            'sameValueControlWritesPerMode': 16, 'priorRuntimeResultsCountedAsNew': False},
        'cycleAccounting': deepcopy(oracle.CYCLE_ACCOUNTING),
        'trace': {'perInstructionFullCpuPswCompared': True, 'allProgramDataControlFieldsCompared': True,
            'p2GenerationRetainedAcrossTail': True, 'nativeControlGenerationAfterActualWriteOnly': True,
            'logicalControlReadsIncludeTwoSbReads': True, 'canonicalFieldExclusions': []},
        'delivery': {'defaultOffFeature': 'p28-word0196-post-p2-control', 'requiredBaseFeature': 'p28-word0196-p2-handoff',
            'cargoTarget': '.tmp/m2bw-owned/cargo-target', 'bothEnvironmentAndExplicitTargetDirRequired': True,
            'historicalProtectedRunnerPaths': 33, 'requiredCiJobs': 11,
            'inheritedAuthorizedPreservationExceptions': 1, 'strictHistoricalPreservationPass': False,
            'newUnauthorizedProtectedDifferencesRequired': 0, 'privateRomInCi': False,
            'fullPublicCanonicalBytesComparedAcrossThreePlatforms': True},
        'unresolved': UNRESOLVED, 'firmwareReady': False}


def validate_contract(contract=None, source_bindings=None):
    actual = strict_json(PATH.read_bytes()) if contract is None else deepcopy(contract)
    oracle._equal(actual, facts(), 'contract/independent_closed_facts')
    supplied = {row['path']: row for row in source_bindings} if source_bindings is not None else None
    for p, n, h in SOURCES:
        raw = (ROOT / p).read_bytes()
        if len(raw) != n or sha256(raw).hexdigest() != h:
            raise ValueError('ReviewedHistoricalSourceIdentityChanged:' + p)
        if supplied is not None and (p not in supplied or supplied[p]['bytes'] != n or supplied[p]['sha256'] != h):
            raise ValueError('CurrentSourceJoinMissingReviewedBinding:' + p)
    cases = list(corpus.iter_cases())
    expected = [oracle.expected_case(case) for case in cases]
    oracle._equal(corpus.coverage()['retirements'], 680, 'contract/independent_retirements')
    oracle._equal(sum(row['control_instruction_retirements'] for row in expected), 56, 'contract/control_count')
    oracle._equal(sum(row['peripheral_control_journal'][-1]['same_value'] for row in expected), 16, 'contract/same_value_controls')
    public = oracle.public_program_identity()
    oracle._equal(len(public['selected_extent_sha256']), 31, 'contract/closed31_public_forms')
    return {'schemaVersion': 1, 'milestone': 'M2bw', 'passed': True,
        'classification': 'IndependentStaticPostP2ControlContractValidated_NotExecutionEvidence',
        'casesPerMode': 32, 'retirementsPerMode': 680, 'publicProgramSha256': public['program_sha256'],
        'initialNativeControlOwnerEstablished': False, 'actualCpuExecutions': 0, 'firmwareReady': False}
