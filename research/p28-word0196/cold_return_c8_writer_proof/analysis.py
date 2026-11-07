"""Project complete M2cz source results to canonical research records."""
from copy import deepcopy
import json
from pathlib import Path

from enclosing_caller_return.state import need, shape
from indexed_suffix_ie_provenance.analysis import validate_authority

from .c8_helper import c8_branch_consensus, helper_5cd9_extended
from .cold_source_join import cold_caller_mode_source_join, cold_return_path_obligations
from .competing_writers import (
    data03cb_competing_writer_exclusion, data03cb_to_mode_reaching_definitions, usp27b2_alias_proof,
)
from .wire import AUTHORITY, BASE, RECORD_FIELDS, SOURCE_IDENTITIES, canonical

OPERATIONS = {function.__name__: function for function in (
    c8_branch_consensus, helper_5cd9_extended, cold_return_path_obligations, cold_caller_mode_source_join,
    data03cb_competing_writer_exclusion, data03cb_to_mode_reaching_definitions, usp27b2_alias_proof,
)}


def record(case):
    shape(case, ('id', 'operation', 'input'), 'ClosedCaseRequired')
    name, identity = case['operation'], case['id']
    need(type(name) is str and name in OPERATIONS and type(identity) is str and bool(identity),
         'KnownOperationAndCaseIdentityRequired')
    output = OPERATIONS[name](deepcopy(case['input']))
    validate_authority(output)
    return deepcopy({'caseId': identity, 'operation': name, 'input': case['input'], 'output': output,
                     **{key: output[key] for key in RECORD_FIELDS},
                     'executionAuthority': {key: output[key] for key in AUTHORITY}})


def load_contract():
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    shape(contract, ('schemaVersion', 'milestone', 'baseSha', 'sourceIdentities', 'authority',
                     'operations', 'canonical', 'stopBoundaries', 'scopeClass'), 'ClosedSourceContractRequired')
    need(type(contract['schemaVersion']) is int and contract['schemaVersion'] == 1
         and contract['milestone'] == 'M2cz' and contract['baseSha'] == BASE
         and contract['sourceIdentities'] == SOURCE_IDENTITIES and set(contract['operations']) == set(OPERATIONS)
         and canonical(contract['authority']) == canonical(dict(AUTHORITY)), 'ExactSourceContractRequired')
    return contract
