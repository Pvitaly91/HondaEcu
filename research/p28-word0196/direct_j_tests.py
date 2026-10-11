"""Independent direct-J primary checks and isolated compatibility controls.

All expected bytes originate in the preimplementation manufacturer oracle.
Round trips are compatibility checks, not independent instruction proofs.
Only individual synthetic three-byte instructions are produced in memory.
"""
from __future__ import annotations

from dataclasses import fields, FrozenInstanceError
import json
from pathlib import Path
import sys

from direct_j_primary_oracle import (
    PRIMARY_LITERALS, expected_metadata, independently_expected_bytes,
    independently_expected_target,
)

HERE = Path(__file__).resolve().parent


def value(spec):
    if type(spec) is dict and set(spec) == {"integerSubclass"}:
        class IntSubclass(int):
            pass
        return IntSubclass(spec["integerSubclass"])
    return spec


def negative_descriptors():
    """All shape/type/range/header expectations fixed before codec execution."""
    rows = []
    def add(api, label, code, **data):
        rows.append({"api": api, "label": label, "expectedCode": code, **data})
    for api in ("Encoder", "Decoder"):
        for kind in ("missing-request", "dict-request", "spoof-request", "request-subclass"):
            add(api, kind, "RequestShape", kind=kind)
        slots = ("target", "origin_pc", "incoming_dd") if api == "Encoder" else (
            "encoded_bytes", "origin_pc", "incoming_dd")
        for slot in slots:
            add(api, "missing-slot-" + slot, "RequestShape", kind="missing-slot", slot=slot)

    for bad in (True, False, 1.0, "1", None, {"integerSubclass": 1}):
        add("Encoder", "target-value-type-" + repr(bad), "TargetTypeInvalid", target=bad)
    for bad in (-1, 65536, 2 ** 80):
        add("Encoder", "target-range-" + str(bad), "TargetOutOfRange", target=bad)
    for kind in ("raw-target", "target-subclass", "missing-target-value", "spoof-target"):
        add("Encoder", kind, "TargetTypeInvalid", kind=kind)
    for api in ("Encoder", "Decoder"):
        for bad in (-1, 2, 65536, True, False, 0.0, "0", None, {"integerSubclass": 0}):
            add(api, "DD-invalid-" + repr(bad), "IncomingDDInvalid", dd=bad)
        for bad in (-1, 65536, True, False, 4096.0, "4096", None, {"integerSubclass": 4096}):
            add(api, "origin-invalid-" + repr(bad), "OriginInvalid", origin=bad)
        for origin in (65534, 65535):
            add(api, "span-" + str(origin), "OriginSpanOutsideProfile", origin=origin)

    for kind in ("bytearray", "bytes-subclass", "memoryview", "list-bytes", "string-bytes", "null-bytes"):
        add("Decoder", kind, "EncodedBytesInvalid", kind=kind)
    for payload, code in (("", "EncodedLengthInvalid"), ("03", "TruncatedEncoding"),
                          ("0396", "TruncatedEncoding"), ("039655AA", "TrailingBytes"),
                          ("039655AA7D", "TrailingBytes"), ("039655AA7DA1", "TrailingBytes")):
        add("Decoder", "length-" + str(len(payload) // 2), code, payloadHex=payload)
    for origin in (0, 4096, 65533):
        for dd in (0, 1):
            for header in range(256):
                if header != 3:
                    add("Decoder", f"wrong-header-{header:02X}-DD{dd}-O{origin}",
                        "UnsupportedEncoding", payloadHex=bytes((header, 0x96, 0x55)).hex(),
                        origin=origin, dd=dd, domain="ClosedOneFormHeader")
    # Coupled-invalid cases verify the exact presealed validation precedence.
    add("Encoder", "target-before-DD-origin", "TargetTypeInvalid", target=True, dd=2, origin=65535)
    add("Encoder", "range-before-DD-origin", "TargetOutOfRange", target=65536, dd=2, origin=65535)
    add("Encoder", "DD-before-origin", "IncomingDDInvalid", dd=2, origin=65535)
    add("Decoder", "empty-before-DD-origin", "EncodedLengthInvalid", payloadHex="", dd=2, origin=65535)
    add("Decoder", "truncated-before-DD-origin", "TruncatedEncoding", payloadHex="FF00", dd=2, origin=65535)
    add("Decoder", "trailing-before-DD-origin", "TrailingBytes", payloadHex="039655AA", dd=2, origin=65535)
    add("Decoder", "DD-before-origin-header", "IncomingDDInvalid", payloadHex="FF9655", dd=2, origin=65535)
    add("Decoder", "origin-before-header", "OriginInvalid", payloadHex="FF9655", origin=-1)
    add("Decoder", "span-before-header", "OriginSpanOutsideProfile", payloadHex="FF9655", origin=65534)
    add("Decoder", "SJ-two-byte-not-direct", "TruncatedEncoding", payloadHex="CB00")
    add("Decoder", "SJ-header-three-cell-not-direct", "UnsupportedEncoding", payloadHex="CB0000")
    add("Decoder", "J-obj-DP-two-byte-not-direct", "TruncatedEncoding", payloadHex="9222")
    add("Decoder", "J-obj-DP-three-cell-not-direct", "UnsupportedEncoding", payloadHex="922200")
    for api in ("Encoder", "Decoder"):
        for claim in ("CPUExecutionResult", "StackFrameCreated", "FirmwareReady"):
            add(api, "spoofed-authority-" + claim, "RequestShape", kind="dict-request", claim=claim)
    return rows


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def mutation_contexts():
    """Operand changes and LE swaps remain valid alternative program targets."""
    attempts, unique = 0, {}
    for case in PRIMARY_LITERALS:
        for cell in (1, 2):
            for scalar in range(256):
                data = list(case.expected_bytes)
                data[cell] = scalar
                payload = bytes(data)
                target = independently_expected_target(payload)
                key = (payload, case.origin, case.incoming_dd)
                unique[key] = target
                attempts += 1
        payload = bytes((3, case.expected_bytes[2], case.expected_bytes[1]))
        unique[(payload, case.origin, case.incoming_dd)] = independently_expected_target(payload)
        attempts += 1
    return attempts, unique


def main():
    if sys.argv[1:] == ["--observe-absent"]:
        absent = not (HERE / "direct_j_encoder.py").exists() and not (HERE / "direct_j_decoder.py").exists()
        assert absent, "Genuine absence requires both codec files absent"
        print(json.dumps({"milestone": "M2bg", "kind": "EncoderDecoderNotImplemented",
                          "encoderCalls": 0, "decoderCalls": 0, "testsRun": 0, "fakeRED": False},
                         sort_keys=True))
        return
    assert not sys.argv[1:], "No ROM, paths, assembly or stream arguments accepted"
    from direct_j_types import (
        ProgramTarget16, DirectJForm, DirectJEncodeRequest, DirectJDecodeRequest,
        EncodedDirectJ, DecodedDirectJ, DirectJEncodeError, DirectJDecodeError,
        EncodeErrorCode, DecodeErrorCode,
    )
    from direct_j_encoder import encode_direct_j
    from direct_j_decoder import decode_direct_j
    encode_codes = {"RequestShape", "TargetTypeInvalid", "TargetOutOfRange", "IncomingDDInvalid",
                    "OriginInvalid", "OriginSpanOutsideProfile"}
    decode_codes = {"RequestShape", "EncodedBytesInvalid", "EncodedLengthInvalid", "TruncatedEncoding",
                    "TrailingBytes", "IncomingDDInvalid", "OriginInvalid", "OriginSpanOutsideProfile",
                    "UnsupportedEncoding"}
    assert {code.value for code in EncodeErrorCode} == encode_codes
    assert {code.value for code in DecodeErrorCode} == decode_codes
    assert EncodeErrorCode is not DecodeErrorCode
    counts = {"primaryLiteralCases": 24, "mainUniqueContexts": 393216,
              "positiveLabels": 0, "primaryEncoderComparisons": 0, "primaryDecoderComparisons": 0,
              "typedEncodeDecodeComparisons": 0, "primaryDecodeEncodeComparisons": 0,
              "encoderCalls": 0, "decoderCalls": 0, "successfulEncodedSequences": 0,
              "successfulEncodedOctets": 0, "successfulDecodedResults": 0,
              "negativeEncoderLabels": 0, "negativeDecoderLabels": 0,
              "negativeEncoderCalls": 0, "negativeDecoderCalls": 0,
              "operandMutationAttempts": 0, "operandMutationDecoderCalls": 0,
              "immutabilityChecks": 0}
    positive_keys, negative_encode_keys, negative_decode_keys = set(), set(), set()
    observed_encode_codes, observed_decode_codes = set(), set()
    hooks = {"spoofReads": 0}

    def encode(request):
        counts["encoderCalls"] += 1
        result = encode_direct_j(request)
        if type(result) is EncodedDirectJ:
            counts["successfulEncodedSequences"] += 1
            counts["successfulEncodedOctets"] += len(result.encoded_bytes)
        return result

    def decode(request):
        counts["decoderCalls"] += 1
        result = decode_direct_j(request)
        if type(result) is DecodedDirectJ:
            counts["successfulDecodedResults"] += 1
        return result

    def success(result, target, origin, dd, direction):
        assert type(result) is (EncodedDirectJ if direction == "Encoding" else DecodedDirectJ)
        assert type(result.target) is ProgramTarget16 and type(result.target.value) is int
        assert result.form is DirectJForm.J_ADDRESS
        wanted = expected_metadata(target, origin, dd, direction)
        for name, expected in wanted.items():
            actual = result.target.value if name == "target" else result.form.value if name == "form" else getattr(result, name)
            assert type(actual) is type(expected) and actual == expected, (name, actual, expected)
        names = set(wanted)
        if direction == "Encoding":
            names.add("encoded_bytes")
            assert type(result.encoded_bytes) is bytes and result.encoded_bytes == independently_expected_bytes(target)
        assert {field.name for field in fields(result)} == names
        assert not hasattr(result, "__dict__")
        assert not any(hasattr(result, key) for key in
                       ("CPUState", "RAMState", "stack_frame", "runtimePermission", "firmwareReady", "signed_delta"))

    def frozen(obj, attribute, bad):
        try:
            setattr(obj, attribute, bad)
        except (FrozenInstanceError, AttributeError, TypeError):
            counts["immutabilityChecks"] += 1
        else:
            raise AssertionError("Frozen object was modified")

    def positive(target, origin, dd, literal_bytes=None, check_immutable=False):
        primary = independently_expected_bytes(target) if literal_bytes is None else literal_bytes
        assert independently_expected_target(primary) == target
        request = DirectJEncodeRequest(ProgramTarget16(target), origin, dd)
        decoded_request = DirectJDecodeRequest(primary, origin, dd)
        request_fields = request.target, request.origin_pc, request.incoming_dd
        encoded = encode(request)
        success(encoded, target, origin, dd, "Encoding")
        assert encoded.encoded_bytes == primary
        counts["primaryEncoderComparisons"] += 1
        decoded = decode(decoded_request)
        success(decoded, target, origin, dd, "Decoding")
        counts["primaryDecoderComparisons"] += 1
        round_decoded = decode(DirectJDecodeRequest(encoded.encoded_bytes, origin, dd))
        success(round_decoded, target, origin, dd, "Decoding")
        assert round_decoded.target == request.target
        counts["typedEncodeDecodeComparisons"] += 1
        round_encoded = encode(DirectJEncodeRequest(decoded.target, origin, dd))
        success(round_encoded, target, origin, dd, "Encoding")
        assert round_encoded.encoded_bytes == primary
        counts["primaryDecodeEncodeComparisons"] += 1
        assert request_fields == (request.target, request.origin_pc, request.incoming_dd)
        assert decoded_request.encoded_bytes is primary
        counts["positiveLabels"] += 1
        positive_keys.add((target, origin, dd))
        if check_immutable:
            for obj, attribute, bad in ((request.target, "value", -1), (request, "incoming_dd", 2),
                                        (decoded_request, "encoded_bytes", b""),
                                        (encoded, "classification", "FirmwareReady"),
                                        (decoded, "pc_effect", "CPUExecutionResult")):
                frozen(obj, attribute, bad)

    for case in PRIMARY_LITERALS:
        positive(case.target, case.origin, case.incoming_dd, case.expected_bytes, True)
    for target in range(65536):
        for dd in (0, 1):
            for origin in (0, 4096, 65533):
                positive(target, origin, dd)

    mutation_attempts, mutations = mutation_contexts()
    counts["operandMutationAttempts"] = mutation_attempts
    for (payload, origin, dd), target in mutations.items():
        decoded = decode(DirectJDecodeRequest(payload, origin, dd))
        success(decoded, target, origin, dd, "Decoding")
        assert target == payload[1] + 256 * payload[2]
        assert (target, origin, dd) in positive_keys
        counts["operandMutationDecoderCalls"] += 1

    class Spoof:
        def __getattribute__(self, key):
            hooks["spoofReads"] += 1
            raise AssertionError("Wrong request/operand object must not be inspected")

    def materialize(case):
        api, kind = case["api"], case.get("kind", "standard")
        origin, dd = value(case.get("origin", 4096)), value(case.get("dd", 0))
        target = ProgramTarget16(value(case.get("target", 0x5596)))
        payload = bytes.fromhex(case.get("payloadHex", "039655"))
        request_class = DirectJEncodeRequest if api == "Encoder" else DirectJDecodeRequest
        values = {"target": target, "origin_pc": origin, "incoming_dd": dd} if api == "Encoder" else {
            "encoded_bytes": payload, "origin_pc": origin, "incoming_dd": dd}
        if kind == "missing-request":
            return None
        if kind == "dict-request":
            return values | {"classification": case.get("claim", "Synthetic")}
        if kind == "spoof-request":
            return Spoof()
        if kind == "request-subclass":
            class RequestSubclass(request_class):
                pass
            return RequestSubclass(**values)
        if kind == "missing-slot":
            request = object.__new__(request_class)
            for key, scalar in values.items():
                if key != case["slot"]:
                    object.__setattr__(request, key, scalar)
            return request
        if api == "Encoder":
            if kind == "raw-target":
                values["target"] = 0x5596
            elif kind == "target-subclass":
                class TargetSubclass(ProgramTarget16):
                    pass
                values["target"] = TargetSubclass(0x5596)
            elif kind == "missing-target-value":
                values["target"] = object.__new__(ProgramTarget16)
            elif kind == "spoof-target":
                values["target"] = Spoof()
        else:
            if kind == "bytearray":
                values["encoded_bytes"] = bytearray(payload)
            elif kind == "bytes-subclass":
                class BytesSubclass(bytes):
                    pass
                values["encoded_bytes"] = BytesSubclass(payload)
            elif kind == "memoryview":
                values["encoded_bytes"] = memoryview(payload)
            elif kind == "list-bytes":
                values["encoded_bytes"] = list(payload)
            elif kind == "string-bytes":
                values["encoded_bytes"] = payload.hex()
            elif kind == "null-bytes":
                values["encoded_bytes"] = None
        return request_class(**values)

    for case in negative_descriptors():
        api, wanted = case["api"], case["expectedCode"]
        keys = negative_encode_keys if api == "Encoder" else negative_decode_keys
        keys.add(stable({key: scalar for key, scalar in case.items() if key not in ("label", "domain")}))
        counts["negative" + api + "Labels"] += 1
        seen = []
        for _ in range(2):
            result = encode(materialize(case)) if api == "Encoder" else decode(materialize(case))
            expected_type = DirectJEncodeError if api == "Encoder" else DirectJDecodeError
            enum_type = EncodeErrorCode if api == "Encoder" else DecodeErrorCode
            assert type(result) is expected_type and type(result.code) is enum_type
            assert result.code.value == wanted, (case["label"], result.code.value, wanted)
            assert {field.name for field in fields(result)} == {"code"}
            assert not hasattr(result, "__dict__")
            assert not any(hasattr(result, key) for key in ("encoded_bytes", "target", "classification", "partial"))
            seen.append((type(result), result.code))
            counts["negative" + api + "Calls"] += 1
            (observed_encode_codes if api == "Encoder" else observed_decode_codes).add(result.code.value)
        assert seen[0] == seen[1]
        frozen(result, "code", None)
    assert hooks["spoofReads"] == 0
    assert observed_encode_codes == encode_codes and observed_decode_codes == decode_codes
    assert counts["positiveLabels"] == 393240 and len(positive_keys) == 393216
    assert counts["successfulEncodedSequences"] == 786480
    assert counts["successfulEncodedOctets"] == 2359440
    assert counts["operandMutationDecoderCalls"] == len(mutations)
    print(json.dumps({
        "milestone": "M2bg", "passed": True, "failed": 0, "skipped": 0, "firstMismatch": None,
        "counts": counts, "uniquePositiveContexts": len(positive_keys),
        "literalLabelsOverlapMainDomain": 24,
        "uniqueNegativeEncoderDescriptors": len(negative_encode_keys),
        "uniqueNegativeDecoderDescriptors": len(negative_decode_keys),
        "uniqueAcceptedMutationInputs": len(mutations),
        "observedEncodeErrorCodes": sorted(observed_encode_codes),
        "observedDecodeErrorCodes": sorted(observed_decode_codes),
        "spoofedFieldReads": hooks["spoofReads"],
        "primaryProofDirections": ["A_IndependentBytesToEncoder", "B_IndependentBytesToDecoder"],
        "roundTripDirections": "CompatibilityOnly_NotIndependentISAProof",
        "emissionScope": "SingleSyntheticThreeByteInstructionInMemory_NoStreams",
        "CPUExecutions": 0, "actualROMExecutions": 0, "persistentMachineCodeFiles": 0,
        "targetObjects": 0, "FirmwareBIN": 0,
        "nativeExitIsolation": "NotEstablished", "actualDownstreamRejoin": "NotEstablished",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
