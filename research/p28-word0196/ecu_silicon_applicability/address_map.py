"""Documentary standard-device address regions, never an actual Bus mapping."""

LIMITS = {
    'MSM66201': (0x3FFF, 0x027F),
    'MSM66207': (0x7FFF, 0x047F),
    'MSM66P201': (0x3FFF, 0x027F),
    'MSM66P207': (0x7FFF, 0x047F),
}


def classify(model, space, address):
    if type(model) is not str or model not in LIMITS:
        raise ValueError('NamedStandardCandidateRequired')
    if type(space) is not str or space not in ('PROGRAM', 'DATA'):
        raise ValueError('SeparateProgramOrDataSpaceRequired')
    if type(address) is not int or not 0 <= address <= 0xFFFF:
        raise ValueError('ExplicitUnsigned16BitAddressRequired')
    program_last, data_last = LIMITS[model]
    if space == 'PROGRAM':
        region = ('InternalProgram16K' if program_last == 0x3FFF else 'InternalProgram32K')
        if address > program_last:
            region = 'ExternalProgram_BoardMappingUnknown'
    elif address < 0x80:
        region = 'SFRNamespace_ImplementedHolesUnknown'
    elif address < 0xC0:
        region = 'InternalRam_PointingBankAlias'
    elif address < 0x100:
        region = 'InternalRam_ZeroPage'
    elif address <= data_last:
        region = 'InternalRam_Paged'
    else:
        region = 'ExternalData_BoardMappingUnknown'
    return {'model': model, 'space': space, 'address': address,
            'documentedRegion': region, 'actualMappingVerified': False,
            'sourceId': 'JapaneseY3', 'sourcePage': 17}
