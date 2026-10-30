"""Finite documentary joins and invented implications, never CPU execution."""
from copy import deepcopy
import json
from pathlib import Path

from native_rxready_irq000a_source.rx_pending import primary_findings, completion_relation
from native_rxready_irq000a_source.mask_lineage import mask_findings, mask_profile, pending_cut


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def load_contract():
    value = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    if (value['milestone'] != 'M2cj'
            or value['baseSha'] != '08df0e3c9e8e90a7b97fc99280b4cb5a5559ca43'):
        raise ValueError('ExactM2cjContractRequired')
    return value


def single_invocation_findings():
    return deepcopy(load_contract()['singleInvocation'])


def proof_dag():
    return deepcopy(load_contract()['dag'])


def default_claim():
    return deepcopy(load_contract()['acceptedClaim'])


def validate_claim(candidate):
    """Only the exact reviewed conditional claim; no native admission follows."""
    if type(candidate) is not dict or canonical(candidate) != canonical(default_claim()):
        raise ValueError('UnqualifiedOrRuntimePromotingClaimRefused')


def frame_relation(ssp):
    """One invented frame's address geometry, without physical admission."""
    if ssp is not None and (type(ssp) is not int or not 0 <= ssp <= 0xFFFF):
        raise ValueError('SymbolicOrInvented16BitSSPRequired')
    words = [{'role': role, 'address': None if ssp is None else ((ssp - offset) & 0xFFFE)}
             for role, offset in (('PC', 0), ('A', 2), ('LRB', 4), ('PSW', 6))]
    footprint = None if ssp is None else sorted(
        {address for word in words for address in (word['address'], word['address'] + 1)})
    overlap = None if footprint is None else bool(set(footprint) & set(range(0x03F0, 0x03F8)))
    return {'classification': 'InventedOnly_OneFrameGeometry_NotActualStack',
            'inventedIncomingSSP': ssp, 'actualIncomingSSP': None,
            'wordRoles': words, 'footprint': footprint,
            'postEntrySSP': None if ssp is None else (ssp - 8) & 0xFFFF,
            'overlapsParserBank': overlap,
            'numericNonOverlapEstablished': overlap is False,
            'physicalWritableFrameEstablished': False, 'safeFrameEstablished': False,
            'rtiPopOrder': ['PSW', 'LRB', 'A', 'PC'], 'actualSavedForegroundPC': None,
            'firstMissingFrameObligation': ('InventedFrameOverlapsParserBank' if overlap
                                           else 'OwnedSSPAndApplicablePhysicalStorage'),
            'runtimeAdmission': 'Blocked'}


def canonical_records():
    contract = load_contract()
    records = []

    def add(case_id, kind, finding):
        records.append({'caseId': case_id, 'recordType': kind,
                        'classification': contract['classification'],
                        'manufacturer': deepcopy(contract['manufacturer']),
                        'finding': finding, 'authority': deepcopy(contract['authority'])})

    add('primary', 'SourceQualifiedFindings', primary_findings())
    add('mask-lineage', 'ConditionalSoftwareChronology', mask_findings())
    add('single-flag', 'InheritedPathWithNewReceivePredecessors', single_invocation_findings())
    add('proof-dag', 'SourceQualifiedObligations', proof_dag())
    for row in contract['receiveControls']:
        add(row['caseId'], 'InventedReceiveImplication', completion_relation(*row['args']))
    for row in contract['maskControls']:
        add(row['caseId'], 'InventedPolarityHypothesis', mask_profile(*row['args']))
    for row in contract['pendingControls']:
        add(row['caseId'], 'InventedPendingOrdering', pending_cut(*row['args']))
    for row in contract['frameControls']:
        add(row['caseId'], 'InventedSingleFrameGeometry', frame_relation(row['ssp']))
    if len(records) != 23 or len({r['caseId'] for r in records}) != 23:
        raise ValueError('Closed23RecordInventoryRequired')
    return records
