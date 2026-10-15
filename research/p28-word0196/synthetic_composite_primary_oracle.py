"""M2bj independently prepared primary facts; never imports operational codecs.

Per-instruction expectations derive from the September1991 manufacturer code
columns and the immutable M2ay/M2bb/M2bc/M2bg independent fixtures. The complete
reference exists only inside the test-oracle process; no output interface.
"""
from dataclasses import dataclass
from hashlib import sha256

import independent_encoder_oracle as primary_a
import independent_decoder_primary_oracle as grammar_a
import direct_j_primary_oracle as primary_j

MANUAL_SHA256 = primary_a.MANUAL_SHA256
EXACT_BASE = "7585bfc164929c19fa044664c4d8173244a426fa"
SCOPE = "word0196SoftwareAlternate18PlusTwoDirectJ"


@dataclass(frozen=True, slots=True)
class PrimaryNode:
    node_id: int | str
    form: str
    offset: int
    length: int
    values: tuple
    page: int
    target: int | None = None


# Reviewed operands/origins, not encoded output. No full program literal.
NODES = (
    PrimaryNode(21871, "lb-a-page", 0, 2, (None, 142), 124),
    PrimaryNode(21873, "sllb-a", 2, 1, (None,), 197),
    PrimaryNode(21874, "rolb-page", 3, 3, (142,), 173),
    PrimaryNode(21877, "lb-a-r0", 6, 1, (None, 0), 124),
    PrimaryNode(21878, "andb-a-page", 7, 2, (None, 142), 76),
    PrimaryNode(21880, "cmp-page-imm16", 9, 5, (150, 192), 90),
    PrimaryNode(21885, "jlt-rel8", 14, 2, (4138,), 120, 4138),
    PrimaryNode(21887, "movb-r1-page", 16, 3, (1, 23), 153),
    PrimaryNode(21890, "andb-page-a", 19, 3, (23, None), 77),
    PrimaryNode(21893, "jbs-page-bit7", 22, 3, ((42, 7), 4131), 119, 4131),
    PrimaryNode(21896, "jbs-page-bit5", 25, 3, ((36, 5), 4131), 119, 4131),
    PrimaryNode(21899, "andb-page-a", 28, 3, (143, None), 77),
    PrimaryNode(21902, "orb-page-imm8", 31, 4, (42, 1), 163),
    PrimaryNode(21906, "lb-a-page", 35, 2, (None, 143), 124),
    PrimaryNode(21908, "orb-a-imm8", 37, 2, (None, 240), 160),
    PrimaryNode("DirectJ_NotBelow", "j-address", 39, 3, (21910,), 116, 21910),
    PrimaryNode(21951, "lb-a-imm8", 42, 2, (None, 15), 124),
    PrimaryNode(21953, "stb-a-page", 44, 2, (None, 23), 208),
    PrimaryNode(21955, "stb-a-page", 46, 2, (None, 143), 208),
    PrimaryNode("DirectJ_Below", "j-address", 48, 3, (21957,), 116, 21957),
)


def expected_instruction(index):
    """Single independently expected fragment; no actual emission consulted."""
    if type(index) is not int or not 0 <= index < 20:
        raise ValueError("Closed primary-node index")
    node = NODES[index]
    if node.form == "j-address":
        payload = primary_j.independently_expected_bytes(node.target)
        if primary_j.independently_expected_target(payload) != node.target:
            raise ValueError("Primary direct-J arithmetic conflict")
    else:
        payload = bytes(primary_a.primary_expected(node.form, node.values, 4096 + node.offset))
        # Independent M2bc column grammar, not the operational decoder.
        row = next(row for row in grammar_a.ROWS if row.form_id == node.form)
        options = {}
        for rule, value in zip(row.operands, node.values):
            if rule.kind in ("PageOffset8", "EvenPageOffset8"):
                options["offset"] = value
            elif rule.kind.startswith("PageBit"):
                options["offset"] = value[0]
            elif rule.kind == "Immediate8":
                options["immediate8"] = value
            elif rule.kind == "Immediate16":
                options["immediate16"] = value
            elif rule.kind == "TargetPC16":
                options["delta"] = value - (4096 + node.offset + node.length)
        if payload != grammar_a.primary_payload(node.form, **options):
            raise ValueError("Independent primary column disagreement")
    if len(payload) != node.length:
        raise ValueError("Primary length conflict")
    return payload


def expected_reference_for_test(initial_dd):
    """Only test oracle concatenates the independently fixed twenty facts."""
    if type(initial_dd) is not int or initial_dd not in (0, 1):
        raise ValueError("Scalar DD fixture required")
    parts = tuple(expected_instruction(i) for i in range(20))
    reference = b"".join(parts)
    if len(reference) != 51:
        raise ValueError("Primary reference length conflict")
    return reference


def preparation_receipt():
    """Safe persistable metadata, explicitly excluding executable payloads."""
    primary_a.check_literal_examples()
    grammar_a.verify_literal_fixtures()
    records = []
    for i, node in enumerate(NODES):
        payload = expected_instruction(i)
        if node.form != "j-address":
            for dd in ((0, 1) if i == 0 else (0,)):
                decoded = grammar_a.classify_primary(payload, dd, 4096 + node.offset)
                if type(decoded) is not grammar_a.ExpectedDecoded or decoded.form_id != node.form:
                    raise ValueError("Independent grammar fixture conflict")
        records.append({"nodeId": node.node_id, "form": node.form,
                        "origin": 4096 + node.offset, "length": node.length,
                        "target": node.target, "primaryPdfPage": node.page,
                        "expectedInstructionSha256": sha256(payload).hexdigest()})
    references = tuple(expected_reference_for_test(dd) for dd in (0, 1))
    return {"schemaVersion": 1, "exactBase": EXACT_BASE, "manualSha256": MANUAL_SHA256,
            "source": "ManufacturerColumnsAndImmutableIndependentPriorFixtures",
            "nodes": records, "referenceSha256": [sha256(x).hexdigest() for x in references],
            "referenceLengths": [len(x) for x in references],
            "ddReferencesEqual": references[0] == references[1],
            "operationalEncoderCalls": 0, "operationalDecoderCalls": 0,
            "emitterCalls": 0, "rawStreamPersisted": False}
