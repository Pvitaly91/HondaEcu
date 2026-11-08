"""Closed static record format, source identities, and execution restrictions."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from .ci import BASE, ROOT

AUTHORITY = MappingProxyType({
    'executionStatus': 'EXECUTION_BLOCKED',
    'firmwareReady': False,
    'cpuInstructionRetirements': 0,
    'actualCpuExecutions': 0,
    'actualPeripheralOperations': 0,
    'actualCallExecution': None,
    'actualReturnExecution': None,
    'actualFramePop': None,
    'actualIeWrite': None,
    'actualIrqDelivery': None,
    'actualBufferWrite': None,
    'actualTransmission': None,
    'actualHardwareObservation': None,
    'stbufStopBoundary': 'STOP_BEFORE_STBUF_2995',
})


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def record(case, output):
    return {
        'caseId': case['id'],
        'operation': case['operation'],
        'input': case['input'],
        'output': output,
        'sourceClass': 'BoundedSoftwareProjection',
        'executionAuthority': dict(AUTHORITY),
    }


def operations():
    from .frames import cold_multi_frame_chain, helper_rt_frame_lifetime
    from .helper import helper_ingress_proof, helper_normal_feasibility
    from .lineage import data03cb_post_helper_lineage

    return {function.__name__: function for function in (
        helper_ingress_proof, helper_normal_feasibility, helper_rt_frame_lifetime,
        cold_multi_frame_chain, data03cb_post_helper_lineage,
    )}


def validate_contract(contract):
    if type(contract) is not dict or set(contract) != {
        'schemaVersion', 'milestone', 'baseSha', 'authority', 'operations',
        'sources', 'boundaries', 'canonical', 'sourceReviewIdentity',
    }:
        raise ValueError('ClosedSourceContractRequired')
    if (type(contract['schemaVersion']) is not int or contract['schemaVersion'] != 1
            or contract['milestone'] != 'M2db' or contract['baseSha'] != BASE
            or canonical(contract['authority']) != canonical(dict(AUTHORITY))
            or contract['boundaries'] != ['STOP_BEFORE_IE_WRITE_5CB9', 'STOP_BEFORE_IE_WRITE_5CCB',
                                         'STOP_BEFORE_BRK_5CF8', 'STOP_BEFORE_STBUF_2995']
            or contract['operations'] != sorted(operations())):
        raise ValueError('ExactSourceContractRequired')
    if type(contract['sources']) is not dict:
        raise ValueError('ClosedSourceBindingInventoryRequired')
    review = contract['sourceReviewIdentity']
    if (type(review) is not str or len(review) != 64
            or any(ch not in '0123456789abcdef' for ch in review)):
        raise ValueError('SourceReviewFingerprintRequired')
    for path, digest in contract['sources'].items():
        if path not in SOURCE_PATHS or sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('FrozenSourceBindingChanged')
    if set(contract['sources']) != SOURCE_PATHS:
        raise ValueError('ClosedSourceBindingInventoryRequired')
    return contract


SOURCE_PATHS = frozenset({
    'research/p28-word0196/c8_normal_helper_continuity/contract.json',
    'research/p28-word0196/cold_return_c8_writer_proof/contract.json',
    'research/p28-word0196/shadow_cold_reacquisition/contract.json',
    'research/p28-word0196/indexed_suffix_ie_provenance/contract.json',
    'research/p28-word0196/enclosing_caller_return/contract.json',
})


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))
