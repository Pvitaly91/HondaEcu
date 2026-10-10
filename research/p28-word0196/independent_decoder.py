"""Own closed MSM66201/nX-8/200 synthetic single-instruction decoder.

PrimaryManualDerivedIndependentImplementation, not legal clean-room certification.
Recognition was authored from the manufacturer code columns, independently of
encoder emission and the separately sealed test grammar. Shared imports below
are public immutable types only, never encoder functions, tables or oracle rules.
No file/ROM/CPU/process/network, stream progression or runtime authority exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TypeAlias

from independent_encoder import (
    FormId, AccumulatorA, Register0, Register1, PageOffset8, EvenPageOffset8,
    Immediate8, Immediate16, PageBit7, PageBit5, TargetPC16,
)


@unique
class DecodeErrorCode(str, Enum):
    REQUEST_SHAPE = "RequestShape"
    ENCODED_BYTES_INVALID = "EncodedBytesInvalid"
    ENCODED_LENGTH_OUTSIDE_PROFILE = "EncodedLengthOutsideProfile"
    INCOMING_DD_INVALID = "IncomingDDInvalid"
    ORIGIN_INVALID = "OriginInvalid"
    ORIGIN_SPAN_OUTSIDE_PROFILE = "OriginSpanOutsideProfile"
    UNSUPPORTED_ENCODING = "UnsupportedEncoding"
    WRONG_DD = "WrongDD"
    TRUNCATED_ENCODING = "TruncatedEncoding"
    TRAILING_BYTES = "TrailingBytes"
    ODD_WORD_OFFSET_OUTSIDE_PROFILE = "OddWordOffsetOutsideProfile"
    RELATIVE_TARGET_OUTSIDE_PROFILE = "RelativeTargetOutsideProfile"
    AMBIGUOUS_PROFILE_MATCH = "AmbiguousProfileMatch"


@unique
class DecodeInputClassification(str, Enum):
    EXACT_SUPPORTED_FORM = "ExactSupportedForm"
    TRUNCATED_ENCODING = "TruncatedEncoding"
    TRAILING_BYTES = "TrailingBytes"
    UNSUPPORTED_ENCODING_WITHIN_PROFILE = "UnsupportedEncodingWithinProfile"
    WRONG_DD = "WrongDD"
    PROFILE_RESTRICTION_VIOLATION = "ProfileRestrictionViolation"
    MALFORMED_REQUEST = "MalformedRequest"
    AMBIGUOUS_PROFILE_MATCH = "AmbiguousProfileMatch"


@unique
class DDEffect(str, Enum):
    SETS_DD0_WHEN_EXECUTED = "SetsDD0WhenExecuted"
    PRESERVES_DD_WHEN_EXECUTED = "PreservesDDWhenExecuted"


Operand: TypeAlias = (
    AccumulatorA | Register0 | Register1 | PageOffset8 | EvenPageOffset8
    | Immediate8 | Immediate16 | PageBit7 | PageBit5 | TargetPC16
)


@dataclass(frozen=True, slots=True)
class DecoderRequest:
    encoded_bytes: bytes
    incoming_dd: int
    origin_pc: int


@dataclass(frozen=True, slots=True)
class DecodedInstruction:
    reviewed_form_id: FormId
    typed_operands: tuple[Operand, ...]
    length: int
    origin_pc: int
    incoming_dd: int
    relative_target_pc: int | None
    documented_dd_effect: DDEffect
    classification: str = field(default="SyntheticInstructionDecodingOnly", init=False)
    input_classification: DecodeInputClassification = field(
        default=DecodeInputClassification.EXACT_SUPPORTED_FORM, init=False,
    )


@dataclass(frozen=True, slots=True)
class ExplicitDecodeError:
    code: DecodeErrorCode

    @property
    def input_classification(self) -> DecodeInputClassification:
        if self.code in (DecodeErrorCode.REQUEST_SHAPE, DecodeErrorCode.ENCODED_BYTES_INVALID,
                         DecodeErrorCode.INCOMING_DD_INVALID, DecodeErrorCode.ORIGIN_INVALID):
            return DecodeInputClassification.MALFORMED_REQUEST
        if self.code in (DecodeErrorCode.ENCODED_LENGTH_OUTSIDE_PROFILE,
                         DecodeErrorCode.ORIGIN_SPAN_OUTSIDE_PROFILE,
                         DecodeErrorCode.ODD_WORD_OFFSET_OUTSIDE_PROFILE,
                         DecodeErrorCode.RELATIVE_TARGET_OUTSIDE_PROFILE):
            return DecodeInputClassification.PROFILE_RESTRICTION_VIOLATION
        if self.code is DecodeErrorCode.UNSUPPORTED_ENCODING:
            return DecodeInputClassification.UNSUPPORTED_ENCODING_WITHIN_PROFILE
        if self.code is DecodeErrorCode.WRONG_DD:
            return DecodeInputClassification.WRONG_DD
        if self.code is DecodeErrorCode.TRUNCATED_ENCODING:
            return DecodeInputClassification.TRUNCATED_ENCODING
        if self.code is DecodeErrorCode.TRAILING_BYTES:
            return DecodeInputClassification.TRAILING_BYTES
        return DecodeInputClassification.AMBIGUOUS_PROFILE_MATCH


DecodingResult: TypeAlias = DecodedInstruction | ExplicitDecodeError


def _request_slots_present(request: DecoderRequest) -> bool:
    try:
        for name in DecoderRequest.__slots__:
            object.__getattribute__(request, name)
    except AttributeError:
        return False
    return True


def _header_matches(payload: bytes) -> list[tuple[FormId, int]]:
    """Own exact code-column recognition, called only after complete headers.

    No shortest-prefix matching, generic registry or external inverse emitter.
    Every condition is independent; multiple matches would fail closed. These
    fifteen fixed conditions are disjoint, so that guard is normally unreachable.
    """
    first = payload[0]
    matches: list[tuple[FormId, int]] = []
    if first == 0xF4:  # LB, printed3-70
        matches.append((FormId.LB_A_PAGE, 2))
    if first == 0x53:  # SLLB, printed3-144; DD checked separately
        matches.append((FormId.SLLB_A, 1))
    if first == 0xC4 and payload[2] == 0xB7:  # ROLB, printed3-120
        matches.append((FormId.ROLB_PAGE, 3))
    if first == 0x78:  # LB local register0 ONLY, printed3-70
        matches.append((FormId.LB_A_R0, 1))
    if first == 0xD7:  # ANDB accumulator, printed3-24
        matches.append((FormId.ANDB_A_PAGE, 2))
    if first == 0xB4 and payload[2] == 0xC0:  # CMP word immediate, printed3-38
        matches.append((FormId.CMP_PAGE_IMM16, 5))
    if first == 0xCA:  # JLT ONLY, printed3-66/67; no C8 interpretation
        matches.append((FormId.JLT_REL8, 2))
    if first == 0xC4 and payload[2] == 0x49:  # MOVB r1 ONLY, printed3-99
        matches.append((FormId.MOVB_R1_PAGE, 3))
    if first == 0xC4 and payload[2] == 0xD1:  # ANDB object, printed3-25
        matches.append((FormId.ANDB_PAGE_A, 3))
    if first == 0xEF:  # JBS bit7 ONLY, printed3-65
        matches.append((FormId.JBS_PAGE_BIT7, 3))
    if first == 0xED:  # JBS bit5 ONLY, printed3-65
        matches.append((FormId.JBS_PAGE_BIT5, 3))
    if first == 0xC4 and payload[2] == 0xE0:  # ORB immediate, printed3-110
        matches.append((FormId.ORB_PAGE_IMM8, 4))
    if first == 0xE6:  # ORB accumulator, printed3-107
        matches.append((FormId.ORB_A_IMM8, 2))
    if first == 0x77:  # LB immediate, printed3-70
        matches.append((FormId.LB_A_IMM8, 2))
    if first == 0xD4:  # STB accumulator, printed3-155
        matches.append((FormId.STB_A_PAGE, 2))
    return matches


def decode_instruction(request: DecoderRequest) -> DecodingResult:
    """Pure single-payload validation, exact recognition, then typed construction.

    The preimplementation policy fixes precedence: shape, bytes,1..5 length, DD
    type, origin type, complete header, unique match, exact length, required DD,
    span, even CMP and linear branch target. No context is executed or mutated.
    """
    if type(request) is not DecoderRequest or not _request_slots_present(request):
        return ExplicitDecodeError(DecodeErrorCode.REQUEST_SHAPE)
    payload = request.encoded_bytes
    if type(payload) is not bytes:
        return ExplicitDecodeError(DecodeErrorCode.ENCODED_BYTES_INVALID)
    if not 1 <= len(payload) <= 5:
        return ExplicitDecodeError(DecodeErrorCode.ENCODED_LENGTH_OUTSIDE_PROFILE)
    if type(request.incoming_dd) is not int or request.incoming_dd not in (0, 1):
        return ExplicitDecodeError(DecodeErrorCode.INCOMING_DD_INVALID)
    if type(request.origin_pc) is not int or not 0 <= request.origin_pc <= 65535:
        return ExplicitDecodeError(DecodeErrorCode.ORIGIN_INVALID)
    if payload[0] in (0xC4, 0xB4) and len(payload) < 3:
        return ExplicitDecodeError(DecodeErrorCode.TRUNCATED_ENCODING)
    matches = _header_matches(payload)
    if not matches:
        return ExplicitDecodeError(DecodeErrorCode.UNSUPPORTED_ENCODING)
    if len(matches) != 1:
        return ExplicitDecodeError(DecodeErrorCode.AMBIGUOUS_PROFILE_MATCH)
    form, length = matches[0]
    if len(payload) < length:
        return ExplicitDecodeError(DecodeErrorCode.TRUNCATED_ENCODING)
    if len(payload) > length:
        return ExplicitDecodeError(DecodeErrorCode.TRAILING_BYTES)
    if form in (FormId.SLLB_A, FormId.ANDB_A_PAGE, FormId.ORB_A_IMM8, FormId.STB_A_PAGE) and request.incoming_dd != 0:
        return ExplicitDecodeError(DecodeErrorCode.WRONG_DD)
    relative = form in (FormId.JLT_REL8, FormId.JBS_PAGE_BIT7, FormId.JBS_PAGE_BIT5)
    next_pc = request.origin_pc + length
    if next_pc > 65536 or (relative and next_pc > 65535):
        return ExplicitDecodeError(DecodeErrorCode.ORIGIN_SPAN_OUTSIDE_PROFILE)
    if form is FormId.CMP_PAGE_IMM16 and payload[1] & 1:
        return ExplicitDecodeError(DecodeErrorCode.ODD_WORD_OFFSET_OUTSIDE_PROFILE)
    target: int | None = None
    if relative:
        raw = payload[-1]
        signed = raw if raw < 128 else raw - 256
        target = next_pc + signed
        if not 0 <= target <= 65535:
            return ExplicitDecodeError(DecodeErrorCode.RELATIVE_TARGET_OUTSIDE_PROFILE)

    # CONSTRUCTION BOUNDARY: complete syntax/context/profile validation passed.
    operands: tuple[Operand, ...]
    if form is FormId.LB_A_PAGE or form is FormId.ANDB_A_PAGE or form is FormId.STB_A_PAGE:
        operands = (AccumulatorA(), PageOffset8(payload[1]))
    elif form is FormId.SLLB_A:
        operands = (AccumulatorA(),)
    elif form is FormId.ROLB_PAGE:
        operands = (PageOffset8(payload[1]),)
    elif form is FormId.LB_A_R0:
        operands = (AccumulatorA(), Register0())
    elif form is FormId.CMP_PAGE_IMM16:
        word = payload[3] | (payload[4] << 8)
        operands = (EvenPageOffset8(payload[1]), Immediate16(word))
    elif form is FormId.JLT_REL8:
        assert target is not None  # Internal post-validation invariant, no guessed0.
        operands = (TargetPC16(target),)
    elif form is FormId.MOVB_R1_PAGE:
        operands = (Register1(), PageOffset8(payload[1]))
    elif form is FormId.ANDB_PAGE_A:
        operands = (PageOffset8(payload[1]), AccumulatorA())
    elif form is FormId.JBS_PAGE_BIT7:
        assert target is not None
        operands = (PageBit7(payload[1], 7), TargetPC16(target))
    elif form is FormId.JBS_PAGE_BIT5:
        assert target is not None
        operands = (PageBit5(payload[1], 5), TargetPC16(target))
    elif form is FormId.ORB_PAGE_IMM8:
        operands = (PageOffset8(payload[1]), Immediate8(payload[3]))
    else:  # Only the two reviewed immediate accumulator forms remain.
        operands = (AccumulatorA(), Immediate8(payload[1]))
    effect = (DDEffect.SETS_DD0_WHEN_EXECUTED
              if form in (FormId.LB_A_PAGE, FormId.LB_A_R0, FormId.LB_A_IMM8)
              else DDEffect.PRESERVES_DD_WHEN_EXECUTED)
    return DecodedInstruction(form, operands, length, request.origin_pc,
                              request.incoming_dd, target, effect)
