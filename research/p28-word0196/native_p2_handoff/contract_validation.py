"""Static closed requirements validation, never CPU or current-owner evidence."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from original_rom_execution.verify import strict_json
from . import corpus, oracle

ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name('contract.json')
BASE = 'df55bc5d86f85906813a8241608dac542ab4c302'
SOURCES = (
    ('research/p28-word0196/native_entry_continuity/contract.json', 6673, '82e388caec27fb0c99cee68cb429b32eaba98ae84e6b2f213f30424d9016a1bc'),
    ('research/p28-word0196/native_entry_continuity/corpus.py', 7204, '625c15fd5f39e0416fde809a2cb31f9e38e8d4d9d2d605f0b591427791f4f075'),
    ('research/p28-word0196/native_entry_continuity/oracle.py', 22602, '71c8acc9ff15b87f0aad76435dad0a3cbcd107983c0cd94348c0d5ff4ead9940'),
    ('research/p28-word0196/native_entry_continuity/admission.py', 3698, 'd9a8e8e2eb15eb70c97b80b185c62534552942877d3c0c5f97d6fca561c655e6'),
    ('research/p28-word0196/original_rom_boundary/contract.json', 17557, 'b8a1a482dfa8f48f310db89d291014d1f4ebf83f51022cf7f70fb1dea0c1da30'),
    ('research/p28-word0196/original_rom_boundary/decode.py', 13934, 'ad7079c1894488834fa85d3f24b483e530440853eade244ff54556a3b442ad58'),
    ('docs/M2AA_P2_OUTPUT_LATCH_HANDOFF.md', 8442, '14459918ab1b863e00dcc36ff32fd6b2cf53d3cb74ae60248364700a5c85c096'),
    ('src/HondaEcu.Core/P28P2LatchModel.cs', 6883, 'ad6ae4f81f4a1659ac75361637bad7088597c4bcaa5c3d8c8911bb9adee144b5'),
    ('research/p28-word0196/native_p2_handoff/ownership_contract.json', 11908, '2c26bb412499cc7d333fb7a634c170f447e5c03642870c6dcde59ccd5bc3f380'))
UNRESOLVED = ['ActualHardwareEcuExecutionNotObserved', 'RecoveredFullEcuSchedulerNotEstablished',
    'PhysicalSFNotEstablished', 'NativeStackSafetyNotEstablished', 'CurrentNativeP2InitialOwnerNotEstablished',
    'PhysicalP2ElectricalEffectNotEstablished', 'PhysicalP2RoleAndPolarityNotEstablished',
    'DownstreamTRNSITAndTCON0NotExecutedInM2bv', 'ActualNativeDownstreamRejoinNotEstablished',
    'SafeROMPlacementNotEstablished', 'TargetProgramEquivalenceNotEstablished', 'FirmwareIntegrationNotEstablished',
    'DiagnosticCycleTimingEquivalenceNotEstablished']


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def validate_contract(contract=None, source_bindings=None):
    actual = strict_json(PATH.read_bytes()) if contract is None else deepcopy(contract)
    expected = strict_json(PATH.read_bytes())
    keys = {'schemaVersion', 'milestone', 'baseCommit', 'classification', 'sourceBindings', 'manufacturer',
            'program', 'entry', 'p2', 'paths', 'corpus', 'cycleAccounting', 'trace', 'delivery', 'unresolved', 'firmwareReady'}
    need(type(actual) is dict and set(actual) == keys, 'ClosedM2bvContractRequired')
    # Compare against explicit independent facts, not a second read of a changed
    # JSON document. The file itself is also source-fingerprinted before runtime.
    facts = {
        'schemaVersion': 1, 'milestone': 'M2bv', 'baseCommit': BASE,
        'classification': 'ClosedP2HandoffRequirements_NotExecutionEvidence', 'unresolved': UNRESOLVED, 'firmwareReady': False,
        'sourceBindings': [{'path': path, 'bytes': size, 'sha256': digest} for path, size, digest in SOURCES],
        'manufacturer': {'instructionManualSha256': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
            'peripheralPackageSha256': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf',
            'andForm': 'andb-zero-a', 'andPrintedPage': '3-25', 'orForm': 'orb-zero-a', 'orPrintedPage': '3-108',
            'ddIndependent': True, 'physicalCustomerAsicIdentityEstablished': False},
        'program': {'entryPc': 0x54F5, 'privateEndExclusive': 0x55C8, 'segmentBytes': 211,
            'selectedInstructionNodes': 26, 'selectedInstructionBytes': 65, 'publicBase': 0x6400, 'publicEndExclusive': 0x64D3,
            'privateSource': 'VerifiedUnmodifiedOriginalImage_NoRelocationOrPadding',
            'publicSource': 'IndependentInventedInstructionCellsAndOperands_NotOemByteCopy', 'stopBeforeNextInstruction': True},
        'entry': {'classification': 'TechnicalSeededEntryContext_NoRecoveredScheduler', 'oneCpuBusPerCase': True,
            'noHostPcJump': True, 'noMidExecutionReseed': True, 'noSnapshotImport': True,
            'p2SnapshotBeforeFirstFunctionalInstructionOnly': True, 'data0196Owner': 'TechnicalSeedPair_NoNativeGenerationOwner',
            'nativeProducer05ebExecuted': False, 'er1IsLiveOutNotSuffixRead': True, 'physicalSfKnown': False},
        'p2': {'address': 36, 'width': 8, 'p2io': 255, 'p2sf': 7, 'provenance': corpus.PROVENANCE,
            'initialNativeOwner': 'NotEstablished', 'initialSnapshotCreatesNativeGeneration': False,
            'permittedInitialValues': [0, 15, 165, 240, 255], 'operationReadsOldBeforeWritingNew': True,
            'flagsWritten': ['ZF'], 'preserved': ['A', 'CF', 'HC', 'DD', 'OtherPSW', 'LRB', 'SCB', 'SSP', 'PointingBanks', 'RAM'],
            'sameValueWriteCreatesFreshGeneration': True, 'p2IoSfFunctionalAccesses': 0, 'otherSfrFunctionalAccesses': 0,
            'physicalOutputEffect': 'NotObserved'},
        'paths': {path: {'budget': corpus.BUDGETS[path], 'p2Pc': corpus.P2_PCS[path],
            'stopBeforePc': corpus.TERMINALS[path], 'operation': 'OR' if path == 'A' else 'AND'} for path in 'ABCD'},
        'corpus': {'privateCases': 32, 'publicCases': 32, 'casesPerPathPerMode': 8, 'retirementsPerMode': 624,
            'p2RetirementsPerMode': 32, 'predecessorRetirementsPerMode': 192, 'algorithmRetirementsPerMode': 400,
            'orZeroResultReachable': False, 'andZeroResultRequired': True, 'initialDdHcSfScbCoverageRequired': True,
            'priorRuntimeResultsCountedAsNew': False},
        'cycleAccounting': {'softwareDiagnosticCounterDelta': 6, 'primaryManualIntCycles': 7,
            'classification': 'UserApprovedDiagnosticAccounting_NotManufacturerTimingEquivalence',
            'basis': 'RetainedHistoricalFallbackTwoPerInstructionByte_ThreeByteForm',
            'semanticOrCanonicalFieldsOmitted': [], 'timingEquivalenceEstablished': False, 'physicalTimeClaimed': False},
        'trace': {'perInstructionStateAndFullPsw': True, 'allProgramAndDataFieldsCompared': True,
            'peripheralP2JournalSeparateFromRam': True, 'functionalP2EventsPerCase': ['Read', 'Write'],
            'functionalP2WriteCountPerCase': 1, 'allRepresentationsReferToOneSemanticWrite': True,
            'nativeWriteOrdinalExcludesSetupSeeds': True, 'globalLogicalWriteOrdinalIncludes48Seeds': True,
            'globalRawWriteOrdinalIncludes80Seeds': True, 'initialLatchHasNoNativeWriterGeneration': True,
            'historicalGenerationIdsTransferred': False, 'canonicalFieldExclusions': []},
        'delivery': {'defaultOffFeature': 'p28-word0196-p2-handoff', 'requiredBaseFeature': 'p28-word0196-entry-continuity',
            'cargoTarget': '.tmp/m2bv-owned/cargo-target', 'bothEnvironmentAndExplicitTargetDirRequired': True,
            'inheritedAuthorizedPreservationExceptions': 1, 'newUnauthorizedProtectedDifferencesRequired': 0,
            'strictHistoricalPreservationPass': False, 'privateRomInCi': False, 'fullPublicCanonicalBytesComparedAcrossThreePlatforms': True}}
    oracle._equal(actual, facts, 'contract/independent_closed_facts')
    oracle._equal(expected, facts, 'contract/saved_independent_closed_facts')
    oracle._equal(oracle.CYCLE_ACCOUNTING, facts['cycleAccounting'], 'contract/explicit_diagnostic_cycle_policy')
    supplied = {row['path']: row for row in source_bindings} if source_bindings is not None else None
    for path, size, digest in SOURCES:
        raw = (ROOT / path).read_bytes()
        need(len(raw) == size and sha256(raw).hexdigest() == digest, 'ReviewedSourceIdentityChanged:' + path)
        if supplied is not None:
            need(path in supplied and supplied[path]['bytes'] == size and supplied[path]['sha256'] == digest,
                 'CurrentSourceJoinMissingReviewedBinding:' + path)
    ownership = strict_json((ROOT / SOURCES[-1][0]).read_bytes())
    need(ownership['modePrecondition']['p2ioCanonical'] == 255 and ownership['modePrecondition']['p2sfCanonical'] == 7
         and ownership['staticInventoryScope']['startupExecutionEstablished'] is False
         and ownership['actualExecutionReceipt'] is False and ownership['firmwareReady'] is False,
         'TechnicalOwnershipContractCannotPromoteCurrentNativeP2')
    cases = list(corpus.iter_cases())
    expected_cases = [oracle.expected_case(case) for case in cases]
    need(corpus.coverage(cases)['retirements'] == 624 and sum(row['final_p2_zf'] for row in expected_cases) == 6
         and sum(row['same_value_p2_write'] for row in expected_cases) >= 16,
         'IndependentP2CoverageMustIncludeZeroAndFreshSameValueWrites')
    public = oracle.public_program_identity()
    need(len(public['selected_extent_sha256']) == 26 and public['program_base'] == 0x6400,
         'IndependentPublicProgramIdentityRequired')
    return {'schemaVersion': 1, 'milestone': 'M2bv', 'passed': True,
        'classification': 'IndependentStaticP2HandoffContractValidated_NotExecutionEvidence',
        'casesPerMode': 32, 'retirementsPerMode': 624, 'publicProgramSha256': public['program_sha256'],
        'initialNativeP2OwnerEstablished': False, 'actualCpuExecutions': 0, 'firmwareReady': False}
