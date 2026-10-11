"""Independent primary direct-J literals and arithmetic, prepared before codecs.

Personally reviewed complete manufacturer pages establish the fixed header and
low/high PROGRAM-target cells. This module imports no encoder, decoder, types,
Rust, ASM, file, process, network or CPU implementation. Single invented
instructions are expected in memory; no sequence assembly or runtime proof.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrimaryJLiteral:
    identifier: str
    target: int
    incoming_dd: int
    origin: int
    expected_bytes: bytes


# Literal values independently fixed from the primary 03/adrL/adrH row.
# They are invented operands, not copied OEM routine windows or native traces.
PRIMARY_LITERALS = (
    PrimaryJLiteral("0000-DD0", 0x0000, 0, 0x0000, b"\x03\x00\x00"),
    PrimaryJLiteral("0000-DD1", 0x0000, 1, 0x1000, b"\x03\x00\x00"),
    PrimaryJLiteral("0001-DD0", 0x0001, 0, 0x1000, b"\x03\x01\x00"),
    PrimaryJLiteral("0001-DD1", 0x0001, 1, 0xFFFD, b"\x03\x01\x00"),
    PrimaryJLiteral("00FF-DD0", 0x00FF, 0, 0xFFFD, b"\x03\xFF\x00"),
    PrimaryJLiteral("00FF-DD1", 0x00FF, 1, 0x0000, b"\x03\xFF\x00"),
    PrimaryJLiteral("0100-DD0", 0x0100, 0, 0x0000, b"\x03\x00\x01"),
    PrimaryJLiteral("0100-DD1", 0x0100, 1, 0x1000, b"\x03\x00\x01"),
    PrimaryJLiteral("5596-DD0", 0x5596, 0, 0x1000, b"\x03\x96\x55"),
    PrimaryJLiteral("5596-DD1", 0x5596, 1, 0xFFFD, b"\x03\x96\x55"),
    PrimaryJLiteral("55C5-DD0", 0x55C5, 0, 0xFFFD, b"\x03\xC5\x55"),
    PrimaryJLiteral("55C5-DD1", 0x55C5, 1, 0x0000, b"\x03\xC5\x55"),
    PrimaryJLiteral("7FFF-DD0", 0x7FFF, 0, 0x0000, b"\x03\xFF\x7F"),
    PrimaryJLiteral("7FFF-DD1", 0x7FFF, 1, 0x1000, b"\x03\xFF\x7F"),
    PrimaryJLiteral("8000-DD0", 0x8000, 0, 0x1000, b"\x03\x00\x80"),
    PrimaryJLiteral("8000-DD1", 0x8000, 1, 0xFFFD, b"\x03\x00\x80"),
    PrimaryJLiteral("FFFF-DD0", 0xFFFF, 0, 0xFFFD, b"\x03\xFF\xFF"),
    PrimaryJLiteral("FFFF-DD1", 0xFFFF, 1, 0x0000, b"\x03\xFF\xFF"),
    PrimaryJLiteral("00F0-DD0", 0x00F0, 0, 0x0000, b"\x03\xF0\x00"),
    PrimaryJLiteral("00F0-DD1", 0x00F0, 1, 0x1000, b"\x03\xF0\x00"),
    PrimaryJLiteral("12A7-DD0", 0x12A7, 0, 0x1000, b"\x03\xA7\x12"),
    PrimaryJLiteral("12A7-DD1", 0x12A7, 1, 0xFFFD, b"\x03\xA7\x12"),
    PrimaryJLiteral("A35C-DD0", 0xA35C, 0, 0xFFFD, b"\x03\x5C\xA3"),
    PrimaryJLiteral("A35C-DD1", 0xA35C, 1, 0x0000, b"\x03\x5C\xA3"),
)


def independently_expected_bytes(target):
    """Positional base-256 arithmetic, not codec bit operations or output."""
    if type(target) is not int or not 0 <= target <= 65535:
        raise ValueError("Independent invented ProgramTarget16 domain")
    quotient, remainder = divmod(target, 256)
    return bytes((3, remainder, quotient))


def independently_expected_target(payload):
    """Weighted cell arithmetic, independent of encoder/decoder implementations."""
    if type(payload) is not bytes or len(payload) != 3 or payload[0] != 3:
        raise ValueError("Independent primary three-cell direct-J grammar")
    return payload[1] + 256 * payload[2]


def expected_metadata(target, origin, incoming_dd, direction):
    if type(target) is not int or not 0 <= target <= 65535:
        raise ValueError("Independent target domain")
    if type(origin) is not int or not 0 <= origin <= 65533:
        raise ValueError("Independent complete instruction span")
    if type(incoming_dd) is not int or incoming_dd not in (0, 1):
        raise ValueError("Independent incoming DD domain")
    if direction not in ("Encoding", "Decoding"):
        raise ValueError("Independent result direction")
    return {
        "target": target, "origin_pc": origin, "incoming_dd": incoming_dd,
        "form": "j-address", "length": 3, "end_exclusive": origin + 3,
        "pc_effect": "DocumentedPCReplacement",
        "dd_effect": "DocumentedDDPreservedWhenExecuted",
        "noninterference_scope": "ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence",
        "classification": "SyntheticDirectJ" + direction + "Only",
    }
