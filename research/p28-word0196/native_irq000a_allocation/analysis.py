"""Closed documentary allocation correction; never an IRQ or CPU model.

The content seal limits inputs to this reviewed contract. It does not authenticate
silicon, establish a manual revision, or supply runtime observations.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

STATIC = 'DocumentaryStaticAllocationReview_NotExecution'
CONTRACT_RAW_SHA256 = '0ec5bb4e8a9e4b590eaa6ea1ed36df945bb16a6255f850510f82774d28f4ceab'
CONTRACT_CONTENT_SHA256 = '25b78897785ea0b6e77678002490e4f67f2e092c0d150e7d938d0ce1947d57a6'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')


def _closed_json(value):
    if type(value) is dict:
        return all(type(k) is str and _closed_json(v) for k, v in value.items())
    if type(value) is list:
        return all(_closed_json(v) for v in value)
    return type(value) in (str, int, bool, type(None))


def validate_contract(candidate):
    if (type(candidate) is not dict or not _closed_json(candidate)
            or sha256(canonical(candidate)).hexdigest() != CONTRACT_CONTENT_SHA256):
        raise ValueError('ClosedSourceQualifiedContractRequired')


def load_contract():
    raw = Path(__file__).with_name('contract.json').read_bytes()
    if sha256(raw).hexdigest() != CONTRACT_RAW_SHA256:
        raise ValueError('ReviewedContractBytesRequired')
    contract = json.loads(raw)
    validate_contract(contract)
    return contract


def compare_claim(profile, vectorAddress, interruptSource, irqBit, ieBit, irqSymbol, ieSymbol):
    """Accept a printed-table tuple, without promoting it to actual ECU fact."""
    result = {'accepted': False, 'refusal': 'UnsupportedSourceQualifiedAllocationClaim',
        'actualHardwareApplicabilityEstablished': False}
    if (type(profile) is not str or type(vectorAddress) is not int
            or type(interruptSource) is not str
            or any(type(v) not in (int, type(None)) for v in (irqBit, ieBit))
            or any(type(v) not in (str, type(None)) for v in (irqSymbol, ieSymbol))):
        return result
    contract = load_contract()
    source = next((p['source'] for p in contract['profiles'] if p['profile'] == profile), None)
    row = next((r for r in contract['vectors'] if r['vectorAddress'] == vectorAddress), None)
    supplied = {'interruptSource': interruptSource, 'irqBit': irqBit, 'ieBit': ieBit,
        'irqSymbol': irqSymbol, 'ieSymbol': ieSymbol}
    if source is not None and row is not None and canonical(supplied) == canonical(row[source]):
        result.update(accepted=True, refusal=None)
    return result


def mask_implications(entry_mask, tail_mask):
    """Only the two reviewed shadow-mask pairs; actual IE remains unknown."""
    if (type(entry_mask) is not int or type(tail_mask) is not int
            or (entry_mask, tail_mask) not in ((0x02A0, 0x2BAB), (0x00A0, 0xA9A3))):
        raise ValueError('ClosedMaskPairRequired')
    return {'entryMask': entry_mask, 'tailMask': tail_mask,
        'sourceProfile': 'UserTable17_1', 'rxBit': 1,
        'rxEntryEnabled': bool(entry_mask & (1 << 1)),
        'rxTailEnabled': bool(tail_mask & (1 << 1)), 'txBit': 2,
        'txEntryEnabled': bool(entry_mask & (1 << 2)),
        'txTailEnabled': bool(tail_mask & (1 << 2)),
        'enablePolaritySource': 'UserSection17_2_2_Printed165_IESet1',
        'contradictoryEntryParagraph': 'Printed167SaysIESet0_NotResolvedAsErratum',
        'actualEnableStateKnown': False, 'deliveryObserved': False,
        'interpretation': 'ConditionalRxSelfMaskThenReenable_NotTxEnable'}


def evaluate(candidate=None):
    contract = load_contract() if candidate is None else deepcopy(candidate)
    validate_contract(contract)
    report = {key: deepcopy(contract[key]) for key in
        ('schemaVersion', 'milestone', 'classification', 'documents', 'vectors',
            'profiles', 'correction', 'authority')}
    report['masks'] = [mask_implications(entry, tail) for entry, tail in contract['maskPairs']]
    return report


def canonical_records(candidate=None):
    report = evaluate(candidate)
    records = []

    def add(identity, kind, finding):
        records.append({'caseId': identity, 'recordType': kind,
            'classification': STATIC, 'finding': finding})

    for document in report['documents']:
        add('document:' + document['id'], 'document', document)
    for vector in report['vectors']:
        add(f'vector:{vector["vectorAddress"]:04X}', 'vector', vector)
    for profile in report['profiles']:
        add('profile:' + profile['profile'], 'profile', profile)
    for mask in report['masks']:
        add(f'mask:{mask["entryMask"]:04X}:{mask["tailMask"]:04X}', 'mask', mask)
    add('correction', 'correction', report['correction'])
    add('authority', 'authority', report['authority'])
    return records
