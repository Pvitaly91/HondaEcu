"""Review the alternate parser's address spaces and conditional read limits."""

from enclosing_caller_return.state import need, shape


TABLE_BASE = 0x6E12
_DP_BASE = 0x0084
_STANDARD_RAM_END = {
    'ConditionalStandardInternal201': 0x0280,
    'ConditionalStandardInternal207': 0x0480,
}
_MAPPINGS = {*_STANDARD_RAM_END, 'Unknown'}
_SPACES = {'DATA', 'PROGRAM'}
_POINTING_REGISTERS = ('X1', 'X2', 'DP', 'USP')
_READABLE = {'ConditionalArchitecturalAlias', 'ConditionalPointerBankRead', 'QualifiedOrdinaryDataRead'}


def _unsigned(value, maximum):
    return value is None or type(value) is int and 0 <= value <= maximum


def program_address(index_byte, scb):
    """Return the PROGRAM table slot and its selected DATA DP backing address."""
    need(_unsigned(index_byte, 255) and _unsigned(scb, 7), 'TypedTableIndexAndScbRequired')
    return (None if index_byte is None else TABLE_BASE + 2 * index_byte,
            None if scb is None else _DP_BASE + 8 * scb)


def _pointer_alias(address, scb):
    if address is None or not 0x0080 <= address < 0x00C0:
        return None
    bank, offset = divmod(address - 0x0080, 8)
    return {'bank': bank, 'register': _POINTING_REGISTERS[offset // 2], 'byteOffset': offset % 2,
            'selected': None if scb is None else bank == scb}


def _local_aliases(address, width_bits, lrb):
    if address is None or lrb is None:
        return []
    base = (lrb & 0x1FFF) * 8
    return [offset for offset in range(8) if address <= base + offset < address + width_bits // 8]


def _byte_read_class(address, premise):
    if address == 0x0051:
        return 'WriteOnlyRegisterReadBlocked'
    if address == 0x0055:
        return 'UnresolvedReadSideEffect'
    if address < 0x0080:
        return 'PotentialSfrRead'
    if premise == 'Unknown':
        return 'AddressApplicabilityUnknown'
    if address < 0x00C0:
        return 'ConditionalPointerBankRead'
    if address < _STANDARD_RAM_END[premise]:
        return 'QualifiedOrdinaryDataRead'
    return 'ExternalDataApplicabilityUnknown'


def _read_obligation(pc, raw_address, space, width_bits, scb, lrb, premise):
    need(pc is not None and _unsigned(pc, 0xFFFF) and _unsigned(raw_address, 0xFFFF)
         and _unsigned(scb, 7) and _unsigned(lrb, 0xFFFF)
         and type(space) is str and space in _SPACES and type(width_bits) is int and width_bits in (8, 16)
         and type(premise) is str and premise in _MAPPINGS, 'TypedAlternateMemoryReadRequired')
    effective = None
    if space != 'DATA':
        classification = 'WrongDataAddressSpace'
    elif pc not in (0x0231, 0x023B):
        classification = 'OutsideVerifiedReadScope'
    elif width_bits != (16 if pc == 0x0231 else 8):
        classification = 'WrongDataReadWidth'
    elif raw_address is None:
        classification = 'UnknownEffectiveAddress'
    elif pc == 0x0231:
        effective = raw_address & 0xFFFE
        classification = 'ConditionalArchitecturalAlias' if raw_address == 0x0006 else 'SourceOperandMismatch'
    else:
        effective = raw_address
        classification = _byte_read_class(effective, premise)
    return {
        'pc': pc, 'space': space, 'rawAddress': raw_address, 'effectiveAddress': effective,
        'widthBits': width_bits, 'classification': classification, 'allowed': classification in _READABLE,
        'pointerAlias': _pointer_alias(effective, scb), 'localAliases': _local_aliases(effective, width_bits, lrb),
        'actualHardwareRead': None,
    }


def qualify_data_read(pc, raw_address, width_bits, scb, lrb, premise):
    """Return a conditional DATA obligation for an already reviewed source PC."""
    return _read_obligation(pc, raw_address, 'DATA', width_bits, scb, lrb, premise)


def alternate_memory_read_obligations(query):
    shape(query, ('pc', 'address', 'space', 'widthBits', 'scb', 'lrb', 'dataMapping'),
          'ClosedAlternateMemoryReadQueryRequired')
    return _read_obligation(query['pc'], query['address'], query['space'], query['widthBits'],
                            query['scb'], query['lrb'], query['dataMapping'])


def _program_word_status(word, expected_address, dp_storage):
    if expected_address is None:
        return 'UnknownTableIndex'
    if dp_storage is None:
        return 'SelectedPointingBankUnknown'
    if word is None:
        return 'ProgramWordEvidenceMissing'
    if word['space'] != 'PROGRAM':
        return 'WrongProgramAddressSpace'
    if word['widthBits'] != 16:
        return 'WrongProgramWidth'
    if word['address'] != expected_address:
        return 'ProgramAddressMismatch'
    if word['generation'] is None:
        return 'ProgramWordGenerationMissing'
    if word['value'] is None:
        return 'ProgramWordValueUnknown'
    return 'ConditionalProgramToDataAddress'


def program_to_data_address_qualification(query):
    """Check the distinct PROGRAM word and downstream DATA byte obligations."""
    shape(query, ('indexByte', 'scb', 'lrb', 'programWord', 'dataMapping'), 'ClosedProgramToDataQueryRequired')
    index, scb, lrb, word, premise = (query[key] for key in ('indexByte', 'scb', 'lrb', 'programWord', 'dataMapping'))
    expected_address, dp_storage = program_address(index, scb)
    need(_unsigned(lrb, 0xFFFF) and type(premise) is str and premise in _MAPPINGS, 'TypedAddressingPremiseRequired')
    if word is not None:
        shape(word, ('address', 'space', 'widthBits', 'value', 'generation'), 'ClosedProgramWordEvidenceRequired')
        need(word['address'] is not None and _unsigned(word['address'], 0xFFFF)
             and type(word['space']) is str and word['space'] in _SPACES
             and type(word['widthBits']) is int and word['widthBits'] in (8, 16)
             and _unsigned(word['value'], 0xFFFF) and (word['generation'] is None or
                 type(word['generation']) is str and 0 < len(word['generation']) <= 128),
             'TypedProgramWordEvidenceRequired')
    status = _program_word_status(word, expected_address, dp_storage)
    target = word['value'] if status == 'ConditionalProgramToDataAddress' else None
    return {
        'status': status, 'indexByte': index, 'programAddress': expected_address, 'dpStorageAddress': dp_storage,
        'programWord': None if word is None else dict(word), 'dataAddress': target,
        'dataReadQualification': None if target is None else qualify_data_read(0x023B, target, 8, scb, lrb, premise),
        'actualProgramRead': None, 'actualDataRead': None, 'actualHardwareMapping': None,
    }
