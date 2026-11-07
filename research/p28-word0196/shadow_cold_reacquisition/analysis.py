"""Public canonical projection for complete bounded source results."""
from copy import deepcopy
import json
from pathlib import Path

from enclosing_caller_return.state import need, shape
from indexed_suffix_ie_provenance.analysis import validate_authority

from .adc_generation_timeline import cold_adc_generation_timeline, data03d1_reaching_definitions
from .cold_reacquisition import cold_reacquisition_sequence, cold_reacquisition_step
from .helper_5cd9 import helper_5cd9, rt5cf9_obligations
from .shadow_lineage import data00fa_caller_reaching_definitions
from .wire import AUTHORITY, BASE, RECORD_FIELDS, SOURCE_IDENTITIES, canonical

OPERATIONS = {function.__name__: function for function in (
    data00fa_caller_reaching_definitions, cold_reacquisition_step, cold_reacquisition_sequence,
    cold_adc_generation_timeline, data03d1_reaching_definitions, helper_5cd9, rt5cf9_obligations,
)}


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
         and contract['milestone'] == 'M2cy' and contract['baseSha'] == BASE
         and contract['sourceIdentities'] == SOURCE_IDENTITIES and set(contract['operations']) == set(OPERATIONS)
         and canonical(contract['authority']) == canonical(dict(AUTHORITY)), 'ExactSourceContractRequired')
    return contract
