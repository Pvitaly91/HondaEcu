"""Source-scoped matrix and prerequisite graph; no ECU execution or simulation."""
from copy import deepcopy
import json
from pathlib import Path

from .address_map import classify

DEPENDENCIES = {
    'actual_unit': (), 'image_identity': (),
    'rom_custody': ('actual_unit', 'image_identity'),
    'chip_identity': ('actual_unit',), 'isa': ('chip_identity',),
    'memory': ('chip_identity', 'actual_unit'), 'psw': ('chip_identity', 'isa'),
    'reset': ('memory', 'psw', 'rom_custody'),
    'vectors': ('memory', 'chip_identity', 'rom_custody'), 'frame': ('memory', 'psw'),
    'interrupts': ('vectors', 'psw', 'frame'),
    'serial': ('memory', 'interrupts', 'chip_identity'),
    'rom_reads': ('memory', 'rom_custody'),
    'retirement': ('isa', 'psw', 'memory', 'rom_reads'),
    'foreground': ('frame', 'retirement', 'interrupts'),
    'execution': ('isa', 'reset', 'psw', 'memory', 'vectors', 'interrupts', 'serial',
                  'frame', 'retirement', 'rom_reads', 'foreground', 'rom_custody', 'chip_identity'),
}


def load_contract():
    value = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    if (value.get('milestone') != 'M2cl'
            or value.get('baseSha') != '081c9c49f2cda648a6be6c63d87e58c4417bf519'
            or value.get('classification') != 'ECU_SILICON_IDENTITY_UNRESOLVED'):
        raise ValueError('ExactSourceQualifiedM2clContractRequired')
    authority = value['authority']
    if (authority.get('runtime') != 'EXECUTION_BLOCKED'
            or authority.get('firmwareReady') is not False
            or authority.get('actualEcuId') is not None
            or authority.get('actualCpuMarking') is not None
            or authority.get('newCpuRomIrqRtiExecutions') != 0):
        raise ValueError('NoRuntimeOrHardwareIdentityPromotion')
    return value


def validate_graph(graph):
    if type(graph) is not dict or set(graph) != {'nodes'} or type(graph['nodes']) is not list:
        raise ValueError('ClosedPrerequisiteGraphRequired')
    nodes = graph['nodes']
    if len(nodes) != 16 or any(type(n) is not dict for n in nodes):
        raise ValueError('SixteenPrerequisiteNodesRequired')
    fields = {'id', 'component', 'status', 'requires', 'neededEvidence', 'actualObservation'}
    if any(set(n) != fields or type(n['id']) is not str for n in nodes):
        raise ValueError('TypedSourceScopedNodeRequired')
    by_id = {n['id']: n for n in nodes}
    if set(by_id) != set(DEPENDENCIES) or len(by_id) != len(nodes):
        raise ValueError('MissingOrDuplicateComponent')
    expected = {n['id']: n for n in load_contract()['graph']['nodes']}
    for node_id, node in by_id.items():
        if (type(node['requires']) is not list
                or any(type(parent) is not str for parent in node['requires'])
                or len(set(node['requires'])) != len(node['requires'])
                or set(node['requires']) != set(DEPENDENCIES[node_id])
                or node['status'] != expected[node_id]['status']
                or node['actualObservation'] is not None
                or type(node['component']) is not str or not node['component']
                or type(node['neededEvidence']) is not list or not node['neededEvidence']
                or any(type(item) is not str or not item for item in node['neededEvidence'])):
            raise ValueError('MissingDependencyOrUnobservedOwnerPromoted')
    visiting, done = set(), set()

    def visit(node_id):
        if node_id in visiting:
            raise ValueError('CyclicPrerequisites')
        if node_id not in done:
            visiting.add(node_id)
            for dependency in by_id[node_id]['requires']:
                visit(dependency)
            visiting.remove(node_id)
            done.add(node_id)

    for node_id in by_id:
        visit(node_id)
    return {'acyclic': True, 'executionAdmission': False}


def validate_matrix(rows, registry=None):
    """Check schema and source bindings; this does not authenticate claim truth."""
    contract = load_contract()
    if registry is None:
        registry = contract['source_registry'] + contract['boundPublicReports']
    sources = {row['sourceId']: row['sha256'] for row in registry}
    fields = {'claimId', 'component', 'statement', 'sourceRefs', 'classification', 'confidence',
              'rationale', 'applicability', 'alternatives', 'unknownConditions', 'neededEvidence'}
    if type(rows) is not list or len(rows) != 49:
        raise ValueError('ClosedFortyNineClaimMatrixRequired')
    if any(type(row) is not dict or set(row) != fields for row in rows):
        raise ValueError('CompleteClaimEvidenceFieldsRequired')
    ids = [row['claimId'] for row in rows]
    if any(type(value) is not str or not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('UniqueClaimIdentityRequired')
    approved_classes = {row['classification'] for row in contract['matrix']}
    for row in rows:
        if (type(row['classification']) is not str or row['classification'] not in approved_classes
                or any(type(row[k]) is not str or not row[k] for k in (
                    'component', 'statement', 'confidence', 'rationale', 'applicability'))
                or any(type(row[k]) is not list or not row[k]
                       or any(type(item) is not str or not item for item in row[k])
                       for k in ('alternatives', 'unknownConditions', 'neededEvidence'))):
            raise ValueError('QualifiedClaimScopeAndUnknownsRequired')
        refs = row['sourceRefs']
        if type(refs) is not list or not refs:
            raise ValueError('SourceBindingRequired')
        for ref in refs:
            if (type(ref) is not dict or set(ref) != {'sourceId', 'locator', 'sourceHash'}
                    or type(ref['sourceId']) is not str or ref['sourceId'] not in sources
                    or ref['sourceHash'] != sources[ref['sourceId']]
                    or type(ref['locator']) is not str or not ref['locator']):
                raise ValueError('KnownSourceHashAndLocatorRequired')
    return {'valid': True, 'actualHardwareIdentityEstablished': False, 'executionAdmission': False}


def canonical_records():
    contract = load_contract()
    validate_graph(contract['graph'])
    validate_matrix(contract['matrix'], contract['source_registry'] + contract['boundPublicReports'])
    records = []

    def add(record_id, record_class, payload):
        records.append({'recordId': record_id, 'recordClass': record_class, 'payload': deepcopy(payload),
                        'actualHardwareObservation': None, 'executionBlocked': True, 'firmwareReady': False})

    for candidate in contract['candidates']:
        add('candidate-' + candidate['candidate'], 'CandidateComparison', candidate)
    for candidate in contract['candidates']:
        model = candidate['candidate']
        mapped = [classify(model, space, address) for space in ('PROGRAM', 'DATA')
                  for address in contract['addresses']]
        add('map-' + model, 'AddressMapComparison', {'model': model, 'classifications': mapped})
    add('evidence-matrix', 'EvidenceMatrix', {'claims': contract['matrix']})
    add('native-prerequisites', 'NativePrerequisiteGraph', contract['graph'])
    add('rom-metadata', 'RomMetadata', contract['metadata'])
    add('authority', 'Authority', contract['authority'])
    if len(records) != 12 or len({r['recordId'] for r in records}) != 12:
        raise ValueError('ClosedTwelveRecordStreamRequired')
    return records
