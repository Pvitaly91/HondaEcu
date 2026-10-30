"""Standard-device configuration premises; never a physical identity detector."""
ECUS = ('P28-A01', 'P28-A51', 'P28-A02', 'P28-A52', 'Unknown')
MCUS = ('MSM66201', 'MSM66207', 'MSM66P201', 'MSM66P207')
CONFIGURATIONS = ('InternalOnly32K', 'ExternalProgramSupported', 'Unknown')


def classify(ecu, mcu, configuration):
    if (type(ecu) is not str or ecu not in ECUS or type(mcu) is not str or mcu not in MCUS
            or type(configuration) is not str or configuration not in CONFIGURATIONS):
        raise ValueError('ClosedTypedCandidateAndConfigurationRequired')
    is201 = mcu in ('MSM66201', 'MSM66P201')
    if configuration == 'Unknown':
        status, basis = 'Unknown', 'ActualProgramSelectionAndBoardDecodeUnknown'
    elif configuration == 'InternalOnly32K' and is201:
        status, basis = 'ConflictsWithStatedStandardPremise', '32KiBInternalOnlyPremiseExceedsStandard16KiBCapacity'
    else:
        status = 'ConditionallyCompatible'
        basis = ('StandardExternalProgramExists_BoardSelectionUnestablished'
                 if configuration == 'ExternalProgramSupported'
                 else 'Standard32KiBCapacityFits_NoActualProgramSelectionProof')
    return {'ecuCandidate': ecu, 'mcuCandidate': mcu, 'memoryConfiguration': configuration,
            'status': status, 'basis': basis, 'studiedPayloadBytes': 32768,
            'standardInternalProgramBytes': 16384 if is201 else 32768,
            'standardTotalInternalDataBytes': 512 if is201 else 1024,
            'externalProgramDocumented': True,
            'otpQualification': ('PairedNominalCounterpart_NotProgrammingModeProof'
                                 if mcu.startswith('MSM66P') else 'NotOtpCandidate'),
            'actualEcuRuledOut': False, 'physicalUnitBound': False,
            'actualSiliconConfirmed': False, 'peripheralApplicability': 'Unestablished',
            'executionAdmission': False, 'firmwareReady': False}
