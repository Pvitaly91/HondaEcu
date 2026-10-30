"""Closed documentary claims and refusals; no receiver or CPU state machine."""
from copy import deepcopy
import json
from pathlib import Path


def load_contract():
    value = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    if (value.get('milestone') != 'M2ck'
            or value.get('baseSha') != 'b2f5331a077a25a2bf29331f38a6b6041792cd55'
            or value.get('classification') != 'RXREADY_SOURCE_CONFLICT_UNRESOLVED'
            or value.get('executionStatus') != 'EXECUTION_BLOCKED'
            or value.get('actualObservation') is not None
            or value.get('firmwareReady') is not False
            or any(value.get(k) != 0 for k in ('targetCpuExecutions', 'actualIrqDeliveries', 'actualRtiExecutions'))):
        raise ValueError('QualifiedM2ckSourceContractRequired')
    rows = value.get('claims')
    if (type(rows) is not list or len(rows) != 28
            or len({r['topic'] for r in rows}) != 28
            or any(set(r) != {'topic', 'recordClass', 'conclusion', 'sourceIds'} for r in rows)):
        raise ValueError('Closed28DocumentaryClaimsRequired')
    return value


def claim(topic, value):
    """Accept a qualified reviewed statement, never infer missing side effects."""
    if type(topic) is not str or type(value) is not str:
        raise ValueError('ExplicitQualifiedDocumentaryStatementRequired')
    rows = {r['topic']: r['conclusion'] for r in load_contract()['claims']}
    if topic not in rows or value != rows[topic]:
        raise ValueError('UnsupportedSemanticOrRuntimePromotion')
    return value


def canonical_records():
    output = []
    for row in load_contract()['claims']:
        output.append({'recordId': 'm2ck-' + row['topic'], 'recordClass': row['recordClass'],
                       'topic': row['topic'], 'conclusion': claim(row['topic'], row['conclusion']),
                       'sourceIds': deepcopy(row['sourceIds']), 'actualObservation': None,
                       'executionBlocked': True, 'firmwareReady': False})
    return output
