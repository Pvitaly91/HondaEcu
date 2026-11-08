"""Exact reviewed byte arithmetic, independent of physical transmission."""
from enclosing_caller_return.state import need, number, shape


def byte_effect(kind, left, right):
    """Apply ADD or SUB unsigned carry/borrow, nibble carry/borrow and ZF."""
    need(kind in ('Add', 'Subtract') and number(left, 255) and number(right, 255),
         'TypedReviewedByteArithmeticRequired')
    if left is None or right is None:
        return {'value': None, 'cf': None, 'zf': None, 'hc': None}
    if kind == 'Add':
        total = left + right
        cf = total > 255
        hc = (left & 15) + (right & 15) > 15
    else:
        total = left - right
        cf = total < 0
        hc = (left & 15) < (right & 15)
    value = total & 255
    return {'value': value, 'cf': int(cf), 'zf': int(value == 0), 'hc': int(hc)}


def alternate_checksum_accumulation(query):
    """Apply the two source-qualified checksum equations at their own sites."""
    shape(query, ('site', 'left', 'right'), 'ClosedChecksumEquationQueryRequired')
    site, left, right = (query[key] for key in ('site', 'left', 'right'))
    need(type(site) is int and site in (0x023C, 0x0252) and number(left, 255) and number(right, 255),
         'ReviewedChecksumEquationRequired')
    qualified = site == 0x023C or left == 0
    status = 'RefusedSourcePremise' if not qualified else (
        'PartialArithmetic' if left is None or right is None else 'ByteArithmeticQualified')
    result = byte_effect('Add' if site == 0x023C else 'Subtract', left, right) if qualified else None
    return {'status': status, 'site': site, 'result': result,
            'destination': 'DATA03F6' if site == 0x023C else 'AL',
            'preservesDd': True, 'sideEffectsApplied': False,
            'requiredPremise': 'CurrentR6AndResponseAL' if site == 0x023C else 'ALZeroFrom0251'}
