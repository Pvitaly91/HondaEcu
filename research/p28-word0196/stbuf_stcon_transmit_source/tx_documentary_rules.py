"""Source-qualified documentary facts; no peripheral state machine or execution authority."""
from copy import deepcopy

DOCUMENTED_FACTS = {'BRG_RELOAD_WRITE_NOT_COUNTER_SEED': {'pages': [120],
                                       'rule': 'Writing STTMR alone does not change STTM; both reload '
                                               'register and counter must be assigned the same value '
                                               'beforehand for a fixed start period.'},
 'BRG_TIMER_AUTO_RELOAD_OVERFLOW': {'pages': [120],
                                    'rule': 'Auto-reload timer overflow reloads STTMR into STTM and '
                                            'generates an overflow request; this is documentary '
                                            'behavior, not a performed clock event.'},
 'BUFFERED_NEXT_START_RAISES_TX_READY': {'pages': [125],
                                         'rule': 'When previous transmission completes, buffered next '
                                                 'data starts and a transmission interrupt request is '
                                                 'generated at that new start.'},
 'BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION': {'pages': [125],
                                                'rule': 'A documented write while previous '
                                                        'transmission is active does not interrupt '
                                                        'that previous transfer; the text describes '
                                                        'next data beginning after it completes.'},
 'IDLE_STBUF_WRITE_STARTS_TRANSMISSION': {'pages': [125, 131],
                                          'rule': 'A qualified write when there is no previous '
                                                  'transmission is the documented transmission '
                                                  'trigger; no event is performed in M2cs.'},
 'RX_MODE_CHANGE_REQUIRES_SREN_ZERO': {'pages': [127],
                                       'rule': 'Changing receiver operation mode must occur with '
                                               'receiving prohibited, SREN=0. This restriction is '
                                               'receiver-specific and is not copied onto STCON.'},
 'SHIFT_REGISTER_NOT_SOFTWARE_ACCESSIBLE': {'pages': [125],
                                            'rule': 'Software cannot directly read or write the '
                                                    'transmission shift register.'},
 'STBUF_RESET_UNAFFECTED_NO_DEFINED_VALUE': {'pages': [125],
                                             'rule': 'Reset does not modify STBUF contents; this does '
                                                     'not supply a known reset/current value.'},
 'STBUF_TO_SHIFT_HALF_CLK_DOC': {'pages': [125, 131],
                                 'rule': 'The body documents a half-CLK transfer/start relation and an '
                                         'illustrative200ns at10MHz; actual clock, elapsed time and '
                                         'ordering are not observed.'},
 'STBUF_WRITE_ONLY_8_LSB_FIRST': {'pages': [125],
                                  'rule': 'STBUF at0051 is an8-bit write-only data buffer; bit0 is '
                                          'transmitted first, with selected data length.'},
 'TRANSMIT_TWO_STAGES': {'pages': [125],
                         'rule': 'STBUF holding buffer and separate transmit shift register form two '
                                 'stages; no arbitrary FIFO depth is established.'},
 'TX_READY_AT_START_IRQ_BIT2': {'pages': [131],
                                'rule': 'TXREADY is generated with M1ST instruction-start '
                                        'synchronization and sets IRQ word bit2 in the documented UART '
                                        'normal start sequence; it is not renamed TX COMPLETE.'},
 'TX_SETUP_BEFORE_STBUF': {'pages': [125],
                           'rule': 'Configure baud generation and transmission mode before a '
                                   'contemplated STBUF write.'},
 'UART_NORMAL_BRG_DIVIDE_16': {'pages': [131],
                               'rule': 'The UART normal description divides the BRG clock by16 to form '
                                       'STCLK; no actual frequency or general baud/reload formula is '
                                       'inferred.'},
 'UART_NORMAL_FRAME_END_STOP_BIT': {'pages': [131],
                                    'rule': 'UART normal sends selected data LSB first, parity when '
                                            'designated, then stop bit to end one frame; a separate '
                                            'completion IRQ is not established.'},
 'UART_NORMAL_START_BIT_AFTER_STFREE_LOW': {'pages': [131],
                                            'rule': 'STFREE is described as an internal progress '
                                                    'signal becoming low; the next STCLK falling edge '
                                                    'generates the start bit. No SFR address/bit '
                                                    'mapping for STFREE is established.'},
 'UART_NORMAL_WSTBUF_LSTSF_START': {'pages': [131],
                                    'rule': 'WSTBUF triggers LSTSF; STBUF contents move to the shift '
                                            'register at its falling edge, in this documented UART '
                                            'normal sequence.'}}

UNKNOWN_FACTS = {'ACTUAL_ECU_APPLICABILITY': 'No same-unit MCU/customer-mask/peripheral applicability bridge.',
 'ACTUAL_NATIVE_TX_READINESS': 'No native current buffer/shift/configuration owner or clock state '
                               'observed.',
 'CLOCK_OR_RELOAD_CHANGE_DURING_ACTIVE_TRANSFER': 'No intact applicable safe mid-TX '
                                                  'clock/reload-change rule acquired.',
 'FULL_HOLDING_BUFFER_WRITE_COLLISION': 'Two stages and one buffered next-data case do not define '
                                        'another write when the holding buffer is already occupied.',
 'GENERAL_BAUD_RATE_FORMULA': 'Equation photo116/117 is CRC-failed; do not reuse its visible formula '
                              'as semantic authority.',
 'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY': 'No TX-specific collision-priority/total-order rule acquired.',
 'IE_POLARITY_CONFLICT': 'Separate IRQ/IE proof retains contradictory manufacturer-body predicates; no '
                         'actual-Honda polarity selected.',
 'LEVEL_REASSERT_WITHOUT_NEW_DATA': 'No source establishing level reassertion after clear without '
                                    'another eligible data/start condition.',
 'MISSING_PAGES132_147_CONTENT': 'Eight missing photo members do not establish contents of '
                                 'printed132..147.',
 'STBUF_WRITE_SPECIFIC_ACK': 'No intact applicable rule acquired proving write clears TXREADY request.',
 'STCON_BIT7_OR_TX_PERMISSION_FIELD': 'Bit7 or TX-enable meaning is not established from intact pages; '
                                      'reset80 does not identify such a field.',
 'STCON_FULL_LENGTH_STOP_PARITY_ENCODING': 'Allocation table123 is CRC-failed; normal '
                                           'length-code/stop-code and parity presence/polarity '
                                           'encodings remain incomplete.',
 'TX_COMPLETE_INTERRUPT': 'No separate completion interrupt source established from intact TX pages; '
                          'do not rename TXREADY.',
 'TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER': 'Relevant full STCON configuration restrictions unavailable; '
                                          'receiver SREN rule is not transferred.',
 'TX_REQUEST_READ_ACK': 'No read-ack rule established; STBUF is write-only.'}

SITUATIONS = {'Acknowledge': {'documentedRules': [],
                 'unknownRules': ['STBUF_WRITE_SPECIFIC_ACK',
                                  'TX_REQUEST_READ_ACK',
                                  'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY',
                                  'IE_POLARITY_CONFLICT']},
 'BusyWrite': {'documentedRules': ['TRANSMIT_TWO_STAGES',
                                   'BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION',
                                   'BUFFERED_NEXT_START_RAISES_TX_READY'],
               'unknownRules': ['ACTUAL_NATIVE_TX_READINESS',
                                'FULL_HOLDING_BUFFER_WRITE_COLLISION',
                                'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY']},
 'Collision': {'documentedRules': ['BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION',
                                   'BUFFERED_NEXT_START_RAISES_TX_READY'],
               'unknownRules': ['FULL_HOLDING_BUFFER_WRITE_COLLISION',
                                'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY',
                                'TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER']},
 'Completion': {'documentedRules': ['UART_NORMAL_FRAME_END_STOP_BIT',
                                    'BUFFERED_NEXT_START_RAISES_TX_READY'],
                'unknownRules': ['TX_COMPLETE_INTERRUPT', 'ACTUAL_NATIVE_TX_READINESS']},
 'IdleWrite': {'documentedRules': ['TX_SETUP_BEFORE_STBUF',
                                   'STBUF_WRITE_ONLY_8_LSB_FIRST',
                                   'TRANSMIT_TWO_STAGES',
                                   'IDLE_STBUF_WRITE_STARTS_TRANSMISSION',
                                   'STBUF_TO_SHIFT_HALF_CLK_DOC',
                                   'UART_NORMAL_WSTBUF_LSTSF_START',
                                   'TX_READY_AT_START_IRQ_BIT2'],
               'unknownRules': ['ACTUAL_ECU_APPLICABILITY',
                                'ACTUAL_NATIVE_TX_READINESS',
                                'STBUF_WRITE_SPECIFIC_ACK']},
 'ModeChange': {'documentedRules': ['TX_SETUP_BEFORE_STBUF',
                                    'RX_MODE_CHANGE_REQUIRES_SREN_ZERO',
                                    'BRG_RELOAD_WRITE_NOT_COUNTER_SEED'],
                'unknownRules': ['TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER',
                                 'CLOCK_OR_RELOAD_CHANGE_DURING_ACTIVE_TRANSFER',
                                 'STCON_FULL_LENGTH_STOP_PARITY_ENCODING']},
 'Reassertion': {'documentedRules': ['BUFFERED_NEXT_START_RAISES_TX_READY'],
                 'unknownRules': ['LEVEL_REASSERT_WITHOUT_NEW_DATA',
                                  'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY']}}

REGISTER_INVENTORY = [{'access': 'R/W',
  'address': 72,
  'name': 'STTM',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 0,
  'role': 'Transmission baud generator counter',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 73,
  'name': 'STTMR',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 0,
  'role': 'Transmission baud generator reload register',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 74,
  'name': 'STTMC',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 12,
  'role': 'Transmission/shared baud generator control',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 76,
  'name': 'SRTM',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 0,
  'role': 'Receiving baud generator counter',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 77,
  'name': 'SRTMR',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 0,
  'role': 'Receiving baud generator reload register',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 78,
  'name': 'SRTMC',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 14,
  'role': 'Receiving baud generator control',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 80,
  'name': 'STCON',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 128,
  'role': 'Transmission mode control',
  'widthBits': 8},
 {'access': 'W',
  'address': 81,
  'name': 'STBUF',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'Undefined',
  'resetValue': None,
  'role': 'Transmission data buffer',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 84,
  'name': 'SRCON',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 0,
  'role': 'Receiving mode control',
  'widthBits': 8},
 {'access': 'R',
  'address': 85,
  'name': 'SRBUF',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'Undefined',
  'resetValue': None,
  'role': 'Receiving data buffer',
  'widthBits': 8},
 {'access': 'R/W',
  'address': 86,
  'name': 'SRSTAT',
  'primaryLocators': ['EnglishY4:11/30', 'JapaneseY3:11/30'],
  'resetClassification': 'ManufacturerResetValue_NotCurrentState',
  'resetValue': 240,
  'role': 'Receiving error register',
  'widthBits': 8}]

STTMC = {'address': 74,
 'clockBits': [7, 6, 5],
 'clockDivisorsByCode': [2, 4, 8, 16, 32, 128, 512, 512],
 'documentedReadBits': {'2': 1, '3': 1},
 'intent12': {'actualCounterRunning': 'NotObserved',
              'clockCode': 0,
              'clockDivisor': 2,
              'mode': 'TransmissionReceivingBaudGenerator',
              'modeCode': 2,
              'physicalReadbackValue': 'NotAssigned',
              'runBit': 1},
 'modeBits': [1, 0],
 'modeTable': {'0': 'AutoReloadTimer',
               '1': 'TransmissionBaudGenerator',
               '2': 'TransmissionReceivingBaudGenerator',
               '3': 'TransmissionReceivingBaudGenerator'},
 'nonexistentBits': [2, 3],
 'pages': [112, 113],
 'runBit4': {'0': 'Stopped', '1': 'Operating'}}

STCON_FIELDS = {'bit0': {'0': 'Normal', '1': 'Multiprocessor'},
 'bit1': {'0': 'UART', '1': 'Synchronous'},
 'bit5': 'ParityPresenceSelector_ExactPresencePolarityNotIndependentlyEstablishedWithoutAllocationTable',
 'bit6': 'OddEvenSelector_PolarityUnknown_ExplicitlyIgnoredWhenBit5Zero',
 'bit7': 'Unknown_NotPromotedToTxEnableOrStfree',
 'excludedSource': 'CrcFailedPhoto122_123_NotSemanticAuthority',
 'modeChangeDuringTx': 'NotEstablished',
 'multiprocessorBit2': {'0': 'Data', '1': 'Address'},
 'multiprocessorBit3': 'Ignored',
 'normalModeBits2_3': 'DataLengthCode_ExactCodeToBitCountUnknown',
 'pages': [124, 131],
 'receiveRuleNotTransferred': True,
 'synchronousBit4': {'0': 'Slave', '1': 'Master'},
 'uartBit4': 'StopLengthCode_EncodingUnknown'}

SRCON_FIELDS = {'address': 84,
 'bit4Synchronous': {'0': 'Slave', '1': 'Master'},
 'bit4Uart': 'Ignored',
 'bit5': {'0': 'NoParity', '1': 'Parity'},
 'bit6When5One': {'0': 'Odd', '1': 'Even'},
 'bit6When5Zero': 'Ignored',
 'bit7': {'0': 'ReceivingProhibited', '1': 'ReceivingAllowed'},
 'modeBits1_0': {'0': 'UARTNormal',
                 '1': 'UARTMultiprocessor',
                 '2': 'SynchronousNormal',
                 '3': 'SynchronousMultiprocessor'},
 'modeChangeRequirement': 'ReceivingProhibited_SREN0',
 'multiprocessorBit2': {'0': 'DataReceive', '1': 'AddressReceive'},
 'multiprocessorBit3': 'Ignored',
 'normalDataLengthBits3_2': {'0': 5, '1': 6, '2': 7, '3': 8},
 'pages': [126, 127],
 'synchronousMasterAfterOneFrame': 'Bit7ClearsToZero_OtherModesBit7DoesNotChange',
 'txFieldPolarityNotInferredFromReceiver': True}

def documentary_rules():
    """Return an independent copy of the closed, qualified primary-source catalog."""
    return deepcopy({
        'documentedFacts': DOCUMENTED_FACTS,
        'unknownFacts': UNKNOWN_FACTS,
        'situations': SITUATIONS,
        'registerInventory': REGISTER_INVENTORY,
        'sttmc': STTMC,
        'stconFields': STCON_FIELDS,
        'srconFields': SRCON_FIELDS,
    })
