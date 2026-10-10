"""M2bc independent PRIMARY-MANUAL fixture grammar and scalar oracle.

No decoder, encoder, encoder oracle, ASM662 or production table is imported.
Rows are our fixed-cell reading of manufacturer code columns. Generated tuples
are synthetic expected inputs, never firmware, streams or execution authority.
"""
from dataclasses import dataclass

MANUAL_SHA256 = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
M2AY_SHA256 = "a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44"


@dataclass(frozen=True, slots=True)
class OperandRule:
    kind: str
    cells: tuple[int, ...] = ()
    fixed_tail: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ManualRow:
    form_id: str
    page: int
    printed_page: str
    frame: tuple
    operands: tuple[OperandRule, ...]
    dd0_required: bool = False
    sets_dd0_when_executed: bool = False

    @property
    def length(self):
        return len(self.frame)

    @property
    def fixed_cells(self):
        return tuple((i, cell) for i, cell in enumerate(self.frame) if type(cell) is int)

    @property
    def allowed_dd(self):
        return (0,) if self.dd0_required else (0, 1)


# Manufacturer functional facts, separately reviewed full pages for M2bc.
ROWS = (
    ManualRow("lb-a-page", 124, "3-70", (244, "offset"), (OperandRule("AccumulatorA"), OperandRule("PageOffset8", (1,))), sets_dd0_when_executed=True),
    ManualRow("sllb-a", 197, "3-144", (83,), (OperandRule("AccumulatorA"),), dd0_required=True),
    ManualRow("rolb-page", 173, "3-120", (196, "offset", 183), (OperandRule("PageOffset8", (1,)),)),
    ManualRow("lb-a-r0", 124, "3-70", (120,), (OperandRule("AccumulatorA"), OperandRule("Register0", fixed_tail=(0,))), sets_dd0_when_executed=True),
    ManualRow("andb-a-page", 76, "3-24", (215, "offset"), (OperandRule("AccumulatorA"), OperandRule("PageOffset8", (1,))), dd0_required=True),
    ManualRow("cmp-page-imm16", 90, "3-38", (180, "offset", 192, "low", "high"), (OperandRule("EvenPageOffset8", (1,)), OperandRule("Immediate16", (3, 4)))),
    ManualRow("jlt-rel8", 120, "3-66/3-67", (202, "delta"), (OperandRule("TargetPC16", (1,)),)),
    ManualRow("movb-r1-page", 153, "3-99", (196, "offset", 73), (OperandRule("Register1", fixed_tail=(1,)), OperandRule("PageOffset8", (1,)))),
    ManualRow("andb-page-a", 77, "3-25", (196, "offset", 209), (OperandRule("PageOffset8", (1,)), OperandRule("AccumulatorA"))),
    ManualRow("jbs-page-bit7", 119, "3-65", (239, "offset", "delta"), (OperandRule("PageBit7", (1,), (7,)), OperandRule("TargetPC16", (2,)))),
    ManualRow("jbs-page-bit5", 119, "3-65", (237, "offset", "delta"), (OperandRule("PageBit5", (1,), (5,)), OperandRule("TargetPC16", (2,)))),
    ManualRow("orb-page-imm8", 163, "3-110", (196, "offset", 224, "imm8"), (OperandRule("PageOffset8", (1,)), OperandRule("Immediate8", (3,)))),
    ManualRow("orb-a-imm8", 160, "3-107", (230, "imm8"), (OperandRule("AccumulatorA"), OperandRule("Immediate8", (1,))), dd0_required=True),
    ManualRow("lb-a-imm8", 124, "3-70", (119, "imm8"), (OperandRule("AccumulatorA"), OperandRule("Immediate8", (1,))), sets_dd0_when_executed=True),
    ManualRow("stb-a-page", 208, "3-155", (212, "offset"), (OperandRule("AccumulatorA"), OperandRule("PageOffset8", (1,))), dd0_required=True),
)
FORM_IDS = tuple(row.form_id for row in ROWS)
ERROR_CLASSIFICATIONS = {
    "RequestShape": "MalformedRequest", "EncodedBytesInvalid": "MalformedRequest",
    "EncodedLengthOutsideProfile": "ProfileRestrictionViolation",
    "IncomingDDInvalid": "MalformedRequest", "OriginInvalid": "MalformedRequest",
    "OriginSpanOutsideProfile": "ProfileRestrictionViolation",
    "UnsupportedEncoding": "UnsupportedEncodingWithinProfile", "WrongDD": "WrongDD",
    "TruncatedEncoding": "TruncatedEncoding", "TrailingBytes": "TrailingBytes",
    "OddWordOffsetOutsideProfile": "ProfileRestrictionViolation",
    "RelativeTargetOutsideProfile": "ProfileRestrictionViolation",
    "AmbiguousProfileMatch": "AmbiguousProfileMatch",
}


@dataclass(frozen=True, slots=True)
class ExpectedDecoded:
    form_id: str
    operands: tuple[tuple[str, tuple[int, ...]], ...]
    length: int
    origin: int
    incoming_dd: int
    relative_target: int | None
    dd_effect: str


@dataclass(frozen=True, slots=True)
class LiteralFixture:
    name: str
    form_id: str
    payload: tuple[int, ...]
    dd: int
    origin: int
    operands: tuple[tuple[str, tuple[int, ...]], ...]
    relative_target: int | None = None


# Fifteen old M2ay/M2ba PRIMARY literals, not M2bb encoder-derived results.
OLD_LITERALS = (
    LiteralFixture("old:lb-a-page", "lb-a-page", (244, 55), 0, 256, (("AccumulatorA", ()), ("PageOffset8", (55,)))),
    LiteralFixture("old:sllb-a", "sllb-a", (83,), 0, 256, (("AccumulatorA", ()),)),
    LiteralFixture("old:rolb-page", "rolb-page", (196, 55, 183), 0, 256, (("PageOffset8", (55,)),)),
    LiteralFixture("old:lb-a-r0", "lb-a-r0", (120,), 0, 256, (("AccumulatorA", ()), ("Register0", (0,)))),
    LiteralFixture("old:andb-a-page", "andb-a-page", (215, 55), 0, 256, (("AccumulatorA", ()), ("PageOffset8", (55,)))),
    LiteralFixture("old:cmp-page-imm16", "cmp-page-imm16", (180, 54, 192, 90, 165), 0, 256, (("EvenPageOffset8", (54,)), ("Immediate16", (42330,)))),
    LiteralFixture("old:jlt-rel8", "jlt-rel8", (202, 7), 0, 256, (("TargetPC16", (265,)),), 265),
    LiteralFixture("old:movb-r1-page", "movb-r1-page", (196, 55, 73), 0, 256, (("Register1", (1,)), ("PageOffset8", (55,)))),
    LiteralFixture("old:andb-page-a", "andb-page-a", (196, 55, 209), 0, 256, (("PageOffset8", (55,)), ("AccumulatorA", ()))),
    LiteralFixture("old:jbs-page-bit7", "jbs-page-bit7", (239, 55, 249), 0, 512, (("PageBit7", (55, 7)), ("TargetPC16", (508,))), 508),
    LiteralFixture("old:jbs-page-bit5", "jbs-page-bit5", (237, 55, 7), 0, 768, (("PageBit5", (55, 5)), ("TargetPC16", (778,))), 778),
    LiteralFixture("old:orb-page-imm8", "orb-page-imm8", (196, 55, 224, 166), 0, 256, (("PageOffset8", (55,)), ("Immediate8", (166,)))),
    LiteralFixture("old:orb-a-imm8", "orb-a-imm8", (230, 166), 0, 256, (("AccumulatorA", ()), ("Immediate8", (166,)))),
    LiteralFixture("old:lb-a-imm8", "lb-a-imm8", (119, 166), 0, 256, (("AccumulatorA", ()), ("Immediate8", (166,)))),
    LiteralFixture("old:stb-a-page", "stb-a-page", (212, 55), 0, 256, (("AccumulatorA", ()), ("PageOffset8", (55,)))),
)
# Fifteen NEW M2bc literals, deliberately different from M2bb extra examples.
NEW_LITERALS = (
    LiteralFixture("new:lb-a-page", "lb-a-page", (244, 163), 1, 12288, (("AccumulatorA", ()), ("PageOffset8", (163,)))),
    LiteralFixture("new:sllb-a", "sllb-a", (83,), 0, 12288, (("AccumulatorA", ()),)),
    LiteralFixture("new:rolb-page", "rolb-page", (196, 163, 183), 1, 12288, (("PageOffset8", (163,)),)),
    LiteralFixture("new:lb-a-r0", "lb-a-r0", (120,), 1, 12288, (("AccumulatorA", ()), ("Register0", (0,)))),
    LiteralFixture("new:andb-a-page", "andb-a-page", (215, 163), 0, 12288, (("AccumulatorA", ()), ("PageOffset8", (163,)))),
    LiteralFixture("new:cmp-page-imm16", "cmp-page-imm16", (180, 162, 192, 145, 108), 1, 12288, (("EvenPageOffset8", (162,)), ("Immediate16", (27793,)))),
    LiteralFixture("new:jlt-rel8", "jlt-rel8", (202, 250), 1, 8704, (("TargetPC16", (8700,)),), 8700),
    LiteralFixture("new:movb-r1-page", "movb-r1-page", (196, 163, 73), 1, 12288, (("Register1", (1,)), ("PageOffset8", (163,)))),
    LiteralFixture("new:andb-page-a", "andb-page-a", (196, 163, 209), 1, 12288, (("PageOffset8", (163,)), ("AccumulatorA", ()))),
    LiteralFixture("new:jbs-page-bit7", "jbs-page-bit7", (239, 163, 0), 1, 9216, (("PageBit7", (163, 7)), ("TargetPC16", (9219,))), 9219),
    LiteralFixture("new:jbs-page-bit5", "jbs-page-bit5", (237, 163, 127), 1, 9728, (("PageBit5", (163, 5)), ("TargetPC16", (9858,))), 9858),
    LiteralFixture("new:orb-page-imm8", "orb-page-imm8", (196, 163, 224, 75), 1, 12288, (("PageOffset8", (163,)), ("Immediate8", (75,)))),
    LiteralFixture("new:orb-a-imm8", "orb-a-imm8", (230, 75), 0, 12288, (("AccumulatorA", ()), ("Immediate8", (75,)))),
    LiteralFixture("new:lb-a-imm8", "lb-a-imm8", (119, 75), 1, 12288, (("AccumulatorA", ()), ("Immediate8", (75,)))),
    LiteralFixture("new:stb-a-page", "stb-a-page", (212, 163), 0, 12288, (("AccumulatorA", ()), ("PageOffset8", (163,)))),
)
LITERALS = OLD_LITERALS + NEW_LITERALS


def primary_payload(form_id, *, offset=55, immediate8=166, immediate16=42330, delta=7):
    """Expected synthetic input from OUR manufacturer column rows, not encoder."""
    row = next(row for row in ROWS if row.form_id == form_id)
    high, low = divmod(immediate16, 256)
    if not -128 <= delta <= 127:
        raise ValueError("Invalid fixture displacement, never repair range")
    values = {"offset": offset, "imm8": immediate8, "low": low, "high": high,
              "delta": delta if delta >= 0 else 256 + delta}
    result = tuple(cell if type(cell) is int else values[cell] for cell in row.frame)
    if any(type(cell) is not int or not 0 <= cell <= 255 for cell in result):
        raise ValueError("Invalid fixture unsigned width")
    return bytes(result)


def header_candidates(payload):
    return tuple(row for row in ROWS
                 if all(index < len(payload) and payload[index] == expected
                        for index, expected in row.fixed_cells))


def classify_primary(payload, dd, origin):
    """Test-only mathematical grammar oracle: ExpectedDecoded or error STRING."""
    if type(payload) is not bytes:
        return "EncodedBytesInvalid"
    if not 1 <= len(payload) <= 5:
        return "EncodedLengthOutsideProfile"
    if type(dd) is not int or dd not in (0, 1):
        return "IncomingDDInvalid"
    if type(origin) is not int or not 0 <= origin <= 65535:
        return "OriginInvalid"
    front = tuple(row for row in ROWS if row.frame[0] == payload[0])
    if front and len(payload) < min(max(index for index, _ in row.fixed_cells) + 1 for row in front):
        return "TruncatedEncoding"
    candidates = header_candidates(payload)
    if not candidates:
        return "UnsupportedEncoding"
    if len(candidates) != 1:
        return "AmbiguousProfileMatch"
    row = candidates[0]
    if len(payload) < row.length:
        return "TruncatedEncoding"
    if len(payload) > row.length:
        return "TrailingBytes"
    if row.dd0_required and dd != 0:
        return "WrongDD"
    branch = any(operand.kind == "TargetPC16" for operand in row.operands)
    next_pc = origin + row.length
    if next_pc > (65535 if branch else 65536):
        return "OriginSpanOutsideProfile"
    if any(operand.kind == "EvenPageOffset8" for operand in row.operands) and payload[1] % 2:
        return "OddWordOffsetOutsideProfile"
    typed = []
    target = None
    for operand in row.operands:
        if operand.kind == "Immediate16":
            fields = (sum(payload[index] * 256 ** significance
                          for significance, index in enumerate(operand.cells)),)
        elif operand.kind == "TargetPC16":
            raw_delta = payload[operand.cells[0]]
            signed = (raw_delta + 128) % 256 - 128
            target = next_pc + signed
            if not 0 <= target <= 65535:
                return "RelativeTargetOutsideProfile"
            fields = (target,)
        else:
            fields = tuple(payload[index] for index in operand.cells) + operand.fixed_tail
        typed.append((operand.kind, fields))
    effect = "SetsDD0WhenExecuted" if row.sets_dd0_when_executed else "PreservesDDWhenExecuted"
    return ExpectedDecoded(row.form_id, tuple(typed), row.length, origin, dd, target, effect)


def verify_literal_fixtures():
    for literal in LITERALS:
        result = classify_primary(bytes(literal.payload), literal.dd, literal.origin)
        assert type(result) is ExpectedDecoded
        assert result.form_id == literal.form_id and result.operands == literal.operands
        assert result.length == len(literal.payload) and result.relative_target == literal.relative_target
    return len(LITERALS)


def verify_closed_header_uniqueness():
    checked = 0
    ambiguities = 0
    for first in range(256):
        for third in range(256):
            count = len(header_candidates(bytes((first, 55, third, 0, 0))))
            ambiguities += int(count > 1)
            checked += 1
    assert ambiguities == 0
    assert len(tuple(row for row in ROWS if row.frame[0] == 196)) == 4
    assert classify_primary(bytes((196,)), 0, 256) == "TruncatedEncoding"
    assert classify_primary(bytes((196, 55)), 0, 256) == "TruncatedEncoding"
    return {"completeHeadersChecked": checked, "ambiguousCompleteHeaders": ambiguities,
            "sharedC4Forms": 4, "partialPrefixNeverGuessed": True}
