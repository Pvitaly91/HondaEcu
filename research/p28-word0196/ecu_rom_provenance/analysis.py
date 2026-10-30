"""Closed documentary bridge and static reconstruction inventory, not execution."""
from copy import deepcopy
import json
from pathlib import Path
import re

from .compatibility import ECUS, MCUS, CONFIGURATIONS, classify
from .provenance import CLAIM_FIELDS, compare_claims

SOURCE_IDS = frozenset(('JapaneseY3', 'EnglishY4', 'ISA1991', 'UserIncomplete', 'ArchiveCatalogue',
    'BomarcSchematic', 'M1aPublicReport', 'M1fPublicReport', 'M2clPublic', 'M2avDoc', 'M2avIR',
    'M2avC11', 'M2bdDoc', 'M2cjDoc', 'M2ckDoc', 'M2amDoc', 'M2awDoc', 'HALoggedList',
    'HaEquivalent', 'PartsNowCatalogue', 'DgProductPage', 'DGTuneA02Photo', 'EbayA01Photo', 'M2cmLocalAuditDeclaration'))

NODE_IDS = frozenset(('studied_rom', 'acquisition_source', 'claimed_ecu_model', 'observed_ecu_label',
    'pcb_revision', 'observed_mcu_marking', 'candidate_mcu', 'candidate_customer_code',
    'manufacturer_document', 'memory_map', 'peripheral_applicability', 'actual_hardware_identity',
    'extraction_custody', 'board_memory_configuration'))
UNKNOWN_NODES = frozenset(('observed_ecu_label', 'pcb_revision', 'observed_mcu_marking',
    'actual_hardware_identity', 'extraction_custody', 'board_memory_configuration', 'peripheral_applicability'))
EDGES = frozenset((
    ('studied_rom', 'acquisition_source'), ('studied_rom', 'claimed_ecu_model'),
    ('acquisition_source', 'extraction_custody'), ('extraction_custody', 'observed_ecu_label'),
    ('claimed_ecu_model', 'observed_ecu_label'), ('observed_ecu_label', 'pcb_revision'),
    ('pcb_revision', 'observed_mcu_marking'), ('observed_mcu_marking', 'candidate_mcu'),
    ('observed_mcu_marking', 'candidate_customer_code'), ('candidate_mcu', 'manufacturer_document'),
    ('manufacturer_document', 'memory_map'), ('pcb_revision', 'board_memory_configuration'),
    ('board_memory_configuration', 'memory_map'), ('memory_map', 'peripheral_applicability'),
    ('candidate_customer_code', 'peripheral_applicability'), ('observed_mcu_marking', 'actual_hardware_identity'),
    ('extraction_custody', 'actual_hardware_identity'), ('peripheral_applicability', 'actual_hardware_identity')))


def require(condition, reason):
    if condition is not True:
        raise ValueError(reason)


def source_map(inventory):
    require(type(inventory) is list and len(inventory) == 24, 'TwentyFourSourceBindingsRequired')
    fields = {'sourceId', 'sourceKind', 'bytes', 'sha256', 'url', 'scope', 'independenceGroup'}
    result = {}
    for row in inventory:
        require(type(row) is dict and set(row) == fields, 'ClosedSourceBindingRequired')
        require(all(type(row[k]) is str and row[k] for k in fields - {'bytes'}), 'TypedSourceFieldsRequired')
        require(type(row['bytes']) is int and row['bytes'] > 0
                and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'ActualDocumentBytesHashRequired')
        require(row['sourceId'] not in result, 'UniqueSourceIdentityRequired')
        result[row['sourceId']] = row['sha256']
    require(set(result) == SOURCE_IDS, 'ExactSourceSubjectsRequired')
    return result


def refs(value, sources):
    require(type(value) is list and bool(value), 'QualifiedSourceReferencesRequired')
    for item in value:
        require(type(item) is dict and set(item) == {'sourceId', 'locator', 'sourceHash'}, 'TypedReferenceRequired')
        require(type(item['sourceId']) is str and item['sourceId'] in sources
                and item['sourceHash'] == sources[item['sourceId']]
                and type(item['locator']) is str and bool(item['locator']), 'KnownSourceHashAndLocatorRequired')


def validate_graph(graph, inventory):
    sources = source_map(inventory)
    require(type(graph) is dict and set(graph) == {'nodes', 'edges', 'actualSiliconConfirmed', 'executionAdmission'},
            'ClosedSameUnitGraphRequired')
    require(graph['actualSiliconConfirmed'] is False and graph['executionAdmission'] is False,
            'DocumentaryGraphCannotAdmitActualHardware')
    nodes, edges = graph['nodes'], graph['edges']
    require(type(nodes) is list and len(nodes) == 14 and all(type(n) is dict for n in nodes), 'FourteenNodesRequired')
    nf = {'nodeId', 'component', 'value', 'evidenceClass', 'sourceRefs', 'unresolvedConditions'}
    require(all(set(n) == nf and type(n['nodeId']) is str for n in nodes), 'TypedNodeRequired')
    by_id = {n['nodeId']: n for n in nodes}
    require(set(by_id) == NODE_IDS and len(by_id) == len(nodes), 'ClosedUniqueNodeInventoryRequired')
    for node in nodes:
        require(all(type(node[k]) is str and node[k] for k in ('component', 'evidenceClass')), 'NodeScopeRequired')
        require(type(node['unresolvedConditions']) is list and bool(node['unresolvedConditions'])
                and all(type(x) is str and x for x in node['unresolvedConditions']), 'NodeUnknownsRequired')
        refs(node['sourceRefs'], sources)
        if node['nodeId'] in UNKNOWN_NODES:
            require(node['value'] is None and node['evidenceClass'] == 'Unknown', 'NoInventedObservedUnitOrOwner')
    ef = {'from', 'to', 'sourceRefs', 'evidenceClass', 'confidenceRationale', 'applicability',
          'provenance', 'unresolvedConditions', 'competingHypotheses', 'requiredConfirmation', 'sameUnitEstablished'}
    require(type(edges) is list and len(edges) == 18, 'EighteenClosedRelationsRequired')
    require(all(type(e) is dict and set(e) == ef for e in edges), 'CompleteEdgeEvidenceRequired')
    require(all(type(e['from']) is str and type(e['to']) is str for e in edges), 'TypedEdgeEndpointsRequired')
    keys = [(e['from'], e['to']) for e in edges]
    require(len(set(keys)) == 18 and set(keys) == EDGES, 'MissingDanglingDuplicateOrChangedRelation')
    for edge in edges:
        refs(edge['sourceRefs'], sources)
        require(edge['sameUnitEstablished'] is False, 'UnobservedSameUnitCannotBeAsserted')
        require(all(type(edge[k]) is str and edge[k] for k in (
            'evidenceClass', 'confidenceRationale', 'applicability', 'provenance')), 'QualifiedEdgeScopeRequired')
        require(all(type(edge[k]) is list and bool(edge[k]) and all(type(x) is str and x for x in edge[k])
                    for k in ('unresolvedConditions', 'competingHypotheses', 'requiredConfirmation')),
                'EdgeUnknownsAlternativesAndConfirmationRequired')
    return {'validatedNodes': 14, 'validatedEdges': 18, 'actualSiliconConfirmed': False, 'executionAdmission': False}


def _validate_contract(value):
    fields = {'schemaVersion', 'milestone', 'baseSha', 'classification', 'classificationQualification',
              'sourceInventory', 'provenanceChain', 'hardwareExamples', 'attributionPairs', 'graph',
              'backlog', 'physicalChecklist', 'authority'}
    require(type(value) is dict and set(value) == fields and type(value.get('schemaVersion')) is int
            and value['schemaVersion'] == 1 and value.get('milestone') == 'M2cm'
            and value.get('baseSha') == 'cd5575a32d49dcc4109837fe8a58016889f9f5eb', 'ExactM2cmBaseContractRequired')
    require(value.get('classification') == 'ROM_PROVENANCE_ESTABLISHED_HARDWARE_UNBOUND', 'ProjectAcquisitionScopeRequired')
    a = value['authority']
    af = {'executionStatus', 'actualSiliconConfirmed', 'actualEcuIdentity', 'actualMcuIdentity',
          'physicalPeripheralApplicability', 'newCpuRomIrqRtiExecutions', 'runtimeAdmission', 'firmwareReady',
          'historical17', 'desktop', 'newDisassemblyPerformed', 'rxAckReassertion', 'iePolarityConflict',
          'currentSsp', 'safeActualFrame', 'actualData03f3Generation'}
    require(type(a) is dict and set(a) == af and a.get('executionStatus') == 'EXECUTION_BLOCKED'
            and all(a.get(k) is False for k in ('actualSiliconConfirmed', 'firmwareReady', 'runtimeAdmission'))
            and type(a.get('newCpuRomIrqRtiExecutions')) is int and a['newCpuRomIrqRtiExecutions'] == 0
            and all(a.get(k) is None for k in ('actualEcuIdentity', 'actualMcuIdentity', 'physicalPeripheralApplicability',
                                             'currentSsp', 'safeActualFrame', 'actualData03f3Generation'))
            and a['rxAckReassertion'] == 'Unknown' and a['iePolarityConflict'] == 'Unresolved'
            and a['historical17'] == 'NotRun' and a['desktop'] == 'NotRun' and a['newDisassemblyPerformed'] is False,
            'NoRuntimeOrPhysicalIdentityPromotion')
    p = value['provenanceChain']
    pf = {'projectAcquisitionCategory', 'prearchiveDonorCategory', 'classificationScope', 'romBytes',
          'factoryOriginality', 'sameUnitIdentityEstablished', 'privateAcquisitionRecordsPublished',
          'privateSourceVerification', 'historicalHttpMetadata', 'initialProfileTiming', 'initialTrust',
          'transportChecks', 'links'}
    require(type(p) is dict and set(p) == pf and p['projectAcquisitionCategory'] == 'B_PublicFirmwareArchive'
            and p['prearchiveDonorCategory'] == 'E_Unknown' and p['factoryOriginality'] == 'Unknown'
            and p['sameUnitIdentityEstablished'] is False and p['romBytes'] == 32768
            and p['privateAcquisitionRecordsPublished'] is False
            and p['classificationScope'] == 'RecordedProjectArchiveAcquisitionAndComputedByteBlobIdentity_HardwareUnbound'
            and p['privateSourceVerification'] == 'SeparateLocalAudit_NotPerformedByPublicStaticCI'
            and p['historicalHttpMetadata'] == 'RecordedLiteralFields_NoPreservedRawGetTranscriptFound',
            'ProjectAcquisitionNotOriginalDonorOrFactoryProof')
    sources = source_map(value['sourceInventory'])
    source_groups = {row['sourceId']: row['independenceGroup'] for row in value['sourceInventory']}
    require(type(p['links']) is list and len(p['links']) == 5, 'FiveSourceScopedAcquisitionLinksRequired')
    for row in p['links']:
        require(type(row) is dict and set(row) == {'from', 'to', 'evidenceClass', 'sourceRefs', 'qualification',
                                                'sameUnitEstablished', 'unknowns'}, 'ClosedAcquisitionLinkRequired')
        refs(row['sourceRefs'], sources)
        require(row['sameUnitEstablished'] is False and type(row['unknowns']) is list and bool(row['unknowns']),
                'AcquisitionLinkMustRetainOwnershipGaps')
    require(type(value['attributionPairs']) is list and len(value['attributionPairs']) == 6,
            'SixSourceBoundAttributionPairsRequired')
    for pair in value['attributionPairs']:
        require(type(pair) is dict and set(pair) == {'left', 'right'}, 'TypedAttributionPairRequired')
        for side in ('left', 'right'):
            claim = pair[side]
            require(type(claim) is dict and set(claim) == CLAIM_FIELDS | {'sourceRefs'}, 'SourceBoundAttributionRequired')
            refs(claim['sourceRefs'], sources)
            require(len(claim['sourceRefs']) == 1
                    and claim['independenceGroup'] == source_groups[claim['sourceRefs'][0]['sourceId']]
                    and claim['unitScope'] is None and claim['exclusive'] is False,
                    'NonExclusiveSourceScopeAndActualIndependenceGroupRequired')
        compare_claims(*({key: pair[side][key] for key in CLAIM_FIELDS} for side in ('left', 'right')))
    validate_graph(value['graph'], value['sourceInventory'])
    require(type(value['hardwareExamples']) is list and len(value['hardwareExamples']) == 3,
            'ThreeSourceScopedHardwareExamplesRequired')
    hf = {'sourceId', 'sourceRefs', 'sourcePage', 'observedLabel', 'observedPcb', 'observedMcuLiteral',
          'packageAppearance', 'exactPackageCode', 'photographer', 'originalPhotoDate', 'sameUnitAsStudiedRom',
          'linkedDumpDigest', 'factoryUnmodifiedStatus', 'externalProgramSelection', 'evidenceClass',
          'limitations', 'actualStudiedHardwareObservation'}
    require({row['sourceId'] for row in value['hardwareExamples']} == {'DGTuneA02Photo', 'EbayA01Photo', 'BomarcSchematic'},
            'DistinctUnlinkedSourceSubjectsRequired')
    for row in value['hardwareExamples']:
        require(type(row) is dict and set(row) == hf and all(row[k] is None for k in (
            'exactPackageCode', 'photographer', 'originalPhotoDate', 'sameUnitAsStudiedRom', 'linkedDumpDigest',
            'factoryUnmodifiedStatus', 'externalProgramSelection', 'actualStudiedHardwareObservation')),
            'UnlinkedPhotoOrDrawingCannotPromoteStudiedUnit')
        refs(row['sourceRefs'], sources)
        require(row['sourceRefs'][0]['sourceId'] == row['sourceId'], 'PhotoSubjectSourceBindingRequired')
    require(type(value['backlog']) is list and {r['category'] for r in value['backlog']} == set('ABCDE'),
            'FiveStaticReconstructionCategoriesRequired')
    for row in value['backlog']:
        require(row['newExecutionAuthorized'] is False and row['newDisassemblyPerformed'] is False,
                'BacklogIsClassificationNotNewExecution')
        refs(row['sourceRefs'], sources)
    require(type(value['physicalChecklist']) is list and len(value['physicalChecklist']) >= 8,
            'ConcretePhysicalEvidenceChecklistRequired')
    for row in value['physicalChecklist']:
        require(row['physicalInterventionRequested'] is False and row['sufficientAlone'] is False,
                'NoInvasiveOrStandaloneIdentityClaim')
        require(all(type(row[k]) is str and row[k] for k in (
            'material', 'removesUnknown', 'additionalEvidence', 'romLinkVerification', 'remainingConditions')),
            'FiveChecklistProofQuestionsRequired')
    return value


def validate_contract(value):
    try:
        return _validate_contract(value)
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError('MalformedDocumentaryContract') from error


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))


def canonical_records():
    c = load_contract()
    relations = [{'left': pair['left'], 'right': pair['right'],
                  'result': compare_claims(*({key: pair[side][key] for key in CLAIM_FIELDS}
                                            for side in ('left', 'right')))} for pair in c['attributionPairs']]
    matrix = [classify(ecu, mcu, configuration) for ecu in ECUS for mcu in MCUS for configuration in CONFIGURATIONS]
    values = (
        ('source-inventory', c['sourceInventory']), ('provenance-chain', c['provenanceChain']),
        ('hardware-examples', c['hardwareExamples']), ('attribution-relations', relations),
        ('compatibility-matrix', matrix), ('same-unit-graph', c['graph']),
        ('static-reconstruction-backlog', c['backlog']), ('physical-checklist', c['physicalChecklist']),
        ('authority', c['authority']))
    return [{'recordId': key, 'recordClass': 'DocumentaryProvenance_NotActualHardwareObservation',
             'payload': deepcopy(payload), 'actualHardwareObservation': None,
             'executionBlocked': True, 'firmwareReady': False} for key, payload in values]
