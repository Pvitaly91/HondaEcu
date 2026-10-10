"""Own bounded MSM66201/nX-8/200 single-instruction research encoder.

PrimaryManualDerivedIndependentImplementation, not legal clean-room certification.
Functional code columns were independently reviewed in the September1991 manual.
No ASM662/Doc table, decoder, executor or test oracle is an implementation input.
Only a validated synthetic request yields 1..5 immutable bytes in memory.
No file/ROM/CPU/subprocess, stream planner, linker, placement or firmware API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TypeAlias


@unique
class FormId(str, Enum):
    LB_A_PAGE = "lb-a-page"
    SLLB_A = "sllb-a"
    ROLB_PAGE = "rolb-page"
    LB_A_R0 = "lb-a-r0"
    ANDB_A_PAGE = "andb-a-page"
    CMP_PAGE_IMM16 = "cmp-page-imm16"
    JLT_REL8 = "jlt-rel8"
    MOVB_R1_PAGE = "movb-r1-page"
    ANDB_PAGE_A = "andb-page-a"
    JBS_PAGE_BIT7 = "jbs-page-bit7"
    JBS_PAGE_BIT5 = "jbs-page-bit5"
    ORB_PAGE_IMM8 = "orb-page-imm8"
    ORB_A_IMM8 = "orb-a-imm8"
    LB_A_IMM8 = "lb-a-imm8"
    STB_A_PAGE = "stb-a-page"


@unique
class ErrorCode(str, Enum):
    REQUEST_SHAPE = "RequestShape"
    UNSUPPORTED_FORM = "UnsupportedForm"
    INCOMING_DD_INVALID = "IncomingDDInvalid"
    WRONG_DD = "WrongDD"
    ORIGIN_INVALID = "OriginInvalid"
    ORIGIN_SPAN_OUTSIDE_PROFILE = "OriginSpanOutsideProfile"
    OPERAND_COUNT = "OperandCount"
    OPERAND_KIND = "OperandKind"
    OPERAND_SHAPE = "OperandShape"
    OPERAND_RANGE = "OperandRange"
    FIXED_OPERAND_MISMATCH = "FixedOperandMismatch"
    ODD_WORD_OFFSET_OUTSIDE_PROFILE = "OddWordOffsetOutsideProfile"
    REL8_OUT_OF_RANGE = "Rel8OutOfRange"


@dataclass(frozen=True, slots=True)
class AccumulatorA:
    pass


@dataclass(frozen=True, slots=True)
class Register0:
    value: int = 0


@dataclass(frozen=True, slots=True)
class Register1:
    value: int = 1


@dataclass(frozen=True, slots=True)
class PageOffset8:
    value: int


@dataclass(frozen=True, slots=True)
class EvenPageOffset8:
    """Conservative profile, not an ISA prohibition of odd aligned-down reads."""
    value: int


@dataclass(frozen=True, slots=True)
class Immediate8:
    value: int


@dataclass(frozen=True, slots=True)
class Immediate16:
    value: int


@dataclass(frozen=True, slots=True)
class PageBit7:
    offset: int
    bit: int = 7


@dataclass(frozen=True, slots=True)
class PageBit5:
    offset: int
    bit: int = 5


@dataclass(frozen=True, slots=True)
class TargetPC16:
    value: int


Operand: TypeAlias = (
    AccumulatorA | Register0 | Register1 | PageOffset8 | EvenPageOffset8
    | Immediate8 | Immediate16 | PageBit7 | PageBit5 | TargetPC16
)


@dataclass(frozen=True, slots=True)
class EncoderRequest:
    reviewed_form_id: FormId
    typed_operands: tuple[Operand, ...]
    incoming_dd: int
    origin_pc: int


@dataclass(frozen=True, slots=True)
class EncodedInstruction:
    reviewed_form_id: FormId
    encoded_bytes: bytes
    length: int
    origin_pc: int
    typed_operands: tuple[Operand, ...]
    incoming_dd: int
    classification: str = field(default="SyntheticInstructionEncodingOnly", init=False)


@dataclass(frozen=True, slots=True)
class ExplicitError:
    code: ErrorCode


EncodingResult: TypeAlias = EncodedInstruction | ExplicitError

# Fixed typed shapes/lengths only, NOT a generic mnemonic or opcode registry.
# Manufacturer references: LB3-70, SLLB3-144, ROLB3-120, ANDB3-24/25,
# CMP3-38, JLT3-66/67, MOVB3-99, JBS3-65, ORB3-107/110, STB3-155.
_FORM_SHAPES = (
    (FormId.LB_A_PAGE, 2, False, (AccumulatorA, PageOffset8)),
    (FormId.SLLB_A, 1, True, (AccumulatorA,)),
    (FormId.ROLB_PAGE, 3, False, (PageOffset8,)),
    (FormId.LB_A_R0, 1, False, (AccumulatorA, Register0)),
    (FormId.ANDB_A_PAGE, 2, True, (AccumulatorA, PageOffset8)),
    (FormId.CMP_PAGE_IMM16, 5, False, (EvenPageOffset8, Immediate16)),
    (FormId.JLT_REL8, 2, False, (TargetPC16,)),
    (FormId.MOVB_R1_PAGE, 3, False, (Register1, PageOffset8)),
    (FormId.ANDB_PAGE_A, 3, False, (PageOffset8, AccumulatorA)),
    (FormId.JBS_PAGE_BIT7, 3, False, (PageBit7, TargetPC16)),
    (FormId.JBS_PAGE_BIT5, 3, False, (PageBit5, TargetPC16)),
    (FormId.ORB_PAGE_IMM8, 4, False, (PageOffset8, Immediate8)),
    (FormId.ORB_A_IMM8, 2, True, (AccumulatorA, Immediate8)),
    (FormId.LB_A_IMM8, 2, False, (AccumulatorA, Immediate8)),
    (FormId.STB_A_PAGE, 2, True, (AccumulatorA, PageOffset8)),
)


def _slots_present(value: object, names: tuple[str, ...]) -> bool:
    try:
        for name in names:
            object.__getattribute__(value, name)
    except AttributeError:
        return False
    return True


def _unsigned(value: object, maximum: int) -> bool:
    # bool, subclasses, float, numeric text and coercion hooks are NOT integers.
    return type(value) is int and 0 <= value <= maximum


def encode_instruction(request: EncoderRequest) -> EncodingResult:
    """Pure, atomic validation then emission; no context or DD state mutation.

    General checks precede operands; operand errors are deterministic left-to-right,
    not a global priority between unrelated errors. Constructors deliberately
    retain malformed scalar values so this function can return ExplicitError.
    """
    if type(request) is not EncoderRequest or not _slots_present(request, EncoderRequest.__slots__):
        return ExplicitError(ErrorCode.REQUEST_SHAPE)
    form = request.reviewed_form_id
    if type(form) is not FormId or not any(form is member for member in FormId):
        return ExplicitError(ErrorCode.UNSUPPORTED_FORM)
    if not _unsigned(request.incoming_dd, 1):
        return ExplicitError(ErrorCode.INCOMING_DD_INVALID)
    _, length, requires_dd0, operand_types = next(shape for shape in _FORM_SHAPES if shape[0] is form)
    if requires_dd0 and request.incoming_dd != 0:
        return ExplicitError(ErrorCode.WRONG_DD)
    if not _unsigned(request.origin_pc, 65535):
        return ExplicitError(ErrorCode.ORIGIN_INVALID)
    relative = TargetPC16 in operand_types
    next_pc = request.origin_pc + length
    if next_pc > 65536 or (relative and next_pc > 65535):
        return ExplicitError(ErrorCode.ORIGIN_SPAN_OUTSIDE_PROFILE)
    operands = request.typed_operands
    if type(operands) is not tuple or len(operands) != len(operand_types):
        return ExplicitError(ErrorCode.OPERAND_COUNT)

    # Snapshot already validated immutable integer fields, not a partial byte buffer.
    scalars: list[tuple[int, ...]] = []
    displacement = 0
    for operand, expected_type in zip(operands, operand_types):
        if type(operand) is not expected_type:
            return ExplicitError(ErrorCode.OPERAND_KIND)
        if not _slots_present(operand, expected_type.__slots__):
            return ExplicitError(ErrorCode.OPERAND_SHAPE)
        if expected_type is AccumulatorA:
            scalars.append(())
            continue
        if expected_type in (PageBit7, PageBit5):
            if not _unsigned(operand.offset, 255):
                return ExplicitError(ErrorCode.OPERAND_RANGE)
            fixed_bit = 7 if expected_type is PageBit7 else 5
            if type(operand.bit) is not int or operand.bit != fixed_bit:
                return ExplicitError(ErrorCode.FIXED_OPERAND_MISMATCH)
            scalars.append((operand.offset, operand.bit))
            continue
        value = operand.value
        maximum = 65535 if expected_type in (Immediate16, TargetPC16) else 255
        if not _unsigned(value, maximum):
            return ExplicitError(ErrorCode.OPERAND_RANGE)
        if expected_type in (Register0, Register1) and value != (0 if expected_type is Register0 else 1):
            return ExplicitError(ErrorCode.FIXED_OPERAND_MISMATCH)
        if expected_type is EvenPageOffset8 and value % 2:
            return ExplicitError(ErrorCode.ODD_WORD_OFFSET_OUTSIDE_PROFILE)
        if expected_type is TargetPC16:
            displacement = value - next_pc
            if not -128 <= displacement <= 127:
                return ExplicitError(ErrorCode.REL8_OUT_OF_RANGE)
        scalars.append((value,))

    # EMISSION BOUNDARY: every structure/type/DD/span/range/rel8 check is complete.
    # Literal functional code components come from the exact manufacturer columns.
    if form is FormId.LB_A_PAGE:
        payload = bytes((0xF4, scalars[1][0]))
    elif form is FormId.SLLB_A:
        payload = bytes((0x53,))
    elif form is FormId.ROLB_PAGE:
        payload = bytes((0xC4, scalars[0][0], 0xB7))
    elif form is FormId.LB_A_R0:
        payload = bytes((0x78,))
    elif form is FormId.ANDB_A_PAGE:
        payload = bytes((0xD7, scalars[1][0]))
    elif form is FormId.CMP_PAGE_IMM16:
        immediate = scalars[1][0]
        payload = bytes((0xB4, scalars[0][0], 0xC0, immediate & 0xFF, (immediate >> 8) & 0xFF))
    elif form is FormId.JLT_REL8:
        payload = bytes((0xCA, displacement & 0xFF))
    elif form is FormId.MOVB_R1_PAGE:
        payload = bytes((0xC4, scalars[1][0], 0x49))
    elif form is FormId.ANDB_PAGE_A:
        payload = bytes((0xC4, scalars[0][0], 0xD1))
    elif form is FormId.JBS_PAGE_BIT7:
        payload = bytes((0xEF, scalars[0][0], displacement & 0xFF))
    elif form is FormId.JBS_PAGE_BIT5:
        payload = bytes((0xED, scalars[0][0], displacement & 0xFF))
    elif form is FormId.ORB_PAGE_IMM8:
        payload = bytes((0xC4, scalars[0][0], 0xE0, scalars[1][0]))
    elif form is FormId.ORB_A_IMM8:
        payload = bytes((0xE6, scalars[1][0]))
    elif form is FormId.LB_A_IMM8:
        payload = bytes((0x77, scalars[1][0]))
    else:  # The only remaining closed member is STB_A_PAGE.
        payload = bytes((0xD4, scalars[1][0]))
    assert len(payload) == length  # Internal invariant, never input validation/padding.
    return EncodedInstruction(form, payload, length, request.origin_pc, operands, request.incoming_dd)
