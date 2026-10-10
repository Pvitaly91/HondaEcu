"""Independent M2bb PRIMARY-MANUAL expected-vector oracle, tests only.

This is NOT the typed encoder implementation or an operational assembler API.
Only scalar synthetic fixtures are accepted. No encoder, ASM662, decoder or
executor is imported. Expected tuples use independent arithmetic, not emitter
results. No binary, ROM, file, process or CPU execution interface exists.
"""
from dataclasses import dataclass

MANUAL_SHA256 = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
M2AY_SHA256 = "a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44"


@dataclass(frozen=True, slots=True)
class FormFact:
    form_id: str
    mnemonic: str
    pdf_page: int
    printed_page: str
    operand_kinds: tuple[str, ...]
    length: int
    dd_values: tuple[int, ...]
    old_values: tuple
    old_origin: int
    old_expected: tuple[int, ...]
    new_values: tuple
    new_origin: int
    new_expected: tuple[int, ...]


# Independently re-read manufacturer code columns and DD cells for M2bb.
# The new examples differ from the already sealed M2ay examples.
FORMS = (
    FormFact("lb-a-page", "LB A,off N8", 124, "3-70", ("AccumulatorA", "PageOffset8"), 2, (0, 1), (None, 55), 256, (244, 55), (None, 93), 4096, (244, 93)),
    FormFact("sllb-a", "SLLB A", 197, "3-144", ("AccumulatorA",), 1, (0,), (None,), 256, (83,), (None,), 4096, (83,)),
    FormFact("rolb-page", "ROLB off N8", 173, "3-120", ("PageOffset8",), 3, (0, 1), (55,), 256, (196, 55, 183), (93,), 4096, (196, 93, 183)),
    FormFact("lb-a-r0", "LB A,r0", 124, "3-70", ("AccumulatorA", "Register0"), 1, (0, 1), (None, 0), 256, (120,), (None, 0), 4096, (120,)),
    FormFact("andb-a-page", "ANDB A,off N8", 76, "3-24", ("AccumulatorA", "PageOffset8"), 2, (0,), (None, 55), 256, (215, 55), (None, 93), 4096, (215, 93)),
    FormFact("cmp-page-imm16", "CMP off N8,#N16", 90, "3-38", ("EvenPageOffset8", "Immediate16"), 5, (0, 1), (54, 42330), 256, (180, 54, 192, 90, 165), (94, 4660), 4096, (180, 94, 192, 52, 18)),
    FormFact("jlt-rel8", "JLT rel8", 120, "3-66/3-67", ("TargetPC16",), 2, (0, 1), (265,), 256, (202, 7), (4079,), 4096, (202, 237)),
    FormFact("movb-r1-page", "MOVB r1,off N8", 153, "3-99", ("Register1", "PageOffset8"), 3, (0, 1), (1, 55), 256, (196, 55, 73), (1, 93), 4096, (196, 93, 73)),
    FormFact("andb-page-a", "ANDB off N8,A", 77, "3-25", ("PageOffset8", "AccumulatorA"), 3, (0, 1), (55, None), 256, (196, 55, 209), (93, None), 4096, (196, 93, 209)),
    FormFact("jbs-page-bit7", "JBS off N8.7,rel8", 119, "3-65", ("PageBit7", "TargetPC16"), 3, (0, 1), ((55, 7), 508), 512, (239, 55, 249), ((93, 7), 4202), 4096, (239, 93, 103)),
    FormFact("jbs-page-bit5", "JBS off N8.5,rel8", 119, "3-65", ("PageBit5", "TargetPC16"), 3, (0, 1), ((55, 5), 778), 768, (237, 55, 7), ((93, 5), 3971), 4096, (237, 93, 128)),
    FormFact("orb-page-imm8", "ORB off N'8,#N8", 163, "3-110", ("PageOffset8", "Immediate8"), 4, (0, 1), (55, 166), 256, (196, 55, 224, 166), (93, 129), 4096, (196, 93, 224, 129)),
    FormFact("orb-a-imm8", "ORB A,#N8", 160, "3-107", ("AccumulatorA", "Immediate8"), 2, (0,), (None, 166), 256, (230, 166), (None, 129), 4096, (230, 129)),
    FormFact("lb-a-imm8", "LB A,#N8", 124, "3-70", ("AccumulatorA", "Immediate8"), 2, (0, 1), (None, 166), 256, (119, 166), (None, 129), 4096, (119, 129)),
    FormFact("stb-a-page", "STB A,off N8", 208, "3-155", ("AccumulatorA", "PageOffset8"), 2, (0,), (None, 55), 256, (212, 55), (None, 93), 4096, (212, 93)),
)
FORM_IDS = tuple(f.form_id for f in FORMS)


def primary_expected(form_id: str, values: tuple, origin: int) -> tuple[int, ...]:
    """Expected integer octets for valid invented fixtures, never emitted data."""
    fact = next((row for row in FORMS if row.form_id == form_id), None)
    if fact is None or type(form_id) is not str or type(values) is not tuple:
        raise ValueError("Only sealed synthetic form fixtures")
    if len(values) != len(fact.operand_kinds) or type(origin) is not int or not 0 <= origin <= 65535:
        raise ValueError("Invalid oracle fixture")
    if origin + fact.length > 65536:
        raise ValueError("Fixture exceeds conservative instruction extent")
    for kind, value in zip(fact.operand_kinds, values):
        if kind == "AccumulatorA":
            if value is not None:
                raise ValueError("Fixed accumulator fixture")
            continue
        if kind in ("PageBit7", "PageBit5"):
            if type(value) is not tuple or len(value) != 2 or type(value[1]) is not int or value[1] != int(kind[-1]):
                raise ValueError("Fixed bit fixture")
            value = value[0]
        maximum = 65535 if kind in ("Immediate16", "TargetPC16") else 255
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError("Oracle fixture scalar width")
        if kind == "EvenPageOffset8" and value % 2:
            raise ValueError("Conservative even-offset profile, not ISA illegality")
        if kind.startswith("Register") and value != int(kind[-1]):
            raise ValueError("Fixed register fixture")
    if form_id == "lb-a-page":
        return (244, values[1])
    if form_id == "sllb-a":
        return (83,)
    if form_id == "rolb-page":
        return (196, values[0], 183)
    if form_id == "lb-a-r0":
        return (120,)
    if form_id == "andb-a-page":
        return (215, values[1])
    if form_id == "cmp-page-imm16":
        high, low = divmod(values[1], 256)
        return (180, values[0], 192, low, high)
    if form_id in ("jlt-rel8", "jbs-page-bit7", "jbs-page-bit5"):
        next_pc = origin + fact.length
        if next_pc > 65535:
            raise ValueError("Conservative no-wrap fixture profile")
        delta = values[-1] - next_pc
        if not -128 <= delta <= 127:
            raise ValueError("Out-of-range fixture displacement")
        representation = delta % 256  # Only after mathematical signed validation.
        if form_id == "jlt-rel8":
            return (202, representation)
        return (239 if form_id == "jbs-page-bit7" else 237, values[0][0], representation)
    if form_id == "movb-r1-page":
        return (196, values[1], 73)
    if form_id == "andb-page-a":
        return (196, values[0], 209)
    if form_id == "orb-page-imm8":
        return (196, values[0], 224, values[1])
    if form_id == "orb-a-imm8":
        return (230, values[1])
    if form_id == "lb-a-imm8":
        return (119, values[1])
    if form_id == "stb-a-page":
        return (212, values[1])
    raise AssertionError("Unreviewed form escaped closed fixture oracle")


def check_literal_examples() -> int:
    """Cross-check independent math against thirty pre-declared literal cases."""
    count = 0
    for fact in FORMS:
        for values, origin, expected in (
            (fact.old_values, fact.old_origin, fact.old_expected),
            (fact.new_values, fact.new_origin, fact.new_expected),
        ):
            assert primary_expected(fact.form_id, values, origin) == expected
            assert len(expected) == fact.length
            count += 1
    return count
