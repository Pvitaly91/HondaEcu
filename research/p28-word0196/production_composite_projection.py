"""M2bq source draft: lossless declared observation projection, not an oracle.

Every primitive/key/array item is retained. Snapshot RAM has an explicit,
invertible sparse byte encoding relative to production's scratch byte A5.
The inverse is checked against the actual input before a projected row is used.
No expected state, input seed, host normalization or excluded field participates
in compression. This module does not execute instructions or synthesize events.
"""

from copy import deepcopy
from production_composite_common import canonical, first_difference, require

CODEC = "M2bqLosslessJsonAndRamSparseA5V1"
RAM_BEGIN, RAM_END, FILL = 0x80, 0x1000, 0xA5
TAG = "$m2bq_lossless_ram_v1"
SCHEMA = {"codec": CODEC, "droppedFields": [], "platformExclusions": [],
          "ramRange": [RAM_BEGIN, RAM_END], "ramFill": FILL,
          "ramEncoding": "AllActualBytesAsSortedNonFillOffsets_ExactInverseRequired",
          "jsonEncoding": "SortedKeys_Ascii_IntegerBooleanNullExact_NoFloat",
          "programPayload": "NotPartOfObservationSchema_NoByteValuesOrPersistentProgram"}


def _check_ram(value):
    require(type(value) is list and len(value) == RAM_END - RAM_BEGIN, "CompleteActualRamImage")
    require(all(type(byte) is int and 0 <= byte <= 255 for byte in value), "ActualRamU8Values")


def encode_ram(value):
    _check_ram(value)
    return {TAG: {"range": [RAM_BEGIN, RAM_END], "fill": FILL,
                  "non_fill": [[offset, byte] for offset, byte in enumerate(value) if byte != FILL]}}


def decode_ram(value):
    require(type(value) is dict and set(value) == {TAG}, "ClosedRamTag")
    body = value[TAG]
    require(type(body) is dict and set(body) == {"range", "fill", "non_fill"}, "ClosedRamEncoding")
    require(body["range"] == [RAM_BEGIN, RAM_END] and type(body["fill"]) is int
            and body["fill"] == FILL, "ExactRamEncodingIdentity")
    require(type(body["non_fill"]) is list, "OrderedRamOffsets")
    result, prior = [FILL] * (RAM_END - RAM_BEGIN), -1
    for row in body["non_fill"]:
        require(type(row) is list and len(row) == 2, "ClosedRamOffsetPair")
        offset, byte = row
        require(type(offset) is int and prior < offset < len(result), "StrictUniqueRamOffset")
        require(type(byte) is int and 0 <= byte <= 255 and byte != FILL, "CanonicalNonFillRamByte")
        result[offset], prior = byte, offset
    return result


def _project(value):
    if type(value) is dict:
        require(TAG not in value, "ReservedLosslessTagCannotAppearInActualObservation")
        if set(value) == {"cpu", "ram", "ram_range"}:
            require(value["ram_range"] == [RAM_BEGIN, RAM_END], "ExactSnapshotRamRange")
            return {"cpu": _project(value["cpu"]), "ram": encode_ram(value["ram"]),
                    "ram_range": deepcopy(value["ram_range"])}
        return {key: _project(item) for key, item in value.items()}
    if type(value) is list:
        return [_project(item) for item in value]
    require(type(value) in (str, int, bool, type(None)), "LosslessPrimitiveType")
    return value


def restore(value):
    if type(value) is dict:
        if set(value) == {TAG}:
            return decode_ram(value)
        return {key: restore(item) for key, item in value.items()}
    if type(value) is list:
        return [restore(item) for item in value]
    require(type(value) in (str, int, bool, type(None)), "RestoredPrimitiveType")
    return value


def project(actual):
    result = _project(actual)
    require(first_difference(actual, restore(result)) is None, "ActualObservationLosslessRoundTrip")
    return result


def canonical_row(actual):
    return canonical(project(actual)) + b"\n"


def compare_complete(expected, actual):
    """No field exclusions: exact types, keys, order and reconstructed RAM."""
    return first_difference(expected, actual)
