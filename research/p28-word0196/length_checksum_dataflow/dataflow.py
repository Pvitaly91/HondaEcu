"""Conditional persistent-state handoffs, never IRQ/frame or native continuity."""
from copy import deepcopy

from conditional_flag_mode_shadow.state import DATA_KEYS

from .dispatch import ROLES, parser_step
from .state import identifier, require, validate

PERSISTENT = DATA_KEYS - {'0055'}
EDGES = frozenset((('Header', 'Length'), ('Length', 'Flag'),
                   ('Length', 'Checksum'), ('Flag', 'Checksum')))


def persistent(mapping):
    return {key: value for key, value in mapping.items() if key[:4] != '0055'}


def validate_request(request):
    require(type(request) is dict and set(request) == {'stages', 'transfers'}, 'ClosedCompositionRequestRequired')
    stages, transfers = request['stages'], request['transfers']
    require(type(stages) is list and 1 <= len(stages) <= 4, 'BoundedExplicitStagesRequired')
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
    completed, accepted, journal, inputs = [], [], [], []
    final = deepcopy({k: stages[0]['snapshot'][k] for k in ('memory', 'knownBits', 'registers', 'generations')})

    def result(status, reason, stage_id, pc=None):
        return {'procedure': 'compose', 'status': status, 'reason': reason,
            'boundary': {'stageId': stage_id, 'sourcePC': pc},
            'stages': completed, 'transfers': accepted, 'journal': journal,
            'boundaryInputs': inputs, 'finalState': final,
            'effectClass': 'ConditionalDataflowTransfer_NotNativeExecution',
            'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}

    def outside(reason, stage):
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
                return outside('MissingVerifiedInterBlockRelation', stage)
            if transfer['noInterference'] is not True:
                return outside('NoInterferencePremiseNotEstablished', stage)
            if transfer['retainedGenerations'] != persistent(final['generations']):
                return outside('WriterLineageNotEstablished', stage)
            if any(persistent(incoming[key]) != persistent(final[key]) for key in ('memory', 'knownBits', 'generations')):
                return outside('PersistentStateOverwritten', stage)
            if (incoming['inputClass'] != previous['snapshot']['inputClass']
                    or incoming['assumptions'] != previous['snapshot']['assumptions']
                    or incoming['registers']['lrb'] != final['registers']['lrb']):
                return outside('IncompatibleHandoffContext', stage)
            accepted.append({**deepcopy(transfer),
                'classification': 'ConditionalPersistentStateHandoff_NotCfgOrNativeContinuity'})
        inputs.append({'stageId': stage['id'], 'sampleId': stage['sampleId'], 'address': 0x55,
            'widthBits': 8, 'value': incoming['memory']['0055'], 'generation': incoming['generations']['0055'],
            'classification': 'ExplicitSymbolicBoundaryInput_NotPeripheralObservation'})
        output = parser_step(incoming, stage_id=stage['id'], required_role=stage['role'])
        completed.append({'id': stage['id'], 'role': stage['role'], 'sampleId': stage['sampleId'], 'output': output})
        final = output['state']
        for event in output['journal']:
            journal.append({'stageId': stage['id'], 'globalOrdinal': len(journal) + 1, 'event': event})
        if output['status'] != 'CompleteConditional':
            return result(output['status'], output['reason'], stage['id'], output['boundary'])
    return result('CompleteConditional', 'AllRequestedConditionalTransformationsEstablished',
                  stages[-1]['id'], completed[-1]['output']['boundary'])
