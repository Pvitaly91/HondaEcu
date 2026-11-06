"""Reviewed documentary bindings and scope; no model or runtime is imported."""
from copy import deepcopy

BASE = '531b3859a5b63b42ba597fe0a79be408dea151ff'
SOURCE_BINDING = {'base': '531b3859a5b63b42ba597fe0a79be408dea151ff',
 'indexedWriterProof': '706efe9ec87bd0425bfec42b2981400abc887cff4316ade41eb91741517fedd4',
 'aliasInventory': '32405012ce9429ceac9d529fdcd615d0f226164e407061ea06e0e5457a96ec52',
 'extendedMode': '8b0e55b191933df95d1b1ea2d41d6d06f0aa1d73b75b51a051f0f5dddd21d1c4',
 'caller': '545ed5a0396df16b1447e5662b767d9a7cd1e40e2951460a8ce8d3c3bad1e691',
 'callerAdscan': 'c10552327a39026988705f728b3563bcbb314fb63a0c7168714292a7413f8336',
 'primaryV2': '60eb3224b5525deb46e3529010ce5cf496dda52f56f9ab43432902ed26228caf'}

APPLICABILITY = 'StandardMsm66201_207_Documented_NotEcuApplicable'
DOCUMENTARY_FACT_COUNT = 17
DOCUMENTARY_UNKNOWN_COUNT = 15
NEW_OPERATION_RULES = []
SAME_UNIT_APPLICABILITY_ESTABLISHED = False
INHERITED_FACTS_ARE_NEW_DISCOVERIES = False

DOCUMENTARY_FACT_IDS = ['BRG_RELOAD_WRITE_NOT_COUNTER_SEED',
 'BRG_TIMER_AUTO_RELOAD_OVERFLOW',
 'BUFFERED_NEXT_START_RAISES_TX_READY',
 'BUSY_WRITE_CONTINUES_PREVIOUS_TRANSMISSION',
 'IDLE_STBUF_WRITE_STARTS_TRANSMISSION',
 'RX_MODE_CHANGE_REQUIRES_SREN_ZERO',
 'SHIFT_REGISTER_NOT_SOFTWARE_ACCESSIBLE',
 'STBUF_RESET_UNAFFECTED_NO_DEFINED_VALUE',
 'STBUF_TO_SHIFT_HALF_CLK_DOC',
 'STBUF_WRITE_ONLY_8_LSB_FIRST',
 'TRANSMIT_TWO_STAGES',
 'TX_READY_AT_START_IRQ_BIT2',
 'TX_SETUP_BEFORE_STBUF',
 'UART_NORMAL_BRG_DIVIDE_16',
 'UART_NORMAL_FRAME_END_STOP_BIT',
 'UART_NORMAL_START_BIT_AFTER_STFREE_LOW',
 'UART_NORMAL_WSTBUF_LSTSF_START']
UNKNOWN_FACTS = {'ACTUAL_ECU_APPLICABILITY': 'No same-unit MCU/customer-mask/peripheral applicability bridge.',
 'ACTUAL_NATIVE_TX_READINESS': 'No native current buffer/shift/configuration owner or clock state '
                               'observed.',
 'CLOCK_OR_RELOAD_CHANGE_DURING_ACTIVE_TRANSFER': 'No intact applicable safe mid-TX '
                                                  'clock/reload-change rule acquired.',
 'FULL_HOLDING_BUFFER_WRITE_COLLISION': 'Two stages and one buffered next-data case do not define '
                                        'another write when the holding buffer is already '
                                        'occupied.',
 'GENERAL_BAUD_RATE_FORMULA': 'Equation photo116/117 is CRC-failed; do not reuse its visible '
                              'formula as semantic authority.',
 'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY': 'No TX-specific collision-priority/total-order rule '
                                         'acquired.',
 'IE_POLARITY_CONFLICT': 'Separate IRQ/IE proof retains contradictory manufacturer-body '
                         'predicates; no same-unit polarity selected.',
 'LEVEL_REASSERT_WITHOUT_NEW_DATA': 'No source establishing level reassertion after clear without '
                                    'another eligible data/start condition.',
 'MISSING_PAGES132_147_CONTENT': 'Eight missing photo members do not establish contents of '
                                 'printed132..147.',
 'STBUF_WRITE_SPECIFIC_ACK': 'No intact applicable rule acquired proving write clears TXREADY '
                             'request.',
 'STCON_BIT7_OR_TX_PERMISSION_FIELD': 'Bit7 or TX-enable meaning is not established from intact '
                                      'pages; reset80 does not identify such a field.',
 'STCON_FULL_LENGTH_STOP_PARITY_ENCODING': 'Allocation table123 is CRC-failed; normal '
                                           'length-code/stop-code and parity presence/polarity '
                                           'encodings remain incomplete.',
 'TX_COMPLETE_INTERRUPT': 'No separate completion interrupt source established from intact TX '
                          'pages; do not rename TXREADY.',
 'TX_MODE_CHANGE_DURING_ACTIVE_TRANSFER': 'Relevant full STCON configuration restrictions '
                                          'unavailable; receiver SREN rule is not transferred.',
 'TX_REQUEST_READ_ACK': 'No read-ack rule established; STBUF is write-only.'}
IE_POLARITY = {
    'classification': 'SourceConflict',
    'enablePredicatesPrintedPages': [165, 168, 169],
    'contradictoryEntryPrintedPage': 167,
    'resolution': None,
    'actualEcuPolarity': None,
}
DOCUMENTARY_DELTA = {
    'classification': 'BoundedNovelRecovery_RetainedEditionReused_NoNewOperationRules',
    'novelQueries': 12,
    'candidateOpens': 3,
    'newPdfDownloads': 0,
    'retainedFifthEditionReused': True,
    'previousProjectUseEstablished': True,
    'retainedBookIssueDate': 'June 1990',
    'retainedBookPrintedSectionsReviewed': ['363-383', '384-404'],
    'newOperationRulesAdmitted': 0,
    'unknownFactsRetained': 15,
    'globalAbsenceClaim': False,
    'failedCrcPagesExcluded': [114, 115, 116, 117, 122, 123],
    'missing132To147ContentsAssumed': False,
    'srconEncodingTransferredToStcon': False,
    'reset80PromotedToCurrentStateOrTxEnable': False,
}


def binding():
    return deepcopy(SOURCE_BINDING)


def binding_reason(value):
    """Require all seven reviewed strings, without tolerant type coercion."""
    if value is None:
        return 'SourceBindingMissing'
    if (type(value) is not dict or set(value) != set(SOURCE_BINDING)
            or any(type(value[key]) is not str or value[key] != expected
                   for key, expected in SOURCE_BINDING.items())):
        return 'SourceBindingMismatch'
    return None
