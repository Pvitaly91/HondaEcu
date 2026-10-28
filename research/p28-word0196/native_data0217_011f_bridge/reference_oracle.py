"""Independent invented timeline oracle; never imports the constraint model.

The calculation uses immutable selected-bit cells, a separate write counter,
and call-frame identity. Numeric equality cannot create an owner or restore an
overwritten frame generation. Conditional bit lineage is separate from actual
whole-byte admission; no CPU, Bus, ROM reader or IRQ delivery exists here.
"""


def _cell(byte):
    bit = None if byte is None else (byte // 8) % 2
    return bit, 'OwnerUnknown', None, None, None, byte


def _export(cell):
    return dict(zip(('bitValue', 'owner', 'token', 'semanticOrdinal',
        'storageOrdinal', 'byteValue'), cell))


def _masked(byte, position, value):
    if byte is None or value is None:
        return None
    weight = 2 ** position
    return byte - ((byte // weight) % 2) * weight + value * weight


def _architecture(case):
    incoming = case['incoming']
    previous, program = case['previousProgramByte'], case['programByte']
    common = {'ah': incoming['ah'], 'hc': incoming['hc'], 'dd': 0,
        'otherPsw': incoming['otherPsw']}
    def state(al, cf, zf):
        return {**common, 'al': al, 'cf': cf, 'zf': zf}
    return {
        'entryCLRB': state(0, None, 1),
        'beforeLCB': state((previous * 2) % 256, previous // 128, int(previous == 0)),
        'afterLCB': state(program, previous // 128, int(program == 0)),
        'afterShift': state((program * 2) % 256, program // 128, int(program == 0)),
        'afterMB': state((program * 2) % 256, program // 128, int(program == 0)),
    }


def reference_case(case):
    """Evaluate a schema-admitted invented case by independent bit relations.

Schema/refusal validation belongs to the separate constraint model. This
reference accepts its closed valid inputs and computes complete expected
results independently, including contradictory conditional timelines.
"""
    source = _cell(case['incoming']['bufferByte'])
    target = _cell(case['incoming']['targetByte'])
    caller, root = case['callerPc'], case['copyRoot']
    return_pc = caller + 3
    frame_address = case['incoming']['ssp'] - case['incoming']['ssp'] % 2
    frame = {'callPc': caller, 'expectedReturnPc': return_pc,
        'address': frame_address, 'createdOrdinal': None,
        'storageOrdinal': None, 'validReturn': False, 'restoredSsp': None}
    external = {'evidence': None, 'receiver': root,
        'vector': 0x0026 if root == 0x0379 else 0x000E,
        'irqBit': 15 if root == 0x0379 else 3,
        'actualDelivery': False, 'softwareEdgeEstablished': False}
    write_count = producer_count = rmw_count = external_count = reader_count = return_count = 0
    call_seen = frame_live = frame_pristine = copied = False
    frame_word = None
    later_rmw_seen = False
    alias_seen = False
    copy_before_external = False
    violations, trace = set(), []

    def word_cell(word, generation):
        high = None if word is None else word // 256
        value = _cell(high)
        return (*value[:4], generation, high)

    def byte_overlaps_live_frame(address, byte, generation):
        nonlocal frame, frame_pristine, frame_word
        if frame_live and frame_address == address:
            frame_pristine = False
            frame = {**frame, 'storageOrdinal': generation}
            frame_word = (None if frame_word is None or byte is None
                else frame_word % 256 + byte * 256)

    def unknown_frame():
        nonlocal frame, frame_pristine, frame_word
        if frame_live:
            frame_pristine = False
            frame_word = None
            frame = {**frame, 'storageOrdinal': None}

    for event in case['events']:
        kind = event['kind']
        if kind == 'call':
            if frame['createdOrdinal'] is not None:
                violations.add('MultipleCallsInSingleInvocation')
            write_count += 1
            call_seen = frame_live = frame_pristine = True
            frame_word = event['frameWord']
            frame = {**frame, 'createdOrdinal': event['ordinal'],
                'storageOrdinal': write_count, 'validReturn': False, 'restoredSsp': None}
            # The call's own frame write creates its origin. A coinciding DATA
            # cell receives unknown semantic ownership, not a native bit token.
            if frame_address == 0x0216:
                source = word_cell(frame_word, write_count)
            if frame_address == 0x011E:
                target = word_cell(frame_word, write_count)
        elif kind == 'producer':
            if not frame_live:
                violations.add('ProducerOutsideCall')
            producer_count += 1
            later_rmw_seen = False
            if producer_count > 1:
                violations.add('ProducerRepeatedInAcyclicHelper')
            write_count += 1
            selected = case['programByte'] // 128
            token = case['sourceIdentity']
            source = (selected, 'OwnerConditional' if token is not None else 'OwnerUnknown',
                token, write_count if token is not None else None, write_count,
                _masked(source[5], 3, selected))
            byte_overlaps_live_frame(0x0216, source[5], write_count)
        elif kind == 'retainedRmw':
            if not producer_count:
                violations.add('6039BeforeProducer')
            rmw_count += 1
            if rmw_count > 1:
                violations.add('6039RepeatedInAcyclicHelper')
            write_count += 1
            source = (*source[:4], write_count, _masked(source[5], 6, event['value']))
            byte_overlaps_live_frame(0x0216, source[5], write_count)
            if producer_count:
                later_rmw_seen = True
        elif kind == 'return':
            return_count += 1
            if return_count > 1:
                violations.add('ReturnRepeatedInSingleInvocation')
            if not producer_count:
                violations.add('MandatoryProducerBypassed')
            if not later_rmw_seen:
                violations.add('Mandatory6039Bypassed')
            # The exact helper exit has a mandatory word store at60E3 to
            # DATA0382/0383. Neither reviewed value0500/0700 can retain this
            # caller's return word. This is a static contradiction, not a
            # fabricated native write event or a new logical write ordinal.
            if frame_address == 0x0382:
                violations.add('MandatoryFinalStoreOverwritesReturnFrame')
                frame_pristine = False
                frame_word = None
                frame = {**frame, 'storageOrdinal': None}
            if frame_address == 0x0006:
                violations.add('MandatoryAccumulatorWritesOverwriteReturnFrame')
                frame_pristine = False
                frame_word = None
                frame = {**frame, 'storageOrdinal': None}
            match = (frame_live and frame_pristine and frame_word == return_pc
                and event['frameCallerPc'] == caller
                and event['frameOrdinal'] == frame['createdOrdinal']
                and event['returnPc'] == return_pc)
            frame = {**frame, 'validReturn': bool(match),
                'restoredSsp': case['incoming']['ssp'] if match else None}
            frame_live = False
        elif kind == 'external':
            external_count += 1
            if not frame['validReturn']:
                violations.add('ExternalBeforeMatchingReturn')
            if copied or reader_count:
                violations.add('ExternalAfterCopyOrReader')
            if external_count > 1:
                violations.add('ExternalRepeatedInSingleReceiverInvocation')
            external = {**external, 'evidence': event['evidence'], 'receiver': event['receiver']}
            if event['evidence'] == 'ListedSoftwareEdge':
                violations.add('IrqSynthesizedFromListedEdge')
            if event['receiver'] != root:
                violations.add('CrossRootExternalSplice')
        elif kind == 'copy':
            if not external_count:
                copy_before_external = True
            if copied:
                violations.add('CopyRepeatedInSingleReceiverInvocation')
            if not producer_count:
                violations.add('CopyBeforeProducer')
            if not frame['validReturn']:
                violations.add('CopyBeforeMatchingReturn')
            if event['accumulatorMutated']:
                violations.add('CopyAccumulatorMutated')
            write_count += 1
            target = (*source[:4], write_count, source[5])
            byte_overlaps_live_frame(0x011E, target[5], write_count)
            copied = True
        elif kind == 'reader':
            reader_count += 1
            if reader_count > 1:
                violations.add('ReaderRepeatedInSingleReceiverInvocation')
            if not copied:
                violations.add('ReaderBeforeCopy')
        elif kind in ('overwriteBuffer', 'overwriteTarget'):
            write_count += 1
            unknown = (event['bitValue'], 'OwnerUnknown', None, None, write_count, None)
            if kind == 'overwriteBuffer':
                source = unknown
                byte_overlaps_live_frame(0x0216, source[5], write_count)
            else:
                target = unknown
                byte_overlaps_live_frame(0x011E, target[5], write_count)
        elif kind == 'unknownAlias':
            alias_seen = True
            if event['target'] in ('source', 'all'):
                source = _cell(None)
                if frame_address == 0x0216:
                    unknown_frame()
            if event['target'] in ('target', 'all'):
                target = _cell(None)
                if frame_address == 0x011E:
                    unknown_frame()
            if event['target'] in ('frame', 'all'):
                unknown_frame()
        elif kind == 'overlapFrame':
            write_count += 1
            if event['address'] == 0x0216:
                source = word_cell(event['value'], write_count)
            if event['address'] == 0x011E:
                target = word_cell(event['value'], write_count)
            if frame_live and event['address'] == frame_address:
                frame_pristine = False
                frame_word = event['value']
                frame = {**frame, 'storageOrdinal': write_count}
        else:
            raise ValueError('UnknownInventedReferenceEvent')
        trace.append({'ordinal': event['ordinal'], 'kind': kind,
            'sourceBit': source[0], 'sourceOwner': source[1],
            'sourceStorageOrdinal': source[4], 'targetBit': target[0],
            'targetOwner': target[1], 'targetStorageOrdinal': target[4],
            'frameLive': frame_live, 'frameStorageOrdinal': frame['storageOrdinal'],
            'frameMatch': frame['validReturn']})
    context, assumptions = case['context'], case['hypotheses']
    if external_count and copy_before_external:
        violations.add('CopyBeforeExternalBoundary')
    if not reader_count:
        violations.add('MissingReaderRelation')
    if context['sourceHistory'] != context['context012A']:
        violations.add('Incompatible012AHistory')
    if len(context['earlierCalls']) > 1:
        violations.add('MutuallyExclusiveEarlierCallsCombined')
    if context['old012ABit3'] != int(bool(context['earlierCalls'])):
        violations.add('Wrong012ABit3Context')
    if assumptions['helperPredicatesSatisfied'] is False:
        violations.add('HelperPredicatesContradicted')
    if assumptions['receiverPredicatesSatisfied'] is False:
        violations.add('ReceiverPredicatesContradicted')
    if violations:
        result = 'UnsatisfiableWithinReviewedCFG'
    elif not frame['validReturn'] or not assumptions['irqFrameAssumedSafe']:
        result = 'BlockedByMissingReturnFrame'
    elif assumptions['helperPredicatesSatisfied'] is None:
        result = 'UnknownOutsideReviewedScope'
    elif external['evidence'] != 'ExplicitAssumptionOnly':
        result = 'BlockedByExternalInterruptDelivery'
    elif (not assumptions['aliasesDisjoint'] or alias_seen
            or frame_address not in (0x0006, 0x0382)
            and (frame_address < 0x00C0 or 0x0200 <= frame_address < 0x0300
                 or frame_address == 0x0356)):
        result = 'BlockedByAliasUncertainty'
    elif target[1] == 'OwnerUnknown' or target[0] is None:
        result = 'BlockedBySourceOwner'
    else:
        result = 'SatisfiableUnderExplicitAssumptions'
    return {'caseId': case['caseId'],
        'classification': 'StaticSameMachineBridgeFeasibility_NotCpuExecution',
        'machineId': case['machineId'], 'callerPc': caller, 'copyRoot': root,
        'registerEffects': _architecture(case), 'frame': frame,
        'source': _export(source), 'target': _export(target), 'external': external,
        'trace': trace, 'violations': sorted(violations), 'solverResult': result,
        'selectedBitSemanticLineage': ('SelectedBitSemanticLineageEstablishedUnderExplicitAssumptions'
            if result == 'SatisfiableUnderExplicitAssumptions' else 'ConditionalSelectedBitLineage_NotIntegrated'),
        'wholeByteClassification': 'WholeByteValueNotFullyOwned',
        'actualByteReadAdmitted': False,
        'nextReader': 0x064F if target[0] == 0 else None,
        'conditionalStopBefore': (0x0667 if context['old012ABit3'] else 0x0664) if target[0] == 1 else None,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'actualRetiredInstructions': 0, 'nativeEventIndexes': [],
        'nativeWriteOrdinals': [], 'firmwareReady': False}
