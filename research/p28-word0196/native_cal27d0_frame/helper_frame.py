"""Reviewed helper write footprints and conditional frame relationships.

The immutable M2cc graph is reused. These are architectural footprint records,
not native journal events, retirement observations or a second CPU emulator.
Private source verification separately binds the metadata to the original ROM.
"""
from copy import deepcopy

from native_data0217_011f_bridge.helper_cfg import NODE_ROWS
from native_data011f_011b_ownership.caller_reachability import shortest_path

CLASSIFICATION = 'StaticCalRtFrameProvenance_NotCpuExecution'
ENTRY, NORMAL_RT, RETURN_PC = 0x5F45, 0x60E4, 0x27D3
EDGES = {pc: list(edges) for pc, _form, _length, edges in NODE_ROWS}
FORMS = {pc: form for pc, form, _length, _edges in NODE_ROWS}

# Exact reviewed effective destinations under producer page0200/local0208.
# Neither the encoded OEM bytes nor their private source bindings are included.
OFF_WRITES = {
    0x5F4B: (0x0216, 4), 0x5F53: (0x0227, 6),
    0x5F63: (0x0219, 3), 0x5F6B: (0x0217, 3),
    0x5F73: (0x0227, 7), 0x5F7B: (0x0216, 1),
    0x5F83: (0x0216, 7), 0x5F90: (0x0227, 1),
    0x5FAC: (0x0227, 5), 0x5FE7: (0x0216, 2),
    0x6034: (0x0227, 4), 0x6039: (0x0217, 6),
    0x6051: (0x0216, 5), 0x607B: (0x0227, 3),
    0x60BA: (0x0219, 4), 0x7B45: (0x0216, 3),
    0x7B4F: (0x0227, 0), 0x7B80: (0x0216, 0),
    0x7B94: (0x0216, 6), 0x7B9E: (0x0227, 2),
}
DP_ASSIGNMENTS = {
    0x5F86: 0x0356, 0x5F93: 0x03C7, 0x5FAF: 0x03CF,
    0x60B4: 0x03CE, 0x60C9: 0x03CB, 0x60D2: 0x0356,
    0x60E0: 0x0382,
}
LOCAL_WRITES = {
    0x5F97: 1, 0x5FA9: 1, 0x5FB3: 2, 0x5FBA: 2,
    0x5FBC: 2, 0x5FBE: 2, 0x7DF4: 0,
}

# Branch instruction -> immediately relevant ZF-producing instruction. CMP r0
# zero tests share the value loaded at5F99 then stored at7DF4; they are not
# independent arbitrary Boolean choices.
CODE_BRANCH_SOURCES = (
    (0x5FA4, 0x5FA0, 0x60EA), (0x5FB8, 0x5FB4, 0x60EA),
    (0x5FC4, 0x5FC1, 0x60FB), (0x5FD1, 0x5FCE, 0x60FB),
    (0x5FED, 0x5FEA, 0x60FB), (0x6002, 0x5FFF, 0x60FB),
    (0x6012, 0x600E, 0x60F2), (0x601E, 0x601B, 0x60FB),
    (0x6024, 0x6020, 0x60EA), (0x603F, 0x603C, 0x60FB),
    (0x604D, 0x6049, 0x60F2), (0x6057, 0x6054, 0x60FB),
    (0x6068, 0x6065, 0x60FB), (0x6076, 0x6072, 0x60F3),
    (0x6081, 0x607E, 0x60FB), (0x6092, 0x608F, 0x60FB),
    (0x60A3, 0x609F, 0x6104), (0x60C0, 0x60BD, 0x60FB),
    (0x7B5A, 0x7B56, 0x7BA4), (0x7B61, 0x7B5D, 0x60F2),
    (0x7B68, 0x7B64, 0x7BA5), (0x7B75, 0x7B71, 0x7BA5),
    (0x7B8C, 0x7B88, 0x60F3), (0x7DF5, 0x5F99, 0x60FB),
)


def _dominates_normal_return(pc):
    return shortest_path(EDGES, ENTRY, NORMAL_RT, (pc,)) is None


def reviewed_write_inventory():
    """Raw source-bound footprints for independent overlap implementations.

    addressesByScb is indexed by all eight architectural SCB values. Register
    and flag alias effects are separate from explicit functional DATA stores.
    One footprint row is not asserted to be one actual all-write journal event.
    No actual native instruction index or ordinal is synthesized here.
    """
    result = []

    def add(pc, addresses, width, effect, source, role, known=None):
        result.append({'pc': pc, 'form': FORMS[pc], 'widthBytes': width,
            'mustBeforeNormalRt': _dominates_normal_return(pc),
            'addressesByScb': list(addresses), 'effect': effect,
            'valueSource': source, 'role': role, 'knownValue': known,
            'pathPredicate': None if _dominates_normal_return(pc)
                else 'RequiresReviewedPathThrough_' + format(pc, '04X')})

    for pc, form, _length, _successors in NODE_ROWS:
        if pc == NORMAL_RT:
            continue  # RT's own SSP effect is part of the separate RT contract.
        if pc in OFF_WRITES:
            address, bit = OFF_WRITES[pc]
            add(pc, [address] * 8, 1, 'BitRmw_' + str(bit),
                'CFAtReviewedInstruction_OtherBitsRetainedPerOwner', 'ExplicitDataStore')
        elif pc in (0x5F89, 0x60D5):
            add(pc, [0x0356] * 8, 1, 'BitRmw_' + str(int(pc == 0x60D5)),
                'CFAtReviewedInstruction_AfterExplicitDP0356', 'ExplicitDataStore')
        elif pc == 0x60E3:
            add(pc, [0x0382] * 8, 2, 'WordStore',
                '0700If0216Bit3Else0500_After60D7_60DA_60DD', 'ExplicitDataStore')
        if pc in DP_ASSIGNMENTS:
            add(pc, [0x0084 + 8 * scb for scb in range(8)], 2,
                'PointingRegisterDPAssignment', 'CodeOwnedDestinationAddress',
                'ArchitecturalRegisterWrite', DP_ASSIGNMENTS[pc])
        if pc in LOCAL_WRITES:
            add(pc, [0x0208 + LOCAL_WRITES[pc]] * 8, 1,
                'LocalByteRegisterWrite', 'ReviewedLocalInstructionSource',
                'ArchitecturalRegisterWrite')
        writes_al = (form == 'CLRB A' or form.startswith(('LCB A,', 'LB A,'))
                     or form == 'SLLB A')
        if writes_al:
            add(pc, [0x0006] * 8, 1, 'ALWrite_AHRetained',
                'Zero' if form == 'CLRB A' else 'ReviewedInstructionOperandOrOldAL',
                'ArchitecturalRegisterWrite', 0 if form == 'CLRB A' else None)
        if form.startswith('L A,'):
            add(pc, [0x0006] * 8, 2, 'FullAccumulatorWrite',
                'CodeOwnedImmediateWord', 'ArchitecturalRegisterWrite',
                0x0700 if pc == 0x60D7 else 0x0500)
        if form.startswith(('MB PSWL.', 'RB PSWL.')):
            add(pc, [0x0004] * 8, 1, 'PSWLBit4Rmw',
                'CFOrExplicitClear', 'ArchitecturalRegisterWrite')
        if form.startswith('XORB PSWH,'):
            add(pc, [0x0005] * 8, 1, 'PSWHCarryToggle',
                'OldCFComplement_LogicalPswFlagCaveatRetained', 'ArchitecturalRegisterWrite')
        changes_flags = (writes_al or form.startswith(('L A,', 'CMPB '))
                         or form in ('RC', 'SC', 'SLLB r2', 'RORB r2')
                         or form.startswith(('ANDB r1,', 'MB C,')))
        if changes_flags:
            add(pc, [0x0005] * 8, 1, 'ArchitecturalFlagStorageEffect',
                'DocumentedCF_ZF_DDSubset_NoNativeDataStoreCountClaim',
                'ArchitecturalFlagAliasEffect')
    return result


def branch_dependencies():
    rows = [{'pc': pc, 'form': FORMS[pc], 'flagSourcePC': source,
        'sourcePC': program, 'sourceSpace': 'PROGRAM',
        'sourceClassification': 'PrivatelyVerifiedCodeSource_ZeroTestOutcomeNotPublished',
        'predicate': 'ZFEqualsProgramByteZero', 'nativeSourceOwnerObserved': False,
        'actualNativeInstructionIndex': None, 'actualNativeWriteOrdinal': None}
        for pc, source, program in CODE_BRANCH_SOURCES]
    rows.extend([
        {'pc': 0x7B48, 'form': FORMS[0x7B48], 'flagSourcePC': 0x5FCA,
         'sourcePC': 0x5FB2, 'sourceSpace': 'DATA', 'sourceAddress': 0x03CF,
         'sourceClassification': 'UnownedLiveDataUnderPrivateCodePredicateProjection',
         'predicate': 'CF5FCA_DATA03CF_bit7_Equals0',
         'nativeSourceOwnerObserved': False},
        {'pc': 0x60DA, 'form': FORMS[0x60DA], 'flagSourcePC': None,
         'sourcePC': 0x7B45, 'sourceSpace': 'DATA', 'sourceAddress': 0x0216,
         'sourceClassification': 'ConditionalRetainedBitFromCF5FCA',
         'predicate': 'DATA0216_bit3_Equals1_CorrelatedWith7B48',
         'nativeSourceOwnerObserved': False},
        {'pc': 0x7B9A, 'form': FORMS[0x7B9A], 'flagSourcePC': None,
         'sourcePC': 0x7B4F, 'sourceSpace': 'DATA', 'sourceAddress': 0x0227,
         'sourceClassification': 'ConditionalRetainedBitAndPrivateProgramSource7BA6',
         'predicate': 'DATA0227_bit0_Clear_After7B48Alternative',
         'nativeSourceOwnerObserved': False},
        {'pc': 0x609C, 'form': FORMS[0x609C], 'flagSourcePC': None,
         'sourcePC': 0x6039, 'sourceSpace': 'DATA', 'sourceAddress': 0x0217,
         'sourceClassification': 'UnknownPostPSWHLogicalCF6016',
         'predicate': 'DATA0217_bit6_FromUnknownCF6016_Through6019F0_6037_6039',
         'possibleEarlierDataInput': {'readPC': 0x5F96, 'address': 0x03C7,
             'bit': 7, 'determinesPostLogicalCf': False},
         'nativeSourceOwnerObserved': False},
    ])
    for row in rows:
        row.setdefault('actualNativeInstructionIndex', None)
        row.setdefault('actualNativeWriteOrdinal', None)
    return sorted(rows, key=lambda row: row['pc'])


def frame_assessment(frame_address, scb=None):
    """Assess an aligned candidate, never select an actual incoming SSP."""
    if (type(frame_address) is not int or not 0 <= frame_address <= 0xFFFE
            or frame_address & 1 or scb is not None
            and (type(scb) is not int or not 0 <= scb < 8)):
        raise ValueError('AlignedFrameAndOptionalScbRequired_NotOddSspHardwareBan')
    frame = {frame_address, frame_address + 1}
    selected_scbs = range(8) if scb is None else (scb,)
    must, may = [], []
    for row in reviewed_write_inventory():
        hits = [index for index in selected_scbs
                if frame & set(range(row['addressesByScb'][index],
                                     row['addressesByScb'][index] + row['widthBytes']))]
        if not hits:
            continue
        overlap = {'pc': row['pc'], 'role': row['role'], 'effect': row['effect'],
            'writeWidth': row['widthBytes'], 'scbValuesWithOverlap': hits,
            'valueSource': row['valueSource'], 'pathPredicate': row['pathPredicate']}
        (must if row['mustBeforeNormalRt'] and len(hits) == len(selected_scbs) else may).append(overlap)
    controls = {0x0000: 'SSP', 0x0002: 'LRB', 0x0004: 'PSW', 0x0006: 'A'}
    control = controls.get(frame_address)
    pointing = None
    if 0x0080 <= frame_address <= 0x00BE:
        bank, offset = divmod(frame_address - 0x0080, 8)
        pointing = {'scbBank': bank, 'register': ('X1', 'X2', 'DP', 'USP')[offset // 2],
            'selectedBankOwned': scb == bank if scb is not None else None}
    buffer_role = {0x0216: 'ProducerSource0216_0217', 0x0212: 'OtherCopySource0212_0213',
                   0x011E: 'CopyTarget011E_011F', 0x011A: 'OtherCopyTarget011A_011B'}.get(frame_address)
    incompatible = frame_address in (0x0382, 0x0006)
    if control in ('SSP', 'LRB', 'PSW'):
        preservation, feasibility = 'CALStoreChangesArchitecturalContext', 'ControlAliasBlocked'
    elif incompatible:
        preservation, feasibility = 'MustOverwriteFrame', 'CannotReturn27D3InExactOwnedContext'
    elif must:
        preservation, feasibility = 'MustOverwriteFrameGeneration', 'NumericReturnNotSufficient_FrameOwnerLost'
    elif may:
        preservation, feasibility = 'MayOverwriteFrame', 'FrameIntegrityConditionalOnUnknownAliases'
    else:
        preservation, feasibility = 'ProvedDisjointWithinReviewedContext', 'MatchingRTConditional'
    requirements = ['OwnedProducerPage0200_Local0208_AndRetainedScb',
        'NoUnmodeledAccumulatorSTACKRedirection', 'DefinedRetainedDataMemoryAndProgramReads',
        'NoAsynchronousOrUnlistedWriter', 'MatchingCAL27D0FrameAndRT60E4']
    if frame_address == 0x047E:
        requirements += ['Prove24F8To27D0SspContinuity_NotAssumedBalancedCalls',
            'IdentifyApplicableAsicMapping_047EExternalOn66201_InternalOn66207',
            'ProveFrameMemoryWritableAndRetained']
    if control or pointing:
        requirements.append('ArchitecturalRegisterStoreOrderAndContextEffects_NotOrdinaryRam')
    if buffer_role:
        requirements.append('CALFrameReplacesPriorBufferOwnership_FutureCopyRequiresOwnGeneration')
    return {'classification': CLASSIFICATION, 'frameAddress': frame_address,
        'frameWidth': 16, 'frameBytes': sorted(frame),
        'reachedSource': 'Conditional24F8Candidate' if frame_address == 0x047E
            else 'HazardClassOnly_NoReachingSspSource',
        'mustOverlap': must, 'mayOverlap': may, 'effect': control or pointing or buffer_role or 'DataFrame',
        'calStoreEffects': {'returnWord': RETURN_PC, 'littleEndianBytes': [0xD3, 0x27],
            'architecturalAlias': control, 'pointingAlias': pointing, 'bufferRole': buffer_role,
            'wordGeometryDoesNotGrantMemoryPermission': True,
            'arithmeticFromSavedIncomingMayNotApplyAfterSspSelfAlias': control == 'SSP'},
        'framePreservation': preservation, 'returnFeasibility': feasibility,
        'knownFinalFrameWords': [0x0500, 0x0700] if incompatible else None,
        'asynchronousClassification': 'AsynchronousOverwriteUnknown',
        'physicalMemorySafetyEstablished': False, 'unresolvedObligations': requirements,
        'actualFrameCreated': False, 'actualRtRead': False,
        'actualNativeInstructionIndex': None, 'actualNativeWriteOrdinal': None,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}


def analyze_helper_frames():
    """Public semantic projection; private constant outcomes stay private."""
    return deepcopy({
        'classification': CLASSIFICATION, 'inheritedNodeCount': 226,
        'inheritedEdgeCount': 253, 'coreNodes': 182, 'outOfLineNodes': 44,
        'graphReusedWithoutNewDisassembly': True, 'helperEntryPC': ENTRY,
        'normalRtPC': NORMAL_RT, 'writeInventory': reviewed_write_inventory(),
        'inventoryRowsAreNativeJournalEvents': False,
        'addressContext': {'producerPage': 0x0200, 'producerLocalBank': 0x0208,
            'requiredRelevantLrbBits': 0x0041, 'scb': 'RetainedOwnedValue_NotReceiverScb2',
            'pointingBanksEnumerated': list(range(8)), 'nativeContextObserved': False},
        'branchDependencies': branch_dependencies(),
        'termination': {'acyclicReviewedGraph': True, 'onlyClosedGraphExit': NORMAL_RT,
            'everyCompleteDefinedSynchronousGraphPathReachesNormalRt': True,
            'unexpectedListedExit': [], 'nestedCallSites': [],
            'explicitSspOrLrbWritesBeforeRt': [], 'pushPopOrRtiSites': [],
            'x1X2IndexedOrUspRelativeOperands': [],
            'allIndirectWritesAfterExplicitDpAssignments': True,
            'unfilteredSyntacticInstructionEnvelope': [129, 193],
            'privateCodeSourcePredicateCount': 24, 'totalBinaryBranches': 28,
            'privateSourceBoundConservativePathCount': 4,
            'privateSourceBoundConservativeInstructionEnvelope': [146, 149],
            'refinedCountsRequireSeparatePrivateReceipt': True,
            'refinedPathsAreActualExecutionOrFullyProvedFeasible': False,
            'remainingLiveBranchSources': [
                {'readPC': 0x5F96, 'address': None, 'selectedBit': None,
                 'possibleInputAddress': 0x03C7, 'possibleInputBit': 7,
                 'sourceClassification': 'UnknownPostPSWHLogicalCF6016',
                 'logicalPSWHWritePC': 0x6016,
                 'primaryWarning': 'CF_ZF_HC_UndefinedAfterLogicalPSWHOperation',
                 'via': [0x6014, 0x6015, 0x6016, 0x6019, 0x6037, 0x6039, 0x609C]},
                {'readPC': 0x5FB2, 'address': 0x03CF, 'selectedBit': 7,
                 'via': [0x5FCA, 0x7B45, 0x7B48, 0x7B4F, 0x7B9A, 0x60DA]}],
            'otherUnownedReadsAffectDataButNotBranchExit': [0x03CE, 0x03CB],
            'actualTerminationObserved': False,
            'conditions': ['ReviewedEntryAndUnmodifiedCode', 'OwnedProducerAddressContext',
                'DefinedMemoryReads', 'NoUnlistedOrAsynchronousDiversion',
                'NoFrameArchitecturalAliasChangingContext']},
        'frameMatrix': [frame_assessment(address) for address in (
            0x0000, 0x0002, 0x0004, 0x0006, 0x0080, 0x0084, 0x0086,
            0x0094, 0x011A, 0x011E, 0x0212, 0x0216, 0x0356, 0x0382, 0x047E)],
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'actualRetiredInstructions': 0, 'firmwareReady': False,
    })
