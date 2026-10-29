"""Finite invented source constraints and word generations; never a CPU model.

The comparison domain is the frozen curated corpus and its named mutations.
There is no external-input admission API or native execution permission here.
"""
from copy import deepcopy
import json
from pathlib import Path

STATIC = 'StaticData011B7ZeroSourceProvenance_NotCpuExecution'
RESEARCH = 'CONDITIONAL_DATA011B7_ZERO_PRODUCER_ESTABLISHED / EXECUTION_BLOCKED'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')


def empty_result(case_id, reason):
    return {'caseId': case_id, 'valid': reason is None,
        'classification': 'InventedOnly_ConditionalZeroRelations' if reason is None else 'InventedOnly_Refused',
        'firstMismatch': reason,
        'firstMissingObligation': reason or 'CurrentSourceISRAndPacketEntryStateOwners',
        'packetChecksum': None, 'flagBit0': None, 'branch2919ConditionalNext': None,
        'writerWordValue': None, 'writerAddresses': [], 'semanticZeroOwner': None,
        'latestStorageWriterPC': None, 'latestStorageGeneration': None,
        'readerBit7': None, 'conditionalReaderSuccessor': None,
        'preservation': 'NotEstablishedRefused', 'actualCpuExecutions': 0,
        'actualOriginalRomExecutions': 0, 'actualIRQDeliveries': 0,
        'actualMachineId': None, 'actualNativeInstructionIndex': None, 'actualWriterOrdinal': None,
        'actualSourceOwners': {'data03F1': None, 'data03F3': None, 'initialR7': None,
            'irqHistory': None, 'mode0356Bit1': None, 'reads0055': None},
        'actualBranch064FExecuted': False, 'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def evaluate_case(case):
    """Check a declared invented four-read witness and its retention conditions."""
    c = deepcopy(case)
    case_id = c.get('caseId') if isinstance(c, dict) else None
    required = {'source', 'handler', 'producer', 'route', 'reader', 'history', 'actual', 'preservation'}
    if (type(c) is not dict or not required <= set(c)
            or any(type(c[name]) is not dict for name in required)
            or c.get('classification') != 'InventedOnly_ConditionalPacketAndZeroSource'):
        return empty_result(case_id, 'ClosedCaseShapeRequired')
    s, h, p, r, rd, hist, actual = (c[name] for name in
        ('source', 'handler', 'producer', 'route', 'reader', 'history', 'actual'))
    nested = {
        'source': {'space', 'address', 'widthBits', 'generationKind', 'injected03F3',
            'importedHistoricalOwner', 'canary', 'reads'},
        'handler': {'scb', 'lrb', 'mode0356Bit1', 'old0356Bit6', 'initialR7', 'entry', 'vector',
            'irqWordBit', 'actualInitialR7Owner', 'actualModeOwner', 'actualReadOwners', 'actualIRQHistory'},
        'producer': {'ddAfterCLR', 'usp', 'scb', 'lrb', 'page', 'highByteOffset', 'hostBranch2919',
            'clrReached', 'accumulatorMutated', 'storeWidthBits', 'read2966Token', 'read2917Token',
            'read2966ActualValue', 'storePCs', 'ordinaryAccumulator', 'scope'},
        'route': {'kind', 'targetWord', 'sourceWord', 'copySequence', 'storeSequence',
            'bufferOverwrittenUnknown', 'deduplicateSameValue', 'sbrDirection', 'fabricatedIRQ',
            'copyFrameMatches', 'sourceMachine', 'copyMachine', 'copyRoot', 'copyLoadPC',
            'copyWriterPC', 'directBeforeReceiverCopy', 'unknownAlias', 'claimedActualOverwrite'},
        'reader': {'gate011F3', 'gateSource', 'successor', 'actuallyExecuted', 'actualGateOwner',
            'irqH1WordBit', 'oldIrqH1', 'pc'},
        'history': {'source', 'caller', 'frame', 'data012A', 'selector013C'},
        'preservation': {'historicalExpected', 'recordedExpected'},
    }
    if 'machineId' not in c or any(not fields <= set(c[name]) for name, fields in nested.items()):
        return empty_result(case_id, 'ClosedCaseShapeRequired')
    samples = s.get('reads')
    if (type(samples) is not list or len(samples) != 4
            or any(type(x) is not dict or not {'role', 'pc', 'value', 'readId', 'invocation'} <= set(x) for x in samples)
            or any(type(x['value']) is not int or not 0 <= x['value'] <= 255 for x in samples)):
        return empty_result(case_id, 'ClosedCaseShapeRequired')
    header, length, flag, checkbyte = (x['value'] for x in samples)
    copied = r['kind'] in ('B-serial', 'B-int1')
    source_pc_pairs = [('H', 0x0277), ('L', 0x027F), ('F', 0x0262), ('K', 0x0284)]
    copy_pairs = {0x03ED: (0x03FE, 0x0400), 0x0379: (0x5C2B, 0x5C2D)}
    checks = [
        (s['space'] == 'DATA' and s['address'] == 0x0055 and s['widthBits'] == 8
            and r['targetWord'] == 0x011A, 'WrongSourceAddress'),
        (p['ddAfterCLR'] == 1, 'WrongDD'),
        (p['usp'] == 0x0180, 'WrongUSP'),
        (h['scb'] == 2 and p['scb'] == 0, 'WrongSCB'),
        (h['lrb'] == 0x007E and p['lrb'] == 0x0041, 'WrongLRB'),
        (p['page'] == 0x0200, 'WrongPage'),
        (p['highByteOffset'] == 1, 'WrongHighByteMapping'),
        (s['injected03F3'] is None and s['generationKind'] == 'InventedConditionalSfrReads', 'InjectedDATA03F3'),
        (p['hostBranch2919'] is None, 'HostBranch2919Outcome'),
        (p['clrReached'] is True, 'CLR291BBypassed'),
        (p['accumulatorMutated'] is False, 'AccumulatorMutationBeforeStore'),
        (not copied or type(r['copySequence']) is int and r['copySequence'] > r['storeSequence'],
            'CopyBeforeSourceGeneration'),
        (r['bufferOverwrittenUnknown'] is False, 'UnknownBufferOverwrite'),
        (s['importedHistoricalOwner'] is None, 'ImportedM2agFixedSource'),
        (s['canary'] is None, 'ImportedM2bzCanary'),
        (r['sourceWord'] == 0x0212, 'WrongSourceWord0217'),
        (p['storeWidthBits'] == 16, 'WordWriterTreatedAsByte'),
        (r['deduplicateSameValue'] is False, 'SameValueGenerationDeduplicated'),
        (r['sbrDirection'] == 'PrimaryConflictUnresolved', 'SBRDirectionAssumed'),
        (r['fabricatedIRQ'] is False and h['actualIRQHistory'] is None, 'ArtificialIRQTransition'),
        (r['copyFrameMatches'] is True, 'WrongCallerRTFrame'),
        (r['sourceMachine'] == c['machineId'] and r['copyMachine'] == c['machineId'], 'CrossMachineGeneration'),
        (rd['gate011F3'] == 0 and rd['gateSource'] == 'InventedIndependentConditionalSource_NotNativeOwner',
            'MissingIndependent011F3Gate'),
        (rd['successor'] == 0x0652, 'WrongJBS064FSuccessor'),
        (actual == {'cpuExecutions': 0, 'romExecutions': 0, 'irqDeliveries': 0,
            'machineId': None, 'instructionIndex': None, 'writeOrdinal': None}
            and rd['actuallyExecuted'] is False and rd['actualGateOwner'] is None
            and all(h[name] is None for name in ('actualInitialR7Owner', 'actualModeOwner', 'actualReadOwners')),
            'FalseOriginalRomExecution'),
        (c['preservation']['historicalExpected'] == c['preservation']['recordedExpected'],
            'HistoricalFingerprintModified'),
        (length == 4, 'Length3CannotWriteFlagAt0269'),
        (len({x['readId'] for x in samples}) == len({x['invocation'] for x in samples}) == 4,
            'PacketReadIdentityReused'),
        (rd['irqH1WordBit'] == 9 and (r['copyRoot'] != 0x0379 or rd['oldIrqH1'] == 0),
            'SourceIrqBit1IsNotInputGateBit9'),
        (p['read2966Token'] != p['read2917Token'] and p['read2966ActualValue'] is None,
            'Later2966ReadBorrowed2917'),
        (r['claimedActualOverwrite'] is False, 'UnknownAliasIsNotActualOverwrite'),
        (r['kind'] in ('A', 'B-serial', 'B-int1') and (not copied or r['copyRoot'] in copy_pairs
            and (r['copyLoadPC'], r['copyWriterPC']) == copy_pairs[r['copyRoot']]
            and r['copyRoot'] == (0x03ED if r['kind'] == 'B-serial' else 0x0379)), 'RouteCopyContextWrong'),
        (not (r['kind'] == 'A' and r['directBeforeReceiverCopy']), 'DirectGenerationDominatedByReceiverCopy'),
        (h['mode0356Bit1'] == 1 and h['old0356Bit6'] == 0 and h['initialR7'] == 0,
            'ParserModeGateNotSatisfied'),
        ([(x['role'], x['pc']) for x in samples] == source_pc_pairs, 'PacketReadSitesWrong'),
        (h['entry'] == 0x0213 and h['vector'] == 0x000A and h['irqWordBit'] == 1
            and h['actualInitialR7Owner'] is None and h['actualModeOwner'] is None and h['actualReadOwners'] is None,
            'HandlerContextWrong'),
        (p['storePCs'] == [0x291C, 0x291E, 0x2920, 0x2922], 'WrongStoreInventory'),
        (p['ordinaryAccumulator'] == 'ExplicitConditionalHypothesis'
            and p['scope'] == 'ConditionalColdProducerContext_NotGlobalScbRule', 'ClosedCaseShapeRequired'),
        (all(hist[name] == hist['source'] for name in ('caller', 'frame', 'data012A', 'selector013C')),
            'UncorrelatedCallerHistory'),
        (rd['pc'] == 0x064F, 'WrongReaderBoundary'),
        ((header + length + flag + checkbyte) % 256 == 0, 'PacketChecksumNotAccepted'),
        (header == 0x21, 'Command21PredicateNotSatisfied'),
        (flag & 1 == 1, 'CurrentFlagBit0BypassesCLR'),
    ]
    reason = next((name for valid, name in checks if not valid), None)
    if reason is not None:
        return empty_result(case_id, reason)
    result = empty_result(case_id, None)
    words = [((p['usp'] - 0x66) & 0xFFFE), ((p['usp'] - 0x64) & 0xFFFE),
        ((p['page'] + 0x12) & 0xFFFE), ((p['page'] + 0x14) & 0xFFFE)]
    result.update(packetChecksum=(header + length + flag + checkbyte) % 256, flagBit0=flag & 1,
        branch2919ConditionalNext=0x291B, writerWordValue=0,
        writerAddresses=[byte for word in words for byte in (word, word + 1)],
        semanticZeroOwner='model:' + case_id + ':CLR291B')
    if r['unknownAlias']:
        result['preservation'] = 'UnresolvedAlias'
    else:
        result.update(preservation='ConditionalNoRelevantOverlapHypothesis', readerBit7=0,
            conditionalReaderSuccessor=0x0652,
            latestStorageWriterPC=r['copyWriterPC'] if copied else 0x291C,
            latestStorageGeneration='model:' + case_id + (':COPY:5' if copied else ':ST291C:1'))
    return result


def missing_frontier():
    return {'classification': STATIC, 'researchClassification': RESEARCH,
        'firstSourceConditions': ['ActualIRQL1Entry0213AndSafeFourWordFrame', 'ActualInitialR7ZeroOwner',
            'Current0356ModeBit1Owner', 'FourDistinct0055ReadGenerationsAndCompatibleParserStates',
            'Retained03F1Header03F3FlagAnd0290ReadyUntil28AE'],
        'zeroPrefix': {'modeReaderPC': 0x28B1, 'readyReaderPC': 0x28BB,
            'commandReaderPC': 0x28C5, 'flagReaderPC': 0x2917, 'predicateWriterPC': 0x2918,
            'predicatePC': 0x2919, 'predicate': 'Current03F3Bit0Equals1', 'zeroSourcePC': 0x291B,
            'actualSourceOwner': None, 'actualWriterExecuted': False},
        'routeA': ['OwnedSelectedUSP0180AndOrdinaryAccumulator', 'Reached291CFullWordGeneration',
            'NoUnaccountedOverlapOrDominatingReceiverCopy', 'IndependentlyOwned011F3GateZero'],
        'routeB': ['Reached2920Page0200WordGeneration', 'Preserved0212WordBeforeLoad',
            'Genuine0379Or03EDEntryAndFrame', 'MatchingCopyContextAnd038AReturnForINT1',
            'NewTargetCopyStorageGenerationPreservedUntil064F', 'IndependentlyOwned011F3GateZero'],
        'ordinaryPostZeroCall': {'pc': 0x79D5, 'target': 0x5EE3, 'requiredRt': 0x5EF0,
            'requiredReturnPC': 0x79D8, 'c8Site': 0x5EEE, 'matchingFrameObserved': False},
        'secondFlagRead': {'pc': 0x2966, 'bit': 1, 'value': None, 'mayBorrow2917Read': False},
        'reader': {'pc': 0x064F, 'requiredEarlierReader': 0x064C, 'gateAddress': 0x011F,
            'gateBit': 3, 'gateRequiredValue': 0, 'actualGateOwner': None,
            'zeroSuccessor': 0x0652, 'oneSuccessor': 0x065F, 'actuallyExecuted': False},
        'relativeRoutePreference': 'SerialAvoids038AHelperFrame_OverallNativeWinnerNotEstablished',
        'data012AAndSelector': 'OwnCorrelatedCallerHistory_NotM2bzTechnicalSnapshot',
        'inheritedHardwareConstraints': ['ApplicableResetNotObserved', 'Wdt3CUnknownAfterM2cf',
            'PhysicalStackAndSFApplicabilityUnknown', 'NoActualIRQDeliveryOrTimerEvolution'],
        'sbrDirection': 'PrimaryConflictUnresolved', 'c8Predicate': 'PrimaryConflictUnresolved',
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'actualIrqDeliveries': 0, 'actualMachineId': None, 'actualWriterOrdinal': None,
        'actualBranch064CExecuted': False, 'actualBranch064FExecuted': False,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def case_obligations(case, result):
    copied = case['route']['kind'] in ('B-serial', 'B-int1')
    return {'classification': 'StaticConditionalObligations_NativeGenerationsUnknown',
        'producerPC': 0x291B, 'predicateWriterPC': 0x2918,
        'predicateSource': 'CurrentDATA03F3Bit0_Read2917_NotRead2966',
        'predicateClassification': 'ConditionalData0055ReadAndLocal0269Writer_NotObserved',
        'zeroWriterPC': 0x2920 if copied else 0x291C, 'zeroSourcePC': 0x291B,
        'sourceAddress': 0x0212 if copied else None,
        'sourceAddressRole': 'CopyWordInput' if copied else 'CodeConstantZero_NoDataSourceOperand',
        'targetAddress': 0x011A, 'targetAddressRole': 'FinalWordContainingSelectedBit',
        'selectedTargetByteAddress': 0x011B, 'selectedTargetBit': 7,
        'zeroWriterTargetAddress': 0x0212 if copied else 0x011A,
        'widthBits': 16, 'requiredDD': 1,
        'requiredLRB': 0x0041, 'requiredSCB': 0, 'requiredUSP': 0x0180,
        'contextScope': 'ConditionalColdProducerRoute_AlternativeBanksNeedSeparateProof',
        'sourceOwner': None, 'storageGeneration': None, 'semanticBitOwner': None,
        'modeledAtWriteSemanticZero': result['semanticZeroOwner'],
        'modeledCurrentStorageGeneration': result['latestStorageGeneration'],
        'copyWriterPC': case['route']['copyWriterPC'], 'copyRoot': case['route']['copyRoot'],
        'copyContextRequired': {'lrb': 0x0021, 'scb': 2, 'usp': 0x0280, 'page': 0x0100} if copied else None,
        'latestOverlappingWriter': None, 'modeledLatestReviewedWriterPC': result['latestStorageWriterPC'],
        'aliasHazards': ['UnknownIndirectOrAlternateBank', 'SystemAndIRQFrames',
            'StartupRamTestNmiAndBitmapWriters', 'AccumulatorStackApplicability'],
        'interruptDependency': 'FourSourceTXEntriesAndFrames_AdditionalChosenReceiverIfCopied',
        'readerPC': 0x064F, 'readerReachability': 'ConditionalOnly_Separate011F3GateRequired',
        'preservationClassification': result['preservation'],
        'firstMissingObligation': result['firstMissingObligation'],
        'actualCpuExecution': False, 'actualRomExecution': False}


def canonical_records():
    from .producer_prefix import producer_analysis
    from .route_lineage import route_analysis
    from .reference_oracle import curated_controls, independent_check, reference_case
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    expected_contract = {'schemaVersion': 1, 'milestone': 'M2cg', 'classification': STATIC,
        'baseSha': 'bb781647d553ee321ae9ac75732e06736fb01fbb', 'researchClassification': RESEARCH,
        'analysisRecords': 4, 'inventedConstraintCases': 37, 'negativeRequirementCategories': 31,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False}
    if canonical(contract) != canonical(expected_contract):
        raise ValueError('ExactM2cgStaticContractRequired')
    producer, route = producer_analysis(), route_analysis()
    comparison = independent_check(producer, route)
    if comparison.get('valid') is not True:
        raise ValueError('IndependentStaticSourceProjectionMismatch')
    records = [{'caseId': name, 'classification': STATIC, 'data': data,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}
        for name, data in (('new-command-flag-and-four-read-source', producer),
            ('zero-copy-reader-and-retention-cuts', route), ('minimal-missing-evidence-frontier', missing_frontier()),
            ('independent-static-source-comparison', comparison))]
    for control in curated_controls():
        case = control['input']
        actual, expected = evaluate_case(case), reference_case(case)
        if canonical(actual) != canonical(expected):
            raise ValueError('IndependentSourceConstraintMismatch:' + control['caseId'])
        records.append({'caseId': control['caseId'], 'classification': STATIC,
            'data': {'input': case, 'result': actual, 'sourceObligations': case_obligations(case, actual),
                'independentComparison': 'PASS'},
            'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0})
    # Keep every field while making any integer-keyed inherited metadata JSON-stable.
    return json.loads(json.dumps(records, ensure_ascii=True, allow_nan=False))
