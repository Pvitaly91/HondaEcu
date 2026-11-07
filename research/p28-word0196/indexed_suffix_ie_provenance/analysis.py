"""Project full research results onto the canonical, public-safe record wire."""
from copy import deepcopy
import json
from pathlib import Path

from enclosing_caller_return.state import need, shape

from .composition import indexed_suffix_composition
from .provenance import data00fa_shadow_lineage, data03cb_suffix_retention
from .return_obligations import indexed_return_obligations
from .suffix import ie5cb9_boundary_obligations, indexed_suffix_post_ie, indexed_suffix_pre_ie
from .wire import AUTHORITY, BASE, RECORD_FIELDS, SOURCE_IDENTITIES, canonical

OPERATIONS = {function.__name__: function for function in (
    indexed_suffix_pre_ie, data00fa_shadow_lineage, ie5cb9_boundary_obligations, indexed_suffix_post_ie,
    indexed_suffix_composition, data03cb_suffix_retention, indexed_return_obligations,
)}


def validate_authority(value):
    if type(value) is dict:
        for key, item in value.items():
            if key in AUTHORITY:
                expected = AUTHORITY[key]
                need(type(item) is type(expected) and item == expected, 'UnadmittedExecutionAuthority')
            elif key == 'actualPeripheralWrite':
                need(item is None, 'UnadmittedExecutionAuthority')
            validate_authority(item)
    elif type(value) is list:
        for item in value:
            validate_authority(item)


def record(case):
    shape(case, ('id', 'operation', 'input'), 'ClosedCaseRequired')
    name, identifier = case['operation'], case['id']
    need(type(identifier) is str and bool(identifier) and type(name) is str and name in OPERATIONS,
         'KnownOperationAndCaseIdentityRequired')
    output = OPERATIONS[name](deepcopy(case['input']))
    validate_authority(output)
    return deepcopy({'caseId': identifier, 'operation': name, 'input': case['input'], 'output': output,
                     **{key: output[key] for key in RECORD_FIELDS},
                     'executionAuthority': {key: output[key] for key in AUTHORITY}})


def load_contract():
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    shape(contract, ('schemaVersion', 'milestone', 'baseSha', 'sourceIdentities', 'authority',
                     'operations', 'canonical', 'stopBoundaries', 'scopeClass'), 'ClosedSourceContractRequired')
    need(type(contract['schemaVersion']) is int and contract['schemaVersion'] == 1
         and contract['milestone'] == 'M2cx' and contract['baseSha'] == BASE
         and contract['sourceIdentities'] == SOURCE_IDENTITIES and set(contract['operations']) == set(OPERATIONS)
         and canonical(contract['authority']) == canonical(dict(AUTHORITY)), 'ExactSourceContractRequired')
    return contract
