"""Closed static search facts; no ROM loader and no global absence assertion."""

SEARCH_SCOPE = {
    'retainedInstructionExtents': 11499,
    'r4OrEr2SyntaxRows': 155,
    'listedBank03f0R4OrEr2Rows': 1,
    'explicitDp03f4Seeds': 1,
    'pointerUspXSyntaxRows': 698,
    'allBracketSyntaxRows': 710,
    'additionalProgramTableLoadRows': 12,
    'wrongListedPageOffF4F5Rows': 3,
    'zeroPageNumericFalsePositives': 16,
    'uspSyntaxRows': 180,
    'newDisassembly': False,
    'newRomRead': False,
    'globalConsumerAbsenceEstablished': False,
}
CANDIDATES = (
    {'id': 'Payload03F4_AddThree_Store03F2', 'pc': 0x28DB, 'widthBits': 8,
     'dataAddress': 0x3F4, 'addressSource': 'ExplicitDP03F4At28D8',
     'localTransformation': 'SourceQualified_GPlus3_Mod256_Store03F2',
     'specific026CReachingDefinition': 'ConditionalCandidate'},
    {'id': 'IndirectWord02B7', 'pc': 0x2B7, 'widthBits': 16, 'dataAddress': None,
     'addressSource': 'UnboundPointerFromSerialAndAccumulatorContext',
     'localTransformation': 'OutsideSelectedConsumerScope', 'specific026CReachingDefinition': 'SourceUnbound'},
    {'id': 'Flag03F3', 'pc': 0x2917, 'widthBits': 8, 'dataAddress': 0x3F3,
     'addressSource': 'ExplicitDP03F3At2914',
     'localTransformation': 'SeparateFlagParityPredicate_NotGenericPayload',
     'specific026CReachingDefinition': 'DifferentSource_NotEstablished'},
)
POTENTIAL_WRITERS = (
    {'pc': 0x26C, 'qualification': 'ByteOnly_DD0_LRB007E', 'dataAddress': 0x3F4},
    {'pc': 0x2710, 'qualification': 'BootWordLoop_PotentialOverlap_NotRun', 'dataAddress': None},
    {'pc': 0x2689, 'qualification': 'RamTestCall_IndirectWriterScopeUnbound_NotRun', 'dataAddress': None},
)
KNOWN_EDGES = (
    (0x28D8, 0x28DB), (0x28DB, 0x28DC), (0x28DC, 0x28DE), (0x28DE, 0x297C),
    (0x297C, 0x297F), (0x297F, 0x2980),
    (0x270, 0x272), (0x272, 0x295), (0x290, 0x293), (0x293, 0x295),
    (0x295, 0x297), (0x297, 0x29A), (0x29A, 0x29C),
)
UNESTABLISHED_EDGES = (
    '026CGenerationThroughActualRtiAndForegroundTo28DB',
    'Consumer2980ToUnreviewedStatusCounterAndPeripheralTail',
    '029CThroughActualSavedForegroundPcToConsumer',
)


def search_inventory():
    """Return source facts, not a proof that an instruction or IRQ was executed."""
    return {'scope': dict(SEARCH_SCOPE), 'candidates': [dict(row) for row in CANDIDATES],
            'potentialWriters': [dict(row) for row in POTENTIAL_WRITERS],
            'knownConditionalEdges': [list(edge) for edge in KNOWN_EDGES],
            'unestablishedEdges': list(UNESTABLISHED_EDGES),
            'confirmed026CConsumers': [], 'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
