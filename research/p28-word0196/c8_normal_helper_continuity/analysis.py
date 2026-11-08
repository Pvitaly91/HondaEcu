"""Publish full bounded source records without an execution authority."""
from copy import deepcopy
import json
from pathlib import Path

from enclosing_caller_return.state import need, shape
from indexed_suffix_ie_provenance.analysis import validate_authority

from .data03cb_reaching import cold_to_mode_intervening_writes, data03cb_to_60cc_source_proof
from .frame_graph import cold_frame_generation_chain, cold_normal_mode_source_join
from .helper_continuity import (
    c8_primary_evidence_adjudication, c8_source_feasibility,
    helper_normal_continuation, helper_normal_entry_provenance,
)
from .wire import AUTHORITY, BASE, RECORD_FIELDS, SOURCE_IDENTITIES, canonical

OPERATIONS = {function.__name__: function for function in (
    c8_primary_evidence_adjudication, c8_source_feasibility, helper_normal_entry_provenance,
    helper_normal_continuation, cold_frame_generation_chain, cold_normal_mode_source_join,
    cold_to_mode_intervening_writes, data03cb_to_60cc_source_proof,
)}


def record(case):
    shape(case, ('id', 'operation', 'input'), 'ClosedCaseRequired')
    name, identity = case['operation'], case['id']
    need(type(name) is str and name in OPERATIONS and type(identity) is str and bool(identity),
         'KnownOperationAndCaseIdentityRequired')
    output = OPERATIONS[name](deepcopy(case['input']))
    validate_authority(output)
    return deepcopy({'caseId': identity, 'operation': name, 'input': case['input'], 'output': output,
                     **{key: output[key] for key in RECORD_FIELDS}, 'sourceApplicability': output['applicability'],
                     'executionAuthority': {key: output[key] for key in AUTHORITY}})


def load_contract():
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    shape(contract, ('schemaVersion', 'milestone', 'baseSha', 'sourceIdentities', 'authority',
                     'operations', 'canonical', 'stopBoundaries', 'scopeClass'), 'ClosedSourceContractRequired')
    need(type(contract['schemaVersion']) is int and contract['schemaVersion'] == 1
         and contract['milestone'] == 'M2da' and contract['baseSha'] == BASE
         and contract['sourceIdentities'] == SOURCE_IDENTITIES and set(contract['operations']) == set(OPERATIONS)
         and canonical(contract['authority']) == canonical(dict(AUTHORITY)), 'ExactSourceContractRequired')
    return contract
