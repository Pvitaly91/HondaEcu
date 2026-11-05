"""Independent source equations and effects, without new model imports."""
from copy import deepcopy

from payload_consumer_tail.reference_oracle import (
    Reference as ParentReference, _checked as parent_checked, _bits, _scalar,
    _zero, _memory_bits, _input_class, _integer, _generation, canonical,
    payload_consumer as frozen_consumer, COMMON, CONSUMER_SCOPE,
)
from .corpus import SITES, SOURCE_BINDING, PREMISES, cases

SPECIFIC = ('Stbuf2995NotPerformed', 'PeripheralEquivalenceNotEstablished')
SIX = {'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions'}


def _checked(snapshot):
    if type(snapshot) is not dict or set(snapshot) != SIX | {'registerKnownBits'}:
        raise ValueError('ReferenceExtendedSnapshot')
    parent_checked({key: snapshot[key] for key in SIX})
    bits = snapshot['registerKnownBits']
    if type(bits) is not dict:
        raise ValueError('ReferenceRegisterKnowledge')
    for key, bit in bits.items():
        if (type(key) is not str or len(key) != 4 or key[:3] not in ('AL.', 'AH.')
                or key[3] not in '01234567' or type(bit) is not int or bit not in (0, 1)):
            raise ValueError('ReferenceRegisterKnowledge')
        raw = snapshot['registers'][key[:2].lower()]
        if raw is not None and (raw >> int(key[-1])) & 1 != bit:
            raise ValueError('ReferenceRegisterContradiction')
    return deepcopy(snapshot)


class Reference(ParentReference):
    def __init__(self, snapshot, procedure, scope):
        original = _checked(snapshot)
        super().__init__({key: original[key] for key in SIX}, procedure, scope, SPECIFIC)
        self.original = original
        self.state['registerKnownBits'] = deepcopy(original['registerKnownBits'])
        self.stbuf = None

    def result(self, boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        value = super().result(boundary, outcome, status, reason)
        value['stbufObligations'] = deepcopy(self.stbuf)
        return value

    def pointer_read(self, pc):
        self.read(pc, 0x84 + self.registers['scb'] * 8, 16,
                  'ARCHITECTURAL_ADDRESS_DEPENDENCY', 'PointingRegisterAlias')

    def pointer_write(self, pc, value, successor):
        self.write(pc, 0x84 + self.registers['scb'] * 8, [value & 255, value >> 8],
                   'PointingRegisterWrite', 'Literal')
        self.step(pc, successor)


def _body(r):
    failure = r.guard(0x2980)
    if failure is not None:
        return failure
    if r.registers['scb'] is None:
        return r.outside(0x2980, 'PointerBankNotEstablished')
    r.pointer_write(0x2980, 0x0356, 0x2983)
    r.pointer_read(0x2983)
    r.rmw(0x2983, 0x0356, 6, 1)
    r.step(0x2983, 0x2985)
    r.pointer_write(0x2985, 0x03F5, 0x2988)
    if r.original['assumptions']['ordinaryByteSemantics'] is not True:
        return r.outside(0x2988, 'OrdinaryByteSemanticsNotEstablished')
    r.register_byte('al', _bits(2))
    r.registers.update(dd=0, zf=0)
    r.step(0x2988, 0x298A)
    r.pointer_read(0x298A)
    r.store_a(0x298A, 0x03F5)
    r.step(0x298A, 0x298B)
    r.pointer_write(0x298B, 0x03F1, 0x298E)
    if r.original['assumptions']['ordinaryByteSemantics'] is not True:
        return r.outside(0x298E, 'OrdinaryByteSemanticsNotEstablished')
    r.pointer_read(0x298E)
    r.read(0x298E, 0x03F1)
    bits = _memory_bits(r.state, 0x03F1)
    r.register_byte('al', bits)
    r.registers.update(dd=0, zf=_zero(bits, 8))
    r.step(0x298E, 0x298F)
    masked = {bit: value for bit, value in bits.items() if bit < 5}
    masked.update({5: 0, 6: 0, 7: 0})
    r.register_byte('al', masked)
    r.registers['zf'] = _zero(masked, 8)
    r.step(0x298F, 0x2991)
    r.pointer_write(0x2991, 0x03F6, 0x2994)
    r.pointer_read(0x2994)
    r.store_a(0x2994, 0x03F6)
    r.step(0x2994, 0x2995)
    r.stbuf = stbuf_boundary_obligations({'inputClass': r.original['inputClass'],
        'sourceBinding': deepcopy(SOURCE_BINDING), 'pc': 0x2995, 'dd': r.registers['dd'],
        'prospectiveAL': {'value': r.registers['al'],
            'knownBits': {key[3:]: value for key, value in r.state['registerKnownBits'].items()
                          if key.startswith('AL.')},
            'generation': 'ConditionalAl:298F:DATA03F1&1F'},
        'softwareReached': True, 'softwareNoInterference': r.original['assumptions']['noInterference'],
        'premises': dict.fromkeys(PREMISES), 'claim': 'ObligationsOnly'})
    return r.result(0x2995, 'ContinuationPreparedBeforeStbuf')


def post_consumer_continuation(snapshot):
    return _body(Reference(snapshot, 'post_consumer_continuation', SITES))


def consumer_with_continuation(snapshot):
    prefix = frozen_consumer(snapshot)
    if prefix['status'] != 'CompleteConditional' or prefix['boundary'] != 0x2980:
        value = deepcopy(prefix)
        value['stbufObligations'] = None
        return value
    extended = {'inputClass': snapshot['inputClass'], 'assumptions': deepcopy(snapshot['assumptions']),
                **deepcopy(prefix['state'])}
    r = Reference(extended, 'consumer_with_continuation', (*CONSUMER_SCOPE, *SITES))
    r.journal = deepcopy(prefix['journal'])
    r.reads = deepcopy(prefix['reads'])
    r.steps = deepcopy(prefix['steps'])
    r.intermediate = deepcopy(prefix['intermediateStates'])
    if any(label is not None and label.startswith('ConditionalEffect:consumer_with_continuation:')
           for label in snapshot['generations'].values()):
        return r.outside(0x2980, 'EffectNamespaceAlreadyPresent')
    return _body(r)


def _slot(value):
    if (type(value) is not dict or set(value) != {'value', 'knownBits', 'generation'}
            or not _integer(value['value'], 255) or not _generation(value['generation'])
            or type(value['knownBits']) is not dict):
        raise ValueError('ReferenceSlot')
    for key, bit in value['knownBits'].items():
        if type(key) is not str or key not in tuple(str(bit) for bit in range(8)) or type(bit) is not int or bit not in (0, 1):
            raise ValueError('ReferenceSlotBit')
        if value['value'] is not None and (value['value'] >> int(key)) & 1 != bit:
            raise ValueError('ReferenceSlotContradiction')


def _domain(value):
    return {value['value']} if value['value'] is not None else {
        byte for byte in range(256) if all((byte >> int(bit)) & 1 == known
                                         for bit, known in value['knownBits'].items())}


def _nullable_bool(value):
    return value is None or type(value) is bool


def _source(value):
    if value is not None and type(value) is not dict:
        raise ValueError('ReferenceSourceBindingType')


def _same_source(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_same_source(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same_source(a, b) for a, b in zip(left, right))
    return left == right


def _formal(query, procedure, state, scope, status, reason, specific, effect, missing=None):
    value = {'procedure': procedure, 'status': status, 'reason': reason, 'boundary': 0x2995,
        'inputClass': query['inputClass'], 'sourceScope': list(scope), 'state': state,
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [],
        'unresolvedConstraints': list(dict.fromkeys([*COMMON, *specific,
            *([] if status == 'CompleteConditional' else [reason])])),
        'effectClass': effect, 'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
        'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
    if missing is not None:
        value['missingPremises'] = missing
    return value


def stbuf_boundary_obligations(query):
    shape = {'inputClass', 'sourceBinding', 'pc', 'dd', 'prospectiveAL', 'softwareReached',
             'softwareNoInterference', 'premises', 'claim'}
    if type(query) is not dict or set(query) != shape:
        raise ValueError('ReferenceStbufShape')
    _input_class(query['inputClass']); _source(query['sourceBinding']); _slot(query['prospectiveAL'])
    if not _integer(query['pc'], 65535) or not _integer(query['dd'], 1):
        raise ValueError('ReferenceBoundaryType')
    if (not _nullable_bool(query['softwareReached']) or not _nullable_bool(query['softwareNoInterference'])
            or type(query['premises']) is not dict or set(query['premises']) != set(PREMISES)
            or any(not _nullable_bool(v) for v in query['premises'].values())
            or query['claim'] not in ('ObligationsOnly', 'ActualBufferWrite', 'ActualTransmit', 'TxComplete', 'IRQ', 'CpuExecution')):
        raise ValueError('ReferenceStbufPremises')
    missing = []
    for key, reason in (('pc', 'UnknownBoundaryPc'), ('dd', 'UnknownByteDescriptor'),
                         ('softwareReached', 'SoftwareBoundaryNotEstablished'),
                         ('softwareNoInterference', 'SoftwareInterferenceNotExcluded')):
        if query[key] is None:
            missing.append(reason)
    if len(_domain(query['prospectiveAL'])) != 1:
        missing.append('ProspectiveAlUnknown')
    if query['prospectiveAL']['generation'] is None:
        missing.append('ProspectiveAlGenerationUnknown')
    missing.extend('PremiseUnknown:' + key for key in PREMISES if query['premises'][key] is None)
    status, reason = 'CompleteConditional', 'HypotheticalStbufObligationsSpecified'
    if query['claim'] != 'ObligationsOnly':
        status, reason = 'OutsideVerifiedScope', 'PeripheralExecutionNotAuthorized'
    elif query['sourceBinding'] is None:
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMissing'
    elif not _same_source(query['sourceBinding'], SOURCE_BINDING):
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMismatch'
    elif query['pc'] is not None and query['pc'] != 0x2995:
        status, reason = 'OutsideVerifiedScope', 'WrongStbufBoundary'
    elif query['dd'] == 1:
        status, reason = 'OutsideVerifiedScope', 'WordStoreInterpretationNotByteStbuf'
    elif query['softwareReached'] is False or query['softwareNoInterference'] is False:
        status, reason = 'OutsideVerifiedScope', 'DeclaredSoftwarePremiseFalse'
    elif False in query['premises'].values():
        status, reason = 'OutsideVerifiedScope', 'DeclaredPeripheralPremiseFalse'
    elif missing:
        status, reason = 'IndeterminateObligation', 'StbufObligationsNotEstablished'
    state = {'prospectiveAL': deepcopy(query['prospectiveAL']), 'descriptorDD': query['dd'],
        'destinationAddress': 0x51, 'widthBits': 8, 'form': 'STB A,N8', 'instructionLength': 2,
        'retainedFlags': ['CF', 'ZF', 'HC', 'DD'], 'resetValue': None, 'readbackNotSpecified': True,
        'declaredPremisesNotObserved': True, 'actualBufferWrite': None, 'actualAcceptance': None,
        'actualTransmission': None, 'actualCompletion': None, 'actualTxIrq': None}
    return _formal(query, 'stbuf_boundary_obligations', state, [0x2995], status, reason,
        ['PhysicalMcuApplicabilityNotEstablished', 'StbufLifecycleAndOwnershipNotEstablished',
         'NoPeripheralOperationPerformed'], 'FormalStbufObligations_NotPeripheralOperation', missing)


def continuation_lineage(query):
    if type(query) is not dict or set(query) != {'inputClass', 'sourceBinding', 'before', 'after', 'requestedGenerations', 'noInterference', 'claim'}:
        raise ValueError('ReferenceLineageShape')
    _input_class(query['inputClass']); _source(query['sourceBinding'])
    for field in ('before', 'after', 'requestedGenerations'):
        if type(query[field]) is not dict or set(query[field]) != {'03F2', '03F4'}:
            raise ValueError('ReferenceLineageSlots')
    for address in ('03F2', '03F4'):
        _slot(query['before'][address]); _slot(query['after'][address])
        if not _generation(query['requestedGenerations'][address]):
            raise ValueError('ReferenceRequestedGeneration')
    if not _nullable_bool(query['noInterference']) or query['claim'] not in ('ConditionalRetentionOnly', 'ParserLength', 'ContinuationReadsF2', 'Native026COwner', 'ActualTransmit'):
        raise ValueError('ReferenceLineagePremise')
    relations = []
    for address, aliases in (('03F2', ['r2', 'er1.low']), ('03F4', ['r4', 'er2.low'])):
        before, after, wanted = query['before'][address], query['after'][address], query['requestedGenerations'][address]
        left, right = _domain(before), _domain(after)
        if query['noInterference'] is not True:
            relation = 'InterferenceNotExcluded'
        elif left.isdisjoint(right):
            relation = 'ValueContradictsFrame'
        elif before['generation'] is not None and after['generation'] is not None and before['generation'] != after['generation']:
            relation = 'GenerationChanged'
        elif before['generation'] is None or after['generation'] is None or wanted is None:
            relation = 'GenerationNotEstablished'
        elif wanted != after['generation']:
            relation = 'StaleRequestedGeneration'
        elif left != right or before['value'] != after['value'] or before['knownBits'] != after['knownBits']:
            relation = 'KnowledgeChangedWithoutObservation'
        else:
            relation = 'ConditionalRetainedNotRead'
        relations.append({'address': int(address, 16), 'widthBits': 8, 'aliasesIfLocalBank03F0': aliases,
            'before': deepcopy(before), 'after': deepcopy(after), 'requestedGeneration': wanted,
            'sourceWindowRead': False, 'sourceWindowWrite': False, 'relation': relation})
    names = {row['relation'] for row in relations}
    status, reason = 'CompleteConditional', 'ConditionalSourceWindowRetentionOnly'
    if query['claim'] != 'ConditionalRetentionOnly':
        status, reason = 'OutsideVerifiedScope', 'UnestablishedLineageAuthorityClaim'
    elif query['sourceBinding'] is None:
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMissing'
    elif not _same_source(query['sourceBinding'], SOURCE_BINDING):
        status, reason = 'OutsideVerifiedScope', 'SourceBindingMismatch'
    elif query['noInterference'] is not True:
        status, reason = 'IndeterminateLineage', 'InterferenceNotExcluded'
    elif names & {'ValueContradictsFrame', 'GenerationChanged', 'StaleRequestedGeneration'}:
        status, reason = 'OutsideVerifiedScope', 'FrameConditionViolated'
    elif names != {'ConditionalRetainedNotRead'}:
        status, reason = 'IndeterminateLineage', 'RetentionObligationsNotEstablished'
    return _formal(query, 'continuation_lineage', {'relations': relations,
        'sourceWindowHasNoF2F4Access': True, 'endpointEqualityIsNotAnObservation': True,
        'native026CReachingDefinitionEstablished': False, 'parserLengthEstablished': False},
        SITES, status, reason, ['EndpointEqualityAloneDoesNotProveLineage',
        'No03F2Or03F4AccessInReviewedContinuation'], 'ConditionalSourceWindowRetention_NotNativeLineage')


OPERATIONS = {'post_consumer_continuation': post_consumer_continuation,
    'consumer_with_continuation': consumer_with_continuation,
    'stbuf_boundary_obligations': stbuf_boundary_obligations, 'continuation_lineage': continuation_lineage}


def evaluate(case):
    return OPERATIONS[case['operation']](deepcopy(case['input']))


def canonical_records():
    for case in cases():
        yield canonical({'caseId': case['id'], 'operation': case['operation'],
                         'input': case['input'], 'output': evaluate(case)})
