"""Independent equations and frozen prefix expectations for complete M2df records."""
from length_checksum_dataflow.reference_oracle import parser_step as expected_prefix

from .path_reference import expected_auxiliary, expected_selector


def reference_byte(kind, left, right):
    if left is None or right is None:
        return dict(value=None, cf=None, zf=None, hc=None)
    sign = 1 if kind == 'Add' else -1
    byte_carry, result = divmod(left + sign * right, 256)
    nibble_carry, _ = divmod(left % 16 + sign * (right % 16), 16)
    return dict(value=result, cf=int(bool(byte_carry)), zf=int(not result), hc=int(bool(nibble_carry)))


def expected_checksum(q):
    addition = q['site'] == 0x023C
    admitted = addition or q['left'] == 0
    output = reference_byte('Add' if addition else 'Subtract', q['left'], q['right']) if admitted else None
    status = 'RefusedSourcePremise' if output is None else (
        'PartialArithmetic' if output['value'] is None else 'ByteArithmeticQualified')
    return dict(status=status, site=q['site'], result=output, destination='DATA03F6' if addition else 'AL',
                preservesDd=True, sideEffectsApplied=False,
                requiredPremise='CurrentR6AndResponseAL' if addition else 'ALZeroFrom0251')


MEMORY_OUTCOMES = {
    'ordinary': ('QualifiedOrdinaryDataRead', True),
    'alias-accumulator': ('ConditionalArchitecturalAlias', True),
    'wrong-aligned-alias': ('SourceOperandMismatch', False),
    'alias-pointer': ('ConditionalPointerBankRead', True),
    'alias-local': ('QualifiedOrdinaryDataRead', True),
    'unknown-address': ('UnknownEffectiveAddress', False),
    'wrong-space': ('WrongDataAddressSpace', False),
    'wrong-width': ('WrongDataReadWidth', False),
    'write-only': ('WriteOnlyRegisterReadBlocked', False),
    'sfr-side-effect': ('UnresolvedReadSideEffect', False),
    'potential-sfr': ('PotentialSfrRead', False),
    'outside': ('OutsideVerifiedReadScope', False),
    'unknown-mapping': ('AddressApplicabilityUnknown', False),
    'external-unbound': ('ExternalDataApplicabilityUnknown', False),
}


def expected_memory(case):
    q = case['input']
    name = case['id'].removeprefix('memory-')
    outcome, allowed = MEMORY_OUTCOMES[name]
    addr = q['address']
    effective = None if name in ('wrong-space', 'wrong-width', 'outside', 'unknown-address') else (
        6 if name in ('alias-accumulator', 'wrong-aligned-alias') else addr)
    pointer = dict(bank=0, register='DP', byteOffset=1, selected=True) if name == 'alias-pointer' else None
    locals_touched = [6] if name in ('alias-local', 'external-unbound') else []
    return dict(pc=q['pc'], space=q['space'], rawAddress=addr, effectiveAddress=effective, widthBits=q['widthBits'],
                classification=outcome, allowed=allowed, pointerAlias=pointer, localAliases=locals_touched,
                actualHardwareRead=None)


ADDRESS_REFUSALS = {
    'unknown-index': 'UnknownTableIndex', 'unknown-scb': 'SelectedPointingBankUnknown',
    'missing-word': 'ProgramWordEvidenceMissing', 'wrong-space': 'WrongProgramAddressSpace',
    'wrong-width': 'WrongProgramWidth', 'wrong-address': 'ProgramAddressMismatch',
    'unknown-generation': 'ProgramWordGenerationMissing', 'unknown-word': 'ProgramWordValueUnknown',
}


def expected_address(case):
    q = case['input']
    name = case['id'].removeprefix('address-')
    status = ADDRESS_REFUSALS.get(name, 'ConditionalProgramToDataAddress')
    selected = name not in ADDRESS_REFUSALS
    addr = q['programWord']['value'] if selected else None
    read = None
    if selected:
        read = expected_memory({'id': 'memory-write-only' if name == 'sfr-output' else 'memory-ordinary',
                                'input': dict(pc=0x023B, address=addr, space='DATA', widthBits=8)})
    return dict(status=status, indexByte=q['indexByte'], programAddress=None if name == 'unknown-index' else 0x6E1A,
                dpStorageAddress=None if name == 'unknown-scb' else 0x0084, programWord=q['programWord'],
                dataAddress=addr, dataReadQualification=read,
                actualProgramRead=None, actualDataRead=None, actualHardwareMapping=None)


def expected_composition(case):
    q = case['input']
    snapshot = q['snapshot']
    prior = expected_prefix(snapshot)
    status, reason, boundary = prior['status'], prior['reason'], prior['boundary']
    continued, handoff = None, None
    name = case['id'].removeprefix('composition-')
    if name in ('wrong-generation', 'unknown-generation'):
        reason = 'ExactFrozenStatusHandoffNotEstablished'
    elif name in ('table', 'partial-taken', 'epilogue', 'blocked-read'):
        handoff = {
            'entryPc': 0x0227, 'branchPc': 0x0225, 'branchTaken': False,
            'sourceGeneration': snapshot['generations']['0356'],
            'clearedStatusGeneration': prior['state']['generations']['0356'], 'reseeded': False,
        }
        carried = {**prior['state'], 'inputClass': snapshot['inputClass'], 'assumptions': snapshot['assumptions']}
        continued = expected_selector({'snapshot': carried, 'context': q['context']})
        status, reason, boundary = continued['status'], continued['reason'], continued['boundary']
    writes = [{'stage': 'FrozenM2co', 'event': event} for event in prior['journal']]
    if continued is not None:
        writes.extend({'stage': 'Alternate0227', 'event': event} for event in continued['journal'])
    return dict(status=status, reason=reason, boundary=boundary,
                sourceScope='FrozenStatusPrefixToAlternate0227' if handoff else 'FrozenM2coResult',
                handoff=handoff, prefix=prior, alternate=continued, orderedWrites=writes)


def expected(case):
    operation = case['operation']
    if operation == 'alternate_response_selector':
        return expected_selector(case['input'])
    if operation == 'alternate_auxiliary_024c_0253':
        return expected_auxiliary(case['input'])
    if operation == 'alternate_checksum_accumulation':
        return expected_checksum(case['input'])
    return {
        'alternate_parser_step': expected_composition,
        'alternate_memory_read_obligations': expected_memory,
        'program_to_data_address_qualification': expected_address,
    }[operation](case)
