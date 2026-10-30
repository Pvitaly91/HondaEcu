"""Independent standard-device address expectations, never physical ECU observations.

Derived from the reviewed Japanese Y3 specification page17, with source-specific
PSW and hardware identity obligations retained independently of an analysis model.
No model or production CPU import belongs in this file.
"""
from copy import deepcopy


MODELS = ('MSM66201', 'MSM66207', 'MSM66P201', 'MSM66P207')
SELECTED_ADDRESSES = (
    0x0000, 0x000A, 0x0018, 0x001B, 0x0054, 0x0055, 0x0056, 0x007F,
    0x0080, 0x00BF, 0x00C0, 0x00FF, 0x0100, 0x0213, 0x0262, 0x0269,
    0x027F, 0x0280, 0x029C, 0x03F0, 0x03F3, 0x03F7, 0x047E, 0x047F,
    0x0480, 0x3E81, 0x3F14, 0x3F28, 0x3FFF, 0x4000, 0x54EA, 0x54F0,
    0x7FFF, 0x8000, 0xFFFF,
)


def expected_address(model, space, address):
    """Manufacturer standard-map reference; no unknowns become actual ownership."""
    if (type(model) is not str or model not in MODELS
            or type(space) is not str or space not in ('PROGRAM', 'DATA')
            or type(address) is not int or not 0 <= address <= 0xFFFF):
        raise ValueError('ExplicitStandardModelSpaceAnd16BitAddressRequired')
    small = model in ('MSM66201', 'MSM66P201')
    if space == 'PROGRAM':
        boundary = 0x4000 if small else 0x8000
        region = ('InternalProgram16K' if small else 'InternalProgram32K') if address < boundary else 'ExternalProgram_BoardMappingUnknown'
    else:
        if address <= 0x007F:
            region = 'SFRNamespace_ImplementedHolesUnknown'
        elif address <= 0x00BF:
            region = 'InternalRam_PointingBankAlias'
        elif address <= 0x00FF:
            region = 'InternalRam_ZeroPage'
        elif address <= (0x027F if small else 0x047F):
            region = 'InternalRam_Paged'
        else:
            region = 'ExternalData_BoardMappingUnknown'
    return {'model': model, 'space': space, 'address': address,
            'documentedRegion': region, 'actualMappingVerified': False,
            'sourceId': 'JapaneseY3', 'sourcePage': 17}


def expected_address_inventory():
    return [expected_address(model, space, address)
            for model in MODELS for space in ('PROGRAM', 'DATA') for address in SELECTED_ADDRESSES]


# Shared reviewed documentary inputs, frozen before the analysis model was called.
# This literal is not loaded from contract.json or produced by model output.
_FROZEN_SPEC = {'candidates': [{'candidate': 'MSM66201',
                 'counterpartOf': None,
                 'architecture': 'OKI nX-8/200',
                 'programAddressSpaceBytes': 65536,
                 'dataAddressSpaceBytes': 65536,
                 'programAndDataSeparate': True,
                 'nominalInternalProgramBytes': 16384,
                 'nominalInternalDataRamBytes': 512,
                 'internalProgramRangeInclusive': ['0000', '3FFF'],
                 'totalInternalRamRangeInclusive': ['0080', '027F'],
                 'sfrRangeInclusive': ['0000', '007F'],
                 'pointingRamRangeInclusive': ['0080', '00BF'],
                 'otherZeroPageRamRangeInclusive': ['00C0', '00FF'],
                 'pagedRamStart': '0100',
                 'programMemoryKind': 'StandardInternalROM',
                 'packageFormsActuallyListed': ['SS64ShrinkDIP', 'GS-BK64QFP', 'JS68QFJ_PLCC'],
                 'qfpListed': True,
                 'otpMapQualification': None,
                 'commonFamilyResources': {'timers16Bit': 4,
                                           'serialChannels': 1,
                                           'serialModes': ['Synchronous', 'UART'],
                                           'serialBaudRateGenerators': True,
                                           'pwm16BitChannels': 2,
                                           'adcBits': 10,
                                           'adcChannels': 8,
                                           'transitionDetectors': 4,
                                           'watchdogPresent': True,
                                           'nonmaskableExternalInterrupts': 1,
                                           'maskableInternalFactors': 16,
                                           'maskableExternalFactors': 2},
                 'sourceRefs': [{'sourceId': 'JapaneseY3',
                                 'printedPages': [1, 2, 3, 17],
                                 'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
                 'confidence': 'HighForNamedStandardDeviceInventory_ConditionalForActualSilicon',
                 'actualEcuLinkEstablished': False,
                 'actualPackageMarking': None,
                 'actualMaskOrRevision': None},
                {'candidate': 'MSM66207',
                 'counterpartOf': None,
                 'architecture': 'OKI nX-8/200',
                 'programAddressSpaceBytes': 65536,
                 'dataAddressSpaceBytes': 65536,
                 'programAndDataSeparate': True,
                 'nominalInternalProgramBytes': 32768,
                 'nominalInternalDataRamBytes': 1024,
                 'internalProgramRangeInclusive': ['0000', '7FFF'],
                 'totalInternalRamRangeInclusive': ['0080', '047F'],
                 'sfrRangeInclusive': ['0000', '007F'],
                 'pointingRamRangeInclusive': ['0080', '00BF'],
                 'otherZeroPageRamRangeInclusive': ['00C0', '00FF'],
                 'pagedRamStart': '0100',
                 'programMemoryKind': 'StandardInternalROM',
                 'packageFormsActuallyListed': ['SS64ShrinkDIP', 'GS-BK64QFP', 'JS68QFJ_PLCC'],
                 'qfpListed': True,
                 'otpMapQualification': None,
                 'commonFamilyResources': {'timers16Bit': 4,
                                           'serialChannels': 1,
                                           'serialModes': ['Synchronous', 'UART'],
                                           'serialBaudRateGenerators': True,
                                           'pwm16BitChannels': 2,
                                           'adcBits': 10,
                                           'adcChannels': 8,
                                           'transitionDetectors': 4,
                                           'watchdogPresent': True,
                                           'nonmaskableExternalInterrupts': 1,
                                           'maskableInternalFactors': 16,
                                           'maskableExternalFactors': 2},
                 'sourceRefs': [{'sourceId': 'JapaneseY3',
                                 'printedPages': [1, 2, 3, 17],
                                 'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
                 'confidence': 'HighForNamedStandardDeviceInventory_ConditionalForActualSilicon',
                 'actualEcuLinkEstablished': False,
                 'actualPackageMarking': None,
                 'actualMaskOrRevision': None},
                {'candidate': 'MSM66P201',
                 'counterpartOf': 'MSM66201',
                 'architecture': 'OKI nX-8/200',
                 'programAddressSpaceBytes': 65536,
                 'dataAddressSpaceBytes': 65536,
                 'programAndDataSeparate': True,
                 'nominalInternalProgramBytes': 16384,
                 'nominalInternalDataRamBytes': 512,
                 'internalProgramRangeInclusive': ['0000', '3FFF'],
                 'totalInternalRamRangeInclusive': ['0080', '027F'],
                 'sfrRangeInclusive': ['0000', '007F'],
                 'pointingRamRangeInclusive': ['0080', '00BF'],
                 'otherZeroPageRamRangeInclusive': ['00C0', '00FF'],
                 'pagedRamStart': '0100',
                 'programMemoryKind': 'OneTimePROMCounterpart',
                 'packageFormsActuallyListed': ['SS64ShrinkDIP', 'JS68QFJ_PLCC'],
                 'qfpListed': False,
                 'otpMapQualification': 'Nominal paired-device correspondence from page1; no '
                                        'standalone OTP programming-mode map/voltages or actual '
                                        'programmed part established',
                 'commonFamilyResources': {'timers16Bit': 4,
                                           'serialChannels': 1,
                                           'serialModes': ['Synchronous', 'UART'],
                                           'serialBaudRateGenerators': True,
                                           'pwm16BitChannels': 2,
                                           'adcBits': 10,
                                           'adcChannels': 8,
                                           'transitionDetectors': 4,
                                           'watchdogPresent': True,
                                           'nonmaskableExternalInterrupts': 1,
                                           'maskableInternalFactors': 16,
                                           'maskableExternalFactors': 2},
                 'sourceRefs': [{'sourceId': 'JapaneseY3',
                                 'printedPages': [1, 2, 3, 17],
                                 'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
                 'confidence': 'HighForNamedStandardDeviceInventory_ConditionalForActualSilicon',
                 'actualEcuLinkEstablished': False,
                 'actualPackageMarking': None,
                 'actualMaskOrRevision': None},
                {'candidate': 'MSM66P207',
                 'counterpartOf': 'MSM66207',
                 'architecture': 'OKI nX-8/200',
                 'programAddressSpaceBytes': 65536,
                 'dataAddressSpaceBytes': 65536,
                 'programAndDataSeparate': True,
                 'nominalInternalProgramBytes': 32768,
                 'nominalInternalDataRamBytes': 1024,
                 'internalProgramRangeInclusive': ['0000', '7FFF'],
                 'totalInternalRamRangeInclusive': ['0080', '047F'],
                 'sfrRangeInclusive': ['0000', '007F'],
                 'pointingRamRangeInclusive': ['0080', '00BF'],
                 'otherZeroPageRamRangeInclusive': ['00C0', '00FF'],
                 'pagedRamStart': '0100',
                 'programMemoryKind': 'OneTimePROMCounterpart',
                 'packageFormsActuallyListed': ['SS64ShrinkDIP', 'JS68QFJ_PLCC'],
                 'qfpListed': False,
                 'otpMapQualification': 'Nominal paired-device correspondence from page1; no '
                                        'standalone OTP programming-mode map/voltages or actual '
                                        'programmed part established',
                 'commonFamilyResources': {'timers16Bit': 4,
                                           'serialChannels': 1,
                                           'serialModes': ['Synchronous', 'UART'],
                                           'serialBaudRateGenerators': True,
                                           'pwm16BitChannels': 2,
                                           'adcBits': 10,
                                           'adcChannels': 8,
                                           'transitionDetectors': 4,
                                           'watchdogPresent': True,
                                           'nonmaskableExternalInterrupts': 1,
                                           'maskableInternalFactors': 16,
                                           'maskableExternalFactors': 2},
                 'sourceRefs': [{'sourceId': 'JapaneseY3',
                                 'printedPages': [1, 2, 3, 17],
                                 'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
                 'confidence': 'HighForNamedStandardDeviceInventory_ConditionalForActualSilicon',
                 'actualEcuLinkEstablished': False,
                 'actualPackageMarking': None,
                 'actualMaskOrRevision': None}],
 'matrix': [{'claimId': 'MFR-standard-total-ram-includes-pr',
             'component': 'StandardMcuDocumentation',
             'statement': 'Total internal RAM begins0080, including64-byte pointing '
                          'area0080..00BF; it does not begin0100.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '26-27',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-parser-bank-candidate-difference',
             'component': 'StandardMcuDocumentation',
             'statement': 'DATA03F0..03F7 lies inside standard207 internal RAM and outside '
                          'standard201 internal RAM; on201 it is in external DATA region, so not '
                          'intrinsically impossible.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '26-27',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-stack047e-candidate-difference',
             'component': 'StandardMcuDocumentation',
             'statement': 'DATA047E/047F lies in standard207 internal RAM but external201 DATA; '
                          'nominal inclusion does not establish actual SSP ownership, writable '
                          'frame, stack capacity or alias safety.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-rom-size-not-chip-identity',
             'component': 'StandardMcuDocumentation',
             'statement': 'A32768-byte dump is not proof of207 silicon;201 has a separate64KiB '
                          'PROGRAM space with external program access. Actual EA wiring and board '
                          'decode remain unknown.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '1,7-8,17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-external-bus',
             'component': 'StandardMcuDocumentation',
             'statement': 'AD0..7/P0 multiplex lower address/data, A8..15/P1 upper address; ALE '
                          'latches lower address; PSEN PROGRAM reads, RD/WR DATA reads/writes; EA '
                          'low selects external PROGRAM access mode. Actual board wiring '
                          'unobserved.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '3-8/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-package-not-otp-everywhere',
             'component': 'StandardMcuDocumentation',
             'statement': 'SS andJS forms are listed for allfour;64-pinQFP GS-BK only '
                          'standard66201/66207, not66P201/66P207. xxx denotes code number; it is '
                          'not a documented Honda alias or evidence of peripheral '
                          'modifications.66G207VS piggyback is engineering-sample-only.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '2/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'EnglishY4',
                             'locator': '2/30',
                             'sourceHash': 'fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-standard-vectors-not-custom-proof',
             'component': 'StandardMcuDocumentation',
             'statement': 'ISA table1-1 applies only to standardMSM66201. Its note expressly '
                          'permits customer-specific internal I/O and changed vector allocation '
                          'while CPU remains unchanged, including excess vectors afterVCAL. This '
                          'permits a hypothesis, not proof that Honda used such a variant.',
             'sourceRefs': [{'sourceId': 'ISA1991',
                             'locator': '1-5',
                             'sourceHash': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-standard-spaces-tables',
             'component': 'StandardMcuDocumentation',
             'statement': 'Vector table PROGRAM0000..0027,VCAL0028..0037; these are not '
                          'DATA0000SSP or DATA0018IRQ.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'ISA1991',
                             'locator': '1-5',
                             'sourceHash': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-sfr-irq-serial',
             'component': 'StandardMcuDocumentation',
             'statement': 'Standard IRQ0018/19,IE001A/1B R/W8/16 reset00perbyte;SRCON0054R/W8 '
                          'reset00,SRBUF0055R8 resetundefined,SRSTAT0056R/W8 resetF0. Table '
                          'equality is not actual-chip peripheral applicability or ACK authority.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '10-11/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-reset-register-table',
             'component': 'StandardMcuDocumentation',
             'statement': 'Standard SSPFFFF,ACC0000,PSW readbackC8/0C,LRB '
                          'undefined;WDT0011write-only8 reset00/stopped. These are manufacturer '
                          'reset-domain tables, not actual ECU reset observations or WDT3C '
                          'decoder.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '10/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-clock-voltage',
             'component': 'StandardMcuDocumentation',
             'statement': 'Recommended standard conditions:VDD4.5..5.5V atfOSC<=10MHz,fOSC0..10MHz '
                          'atVDD5V+/-10%,Ta-40..85C;400ns minimum instruction cycle is quoted '
                          'at10MHz, not every instruction latency or retired-count-to-time '
                          'conversion.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '1,18/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-reset-pins-not-history',
             'component': 'StandardMcuDocumentation',
             'statement': 'RES is reset input,RESOUT is high during internal reset and '
                          'software-cleared low,OSC0input/OSC1output clock pins. Specification '
                          'does not establish current waveform/release timing/boot history.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '8/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-register-aliases',
             'component': 'StandardMcuDocumentation',
             'statement': 'Standard16-bitACC/PC/LRB/SSP,pointingX1/X2/DP/USP,SCB2..0;local '
                          'r0low/r1high ofER0 and successivepairs. Standard register inventory is '
                          'not actual retained native context.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '9,17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '26-31',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'MFR-psw-source-attribution-correction',
             'component': 'StandardMcuDocumentation',
             'statement': 'JapaneseY3page9 listsMIEbit8;EnglishY4page9 '
                          'callsbit8MIP;User31Fig3-5labelsMIEbit8 and explicitly says '
                          'bits3,6,7,10,11 nonexistent/readone. PriorM2ck page9MIEbit11 '
                          'attribution is an erroneous historical reading, not modified source '
                          'bytes or a physical silicon difference.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '9/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'EnglishY4',
                             'locator': '9/30',
                             'sourceHash': 'fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '31',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'ManufacturerStandardProperty_NotActualEcuObservation',
             'confidence': 'HighForReviewedStandardSource_ConditionalForActualUnit',
             'rationale': 'Independent complete relevant manufacturer-page review; source identity '
                          'and edition limits retained.',
             'applicability': 'OnlyReviewedNamedStandardDeviceOrExplicitQualifiedBody',
             'alternatives': ['Actual customer or board implementation may differ; no substitution '
                              'without evidence.'],
             'unknownConditions': ['Actual MCU full marking, customer code/revision and '
                                   'board-to-ROM custody link'],
             'neededEvidence': ['Applicable manufacturer/OEM bridge tied to independently '
                                'authenticated actual hardware']},
            {'claimId': 'LOCAL-ECU-001',
             'component': 'StudiedEcuIdentity',
             'statement': 'StudiedEcuIdentity remains unknown for the actual admitted-image donor.',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Baseline acquisition/provenance',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'},
                            {'sourceId': 'ArchiveCatalogue',
                             'locator': 'Code304 association and unknown-origin attachment note',
                             'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b'}],
             'classification': 'UnknownActualHardwareIdentity',
             'confidence': 'ScopeQualified',
             'rationale': 'No donor ECU/case label/PCB/MCU photo or custody record linked to the '
                          'admitted payload was found in this reviewed local scope.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Authenticated donor ECU label and board/chip evidence linked to '
                                'this exact acquired image']},
            {'claimId': 'LOCAL-ECU-002',
             'component': 'CommunityCatalogAssociation',
             'statement': 'P28-A01 / USDM / manual / 1992-1995 Civic EX D16Z SOHC VTEC',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Baseline acquisition/provenance',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'},
                            {'sourceId': 'ArchiveCatalogue',
                             'locator': 'Code304 association and unknown-origin attachment note',
                             'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b'}],
             'classification': 'SecondaryHistoricalCatalogAssertion_NotAuthenticatedDonor',
             'confidence': 'ScopeQualified',
             'rationale': 'M1a source record explicitly labels the attachment unknown origin; '
                          'catalog association is a search locator only.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Independent donor/extraction provenance, not a repeated mirror of '
                                'the same catalog']},
            {'claimId': 'LOCAL-ECU-003',
             'component': 'FullOemPartNumber',
             'statement': 'FullOemPartNumber remains unknown for the actual admitted-image donor.',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Baseline acquisition/provenance',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'},
                            {'sourceId': 'ArchiveCatalogue',
                             'locator': 'Code304 association and unknown-origin attachment note',
                             'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b'}],
             'classification': 'Unknown',
             'confidence': 'ScopeQualified',
             'rationale': 'The short catalog family/revision code is not an observed complete OEM '
                          'part number.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Readable actual ECU full part-number label and relation to this '
                                'ROM source']},
            {'claimId': 'LOCAL-ECU-004',
             'component': 'PcbRevisionMarkingManufacturer',
             'statement': 'PcbRevisionMarkingManufacturer remains unknown for the actual '
                          'admitted-image donor.',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Baseline acquisition/provenance',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'},
                            {'sourceId': 'ArchiveCatalogue',
                             'locator': 'Code304 association and unknown-origin attachment note',
                             'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b'}],
             'classification': 'Unknown',
             'confidence': 'ScopeQualified',
             'rationale': 'No authenticated board/revision/manufacturer marking is supplied by the '
                          'admitted ROM/profile manifests.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Same-donor board top/bottom revision and manufacturing markings '
                                'with provenance']},
            {'claimId': 'LOCAL-ECU-005',
             'component': 'CpuPackageMarkingMask',
             'statement': 'CpuPackageMarkingMask remains unknown for the actual admitted-image '
                          'donor.',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Baseline acquisition/provenance',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'},
                            {'sourceId': 'ArchiveCatalogue',
                             'locator': 'Code304 association and unknown-origin attachment note',
                             'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b'}],
             'classification': 'Unknown',
             'confidence': 'ScopeQualified',
             'rationale': 'ROM byte continuity, compatible instruction decoding and file size do '
                          'not encode a verified observed package/part/mask identity.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Same-board package/pin count and complete chip top marking, '
                                'manufacturer cross-reference and mask applicability']},
            {'claimId': 'LOCAL-ROM-001',
             'component': 'ArchivePayloadSize',
             'statement': '32768',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Acquired archive candidate and size/custody limits',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'}],
             'classification': 'CurrentReadOnlyAuthenticatedFileMetadata',
             'confidence': 'ScopeQualified',
             'rationale': 'Exact admitted source path rehashed against M1b binding and M2bs '
                          'profile/verification; no transformation.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Does not establish internal versus external PROGRAM mapping or '
                                'physical silicon']},
            {'claimId': 'LOCAL-ROM-002',
             'component': 'ArchiveByteContinuity',
             'statement': 'VerifiedWithinPinnedArchive',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Acquired archive candidate and size/custody limits',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'}],
             'classification': 'SourceTransportIdentity_NotFactoryAuthenticity',
             'confidence': 'ScopeQualified',
             'rationale': 'Pinned Git payload/history identity and known local raw SHA remain '
                          'unchanged. Identical mirrors are not independent stock dumps.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Authenticated original donor/extraction/custody relationship']},
            {'claimId': 'LOCAL-ROM-003',
             'component': 'ProgramFileSpan',
             'statement': '[0000,8000)',
             'sourceRefs': [{'sourceId': 'M1aReport',
                             'locator': 'Acquired archive candidate and size/custody limits',
                             'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb'}],
             'classification': 'ConditionalZeroBasedFileMapping',
             'confidence': 'ScopeQualified',
             'rationale': 'The admitted raw profile has exact size32768/header0/no padding or '
                          'truncation, and reviewed listings use zero-based PROGRAM addresses.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Actual EA/bus/ROM selection, physical storage and any '
                                'overlay/banking must be separately established']},
            {'claimId': 'LOCAL-ROM-004',
             'component': 'Checksum',
             'statement': 'Byte sum modulo256 residue0',
             'sourceRefs': [{'sourceId': 'M1fReport',
                             'locator': 'Scoped checksum algorithm and limitations',
                             'sourceHash': 'a33caeabd184544b74686110da3a935a91d2dda72e97e60d8f8989c4fbfb5639'}],
             'classification': 'StaticCurrentArithmeticAndInheritedM1fSoftwareContract',
             'confidence': 'ScopeQualified',
             'rationale': 'M1f contract reads every byte ascending through512 blocks, each64bytes, '
                          'fixed residue0; current read-only byte sum independently0. No new '
                          'native runtime occurred.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Not a universal P28 algorithm, factory authentication, separate '
                                'stored checksum field, or physical boot proof']},
            {'claimId': 'LOCAL-MAP-001',
             'component': 'StandardDataRamDiscriminant',
             'statement': '201:0080..027F;207:0080..047F',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'M2arReport',
                             'locator': 'Primary documents and applicability',
                             'sourceHash': 'adad751978bb60883d9874f83587bd3f12509b30bcc78fa5dfa854ce3a654036'}],
             'classification': 'StandardManufacturerMapComparison_PendingParentFreshPrimaryBinding',
             'confidence': 'ScopeQualified',
             'rationale': 'PR0080..00BF is inside total internalRAM. DATA03F3/SSP047E fit '
                          'standard207 internalRAM but require external/custom mapping on '
                          'standard201.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Exact actual MCU and board memory map; software addresses alone '
                                'cannot select207 or exclude201+externalRAM']},
            {'claimId': 'LOCAL-MAP-002',
             'component': 'StandardProgramDiscriminant',
             'statement': '201 internal0000..3FFF;207 internal0000..7FFF',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'M2arReport',
                             'locator': 'Primary documents and applicability',
                             'sourceHash': 'adad751978bb60883d9874f83587bd3f12509b30bcc78fa5dfa854ce3a654036'}],
             'classification': 'StandardManufacturerMapComparison_PendingParentFreshPrimaryBinding',
             'confidence': 'ScopeQualified',
             'rationale': 'Reviewed PROGRAM54EA/54F0 and32K image exceed201 internal16K but '
                          'standard external PROGRAM is allowed; file size cannot distinguish '
                          'internal32K from external32K.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Actual ROM source selection/address decode, EA strap and board '
                                'mapping']},
            {'claimId': 'LOCAL-MAP-003',
             'component': 'DataParserBank',
             'statement': '03F0..03F7',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'M2cjReport',
                             'locator': 'One frame and Flag path',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'ConditionalStaticBankAddress_NotActualPhysicalRamOwner',
             'confidence': 'ScopeQualified',
             'rationale': 'Inherited handler LRB007E maps this local bank under documented CPU '
                          'semantics; actual current LRB/context and physical RAM remain unknown.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Applicable silicon/register banking plus actual retained LRB/SCB '
                                'and byte-generation owners']},
            {'claimId': 'LOCAL-MAP-004',
             'component': 'IrqVectorLink',
             'statement': 'PROGRAM000A ->0213',
             'sourceRefs': [{'sourceId': 'M2ciReport',
                             'locator': 'Source-bound PROGRAM000A target and applicability',
                             'sourceHash': '32c8747e3295bb405fc922332f69b4ed5d61ae7dbbe31df9abc7bbf7c6cce5e0'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '166 Table17-1',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'InheritedSourceBoundVector_NotActualIrq',
             'confidence': 'ScopeQualified',
             'rationale': 'Current source identity and M2ci read-only verification retain this '
                          'vector relationship. DATA0018..001B are a different address space.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Actual customer ASIC vector applicability, '
                                'pending/IE/MIE/priority/frame/delivery evidence']},
            {'claimId': 'LOCAL-MAP-005',
             'component': 'PswSourceInterpretation',
             'statement': 'JapaneseY3 MIEbit8; EnglishY4 MIPbit8; User31 MIEbit8 with bit11 '
                          'nonexistent/read1. Historical M2ck bit11 annotation is a '
                          'source-attribution error, not a silicon revision discovery.',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '9/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'EnglishY4',
                             'locator': '9/30',
                             'sourceHash': 'fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '31 Figure3-5',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'SourceSpecificAttributionCorrection_HistoricalFilesFrozen',
             'confidence': 'ScopeQualified',
             'rationale': 'Fresh enlarged independent complete-page rereads resolved the earlier '
                          'low-resolution misread without changing source bytes.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Exact source/page-specific PSW fields and independent '
                                'applicability/revision evidence']},
            {'claimId': 'LOCAL-CTX-001',
             'component': 'HistoricalBoundedExecution',
             'statement': 'Software-only technical/history source observations',
             'sourceRefs': [{'sourceId': 'M2awReport',
                             'locator': 'Source-owned context versus software-only observations',
                             'sourceHash': '122bbb14adcd5718dc3fbb3fefb19dee74a9228099278802254ef6c7d59f8174'}],
             'classification': 'NotPhysicalDonorIdentification',
             'confidence': 'ScopeQualified',
             'rationale': 'M2bt technical seeded execution and M2bu technical caller-to-exit '
                          'traces do not establish ECU package/mask, native scheduler, physical SF '
                          'or stack frame.',
             'applicability': 'LocalAdmittedArchiveCandidate_NotPhysicalEcuUnlessExplicitlyObserved',
             'alternatives': ['A standard-compatible or externally mapped implementation remains '
                              'possible; exact unit unknown.'],
             'unknownConditions': ['Actual donor, hardware custody, revision and live-state '
                                   'ownership'],
             'neededEvidence': ['Separate physical identity and native-owner evidence; M2cl '
                                'executions remain0']},
            {'claimId': 'ADDR-PROGRAM-000A',
             'component': 'PROGRAMAddressRole',
             'statement': '000A: 16-bit RX-ready vector under applicable standard profile; payload '
                          'target0213',
             'sourceRefs': [{'sourceId': 'M2ciReport',
                             'locator': 'PROGRAM000A target/source-allocation distinction',
                             'sourceHash': '32c8747e3295bb405fc922332f69b4ed5d61ae7dbbe31df9abc7bbf7c6cce5e0'},
                            {'sourceId': 'UserIncomplete',
                             'locator': '166 Table17-1',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-0213',
             'component': 'PROGRAMAddressRole',
             'statement': '0213: Static conditional handler entry',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-0262',
             'component': 'PROGRAMAddressRole',
             'statement': '0262: Static LB DATA0055 toAL; readACK unknown',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-0264',
             'component': 'PROGRAMAddressRole',
             'statement': '0264: CMPB r5,#2, not receivedF',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-0269',
             'component': 'PROGRAMAddressRole',
             'statement': '0269: Static STB AL tolocalr3/DATA03F3; nooddF requirement',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-029C',
             'component': 'PROGRAMAddressRole',
             'statement': '029C: RTI instruction location, not savedforegroundPC',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-DATA-03F0..03F7',
             'component': 'DATAAddressRole',
             'statement': '03F0..03F7: Conditional localparserbank viaLRB007E; '
                          'totalstandard207internalRAM but notstandard201internalRAM',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '10-11,17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'M2cjReport',
                             'locator': 'Conditional register bank and source ownership',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-DATA-0054..0056',
             'component': 'DATAAddressRole',
             'statement': '0054..0056: Standard SRCON/SRBUF/SRSTAT inventory; source-specific '
                          'applicability',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '10-11,17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'M2cjReport',
                             'locator': 'Conditional register bank and source ownership',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-DATA-0018..001B',
             'component': 'DATAAddressRole',
             'statement': '0018..001B: Standard IRQ/IE wordregisters; source-specific '
                          'pending/polarity',
             'sourceRefs': [{'sourceId': 'JapaneseY3',
                             'locator': '10-11,17/30',
                             'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'},
                            {'sourceId': 'M2cjReport',
                             'locator': 'Conditional register bank and source ownership',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-54EA',
             'component': 'PROGRAMAddressRole',
             'statement': '54EA: Static wordIRQclear; pendinggenerationcut conditional',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-54F0',
             'component': 'PROGRAMAddressRole',
             'statement': '54F0: Static IEwriter',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-3F14_3F28',
             'component': 'PROGRAMAddressRole',
             'statement': '3F14/3F28: Alternative staticIEwriters preceding shadowupdates',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'ADDR-PROGRAM-3E81',
             'component': 'PROGRAMAddressRole',
             'statement': '3E81: Static mode/F8/IE/FA consistency checks',
             'sourceRefs': [{'sourceId': 'M2cjReport',
                             'locator': 'Reviewed software receive/mask/Flag relationships',
                             'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60'}],
             'classification': 'StaticSoftwareRoleOrStandardMap_NotPhysicalMapping',
             'confidence': 'HighForReviewedStaticRole_ActualMappingUnknown',
             'rationale': 'PROGRAM and DATA roles are distinct; a code address does not establish '
                          'a physical register.',
             'applicability': 'SourceBoundReviewedSoftwareAndConditionalStandardSemantics',
             'alternatives': ['An actual custom/board mapping may differ; do not infer from '
                              'address coincidence.'],
             'unknownConditions': ['Actual chip, board decode and current register/memory '
                                   'generation'],
             'neededEvidence': ['Authenticated physical mapping plus relevant native ownership '
                                'evidence in a later authorized stage']},
            {'claimId': 'BOARD-LABEL',
             'component': 'UnlinkedBoardIdentity',
             'statement': 'Bomarc drawing associates 37820-P28-A51 with U1 MSM66207-251; it is not '
                          'the P28-A01 archive candidate donor identity.',
             'sourceRefs': [{'sourceId': 'BomarcSchematic',
                             'locator': 'sheet1,3,6',
                             'sourceHash': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5'}],
             'classification': 'UnlinkedThirdPartyDrawingObservation',
             'confidence': 'ReadableDrawingLabel_NotAuthenticatedStudiedHardware',
             'rationale': 'Pinned original raster drawing was reviewed; no same-donor '
                          'ROM/case/board link exists.',
             'applicability': 'OnlyTheDrawingReferenceBoardAndItsAnnotations',
             'alternatives': ['Other ECU/PCB/program-code/population variants remain distinct.'],
             'unknownConditions': ['Whether drawing hardware matches the studied image donor'],
             'neededEvidence': ['Authenticated same-unit ECU/PCB/CPU/photos and extraction '
                                'linkage, plus manufacturer revision bridge']},
            {'claimId': 'BOARD-MARKING',
             'component': 'UnlinkedBoardPcb',
             'statement': 'Raster source sheet8 reads 02D01720-1500 A8Y-D; secondary narrative '
                          'differences are not substituted for source.',
             'sourceRefs': [{'sourceId': 'BomarcSchematic',
                             'locator': 'sheet8',
                             'sourceHash': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5'}],
             'classification': 'UnlinkedThirdPartyDrawingObservation',
             'confidence': 'ReadableDrawingLabel_NotAuthenticatedStudiedHardware',
             'rationale': 'Pinned original raster drawing was reviewed; no same-donor '
                          'ROM/case/board link exists.',
             'applicability': 'OnlyTheDrawingReferenceBoardAndItsAnnotations',
             'alternatives': ['Other ECU/PCB/program-code/population variants remain distinct.'],
             'unknownConditions': ['Whether drawing hardware matches the studied image donor'],
             'neededEvidence': ['Authenticated same-unit ECU/PCB/CPU/photos and extraction '
                                'linkage, plus manufacturer revision bridge']},
            {'claimId': 'BOARD-ASIC',
             'component': 'SeparateBoardComponents',
             'statement': 'Separate U7 MSM7UC16-005 ASIC and U2 MSM6434-13 do not prove custom '
                          'internal peripherals in U1 MSM66207.',
             'sourceRefs': [{'sourceId': 'BomarcSchematic',
                             'locator': 'sheet6',
                             'sourceHash': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5'}],
             'classification': 'UnlinkedThirdPartyDrawingObservation',
             'confidence': 'ReadableDrawingLabel_NotAuthenticatedStudiedHardware',
             'rationale': 'Pinned original raster drawing was reviewed; no same-donor '
                          'ROM/case/board link exists.',
             'applicability': 'OnlyTheDrawingReferenceBoardAndItsAnnotations',
             'alternatives': ['Other ECU/PCB/program-code/population variants remain distinct.'],
             'unknownConditions': ['Whether drawing hardware matches the studied image donor'],
             'neededEvidence': ['Authenticated same-unit ECU/PCB/CPU/photos and extraction '
                                'linkage, plus manufacturer revision bridge']},
            {'claimId': 'BOARD-EXTERNAL',
             'component': 'UnlinkedExternalProgramOptions',
             'statement': 'U3 option/annotation including MSM27256 and Demon2 does not establish '
                          'actual external ROM population, EA strap, banking or decode.',
             'sourceRefs': [{'sourceId': 'BomarcSchematic',
                             'locator': 'sheet6',
                             'sourceHash': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5'}],
             'classification': 'UnlinkedThirdPartyDrawingObservation',
             'confidence': 'ReadableDrawingLabel_NotAuthenticatedStudiedHardware',
             'rationale': 'Pinned original raster drawing was reviewed; no same-donor '
                          'ROM/case/board link exists.',
             'applicability': 'OnlyTheDrawingReferenceBoardAndItsAnnotations',
             'alternatives': ['Other ECU/PCB/program-code/population variants remain distinct.'],
             'unknownConditions': ['Whether drawing hardware matches the studied image donor'],
             'neededEvidence': ['Authenticated same-unit ECU/PCB/CPU/photos and extraction '
                                'linkage, plus manufacturer revision bridge']},
            {'claimId': 'BOARD-SERIAL',
             'component': 'UnlinkedSerialConnections',
             'statement': 'Drawing U1 TxDpin38/RxDpin39 connections are third-party board '
                          'observations, not verified current serial ownership or actual wiring.',
             'sourceRefs': [{'sourceId': 'BomarcSchematic',
                             'locator': 'sheet5',
                             'sourceHash': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5'}],
             'classification': 'UnlinkedThirdPartyDrawingObservation',
             'confidence': 'ReadableDrawingLabel_NotAuthenticatedStudiedHardware',
             'rationale': 'Pinned original raster drawing was reviewed; no same-donor '
                          'ROM/case/board link exists.',
             'applicability': 'OnlyTheDrawingReferenceBoardAndItsAnnotations',
             'alternatives': ['Other ECU/PCB/program-code/population variants remain distinct.'],
             'unknownConditions': ['Whether drawing hardware matches the studied image donor'],
             'neededEvidence': ['Authenticated same-unit ECU/PCB/CPU/photos and extraction '
                                'linkage, plus manufacturer revision bridge']},
            {'claimId': 'RET-IE',
             'component': 'InterruptEnablePolarity',
             'statement': 'IE165/168/169 favors set1; literal167 acceptance-condition set0 '
                          'conflict remains unresolved.',
             'sourceRefs': [{'sourceId': 'UserIncomplete',
                             'locator': '165-169',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'},
                            {'sourceId': 'M2ckReport',
                             'locator': 'Acknowledgement/reassertion source limits',
                             'sourceHash': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e'}],
             'classification': 'RetainedUnknownOrSourceConflict_NotResolvedByStandardTable',
             'confidence': 'ConfirmedLimitOfAcquiredEvidence_NotProofOfEitherHardwareHypothesis',
             'rationale': 'No newly applicable ACK/erratum source or actual silicon bridge '
                          'resolves the prior frontier.',
             'applicability': 'QualifiedIncompleteUserBody_ActualEcuUnknown',
             'alternatives': ['Both unsupported read-side-effect hypotheses and both IE polarity '
                              'hypotheses remain explicit.'],
             'unknownConditions': ['Applicable complete receive/interrupt rules and actual device '
                                   'revision'],
             'neededEvidence': ['Authenticated applicable receive-operation section and '
                                'independent IE erratum/edition evidence']},
            {'claimId': 'RET-ACK',
             'component': 'ReceiveAcknowledgement',
             'statement': 'SRBUF read-clear versus no-side-effect, automatic reassertion and '
                          'set/clear collision priorities remain unknown.',
             'sourceRefs': [{'sourceId': 'UserIncomplete',
                             'locator': '126-131,164-169',
                             'sourceHash': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'},
                            {'sourceId': 'M2ckReport',
                             'locator': 'Acknowledgement/reassertion source limits',
                             'sourceHash': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e'}],
             'classification': 'RetainedUnknownOrSourceConflict_NotResolvedByStandardTable',
             'confidence': 'ConfirmedLimitOfAcquiredEvidence_NotProofOfEitherHardwareHypothesis',
             'rationale': 'No newly applicable ACK/erratum source or actual silicon bridge '
                          'resolves the prior frontier.',
             'applicability': 'QualifiedIncompleteUserBody_ActualEcuUnknown',
             'alternatives': ['Both unsupported read-side-effect hypotheses and both IE polarity '
                              'hypotheses remain explicit.'],
             'unknownConditions': ['Applicable complete receive/interrupt rules and actual device '
                                   'revision'],
             'neededEvidence': ['Authenticated applicable receive-operation section and '
                                'independent IE erratum/edition evidence']}],
 'graph': {'nodes': [{'id': 'actual_unit',
                      'component': 'Actual ECU unit',
                      'status': 'ActualOwnerMissing',
                      'requires': [],
                      'neededEvidence': ['Same-unit ECU label, PCB and complete MCU marking '
                                         'evidence'],
                      'actualObservation': None},
                     {'id': 'image_identity',
                      'component': 'Archive image byte continuity',
                      'status': 'ArchiveByteContinuityVerified',
                      'requires': [],
                      'neededEvidence': ['Donor provenance is separately required in rom_custody'],
                      'actualObservation': None},
                     {'id': 'rom_custody',
                      'component': 'ROM source custody',
                      'status': 'ActualOwnerMissing',
                      'requires': ['actual_unit', 'image_identity'],
                      'neededEvidence': ['Authenticated extraction record tying this exact image '
                                         'to the same ECU'],
                      'actualObservation': None},
                     {'id': 'chip_identity',
                      'component': 'Actual MCU/customer identity',
                      'status': 'ActualOwnerMissing',
                      'requires': ['actual_unit'],
                      'neededEvidence': ['Manufacturer/customer-code and package/mask revision '
                                         'bridge'],
                      'actualObservation': None},
                     {'id': 'isa',
                      'component': 'CPU instruction semantics',
                      'status': 'StandardDocumented_ActualApplicabilityMissing',
                      'requires': ['chip_identity'],
                      'neededEvidence': ['Applicable reviewed instruction forms and actual-chip '
                                         'compatibility'],
                      'actualObservation': None},
                     {'id': 'memory',
                      'component': 'RAM/SFR/PROGRAM map',
                      'status': 'StandardDocumented_ActualApplicabilityMissing',
                      'requires': ['chip_identity', 'actual_unit'],
                      'neededEvidence': ['Board decode, EA/memory population and exact chip memory '
                                         'map'],
                      'actualObservation': None},
                     {'id': 'psw',
                      'component': 'Register and PSW context',
                      'status': 'StandardDocumented_ActualOwnerMissing',
                      'requires': ['chip_identity', 'isa'],
                      'neededEvidence': ['Source-specific PSW rules and current retained register '
                                         'owners'],
                      'actualObservation': None},
                     {'id': 'reset',
                      'component': 'Reset and initial PC',
                      'status': 'ActualOwnerMissing',
                      'requires': ['memory', 'psw', 'rom_custody'],
                      'neededEvidence': ['Actual reset cause, waveform, vector source and initial '
                                         'architectural state'],
                      'actualObservation': None},
                     {'id': 'vectors',
                      'component': 'Interrupt vector applicability',
                      'status': 'StandardDocumented_ActualApplicabilityMissing',
                      'requires': ['memory', 'chip_identity', 'rom_custody'],
                      'neededEvidence': ['Applicable customer vector allocation and immutable '
                                         'source link'],
                      'actualObservation': None},
                     {'id': 'frame',
                      'component': 'Stack and entry/return frame',
                      'status': 'ActualOwnerMissing',
                      'requires': ['memory', 'psw'],
                      'neededEvidence': ['Source-owned SSP, safe writable frame, saved words, '
                                         'aliases and nesting'],
                      'actualObservation': None},
                     {'id': 'interrupts',
                      'component': 'IE/MIE/IRQ behavior',
                      'status': 'PrimaryRuleUnknown_SourceConflict',
                      'requires': ['vectors', 'psw', 'frame'],
                      'neededEvidence': ['Pending/enable/priority ownership plus ACK/IE ambiguity '
                                         'resolution'],
                      'actualObservation': None},
                     {'id': 'serial',
                      'component': 'Serial peripheral ownership',
                      'status': 'PrimaryRuleUnknown_ActualOwnerMissing',
                      'requires': ['memory', 'interrupts', 'chip_identity'],
                      'neededEvidence': ['Applicable serial rules, configuration, source '
                                         'byte/event and request generation'],
                      'actualObservation': None},
                     {'id': 'rom_reads',
                      'component': 'PROGRAM read semantics',
                      'status': 'StaticSoftwareBound_ActualMappingMissing',
                      'requires': ['memory', 'rom_custody'],
                      'neededEvidence': ['Verified actual PROGRAM mapping and source-bound '
                                         'read/fetch behavior'],
                      'actualObservation': None},
                     {'id': 'retirement',
                      'component': 'Instruction retirement',
                      'status': 'FutureAuthorizedRuntimeEvidenceRequired',
                      'requires': ['isa', 'psw', 'memory', 'rom_reads'],
                      'neededEvidence': ['Independently authorized bounded execution with actual '
                                         'ordered observations'],
                      'actualObservation': None},
                     {'id': 'foreground',
                      'component': 'Return-to-foreground continuity',
                      'status': 'FutureAuthorizedRuntimeEvidenceRequired',
                      'requires': ['frame', 'retirement', 'interrupts'],
                      'neededEvidence': ['Matching actual saved foreground PC, state and ordered '
                                         'continuation evidence'],
                      'actualObservation': None},
                     {'id': 'execution',
                      'component': 'Future native execution admission',
                      'status': 'EXECUTION_BLOCKED',
                      'requires': ['isa',
                                   'reset',
                                   'psw',
                                   'memory',
                                   'vectors',
                                   'interrupts',
                                   'serial',
                                   'frame',
                                   'retirement',
                                   'rom_reads',
                                   'foreground',
                                   'rom_custody',
                                   'chip_identity'],
                      'neededEvidence': ['All independent prerequisites plus separate explicit '
                                         'runtime-stage authority'],
                      'actualObservation': None}]},
 'metadata': {'byteCount': 32768,
              'staticRawOffsets': [0, 32767],
              'classification': 'ArchiveByteContinuityOnly',
              'actualEcuId': None,
              'actualCpuMarking': None,
              'factoryRevision': None,
              'checksumStatus': 'StaticResidueNotFactoryAuthentication',
              'noOEMPayload': True},
 'authority': {'classification': 'ECU_SILICON_IDENTITY_UNRESOLVED',
               'runtime': 'EXECUTION_BLOCKED',
               'actualEcuId': None,
               'actualCpuMarking': None,
               'firmwareReady': False,
               'newCpuRomIrqRtiExecutions': 0}}

FROZEN_CANONICAL_SHA256 = 'da4bf5b0324be99d27b9edea5a1bbdf26d0d7288b05de1307329ac9c88f0000b'

FROZEN_CANONICAL_BYTES = 110419


def expected_graph():
    return deepcopy(_FROZEN_SPEC['graph'])


def expected_records():
    def add(record_id, record_class, payload):
        return {'recordId': record_id, 'recordClass': record_class, 'payload': deepcopy(payload),
                'actualHardwareObservation': None, 'executionBlocked': True, 'firmwareReady': False}
    rows = [add('candidate-' + r['candidate'], 'CandidateComparison', r)
            for r in _FROZEN_SPEC['candidates']]
    for model in MODELS:
        maps = [expected_address(model, space, address) for space in ('PROGRAM', 'DATA')
                for address in SELECTED_ADDRESSES]
        rows.append(add('map-' + model, 'AddressMapComparison', {'model': model, 'classifications': maps}))
    rows.extend([
        add('evidence-matrix', 'EvidenceMatrix', {'claims': _FROZEN_SPEC['matrix']}),
        add('native-prerequisites', 'NativePrerequisiteGraph', _FROZEN_SPEC['graph']),
        add('rom-metadata', 'RomMetadata', _FROZEN_SPEC['metadata']),
        add('authority', 'Authority', _FROZEN_SPEC['authority']),
    ])
    return rows
