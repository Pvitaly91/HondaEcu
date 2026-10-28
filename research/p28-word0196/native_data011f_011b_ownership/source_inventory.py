"""Reviewed M2cb writer relationships, never executable ROM or runtime evidence.

The table is the public semantic projection of a separate private comparison of
the reused listed extents with the original image and frozen listing. Calling
this module does not repeat that private comparison or acquire native owners.
"""

from copy import deepcopy


def _writer(pc, form, length, address, width, *, source, mode, conditions,
            bit=None, transformation=None, classification="ConditionalListedWriter"):
    return {
        "writerPC": pc,
        "form": form,
        "length": length,
        "address": address,
        "widthBits": width,
        "targetBit": bit,
        "addressingMode": mode,
        "source": source,
        "valueTransformation": transformation,
        "conditions": conditions,
        "classification": classification,
        "writerFound": True,
        "codeOwnedTransformationEstablished": True,
        "sourceValueOwnedOnCurrentMachine": False,
        "writerExecutedOnCurrentMachine": False,
        "generationPreservedToReader": "NotEstablished",
        "actualEventIndex": None,
        "actualGlobalWriteOrdinal": None,
        "sameValueWriteRetained": True,
    }


def _copies():
    result = []
    for load_pc, store_pc, source, destination, context in (
        (0x03FE, 0x0400, 0x0212, 0x011A, "GenuineSerialEntry03ED"),
        (0x0402, 0x0404, 0x0214, 0x011C, "GenuineSerialEntry03ED"),
        (0x0406, 0x0408, 0x0216, 0x011E, "GenuineSerialEntry03ED"),
        (0x5C2B, 0x5C2D, 0x0212, 0x011A, "ReachedHelper5C2B"),
        (0x5C2F, 0x5C31, 0x0214, 0x011C, "ReachedHelper5C2B"),
        (0x5C33, 0x5C35, 0x0216, 0x011E, "ReachedHelper5C2B"),
    ):
        row = _writer(
            store_pc, "ST A,off N8", 2, destination, 16,
            source={"loadPC": load_pc, "address": source, "widthBits": 16,
                    "loadForm": "L A,S8[USP]", "loadLength": 2,
                    "usp": 0x0280, "signedOffset": source - 0x0280},
            mode="OffPageWord_Page0100",
            conditions=[context, "DD1", "LRB0021OrEquivalentOwnedPageAndBank",
                        "OwnedSCBAndUSP0280", "LoadCompletesBeforeStore",
                        "NoInterveningAccumulatorOrSourceMutation"],
            transformation={"word": "destinationWord=sourceWord",
                            "lowByte": "destination=source",
                            "highByte": "destination+1=source+1",
                            "endian": "LittleEndian", "wordAligned": True},
            classification="ConditionalFullWordCopy_NotCurrentMachineOwner",
        )
        row.update(fullWordStorageWrite=True, wholeWordValueOwnershipEstablished=False,
                   incomingFlagDependency="NoneForLoadStoreSelection",
                   selectionPredicate="NoInternalBranchBetweenLoadAndStore",
                   cfgPredecessor=load_pc, cfgSuccessor=store_pc + 2,
                   footprint=[destination, destination + 1])
        result.append(row)
    return result


def _zero_candidates():
    result = []
    for pc, address, mode, displacement in (
        (0x291C, 0x011A, "USPRelativeWord", -0x66),
        (0x291E, 0x011C, "USPRelativeWord", -0x64),
        (0x2920, 0x0212, "OffPageWord_Page0200", None),
        (0x2922, 0x0214, "OffPageWord_Page0200", None),
    ):
        row = _writer(
            pc, "ST A,S8[USP]" if displacement is not None else "ST A,off N8",
            2, address, 16,
            source={"producerPC": 0x291B, "form": "CLR A", "codeOwnedValue": 0},
            mode=mode,
            conditions=["Reached291B", "Branch2919FallsThrough_CF1",
                        "OwnedDP03F3AndReadValue", "DD1", "OwnedPage0200AndUSP0180",
                        "NoInterveningAccumulatorMutation"],
            transformation="destinationWord=0_if_reached_after_CLR291B",
            classification="ConditionalCodeOwnedZero_NotCurrentMachineGeneration",
        )
        row.update(usp=0x0180 if displacement is not None else None,
                   signedOffset=displacement, footprint=[address, address + 1])
        result.append(row)
    return result


def _buffer_bit_writes():
    result = []
    for pc, op, address, bit in (
        (0x0787, "RB", 0x0217, 4), (0x0A09, "MB", 0x0217, 0),
        (0x105B, "MB", 0x0217, 1), (0x3F1D, "RB", 0x0217, 2),
        (0x3F31, "SB", 0x0217, 2), (0x4097, "SB", 0x0217, 4),
        (0x414E, "MB", 0x0217, 5), (0x5F4B, "MB", 0x0216, 4),
        (0x5F6B, "MB", 0x0217, 3), (0x5F7B, "MB", 0x0216, 1),
        (0x5F83, "MB", 0x0216, 7), (0x5FE7, "MB", 0x0216, 2),
        (0x6039, "MB", 0x0217, 6), (0x6051, "MB", 0x0216, 5),
        (0x7B13, "MB", 0x0217, 7), (0x7B45, "MB", 0x0216, 3),
        (0x7B80, "MB", 0x0216, 0), (0x7B94, "MB", 0x0216, 6),
    ):
        source = {"kind": "IncomingCarry"} if op == "MB" else {"kind": "CodeOwnedBit", "value": int(op == "SB")}
        if pc == 0x5F6B:
            source = {"kind": "VerifiedProgramBitThroughCarry", "programAddress": 0x60EC,
                      "programBit": 7, "loadPC": 0x5F66, "loadForm": "LCB A,N16",
                      "loadLength": 4, "shiftPC": 0x5F6A, "shiftForm": "SLLB A",
                      "shiftLength": 1, "requiredShiftDD": 0,
                      "privateProgramValuePublished": False}
        row = _writer(
            pc, op + " off N8.bit" + (",C" if op == "MB" else ""), 3,
            address, 8, bit=bit, source=source, mode="OffPageByte_Page0200",
            conditions=["ReachedWriter", "OwnedLRBPage0200", "OwnedSourceAndContext",
                        "NoInterveningSelectedBitOverwrite"],
            transformation=("selectedBit=CF;otherBitsRetained" if op == "MB" else
                            "selectedBit=" + str(int(op == "SB")) + ";otherBitsRetained"),
            classification="ConditionalSelectedBitWriter_NotWholeByteOwner",
        )
        row.update(affectsSource0217Bit3=address == 0x0217 and bit == 3,
                   incomingDD="ByteFormPreservesDD", footprint=[address],
                   wholeByteValueOwnershipEstablished=False)
        result.append(row)
    return result


def _bitmap_candidates():
    result = []
    for pc, base in ((0x5B86, 0x011A), (0x5B8A, 0x0212)):
        row = _writer(
            pc, "SBR N16[X1]", 4, None, 8,
            source={"kind": "IndexedBitOperation_PrimaryDirectionUnresolved", "entry": 0x5B7E, "divisor": 8,
                    "sourceRegister": "IncomingWordA", "selectorRegister": "AL_low3"},
            mode="IndexedX1Byte",
            conditions=["ReachedHelper5B7E", "DD0BeforeSUBB5B7E",
                        "OwnedIncomingWordAAndSelectedRegisterBanks",
                        "SUBBChangesALOnly", "DIVBCompletesWithNonzeroCodeDivisor8",
                        "NoInterveningAliasOrInterrupt"],
            transformation="AddressAndSelectedBitVerified;ORSetEffectIsHistoricalSoftwareInterpretationOnly",
            classification="ConditionalIndexedBitWriter_PrimarySetDirectionUnresolved",
        )
        row.update(baseAddress=base, incomingDD="DD0RequiredBeforeSUBB5B7E_AllReviewedByteFormsPreserveDD",
                   actualInputA=None, actualEffectiveAddress=None,
                   wordInputExamplesAreInvented=True,
                   requiredOriginalWordInputs={"targetHighByteBit7": 0x0010,
                                               "targetThirdWordHighByteBit3": 0x002C},
                   thirdCompanionStorePC=0x5B8E,
                   incomingFlagDependency="NoBranchBeforeThreeSBRStores",
                   codeOwnedTransformationEstablished=False,
                   addressAndSelectedBitRelationEstablished=True,
                   oldSelectedBitZfRelationEstablished=True,
                   setDirectionPrimaryEstablished=False,
                   primaryEditorialConflict="SBR_SET1DescriptionVersusFunctionBitAssign0",
                   historicalSoftwareSetInterpretation="newByte=oldByte OR (1<<(AL&7))",
                   knownOneSourceEstablished=False)
        result.append(row)
    return result


def _memory_hazards():
    result = []
    for pc, form, length, mode, relation in (
        (0x2710, "ST A,[DP]", 1, "StartupDescendingWordClear",
         "ConditionalCLR2706AndOwnedDPWalkerCanClearTargetWords"),
        (0x5C68, "XCHG A,N16[X1]", 4, "RamTestPatternExchange",
         "ConditionalEven0084PlusX1CanTemporarilyReplaceTargetWord"),
        (0x5C6C, "XCHG A,N16[X1]", 4, "RamTestOriginalWordRestoration",
         "RestoresOnlySameUninterruptedTargetAndSavedOriginalValue"),
        (0x0048, "ST A,N16[X1]", 3, "NmiConditionalRestoration",
         "Conditional0230Bit7AndOwnedSavedDPAndX1Required"),
    ):
        result.append(_writer(
            pc, form, length, None, 16, source={"kind": "ContextDependent"},
            mode=mode, conditions=["OwnedPointerAndStackDomains", "OwnedCurrentSource",
                                  "ActualRelevantControlHistoryNotEstablished"],
            transformation=relation, classification="ConservativeSourceOrOverwriteHazard"))
    return result


def reviewed_inventory():
    """Return the semantic contract; private exact-byte verification is separate."""
    copies, zeros, bits = _copies(), _zero_candidates(), _buffer_bit_writes()
    indexed, hazards = _bitmap_candidates(), _memory_hazards()
    return deepcopy({
        "schemaVersion": 1, "milestone": "M2cb",
        "classification": "StaticWriterRelationships_NotOriginalRomCpuExecution",
        "scope": "CompleteWithinVerifiedListedExtents_WithUnresolvedAddressContexts",
        "verificationAtPublicInvocation": "SemanticProjectionOnly_NoPrivateRomRead",
        "reusedListedExtentCount": 11499, "reusedOperandAccessCount": 6479,
        "listedWriteAccessCount": 2801, "concreteTargetAndNeighborAccessCount": 28,
        "ordinaryAccessesWithUnresolvedAddress": {
            "IndexedX1": 84, "IndexedX2": 10, "USPRelative": 107, "Indirect": 136},
        "unresolvedAddressCountScope": "OriginalM2aiInventoryBeforeConditionalM2cbNarrowings",
        "historicalConservativeAliasRecords": 5986,
        "historicalConservativeAliasWriterRecords": 5485,
        "historicalConservativeAliasWriterSites": 5099,
        "targetAndNeighborBytes": list(range(0x011A, 0x0120)) + list(range(0x0212, 0x0218)),
        "wordCopies": copies, "codeOwnedZeroCandidates": zeros,
        "sourceBufferBitWrites": bits, "indexedBitmapCandidates": indexed,
        "memoryContextHazards": hazards, "writers": copies + zeros + bits + indexed + hazards,
        "unknownOutsideReviewedCodeOrIndirectContext": True,
        "alternativeLrbScbUspContextsRequireSeparateProof": True,
        "implicitInterruptFrameAddressDomain": "Unknown_NotTechnicalSSP07FE",
        "sameValueWritesDeduplicated": False, "actualCpuExecutions": 0,
        "actualOriginalRomExecutions": 0, "actualRetiredInstructions": 0,
        "currentMachineOwnerEstablished": False, "firmwareReady": False,
    })
