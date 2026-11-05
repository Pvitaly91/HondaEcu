"""Hypothetical four-word frame requirements, without reading or popping a frame."""
from .state import COMMON, inherited, need, number

ROLES = ('psw', 'lrb', 'a', 'pc')
PREMISES = ('mappingQualified', 'readable', 'entryWritable', 'frameOwnerEstablished',
            'integrity', 'noControlAlias', 'nestingExcluded', 'nmiExcluded')
SPECIFIC = ('ActualFrameAndSspOwnershipNotEstablished', 'PhysicalStackSafetyNotEstablished',
            'NmiNotExcludedByMieClear', 'RtiDoesNotRestoreIeOrPrRam', 'NoIndependentSfAssignmentSpecified')


def unknown_query(input_class, ssp):
    return {'inputClass': input_class, 'ssp': ssp, 'frameWords': dict.fromkeys(ROLES),
            'frameGenerations': dict.fromkeys(ROLES),
            'premises': dict.fromkeys((*PREMISES, 'matchingEntrySsp')), 'executionClaim': False}


def rti_obligations(query):
    need(type(query) is dict and set(query) == {
        'inputClass', 'ssp', 'frameWords', 'frameGenerations', 'premises', 'executionClaim'},
        'ClosedRtiObligationQueryRequired')
    need(type(query['inputClass']) is str and query['inputClass'] in inherited.INPUT_CLASSES,
         'ActualHardwareInputNotAdmitted')
    need(number(query['ssp'], 65535) and type(query['executionClaim']) is bool, 'TypedRtiContextRequired')
    frame, labels, premises = query['frameWords'], query['frameGenerations'], query['premises']
    need(type(frame) is dict and set(frame) == set(ROLES) and all(number(v, 65535) for v in frame.values()),
         'FourExplicitFrameWordsRequired')
    need(type(labels) is dict and set(labels) == set(ROLES)
         and all(v is None or type(v) is str and bool(v) for v in labels.values()), 'FourFrameLabelsRequired')
    need(type(premises) is dict and set(premises) == {*PREMISES, 'matchingEntrySsp'}
         and all(premises[k] is None or type(premises[k]) is bool for k in PREMISES)
         and number(premises['matchingEntrySsp'], 65535), 'TypedConditionalFramePremisesRequired')
    t, entry = query['ssp'], premises['matchingEntrySsp']
    missing, reads = [], []
    if query['executionClaim']:
        status, reason = 'OutsideVerifiedScope', 'ActualRtiExecutionNotAuthorized'
        restored = dict.fromkeys((*ROLES, 'ssp', 'scb'))
    else:
        if t is None:
            missing.append('UnknownSsp')
        if entry is None:
            missing.append('MatchingEntryFrameNotEstablished')
        if t is not None and t & 1:
            missing.append('OddSspPhysicalSafetyNotEstablished')
        for role in ROLES:
            if frame[role] is None:
                missing.append('FrameWordUnknown:' + role)
            if labels[role] is None:
                missing.append('FrameGenerationUnknown:' + role)
        for key in PREMISES:
            if premises[key] is None:
                missing.append('PremiseUnknown:' + key)
        for ordinal, role in enumerate(ROLES, 1):
            numeric = None if t is None else (t + 2 * ordinal) & 65535
            reads.append({'ordinal': ordinal, 'role': role, 'numericSspAfterIncrement': numeric,
                'effectiveWordAddress': None if numeric is None else numeric & 0xFFFE,
                'widthBits': 16, 'value': frame[role], 'generation': labels[role],
                'kind': 'Obligation_NotPerformedRead'})
        restored = {**frame, 'ssp': None if t is None else (t + 8) & 65535,
                    'scb': None if frame['psw'] is None else frame['psw'] & 7}
        if entry is not None and t is not None and t != ((entry - 8) & 65535):
            status, reason = 'OutsideVerifiedScope', 'MatchingEntryFrameMismatch'
        elif any(premises[key] is False for key in PREMISES):
            status, reason = 'OutsideVerifiedScope', 'DeclaredFramePremiseFalse'
        elif missing:
            status, reason = 'IndeterminateObligation', 'FrameObligationsNotEstablished'
        else:
            status, reason = 'CompleteConditional', 'HypotheticalFrameObligationsSpecified'
    constraints = [*COMMON, *SPECIFIC]
    if status != 'CompleteConditional' and reason not in constraints:
        constraints.append(reason)
    return {'procedure': 'rti_obligations', 'status': status, 'reason': reason, 'boundary': 0x29C,
        'inputClass': query['inputClass'], 'sourceScope': [0x29C],
        'state': {'hypotheticalRestores': restored, 'numericSspUnrounded': True,
            'byteBusOrder': 'NotEstablished', 'sfAssignment': 'NotEstablished',
            'ieRestoredByRti': False, 'pointingRegisterRamRestored': False, 'parserRamRestored': False,
            'premisesAreConditionalNotObserved': True, 'actualReturnObservation': None},
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [], 'obligationReads': reads,
        'missingPremises': missing, 'unresolvedConstraints': constraints,
        'effectClass': 'ArchitecturalObligationsOnly_NotRtiExecution', 'actualHardwareObservation': None,
        'cpuInstructionRetirements': 0, 'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
