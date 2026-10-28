"""Conditional startup sources, not peripheral emulation or native events.

The new result is a source refinement under the documented standard-device
configuration. No counter, waveform, pending factor or actual read is generated.
"""


def _pwm_control(command):
    """Decode the standard PWMCON fields; bit7 is read-only status, not a seed."""
    clocks = command & 3
    return {
        'command': command, 'clockSelect': clocks,
        'widthBits': (8, 10, 12, 16)[clocks],
        'mode': ('AutoReload', 'FreeRun', 'PWM', 'PWM')[(command >> 2) & 3],
        'run': bool(command & 0x10), 'lowActive': bool(command & 0x20),
        'overflowRequestEnabled': bool(command & 0x40),
        'statusBit7WrittenValueIsObservedOverflow': False,
    }


def gate_analysis():
    """Return deterministic, public-safe obligations for the one cold prefix."""
    writers = (
        (0x25F0, 0x002C, 8, 0xF7),
        (0x25F7, 0x0078, 8, 0x3E),
        (0x25FB, 0x0070, 16, 0xFF00),
        (0x25FD, 0x0072, 16, 0xFF00),
        (0x25FF, 0x007A, 8, 0x7E),
        (0x2603, 0x0074, 16, 0xFF00),
        (0x2605, 0x0076, 16, 0xFF00),
        (0x2607, 0x002D, 8, 0x0D),
        (0x260B, 0x002E, 8, 0xFC),
        (0x261E, 0x0018, 16, 0),
    )
    phases = (
        (0x2623, 0x0177, 0x2626, 0x2627, 0x2629, 0x262C, 0),
        (0x262E, 0x0177, 0x2631, 0x2632, 0x2634, 0x2637, 1),
        (0x2639, 0x00B2, 0x263C, 0x263D, 0x263F, 0x2642, 0),
    )
    return {
        'classification': 'StaticRootedFirstRamtestProvenance_NotCpuExecution',
        'sourceBindings': [
            {'path': 'docs/M2AQ_FIRST_RAMTEST_CAL_RT_PROVENANCE.md',
             'sha256': 'e6fe8af00c39f518e8fd103475baddacecb56159fec5dd5a3472bb90e99b114e'},
            {'path': 'docs/M2AP_SSP_ADC_PENDING_PROVENANCE.md',
             'sha256': '115e4d434ad744cd905b49538b01ca7ea2fd28092762b8be31994db4440e10da'},
            {'path': 'docs/M2AR_RESET_WDT_EXTERNAL4700_PROVENANCE.md',
             'sha256': 'adad751978bb60883d9874f83587bd3f12509b30bcc78fa5dfa854ce3a654036'},
            {'path': 'docs/M2AS_RESET_WDT_CHAPTER4_EVIDENCE.md',
             'sha256': '54ee0d7ade8ba73e0a1e6147594e6bc3433787b61e1cfb2667552fcc5984c2c0'},
        ],
        'inheritedFindings': [
            'M2aq_Exact20FirstCallAndLowHighLowPredicates',
            'M2ap_ConditionalSSP047EAnd510IterationRank',
            'M2ar_DATA4700NumericValueNoninterferenceWithinDomain',
            'M2as_WDT3CMeaningAndHardwareSafeContinuationNotEstablished',
        ],
        'rootWdtAndExternal': {
            'admission': 'Blocked', 'conditionalEntryPC': 0x24ED,
            'wdtPC': 0x24F4, 'wdtAddress': 0x0011, 'wdtCommand': 0x3C,
            'wdtCommandMeaning': 'NotEstablished',
            'hardwareSafeReaching24F8': 'NotEstablished',
            'externalReadPC': 0x251C, 'externalDataAddress': 0x4700,
            'numericNoninterference': 'InheritedM2ar_NotReenumerated',
            'physicalReadCompletion': 'NotEstablished',
            'physicalReadSideEffects': 'NotEstablished',
        },
        'nativeConfiguration': {
            'writers': [{'pc': pc, 'address': address, 'width': width,
                         'command': command,
                         'classification': 'CodeOwnedSoftwareEffect_NotObserved'}
                        for pc, address, width, command in writers],
            'pwm0': _pwm_control(0x3E), 'pwm1': _pwm_control(0x7E),
            'p4io0D': 0x0D, 'p4sfFC': 0xFC,
            'condition': 'ApplicableStandardDevice_AcceptedWrites_RetainedConfiguration',
            'commandsProveActualCounterEvolution': False,
        },
        'earlyP4Gate': {
            'readerPC': 0x2528, 'selectedBit': 1, 'requiredBit': 0,
            'successPC': 0x252E, 'alternativePC': 0x252B,
            'alternativeJumpTarget': 0x003C,
            'source': 'ExternalPinValueBeforePWMConfiguration_NotEstablished',
            'laterPwmConfigurationSuppliesEarlierSample': False,
        },
        'pulseReads': {
            'selectedBits': [2, 3], 'selection': 'CurrentALAnd7',
            'phases': [{'counterSetupPC': setup, 'rank': rank, 'decPC': dec,
                        'zeroBranchPC': zero, 'readerPC': reader,
                        'branchPC': branch, 'requiredBit': bit}
                       for setup, rank, dec, zero, reader, branch, bit in phases],
            'readerSourceByBit': {'2': 'PWM0OutputData', '3': 'PWM1OutputData'},
            'ordinaryReadNoFunctionalPortWrite': True,
            'readSourceCondition': 'StandardP4Table5_5_IO1_SF1_OrdinaryRead',
            'readModifyWriteReadsPinInstead': True,
            'selectorIncrementPC': 0x2644, 'selectorComparePC': 0x2647,
            'selectorBranchPC': 0x2649, 'faultPC': 0x2650,
            'sampleIdentityRequiredForEveryRead': True,
            'physicalMillisecondsFromRank': None,
            'actualPulseHistory': 'NotEstablished',
        },
        'freshIrq': {
            'clearPC': 0x261E, 'readerPC': 0x264B, 'branchPC': 0x264E,
            'selectedWordBit': 13, 'selectedHighBit': 5, 'vectorIdentity': 0x0022,
            'enabledStandardFactorSource': 'PWM1OverflowOnly',
            'disabledSource': 'PWM0',
            'factorCondition': 'RetainedStandardPWMCON1_ERQ1_PWMCON0_ERQ0',
            'oldBitRequired': 1, 'zfFromOldBit': True,
            'zfIfOldBitOne': 0, 'acknowledgedSelectedBit': 0,
            'success': 0x2655, 'fault': 0x2650,
            'preclearPendingSuffices': False,
            'pendingRequiresIsrDelivery': False,
            'actualFactorObserved': False,
        },
        'requiredPartialOrder': [
            ['AcceptedPWMConfiguration', 'ClearIRQ261E'],
            ['RetainedP4IOandSF', 'EachMBRPortRead'],
            ['ClearIRQ261E', 'ApplicableEnabledPWM1Overflow'],
            ['ApplicableEnabledPWM1Overflow', 'CurrentRB264BReadAndAcknowledge'],
            ['CurrentRB264BReadAndAcknowledge', 'Branch264E'],
            ['Bit2LowHighLowReadsComplete', 'Bit3LowHighLowReads'],
            ['Bit3LowHighLowReadsComplete', 'CurrentRB264BReadAndAcknowledge'],
        ],
        'unresolved': [
            'ApplicableEcuSiliconNotEstablished', 'ActualResetEntryNotEstablished',
            'WdtCommandMeaningNotEstablished', 'PhysicalClockHistoryNotEstablished',
            'ExternalData4700PhysicalReadAndEffectsNotEstablished',
            'P4Bit1ActualSampleNotEstablished', 'PeripheralWriteAcceptanceNotEstablished',
            'ActualPWMOutputHistoryNotEstablished', 'FreshIRQH5HardwareEventNotObserved',
            'NoUnaccountedNmiResetOrAliasMutationNotEstablished',
        ],
        'actualEvents': {
            'cpuExecutions': 0, 'originalRomExecutions': 0,
            'machineId': None, 'nativeWriteOrdinal': None,
            'readerObservation': None, 'factorOwner': None,
        },
        'firmwareReady': False,
    }
