"""Deterministic documentary and invented policy cases with closed identities."""
from copy import deepcopy
from itertools import product

ECUS = ('P28-A01', 'P28-A51', 'P28-A02', 'P28-A52', 'Unknown')
MCUS = ('MSM66201', 'MSM66207', 'MSM66P201', 'MSM66P207')
PROGRAM = ('InternalOnly32K', 'ExternalProgramSupported', 'Unknown')
ARCHIVE = ('M1aAcquisition', 'ArchiveImport', 'ArchiveDedup', 'HistoricalAttachment')
ISA_SOURCES = ('Oki1991C8Instruction', 'Oki1991C8SameEditionMirror', 'Oki1998InstructionList',
               'Oki1999Nx8500S', 'Oki1998EnDeviceSpec', 'Oki1998JaDeviceSpec', 'OkiNov1990_207DeviceSpec')


def _case(operation, name, query):
    return {'id': name, 'operation': operation, 'input': deepcopy(query)}


def custody(sources=ARCHIVE, binding='ExactAuthenticatedArchive', claim='ProjectArchiveAcquisition'):
    return {'archiveBinding': binding, 'sourceIds': list(sources), 'requestedConclusion': claim}


def isa_query(**changes):
    return {'inputClass': 'SyntheticTestInput', 'catalogPart': 'MSM66207', 'siliconRevision': None,
            'customerCode': None, 'opcode': 0xC8, 'sourceIds': list(ISA_SOURCES), 'claim': 'Inspect',
            **changes}


def memory_query(ecu='Unknown', mcu='MSM66207', program='Unknown', **changes):
    return {'ecuCandidate': ecu, 'mcuCandidate': mcu, 'programPremise': program,
            'dataPremise': 'Unknown', 'selectionEvidence': 'Unknown', 'accesses': [], **changes}


def attribution_cases():
    operation = 'mcu_candidate_attribution'
    for name, ecu, pcb, marking, catalog, source, promotion in (
        ('a01-photo', 'P28-A01', '1720', 'M66207-251', 'MSM66207', 'EbayA01Photo', 'None'),
        ('a02-photo', 'P28-A02', '11F0', 'M66207-304', 'MSM66207', 'DGTuneA02Photo', 'None'),
        ('a01-wrong-board', 'P28-A01', '11F0', 'M66207-251', 'Unknown', 'EbayA01Photo', 'None'),
        ('drawing', 'P28-A51', '1720', 'MSM66207-251', 'MSM66207', 'BomarcSchematic', 'None'),
        ('251-shop', 'P28-A51', 'Unknown', 'M66207-251', 'Unknown', 'HALoggedList', 'None'),
        ('304-shop', 'P28-A52', 'Unknown', 'M66207-304', 'Unknown', 'HALoggedList', 'None'),
        ('nonexclusive', 'P28-A01', 'Unknown', 'M66207-304', 'Unknown', 'HALoggedList', 'None'),
        ('unknown', 'Unknown', 'Unknown', 'Unknown', 'Unknown', 'Unknown', 'None'),
        ('photo-to-unit', 'P28-A02', '11F0', 'M66207-304', 'MSM66207', 'DGTuneA02Photo', 'SameUnitIdentity'),
        ('unsupported-alias', 'P28-A02', '11F0', 'M66207-304', 'MSM66207', 'DGTuneA02Photo',
         'ManufacturerAlias'),
        ('code-to-revision', 'P28-A01', '1720', 'M66207-251', 'MSM66207', 'EbayA01Photo', 'SiliconRevision'),
        ('code-to-c8', 'P28-A02', '11F0', 'M66207-304', 'MSM66207', 'DGTuneA02Photo', 'C8Semantics'),
        ('alternative-candidate', 'P28-A01', '1720', 'M66207-251', 'MSM66201', 'EbayA01Photo', 'None'),
    ):
        yield _case(operation, 'attribution-' + name, {
            'ecuCandidate': ecu, 'pcbCandidate': pcb, 'literalMarking': marking,
            'catalogMcuCandidate': catalog, 'sourceId': source, 'requestedPromotion': promotion,
        })


def memory_cases():
    operation = 'memory_architecture_compatibility'
    for ecu, mcu, premise in product(ECUS, MCUS, PROGRAM):
        yield _case(operation, f'memory-base-{ecu}-{mcu}-{premise}', memory_query(ecu, mcu, premise))
    spans = [
        {'space': space, 'address': address, 'widthBytes': width}
        for space, address, width in (
            ('DATA', 0x007F, 2), ('DATA', 0x00BF, 2), ('DATA', 0x027F, 2), ('DATA', 0x047F, 2),
            ('DATA', 0x047E, 2), ('DATA', 0x03F0, 1), ('PROGRAM', 0x047F, 1),
            ('PROGRAM', 0x3FFF, 2), ('PROGRAM', 0x7FFF, 2), ('PROGRAM', 0x54EA, 1),
        )
    ]
    for name, mcu, premise, data, selection in (
        ('201-socket', 'MSM66201', 'InternalOnly32K', 'StandardMap', 'SocketVisible'),
        ('207-drawing', 'MSM66207', 'InternalOnly32K', 'StandardMap', 'SchematicOnly'),
        ('otp-external', 'MSM66P201', 'ExternalProgramSupported', 'ExternalDataDocumented', 'HypotheticalEaLow'),
        ('selector-conflict', 'MSM66207', 'InternalOnly32K', 'Unknown', 'HypotheticalEaLow'),
        ('spaces-unknown', 'MSM66P207', 'Unknown', 'Unknown', 'Unknown'),
    ):
        yield _case(operation, 'memory-' + name, memory_query('Unknown', mcu, premise, dataPremise=data,
                    selectionEvidence=selection, accesses=spans))


def isa_cases():
    code_query = {'inputClass': 'SyntheticTestInput', 'literalMarking': 'M66207-251', 'catalogPart': 'MSM66207',
                  'customerCode': '251', 'siliconRevision': None, 'sourceIds': list(ISA_SOURCES),
                  'claim': 'Inspect'}
    for name, changes in (
        ('251-notation', {}),
        ('304-notation', {'literalMarking': 'M66207-304', 'customerCode': '304'}),
        ('numeric-mismatch', {'customerCode': '304'}),
        ('unknown-part', {'catalogPart': None, 'literalMarking': None, 'customerCode': None}),
        ('otp', {'catalogPart': 'MSM66P207', 'literalMarking': None, 'customerCode': None}),
        ('early-only', {'sourceIds': ['OkiNov1990_207DeviceSpec']}),
        ('locator-only', {'sourceIds': ['SearchIndexOnly']}),
        ('alias-promotion', {'claim': 'ResolveAlias'}),
        ('meaning-promotion', {'claim': 'DecodeCustomerCode'}),
        ('stepping-promotion', {'claim': 'PromoteRevision', 'siliconRevision': 'InventedRevision'}),
    ):
        yield _case('customer_code_applicability', 'code-' + name, {**code_query, **changes})
    for name, changes in (
        ('combined', {}),
        ('printed-and-mirror', {'catalogPart': 'MSM66201', 'sourceIds': [
            'Oki1991C8SameEditionMirror', 'Oki1991C8Instruction', 'Oki1991C8Instruction']}),
        ('wrong-family', {'sourceIds': ['Oki1999Nx8500S']}),
        ('wrong-opcode', {'opcode': 0xF0, 'sourceIds': ['Oki1999Nx8500S', 'Oki1991C8Instruction']}),
        ('201-with-207-only', {'catalogPart': 'MSM66201', 'sourceIds': ['OkiNov1990_207DeviceSpec']}),
        ('early-207', {'sourceIds': ['OkiNov1990_207DeviceSpec']}),
        ('early-otp', {'catalogPart': 'MSM66P207', 'sourceIds': ['OkiNov1990_207DeviceSpec']}),
        ('unverified-stepping', {'siliconRevision': 'InventedRevision'}),
        ('unbound-part', {'catalogPart': None, 'sourceIds': ['Oki1991C8Instruction']}),
        ('emulator', {'sourceIds': ['EmulatorBehavior']}),
        ('force-or', {'claim': 'ResolveOr'}),
        ('force-and', {'claim': 'ResolveAnd'}),
        ('force-target', {'claim': 'BindTarget', 'customerCode': '304'}),
    ):
        yield _case('c8_revision_evidence', 'isa-' + name, isa_query(**changes))


def cases():
    for name, query in (
        ('archive', custody()),
        ('extraction', custody(claim='OriginalPhysicalExtraction')),
        ('photo-is-not-donor', custody((*ARCHIVE, 'A01Photo', 'A02Photo'), claim='StudiedDonor')),
        ('hash-is-not-factory', custody(claim='FactoryOriginality')),
        ('upload-is-not-extraction', custody(claim='PhysicalExtractionDate')),
        ('mismatch', custody(binding='ByteIdentityMismatch')),
        ('filename', custody(binding='FilenameOnly')),
        ('unbound', custody(('ArchiveImport', 'HistoricalAttachment'))),
        ('same-hash-origins', custody(('M1aAcquisition', 'ArchiveImport', 'ArchiveDedup'), claim='WitnessComparison')),
        ('different-subjects', custody(('A02Photo', 'A01Photo', 'HALoggedList'), claim='WitnessComparison')),
        ('invented-agreement', custody(('FixtureSameUnitA', 'FixtureIndependentAgreement',
                                        'FixtureSameUnitMirror'), claim='WitnessComparison')),
        ('invented-conflict', custody(('FixtureSameUnitA', 'FixtureSameUnitB',
                                       'FixtureSameUnitMirror'), claim='WitnessComparison')),
        ('invented-promotion', custody(('FixtureSameUnitA', 'FixtureIndependentAgreement'), claim='StudiedDonor')),
    ):
        yield _case('rom_to_hardware_provenance', 'custody-' + name, query)
    yield from attribution_cases()
    yield from memory_cases()
    yield from isa_cases()
    for name, claim, selected in (
        ('independent-axes', 'Inspect', custody()),
        ('no-extraction', 'AssertTargetRule', custody(claim='OriginalPhysicalExtraction')),
        ('filename-unbound', 'Inspect', custody(binding='FilenameOnly')),
        ('execution-refused', 'AuthorizeExecution', custody()),
    ):
        yield _case('target_c8_applicability', 'junction-' + name,
                    {'custody': selected, 'isa': isa_query(), 'claim': claim})
