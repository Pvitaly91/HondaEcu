"""Bounded explicit state handoffs; no native return, IRQ or receiver lifecycle."""
from copy import deepcopy

from length_checksum_dataflow.dataflow import PERSISTENT, persistent
from length_checksum_dataflow.state import identifier, require, validate

from .dispatch import ROLES, parser_step
from .payload import CONSTRAINTS

MAX_STAGES = 512
EDGES = frozenset((('Header', 'Length'), ('Length', 'Flag'), ('Length', 'Checksum'),
    ('Flag', 'Checksum'), ('Flag', 'Generic'), ('Generic', 'Generic'),
    ('Generic', 'Checksum'), ('Generic', 'Length')))


def validate_request(request):
    require(type(request) is dict and set(request) == {'stages', 'transfers'}, 'ClosedCompositionRequestRequired')
    stages, transfers = request['stages'], request['transfers']
    require(type(stages) is list and 1 <= len(stages) <= MAX_STAGES,
            'SyntheticStageResourceLimit512_NotProtocolBound')
    for stage in stages:
        require(type(stage) is dict and set(stage) == {'id', 'role', 'sampleId', 'snapshot'}, 'TypedConditionalStageRequired')
        require(identifier(stage['id']) and identifier(stage['sampleId']), 'TypedUniqueStageIdentifierRequired')
        require(type(stage['role']) is str and stage['role'] in ROLES, 'ClosedConditionalRoleRequired')
        validate(stage['snapshot'])
    require(len({s['id'] for s in stages}) == len(stages)
            and len({s['sampleId'] for s in stages}) == len(stages), 'DistinctStageAndSymbolicSampleIdsRequired')
    require(type(transfers) is list and len(transfers) == len(stages) - 1, 'OneExplicitTransferPerBoundaryRequired')
    for transfer in transfers:
        require(type(transfer) is dict and set(transfer) == {
            'from', 'to', 'relation', 'noInterference', 'retainedGenerations'}, 'ClosedConditionalTransferRequired')
        require(identifier(transfer['from']) and identifier(transfer['to'])
                and type(transfer['relation']) is str and bool(transfer['relation']), 'TypedConditionalTransferIdentityRequired')
        require(transfer['noInterference'] is None or type(transfer['noInterference']) is bool,
                'BooleanOrUnknownTransferPremiseRequired')
        lineage = transfer['retainedGenerations']
        require(type(lineage) is dict and set(lineage) == PERSISTENT
                and all(v is None or type(v) is str and bool(v) for v in lineage.values()), 'FullPersistentGenerationMapRequired')
    return request


def compose(request):
    validate_request(request)
    stages, transfers = request['stages'], request['transfers']
    completed, accepted, rejected, journal, inputs, boundaries, decisions = [], [], [], [], [], [], []
    final = deepcopy({k: stages[0]['snapshot'][k] for k in ('memory', 'knownBits', 'registers', 'generations')})

    def result(status, reason, stage_id, pc=None):
        constraints = list(CONSTRAINTS)
        for stage in completed:
            for constraint in stage['output']['unresolvedConstraints']:
                if constraint not in constraints:
                    constraints.append(constraint)
        if status != 'CompleteConditional' and reason not in constraints:
            constraints.append(reason)
        outcome = completed[-1]['output']['outcome'] if completed else None
        checksum = outcome if outcome in ('ChecksumAccepted', 'ChecksumRejected') else None
        if checksum is None:
            constraints.append('ChecksumNotReachedWithinRequestedSequence')
        return {'procedure': 'compose', 'status': status, 'reason': reason,
            'boundary': {'stageId': stage_id, 'sourcePC': pc}, 'stages': completed,
            'transfers': accepted, 'rejectedTransfers': rejected, 'journal': journal,
            'boundaryInputs': inputs, 'finalState': final, 'stageBoundaries': boundaries,
            'branchDecisions': decisions, 'checksumOutcome': checksum, 'unresolvedConstraints': constraints,
            'effectClass': 'ConditionalDataflowTransfer_NotNativeExecution',
            'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}

    def outside(reason, stage, transfer=None):
        if transfer is not None:
            rejected.append({'transfer': deepcopy(transfer), 'reason': reason,
                'classification': 'RefusedConditionalHandoff_NotRuntimeEvent'})
        return result('OutsideVerifiedScope', reason, stage['id'])

    if stages[0]['role'] != 'Header':
        return outside('CompositionRequiresHeaderOrigin', stages[0])
    namespaces = tuple('ConditionalEffect:parser_step@' + s['id'] + ':' for s in stages)
    if any(value is not None and value.startswith(namespaces) for value in final['generations'].values()):
        return outside('GenerationNamespaceCollision', stages[0])
    for index, stage in enumerate(stages):
        incoming = stage['snapshot']
        if index:
            previous, transfer = stages[index - 1], transfers[index - 1]
            if (transfer['from'] != previous['id'] or transfer['to'] != stage['id']
                    or transfer['relation'] != 'ConditionalPersistentStateHandoff'
                    or (previous['role'], stage['role']) not in EDGES):
                return outside('MissingVerifiedInterBlockRelation', stage, transfer)
            if transfer['noInterference'] is not True:
                return outside('NoInterferencePremiseNotEstablished', stage, transfer)
            if transfer['retainedGenerations'] != persistent(final['generations']):
                return outside('WriterLineageNotEstablished', stage, transfer)
            if any(persistent(incoming[key]) != persistent(final[key]) for key in ('memory', 'knownBits', 'generations')):
                return outside('PersistentStateOverwritten', stage, transfer)
            if (incoming['inputClass'] != previous['snapshot']['inputClass']
                    or incoming['assumptions'] != previous['snapshot']['assumptions']
                    or incoming['registers']['lrb'] != final['registers']['lrb']):
                return outside('IncompatibleHandoffContext', stage, transfer)
            accepted.append({**deepcopy(transfer),
                'classification': 'ConditionalPersistentStateHandoff_NotCfgOrNativeContinuity'})
        inputs.append({'stageId': stage['id'], 'sampleId': stage['sampleId'], 'address': 0x55,
            'widthBits': 8, 'value': incoming['memory']['0055'], 'generation': incoming['generations']['0055'],
            'classification': 'ExplicitSymbolicBoundaryInput_NotPeripheralObservation'})
        output = parser_step(incoming, stage_id=stage['id'], required_role=stage['role'])
        completed.append({'id': stage['id'], 'role': stage['role'], 'sampleId': stage['sampleId'], 'output': output})
        final = output['state']
        boundaries.append({'stageId': stage['id'], 'sourcePC': output['boundary'],
                           'status': output['status'], 'outcome': output['outcome']})
        decisions.extend({'stageId': stage['id'], 'pc': step['pc'], 'next': step['next'],
                          'branchTaken': step['branchTaken']} for step in output['steps'] if step['kind'] == 'Branch')
        for event in output['journal']:
            journal.append({'stageId': stage['id'], 'globalOrdinal': len(journal) + 1, 'event': event})
        if output['status'] != 'CompleteConditional':
            return result(output['status'], output['reason'], stage['id'], output['boundary'])
    return result('CompleteConditional', 'AllRequestedConditionalTransformationsEstablished',
                  stages[-1]['id'], completed[-1]['output']['boundary'])
