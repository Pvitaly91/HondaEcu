"""Address/overlap obligations for static provenance, without a CPU or Bus.

Known arithmetic footprints are separate from unknown pointer values, incoming
stack state and physical interrupt delivery. An alias possibility is not an
observed write, and an apparently disjoint value does not establish its owner.
"""


TARGET_WORDS = (0x011A, 0x011E, 0x0212, 0x0216)


def _unsigned(value, bits, name):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(name)
    return value


def word_footprint(address):
    """Architectural DATA/system-stack word alignment, not PROGRAM/USP policy."""
    base = _unsigned(address, 16, "Address16Required") & 0xFFFE
    return [base, base + 1]


def cal_frame_footprint(ssp):
    """An ordinary CAL writes one PC+length word before decrementing SSP."""
    return word_footprint(_unsigned(ssp, 16, "Ssp16Required"))


def interrupt_frame_footprint(ssp):
    """Conditional four-word IRQ footprint; never an injected frame."""
    ssp = _unsigned(ssp, 16, "Ssp16Required")
    return [address for offset in (0, 2, 4, 6)
            for address in word_footprint((ssp - offset) & 0xFFFF)]


def local_register_addresses(lrb):
    base = (_unsigned(lrb, 16, "Lrb16Required") & 0x1FFF) << 3
    return {"r" + str(index): base + index for index in range(8)}


def off_page_address(lrb, encoded_offset):
    page = (_unsigned(lrb, 16, "Lrb16Required") & 0x1FE0) << 3
    return page | _unsigned(encoded_offset, 8, "Offset8Required")


def pointing_register_storage(scb):
    base = 0x0080 + 8 * _unsigned(scb, 3, "Scb3Required")
    return {name: word_footprint(base + offset)
            for name, offset in (("X1", 0), ("X2", 2), ("DP", 4), ("USP", 6))}


def usp_relative_address(usp, encoded_offset):
    """The effective byte address before any exact-form width qualification."""
    offset = _unsigned(encoded_offset, 8, "Offset8Required")
    signed = offset if offset < 0x80 else offset - 0x100
    return (_unsigned(usp, 16, "Usp16Required") + signed) & 0xFFFF


def bitmap_target(incoming_a, base):
    """Conditional SUBB-low-byte/DIVB-word mapping under reviewed form semantics.

    SUBB changes only AL, retaining AH. DIVB divides that16-bit word by8;
    X1 receives the word quotient and SBR selects the remainder. This relation
    does not establish incoming A, its source owner or an actual SBR write.
    """
    incoming_a = _unsigned(incoming_a, 16, "Accumulator16Required")
    base = _unsigned(base, 16, "BitmapBase16Required")
    pre_division = (incoming_a & 0xFF00) | ((incoming_a - 1) & 0xFF)
    index, bit = divmod(pre_division, 8)
    return {"incomingA": incoming_a, "base": base, "byteIndex": index,
            "bit": bit, "address": (base + index) & 0xFFFF,
            "preDivisionWord": pre_division, "quotientWidth": 16,
            "lowByteDecrementOnly": True,
            "sourceOwner": "IncomingAOwnerNotEstablished",
            "classification": "ConditionalBitmapAddress_NotObservedWrite"}


def aliases():
    """Summarize exact overlap arithmetic and the first unproved domains."""
    target_bytes = {address for word in TARGET_WORDS for address in word_footprint(word)}
    frame_rows = []
    for word in TARGET_WORDS:
        # A four-word descending frame can touch a selected word at any position.
        irq_tops = [word + offset for offset in (0, 2, 4, 6)]
        frame_rows.append({
            "targetWord": word, "targetBytes": word_footprint(word),
            "calEvenSspCollisions": [word],
            "irqEvenSspCollisions": irq_tops,
            "unknownIncomingSsp": True, "nestedFramesBounded": False,
            "classification": "PotentialStackAlias_NotObservedOverwrite",
        })
    scb_storage = [pointing_register_storage(scb) for scb in range(8)]
    pointing_bytes = {address for row in scb_storage for pair in row.values() for address in pair}
    return {
        "classification": "StaticAliasObligations_NotRuntimeJournal",
        "wordLowBitClearedForDataAndSystemStack": True,
        "unalignedTargetAliases": [
            {"encodedAddress": word + 1, "actualFootprint": word_footprint(word + 1)}
            for word in TARGET_WORDS
        ],
        "listedContext": {
            "lrb": 0x0021, "offPageBase": off_page_address(0x0021, 0),
            "localRegisters": local_register_addresses(0x0021),
            "scb": 2, "pointingStorage": pointing_register_storage(2),
            "usp": 0x0280,
            "uspBufferSources": [usp_relative_address(0x0280, n) for n in (0x92, 0x94, 0x96)],
        },
        "alternativeLocalBanks": [
            {"lrb": lrb, "registers": local_register_addresses(lrb),
             "targetOverlap": sorted(set(local_register_addresses(lrb).values()) & target_bytes),
             "liveContextEstablished": False}
            for lrb in (0x0023, 0x0042)
        ],
        "pointingRegisterStorageDisjointForAllEightScb": not bool(pointing_bytes & target_bytes),
        "pointingValuesAndIndirectDereferencesStillUnknown": True,
        "stackCollisions": frame_rows,
        "technicalCalFrame": {"ssp": 0x07FE, "footprint": cal_frame_footprint(0x07FE),
                              "disjointFromTargets": not bool(set(cal_frame_footprint(0x07FE)) & target_bytes),
                              "authority": "AcceptedTechnicalCAL063BOnly_NotEnclosingIrq"},
        "copyHelperSelfAlias": {"caller": 0x038A, "requiredReturnPc": 0x038D,
                                "requiredRt": 0x5C3F,
                                "hazard": "UnknownCALFrameCanOverlapCopyDestinationOrBufferSource"},
        "bitmapExamples": [bitmap_target(value, base)
                           for value in (0x0010, 0x002C) for base in (0x011A, 0x0212)],
        "preservationRules": [
            "EverySameValueWriteCreatesFreshStorageGeneration",
            "BitRmwRetainsOtherBitSemanticLineageOnlyWithKnownOldOwner",
            "WordWriteInvalidatesBothPriorByteStorageGenerations",
            "UnknownIndirectOrFrameOverlapBlocksStrictPreservation",
            "AlternativePageOrUspChangesRequireNewEffectiveAddressProof",
            "UnknownAccumulatorSTACKModeCannotBeDeclaredDisjoint",
            "NoEventIndexOrGlobalWriteOrdinalImportedFromAnotherMachine",
        ],
        "bounds": "CompleteArithmeticForSelectedFootprints_UnknownOutsideReviewedCodeOrIndirectContext",
        "actualCpuExecutions": 0,
        "actualOriginalRomExecutions": 0,
        "actualIrqFramesCreated": 0,
    }
