"""Independent closed Below requirements; JSON grants no execution authority."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from original_rom_execution.verify import strict_json
from . import corpus, oracle
from .resume import UNRESOLVED
ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name('contract.json')
BASE = '4d99ebcf02016df3dfa0a6d035bb01def4b170cd'
SOURCES = (('research/p28-word0196/native_post_p2_control/__init__.py', 70, '1108e1298db7c62361b62dcefb751e9886c85833933d5713a724df7d5ddbcf71'), ('research/p28-word0196/native_post_p2_control/admission.py', 2537, '9ad7987efc3bc1ed9cac761313adf24b923f8acb75b340b6391f0894900aed25'), ('research/p28-word0196/native_post_p2_control/admission_tests.py', 4396, '0eb144e55f72101c324c8eeab41dd86c5bfb0695840082cc9f560250b3fd90b3'), ('research/p28-word0196/native_post_p2_control/build_guard.py', 12530, '3516d7cbb00792b5d1d2c8fd54e9cf197e6a5f2d52eb1a88bfedd68a2ccf6709'), ('research/p28-word0196/native_post_p2_control/build_guard_tests.py', 8627, 'cf1fd63bf5e94f8535815b97b199d272aff400382d236cc4ce56b288b056e18d'), ('research/p28-word0196/native_post_p2_control/checkpoint.py', 2433, '6d8304fe6f13cc9547bf211b386e7210fdd108298902382b3110d33188dacf01'), ('research/p28-word0196/native_post_p2_control/checkpoint_tests.py', 3226, 'e79487f05999216c34595e9e74b26f2956e0706bac9b69d52f79e78d3ad5c0b1'), ('research/p28-word0196/native_post_p2_control/ci_contract.py', 6551, '316fc2991882cc11c1b8ceb2b7431f4f4319d558bd48c9a933afecc9e29ab341'), ('research/p28-word0196/native_post_p2_control/ci_contract_tests.py', 2048, '3c1e37bdc573063ac7db37613e67d22301c8a88bab5f8240bc0f2df78debceec'), ('research/p28-word0196/native_post_p2_control/contract.json', 8038, '5d71edd042075dd0e88df3dcbf40b691cbda887af1b58ce57458a93b3bc20d9b'), ('research/p28-word0196/native_post_p2_control/contract_validation.py', 7949, 'f674c82df24101bdef277d50ee33de15a37071f811bfaf7142a643a7ec355c90'), ('research/p28-word0196/native_post_p2_control/contract_validation_tests.py', 2315, 'e5a0416e6aad4072e525b8eb0276fa6a9ccb5289ea60cd14bcf42828ec896889'), ('research/p28-word0196/native_post_p2_control/corpus.py', 4247, 'ffcbdbb8020e6cca770335aceceee04b155f9550f3dfdd5dc96a2d5b79ffb4cd'), ('research/p28-word0196/native_post_p2_control/corpus_tests.py', 3123, '7f76ad0f7aa87d8438c98e6f51bf9e5ace6e2ff32891e347f5d53f928b322880'), ('research/p28-word0196/native_post_p2_control/oracle.py', 20596, '33adc4957d93e588b7b2cf152e11bb498730494cd51f5d8a57f69b704a182fdb'), ('research/p28-word0196/native_post_p2_control/oracle_tests.py', 14122, '4c8c29442e744407e694dc83d10a5b400aff72821dd1c8a233ca9635fc22b594'), ('research/p28-word0196/native_post_p2_control/resume.py', 38376, '3e55e7b8e19bac4836b46939a19929a9063f8fc6417fc13c158268ffb902e546'), ('research/p28-word0196/native_post_p2_control/resume_tests.py', 22234, '4039c62a40d92e6c01ef16e28d93127d7ef6d7888c21e31db0ec651b03280cc4'), ('research/p28-word0196/native_post_p2_control/source_guard.py', 9156, 'e0fd416f07f96863939fff6c5eccdfccec954c7a28be80b7c776cd42ee598a7a'), ('research/p28-word0196/native_post_p2_control/source_guard_tests.py', 2911, '4d117f8dd02d32edf123172e7592d07c9c48f214c5e3c839eead3b41435ac5d4'), ('research/p28-word0196/native_post_p2_control/verify.py', 4895, 'da360bea89533188eee5d71849f05c21176c3c6d2a0fbe6ef8a6c900c42849f4'), ('research/p28-word0196/native_post_p2_control/verify_tests.py', 2003, 'd99eb9e73d4fc6b1c0461ea6b928c6bc6a86cccfc7bb3820d3fb603f1c83f22b'), ('docs/M2BW_NATIVE_POST_P2_CONTROL_CONTINUITY.md', 12594, '429bc4e1a619cbdd165bbe30478892933d83d129012bb5850cfc1737e46f1fe1'), ('docs/M2BX_NATIVE_BELOW_SECOND_P2_CONTINUITY.md', 15114, '1c2d6c2248464210da76a1fa68ea126256512490379741f0d5b96058a36e0416'), ('docs/M2AB_POST_P2_CONTROL_HANDOFF.md', 8471, '53d0ab78eebb0650ff29feef648d7970ba6f6b4c640494c5641dc71bc4093e7f'), ('research/p28-word0196/original_rom_boundary/contract.json', 17557, 'b8a1a482dfa8f48f310db89d291014d1f4ebf83f51022cf7f70fb1dea0c1da30'), ('research/p28-word0196/word0196_ir.json', 32188, '4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4'), ('research/p28-word0196/word0196_equivalent.c', 8507, '4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3'), ('rust/p28-slice-runner/src/post_p2_control.rs', 6066, '35ac4f0e7f14884eda04a127dd5afac4fdcf9834471249ad018cd347a1191deb'), ('docs/M2AC_BELOW_SECOND_P2_HANDOFF.md', 8181, '40ca68cf13a4ecbfe030a7960e9db8b89ad49b1fa9e80fdd99209e326d029006'), ('rust/p28-slice-runner/src/below_second_p2.rs', 6099, '3942cc0954aed9d29647f12641ff7f66f519d69d943c83c633b2237a4e2166c7'), ('rust/p28-slice-runner/src/below_second_p2_tests.rs', 4324, 'f3a97d55fd1adaedd22c51eb62b260b60bd4e3cd53f912720a4bd773b3cc0dbd'), ('docs/M2BU_NATIVE_ENTRY_CONTINUITY.md', 10808, '9f41342e73aaf7170ca7d252e43b682aa12f65ae33340b5ae87829c53fceb04a'), ('docs/M2BV_NATIVE_P2_OWNERSHIP_HANDOFF.md', 11340, '060dff8fa228750149d29e62b43dcbdda20afb4d0a4ecb24a8889a3103c5d3ca'), ('docs/M2AW_NX8_200_TARGET_ABI_CONTRACT.md', 18935, '122bbb14adcd5718dc3fbb3fefb19dee74a9228099278802254ef6c7d59f8174'), ('docs/M2BS_ORIGINAL_ROM_BOUNDARY_NATIVE_CONTEXT.md', 14412, 'fc507f02e225a8fa23f14f97b68672277aa60bbf2ad3a60c766434ef12a10a96'), ('docs/M2AA_P2_OUTPUT_LATCH_HANDOFF.md', 8442, '14459918ab1b863e00dcc36ff32fd6b2cf53d3cb74ae60248364700a5c85c096'))

def facts():
    return {'schemaVersion': 1, 'milestone': 'M2bx', 'baseCommit': BASE,
        'classification': 'ClosedBelowSecondP2Requirements_NotExecutionEvidence',
        'sourceBindings': [{'path': p, 'bytes': n, 'sha256': h} for p,n,h in SOURCES],
        'manufacturer': {'instructionManualSha256': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
            'peripheralPackageSha256': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf',
            'semanticsAuthority': 'PrimaryManualAndReviewedSource_NotProductionOutput',
            'tailForms': 14, 'selectedTailExtents': 18, 'selectedTailExtentBytes': 41},
        'program': {'entryPc': 0x54F5, 'privateEndExclusive': 0x5688, 'segmentBytes': 403,
            'instructionNodes': 49, 'publicBase': 0x6400, 'publicEndExclusive': 0x6593,
            'privateSource': 'VerifiedUnmodifiedOriginalImage_NoRelocationOrPadding',
            'publicSource': 'IndependentInventedCodeCells_NotOemByteCopy', 'noArbitraryStepping': True,
            'tailPcSequence': list(corpus.DOWNSTREAM), 'stopBeforeRt5688': True, 'rtExecuted': False,
            'returnFrame': 'NotEstablished'},
        'entry': {'oneCpuBusPerCase': True, 'noHostPcJump': True, 'noMidExecutionReseed': True,
            'noSnapshotImport': True, 'oneTechnicalPeripheralInitializationBeforeFirstInstruction': True,
            'dataInventory': list(corpus.INVENTORY), 'newCanaries': list(corpus.NEW_CANARIES),
            'newCanaryValue': 165, 'logicalSetupWrites': 55, 'rawSetupWrites': 87,
            'unownedRamAuthority': 'ExplicitTechnicalBusCanary_NotNativeOwner',
            'controlSnapshotProvenance': corpus.CONTROL_PROVENANCE, 'historicalGenerationIdsTransferred': False},
        'below': {'reachableRolInput': 't=NOT8(ROTL8(initialDATA018E)); incomingCF=t.bit7',
            'rolOutput': 'ROTL8(t)', 'rolOutgoingCf': 't.bit7', 'rolNonCarryPsw': 'Preserved',
            'reachableAh': 0, 'nonzeroAhSeparateInventedInstructionControlOnly': True,
            'wordStores': [{'pc': pc, 'address': address, 'width': 16, 'value': 1}
                for pc,address in ((0x562C,0x0110),(0x5631,0x0112),(0x565D,0x0114))],
            'jnePc': 0x5661, 'jneTaken': True, 'jneOwner': 'NativeL0110AfterNativeStoreOne',
            'secondP2Pc': 0x5682, 'secondP2Al': 15, 'secondP2SameValue': True,
            'finalRbPc': 0x5685, 'finalRbAddress': 0x012A, 'finalRbZf': 'NotOldBit7'},
        'control': {'tcon0Address': 64, 'tcon0AllowedInitial': [0x83,0x87,0x8B,0x8F],
            'generationValues': ['initial OR 04','initial AND FB'], 'nativeReadsPerCase': 4,
            'nativeWritesPerCase': 2, 'journalOperations': ['Read','Read','Write']*2,
            'sameValueWritesCreateGeneration': True, 'alias006': 'CpuAL_LogicalRead_NoRawRamAccess',
            'trnsitAccessedOnBelow': False, 'functionalP2IoSfAccesses': 0,
            'timerEvolutionModeled': False, 'irqDeliveryInjected': False, 'electricalEffectClaimed': False},
        'p2': {'address': 36, 'nativeReadsPerCase': 2, 'nativeWritesPerCase': 2,
            'journalOperations': ['Read','Write']*2, 'generations': 2, 'secondGenerationFreshEvenSameValue': True,
            'nativeWriteOrdinals': [5,12], 'logicalWriteOrdinals': [60,67], 'rawWriteOrdinals': [93,103]},
        'path': {'identity': 'A', 'budget': 39, 'predecessor': 6, 'algorithm': 10,
            'firstP2': 1, 'prefixControl': 4, 'below': 18, 'aggregateP2OverlapsBelow': 2,
            'stopBeforePc': 0x5688, 'selectedInstructionsAtStop': 0},
        'corpus': {'privateCases': 16, 'publicCases': 16, 'retirementsPerMode': 624,
            'totalLocalPositiveRetirements': 1248, 'belowRetirementsPerMode': 288,
            'controlRetirementsPerMode': 64, 'functionalP2ReadsPerMode': 32,
            'functionalP2WritesPerMode': 32, 'sameValueP2WritesPerMode': 20,
            'functionalControlReadsPerMode': 64, 'functionalControlWritesPerMode': 32,
            'sameValueControlWritesPerMode': 8, 'priorRuntimeResultsCountedAsNew': False},
        'cycleAccounting': deepcopy(oracle.CYCLE_ACCOUNTING),
        'trace': {'perInstructionFullCpuPswCompared': True, 'allProgramDataControlFieldsCompared': True,
            'fullLogicalAndRawJournalsCompared': True, 'sameValueWritesRetained': True,
            'firstSingularGenerationsRetained': True, 'twoGenerationArraysCompared': True,
            'canonicalFieldExclusions': []},
        'delivery': {'defaultOffFeature': 'p28-word0196-below-second-p2-continuity',
            'requiredBaseFeature': 'p28-word0196-post-p2-control', 'cargoTarget': '.tmp/m2bx-owned/cargo-target',
            'bothEnvironmentAndExplicitTargetDirRequired': True, 'historicalProtectedRunnerPaths': 38,
            'requiredCiJobs': 13, 'inheritedAuthorizedPreservationExceptions': 1,
            'strictHistoricalPreservationPass': False, 'newUnauthorizedProtectedDifferencesRequired': 0,
            'privateRomInCi': False, 'fullPublicCanonicalBytesComparedAcrossThreePlatforms': True},
        'unresolved': list(UNRESOLVED), 'firmwareReady': False}

def validate_contract(contract=None, source_bindings=None):
    actual = strict_json(PATH.read_bytes()) if contract is None else deepcopy(contract)
    oracle._equal(actual, facts(), 'contract/independent_closed_facts')
    supplied = {row['path']: row for row in source_bindings} if source_bindings is not None else None
    for p,n,h in SOURCES:
        raw=(ROOT/p).read_bytes()
        if len(raw)!=n or sha256(raw).hexdigest()!=h:
            raise ValueError('ReviewedHistoricalSourceIdentityChanged:'+p)
        if supplied is not None and (p not in supplied or supplied[p]['bytes']!=n or supplied[p]['sha256']!=h):
            raise ValueError('CurrentSourceJoinMissingReviewedBinding:'+p)
    cases=list(corpus.iter_cases()); expected=[oracle.expected_case(case) for case in cases]
    oracle._equal(corpus.coverage()['retirements'],624,'contract/independent_retirements')
    oracle._equal(sum(e['below_instruction_retirements'] for e in expected),288,'contract/below_count')
    oracle._equal(sum(e['control_instruction_retirements'] for e in expected),64,'contract/control_count')
    p2=[x for e in expected for x in e['peripheral_p2_journal']]
    control=[x for e in expected for x in e['peripheral_control_journal']]
    oracle._equal(sum(x['same_value'] for x in p2 if x['operation']=='Write'),20,'contract/p2_same_value')
    oracle._equal(sum(x['same_value'] for x in control if x['operation']=='Write'),8,'contract/control_same_value')
    public=oracle.public_program_identity()
    oracle._equal(len(public['selected_extent_sha256']),49,'contract/closed49_public_forms')
    return {'schemaVersion': 1, 'milestone': 'M2bx', 'passed': True,
        'classification': 'IndependentStaticBelowContractValidated_NotExecutionEvidence',
        'casesPerMode': 16, 'retirementsPerMode': 624, 'publicProgramSha256': public['program_sha256'],
        'initialNativeControlOwnerEstablished': False, 'actualCpuExecutions': 0, 'firmwareReady': False}
