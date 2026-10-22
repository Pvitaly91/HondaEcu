"""Closed, pure M2bs instruction-extent interpretation; never a ROM executor.

The fifteen M2bc forms are recognized by the unchanged independent decoder.
Additional closed context/boundary forms use the independently reviewed manual
forms retained by M2x/M2y/M2aa, not production Rust tables or CPU output.
An exact single extent is supplied by the read-only verifier; this module does
not open files, progress through a stream, execute instructions, or retain state.
PROGRAM instruction reads are not functional DATA reads. Returned effects are
static documented obligations, not observations of an actual machine.
"""
from dataclasses import fields

from independent_decoder import DecoderRequest, ExplicitDecodeError, decode_instruction


class DecodeFailure(ValueError):
    """A closed-profile refusal, with no payload or private path in its text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


FLAGS = ("CF", "ZF", "HC", "DD", "OtherPSW")
PRIMARY = {
    "lb-a-page": "IM1991:3-70",
    "sllb-a": "IM1991:3-144",
    "rolb-page": "IM1991:3-120",
    "lb-a-r0": "IM1991:3-70",
    "andb-a-page": "IM1991:3-24",
    "cmp-page-imm16": "IM1991:3-38",
    "jlt-rel8": "IM1991:3-66/3-67",
    "movb-r1-page": "IM1991:3-99",
    "andb-page-a": "IM1991:3-25",
    "jbs-page-bit7": "IM1991:3-65",
    "jbs-page-bit5": "IM1991:3-65",
    "orb-page-imm8": "IM1991:3-110",
    "orb-a-imm8": "IM1991:3-107",
    "lb-a-imm8": "IM1991:3-70",
    "stb-a-page": "IM1991:3-155",
    "l-a-page": "IM1991:3-69",
    "st-a-page": "IM1991:3-154",
    "jne-rel8": "IM1991:3-66/3-67",
    "andb-zero-a": "IM1991:3-25",
    "orb-zero-a": "IM1991:3-108",
    "movb-r0-imm8": "IM1991:3-99",
    "st-a-er1": "IM1991:3-154",
    "jbr-page-bit2": "IM1991:3-64",
    "cmpb-page-imm8": "IM1991:3-42",
}
FLAG_RULES = {
    "lb-a-page": {"ZF": "LoadedByteEqualsZero", "DD": "Set0"},
    "lb-a-r0": {"ZF": "LoadedByteEqualsZero", "DD": "Set0"},
    "lb-a-imm8": {"ZF": "LoadedByteEqualsZero", "DD": "Set0"},
    "sllb-a": {"CF": "OldALBit7"},
    "rolb-page": {"CF": "OldDataByteBit7", "inputCF": "OldCFBecomesResultBit0"},
    "andb-a-page": {"ZF": "NewALByteEqualsZero"},
    "andb-page-a": {"ZF": "WrittenDataByteEqualsZero"},
    "cmp-page-imm16": {"CF": "UnsignedDataWordLessThanImmediate16",
                       "ZF": "DataWordEqualsImmediate16"},
    "orb-page-imm8": {"ZF": "WrittenDataByteEqualsZero"},
    "orb-a-imm8": {"ZF": "NewALByteEqualsZero"},
    "l-a-page": {"ZF": "LoadedWordEqualsZero", "DD": "Set1"},
    "andb-zero-a": {"ZF": "WrittenDataByteEqualsZero"},
    "orb-zero-a": {"ZF": "WrittenDataByteEqualsZero"},
    "cmpb-page-imm8": {"CF": "UnsignedDataByteLessThanImmediate8",
                        "ZF": "DataByteEqualsImmediate8"},
}


def _integer(value, low, high, code):
    if type(value) is not int or not low <= value <= high:
        raise DecodeFailure(code)


def _access(address, width, mode, *, operation=None):
    result = {"address": address, "widthBits": width, "mode": mode,
              "space": "DATA", "byteOrder": "LittleEndian" if width == 16 else "Byte"}
    if operation is not None:
        result.update(operation=operation, ordered=True,
                      sameValueWrite="RetainFreshOrdinal")
    return result


def _operand(operand):
    return {"kind": type(operand).__name__,
            **{field.name: getattr(operand, field.name) for field in fields(operand)}}


def _result(form, length, pc, dd, operands, reads, writes, flags_written=(),
            flags_read=(), *, target=None, predicate=None, dd_after=None,
            dd_selection="AcceptsBothIncomingDD", al_write=None):
    next_pc = pc + length
    return {
        "pc": pc, "formId": form, "length": length, "incomingDd": dd,
        "resultingDd": dd if dd_after is None else dd_after,
        "ddApplicability": dd_selection,
        "typedOperands": operands, "nextPc": next_pc,
        "successors": [next_pc] if target is None else [target, next_pc],
        "branch": None if target is None else {
            "predicate": predicate, "trueTarget": target,
            "falseTarget": next_pc, "signedDelta": target - next_pc},
        "dataReads": reads, "dataWrites": writes,
        "flagEffects": {"read": list(flags_read), "written": list(flags_written),
                        "preserved": [flag for flag in FLAGS if flag not in flags_written],
                        "rules": dict(FLAG_RULES.get(form, {})),
                        "selectionRead": ["DD"] if dd_selection.startswith("RequiresDD") else []},
        "registerEffects": {
            "A": "Preserved" if al_write is None else "ALUpdated_AHRetained",
            "AL": "Preserved" if al_write is None else al_write,
            "AH": "Preserved", "LRB": "Preserved", "SCB": "Preserved",
            "SSP": "Preserved_NoDocumentedStackAccess",
            "X1_X2_DP_USP": "Preserved_NoScopedPointingAccess",
            "SF": "UnknownMeaningStorage_NoScopedWriterClaim"},
        "primaryReference": PRIMARY[form],
        "classification": "StaticDocumentedExtentInterpretation_NotExecution",
        "programFetchIsDataOperandRead": False,
        "actualExecutionObserved": False,
    }


def _context_extent(payload, pc, dd):
    """Closed documentary forms, with parameters but no stream matching.

    Code-cell authority is the same IM1991 manufacturer manual as M2bc; the
    read-only validator binds the retained primary reviews and actual private
    ROM/listing extents separately. No OEM payload is embedded here.
    """
    first = payload[0]
    word_store = first == 0xD4 and dd == 1
    cmpb = first == 0xC4 and len(payload) >= 3 and payload[2] == 0xC0
    if first not in (0xE4, 0xCE, 0xC5, 0x98, 0x89, 0xDA) and not word_store and not cmpb:
        return None
    length = 4 if cmpb else 3 if first in (0xC5, 0xDA) else 1 if first == 0x89 else 2
    if len(payload) < length:
        raise DecodeFailure("TruncatedEncoding")
    if len(payload) > length:
        raise DecodeFailure("TrailingBytes")
    if pc + length > 0x10000 or (first in (0xCE, 0xDA) and pc + length > 0xFFFF):
        raise DecodeFailure("OriginSpanOutsideProfile")
    if cmpb:
        return _result("cmpb-page-imm8", 4, pc, dd,
                       [{"kind": "PageOffset8", "value": payload[1]},
                        {"kind": "Immediate8", "value": payload[3]}],
                       [_access(0x100 + payload[1], 8, "CurrentPage")], [], ("CF", "ZF"))
    if first == 0x98:
        return _result("movb-r0-imm8", 2, pc, dd,
                       [{"kind": "Register0", "value": 0},
                        {"kind": "Immediate8", "value": payload[1]}], [],
                       [_access(0x108, 8, "LocalRegister", operation="CopyImmediateByte")])
    if first == 0x89:
        if dd != 1:
            raise DecodeFailure("WrongDD")
        return _result("st-a-er1", 1, pc, dd,
                       [{"kind": "AccumulatorA"}, {"kind": "RegisterPair1", "value": 1}], [],
                       [_access(0x10A, 16, "LocalRegister", operation="StoreWord")],
                       dd_selection="RequiresDD1")
    if first in (0xE4, 0xD4):
        if payload[1] & 1:
            raise DecodeFailure("OddWordOffsetOutsideProfile")
        operands = [{"kind": "AccumulatorA"},
                    {"kind": "EvenPageOffset8", "value": payload[1]}]
        address = 0x100 + payload[1]
        if word_store:
            return _result("st-a-page", 2, pc, dd, operands, [],
                           [_access(address, 16, "CurrentPage", operation="StoreWord")],
                           dd_selection="RequiresDD1")
        result = _result("l-a-page", 2, pc, dd, operands,
                         [_access(address, 16, "CurrentPage")], [],
                         ("ZF", "DD"), dd_after=1)
        result["registerEffects"].update(A="LoadWord", AL="LoadedWordLowByte",
                                         AH="LoadedWordHighByte_NotPreserved")
        return result
    if first in (0xCE, 0xDA):
        raw = payload[-1]
        delta = raw if raw < 128 else raw - 256
        target = pc + length + delta
        if not 0 <= target <= 0xFFFF:
            raise DecodeFailure("RelativeTargetOutsideProfile")
        if first == 0xDA:
            address = 0x100 + payload[1]
            return _result("jbr-page-bit2", 3, pc, dd,
                           [{"kind": "PageBit2", "offset": payload[1], "bit": 2},
                            {"kind": "TargetPC16", "value": target}],
                           [_access(address, 8, "CurrentPage")], [], target=target,
                           predicate={"kind": "MemoryBitEquals", "address": address,
                                      "bit": 2, "value": 0})
        return _result("jne-rel8", 2, pc, dd,
                       [{"kind": "TargetPC16", "value": target}], [], [],
                       flags_read=("ZF",), target=target,
                       predicate={"kind": "FlagEquals", "flag": "ZF", "value": 0})
    if payload[2] not in (0xD1, 0xE1):
        raise DecodeFailure("UnsupportedEncoding")
    form, operation = (("andb-zero-a", "ReadModifyWriteAnd") if payload[2] == 0xD1
                       else ("orb-zero-a", "ReadModifyWriteOr"))
    address = payload[1]
    result = _result(form, 3, pc, dd,
                     [{"kind": "ZeroPageOffset8", "value": address},
                      {"kind": "AccumulatorA"}],
                     [_access(address, 8, "ZeroPage")],
                     [_access(address, 8, "ZeroPage", operation=operation)], ("ZF",))
    result["sfrOrPeripheralStateOwnership"] = "NotEstablishedByInstructionDecoding"
    return result


def decode_extent(payload, pc, incoming_dd, *, lrb=0x21):
    """Decode one complete reviewed extent without observing or executing CPU state.

    LRB0021 is a declared conditional context, never a freshly established
    runtime value. The verifier separately proves that an extent came from the
    immutable candidate and that its native PC/operands match the frozen scope.
    """
    if type(payload) is not bytes or not 1 <= len(payload) <= 5:
        raise DecodeFailure("ExtentBytesInvalid")
    _integer(pc, 0, 0xFFFF, "PcInvalid")
    _integer(incoming_dd, 0, 1, "IncomingDdInvalid")
    if type(lrb) is not int or lrb != 0x21:
        raise DecodeFailure("UnsupportedLrbContext")
    context = _context_extent(payload, pc, incoming_dd)
    if context is not None:
        return context
    decoded = decode_instruction(DecoderRequest(payload, incoming_dd, pc))
    if isinstance(decoded, ExplicitDecodeError):
        raise DecodeFailure(decoded.code.value)
    form = decoded.reviewed_form_id.value
    operands = [_operand(value) for value in decoded.typed_operands]
    reads, writes, flags_written, flags_read = [], [], (), ()
    dd_after, al_write, target, predicate = None, None, None, None
    requires_dd0 = form in ("sllb-a", "andb-a-page", "orb-a-imm8", "stb-a-page")
    page = 0x100
    offset = next((item["value"] for item in operands
                   if item["kind"] in ("PageOffset8", "EvenPageOffset8")), None)
    if form in ("jbs-page-bit7", "jbs-page-bit5"):
        offset = operands[0]["offset"]
    address = None if offset is None else page + offset
    if form == "lb-a-page":
        reads = [_access(address, 8, "CurrentPage")]
        flags_written, dd_after, al_write = ("ZF", "DD"), 0, "LoadByteRetainAH"
    elif form == "lb-a-r0":
        reads = [_access(0x108, 8, "LocalRegister")]
        flags_written, dd_after, al_write = ("ZF", "DD"), 0, "LoadByteRetainAH"
    elif form == "lb-a-imm8":
        flags_written, dd_after, al_write = ("ZF", "DD"), 0, "LoadImmediateByteRetainAH"
    elif form == "sllb-a":
        flags_written, al_write = ("CF",), "LogicalShiftLeft8_CFfromOldAL7"
    elif form == "rolb-page":
        reads = [_access(address, 8, "CurrentPage")]
        writes = [_access(address, 8, "CurrentPage", operation="ReadModifyWriteRotateThroughCarry")]
        flags_read, flags_written = ("CF",), ("CF",)
    elif form == "andb-a-page":
        reads = [_access(address, 8, "CurrentPage")]
        flags_written, al_write = ("ZF",), "AndByteRetainAH"
    elif form == "cmp-page-imm16":
        reads = [_access(address, 16, "CurrentPage")]
        flags_written = ("CF", "ZF")
    elif form == "jlt-rel8":
        flags_read, target = ("CF",), decoded.relative_target_pc
        predicate = {"kind": "FlagEquals", "flag": "CF", "value": 1}
    elif form == "movb-r1-page":
        reads = [_access(address, 8, "CurrentPage")]
        writes = [_access(0x109, 8, "LocalRegister", operation="CopyByte")]
    elif form == "andb-page-a":
        reads = [_access(address, 8, "CurrentPage")]
        writes = [_access(address, 8, "CurrentPage", operation="ReadModifyWriteAnd")]
        flags_written = ("ZF",)
    elif form in ("jbs-page-bit7", "jbs-page-bit5"):
        reads = [_access(address, 8, "CurrentPage")]
        target = decoded.relative_target_pc
        predicate = {"kind": "MemoryBitEquals", "address": address,
                     "bit": operands[0]["bit"], "value": 1}
    elif form == "orb-page-imm8":
        reads = [_access(address, 8, "CurrentPage")]
        writes = [_access(address, 8, "CurrentPage", operation="ReadModifyWriteOr")]
        flags_written = ("ZF",)
    elif form == "orb-a-imm8":
        flags_written, al_write = ("ZF",), "OrImmediateByteRetainAH"
    elif form == "stb-a-page":
        writes = [_access(address, 8, "CurrentPage", operation="StoreByte")]
    else:
        raise DecodeFailure("UnsupportedDocumentedEffects")
    return _result(form, decoded.length, pc, incoming_dd, operands, reads, writes,
                   flags_written, flags_read, target=target, predicate=predicate,
                   dd_after=dd_after,
                   dd_selection="RequiresDD0" if requires_dd0 else "AcceptsBothIncomingDD",
                   al_write=al_write)
