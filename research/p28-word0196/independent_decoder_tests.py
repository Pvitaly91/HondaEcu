"""M2bc PRIMARY decode tests and separate bidirectional compatibility checks.

A uses own manufacturer-derived bytes/typed oracle. B compares the original
typed request after encode/decode (compatibility only). C re-encodes A's decoded
objects and compares independent primary bytes. No encoder output is an oracle.
Unique positive vectors are counted once by immutable payload/DD/origin.
"""
import argparse
from collections import Counter
import dataclasses
import importlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import independent_decoder_primary_oracle as primary

COUNTS = Counter()
COVERAGE = Counter()
ERRORS = Counter()
CLASSES = Counter()
FORMS_DD = {}
POSITIVE_SEEN = set()
NEGATIVE_SEEN = set()
FIRST_MISMATCH = None


def load_decoder(path):
    spec = importlib.util.spec_from_file_location("m2bc_decoder_under_test", path)
    decoder = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = decoder
    spec.loader.exec_module(decoder)
    return decoder


def decode(decoder, request):
    COUNTS["actualDecodeCalls"] += 1
    result = decoder.decode_instruction(request)
    if type(result) is decoder.DecodedInstruction:
        COUNTS["actualDecodedResults"] += 1
    return result


def encode(shared, request):
    COUNTS["actualEncodeCalls"] += 1
    result = shared.encode_instruction(request)
    if type(result) is shared.EncodedInstruction:
        COUNTS["syntheticEncodedSequences"] += 1
        COUNTS["syntheticEncodedOctets"] += len(result.encoded_bytes)
    return result


def typed_operands(shared, expected):
    result = []
    for kind, fields in expected.operands:
        cls = getattr(shared, kind)
        result.append(cls(*fields))
    return tuple(result)


def operand_description(shared, operands):
    result = []
    for operand in operands:
        kind = type(operand).__name__
        assert type(operand) is getattr(shared, kind)
        if kind == "AccumulatorA":
            fields = ()
        elif kind in ("PageBit7", "PageBit5"):
            fields = (operand.offset, operand.bit)
        else:
            fields = (operand.value,)
        assert all(type(value) is int for value in fields)
        result.append((kind, fields))
    return tuple(result)


def assert_decoded(decoder, shared, actual, expected):
    assert type(actual) is decoder.DecodedInstruction, actual
    assert type(actual.reviewed_form_id) is shared.FormId
    assert actual.reviewed_form_id is shared.FormId(expected.form_id)
    assert type(actual.typed_operands) is tuple
    assert operand_description(shared, actual.typed_operands) == expected.operands
    assert type(actual.length) is int and actual.length == expected.length
    assert type(actual.origin_pc) is int and actual.origin_pc == expected.origin
    assert type(actual.incoming_dd) is int and actual.incoming_dd == expected.incoming_dd
    assert actual.relative_target_pc == expected.relative_target
    assert type(actual.relative_target_pc) is int if expected.relative_target is not None else actual.relative_target_pc is None
    assert type(actual.documented_dd_effect) is decoder.DDEffect
    assert actual.documented_dd_effect.value == expected.dd_effect
    assert actual.classification == "SyntheticInstructionDecodingOnly"
    assert type(actual.input_classification) is decoder.DecodeInputClassification
    assert actual.input_classification.value == "ExactSupportedForm"
    assert dataclasses.is_dataclass(actual) and actual.__dataclass_params__.frozen
    assert not hasattr(actual, "__dict__")


def check_positive(decoder, shared, payload, dd, origin, group, literal=None):
    global FIRST_MISMATCH
    expected = primary.classify_primary(payload, dd, origin)
    assert type(expected) is primary.ExpectedDecoded, (group, expected)
    if literal is not None:
        assert expected.form_id == literal.form_id and expected.operands == literal.operands
        assert expected.relative_target == literal.relative_target
    COVERAGE[group] += 1  # Domain membership attempts, NOT added to positive total.
    key = (payload, dd, origin)
    if key in POSITIVE_SEEN:
        COUNTS["overlappingDomainAttemptsDeduplicated"] += 1
        return
    POSITIVE_SEEN.add(key)
    before = payload
    try:
        # A. Independent primary byte payload -> decoder -> primary typed oracle.
        request = decoder.DecoderRequest(payload, dd, origin)
        result_a = decode(decoder, request)
        assert_decoded(decoder, shared, result_a, expected)
        assert request.encoded_bytes == before and request.incoming_dd == dd
        COUNTS["positiveDecodeCases"] += 1
        COUNTS["primaryDecodeChecksA"] += 1
        FORMS_DD.setdefault(expected.form_id, set()).add(dd)
        # B. Typed request -> M2bb encoder -> decoder -> original typed request.
        original = shared.EncoderRequest(shared.FormId(expected.form_id),
                                         typed_operands(shared, expected), dd, origin)
        encoded_b = encode(shared, original)
        assert type(encoded_b) is shared.EncodedInstruction, encoded_b
        result_b = decode(decoder, decoder.DecoderRequest(encoded_b.encoded_bytes, dd, origin))
        assert_decoded(decoder, shared, result_b, expected)
        assert result_b.reviewed_form_id is original.reviewed_form_id
        assert result_b.typed_operands == original.typed_operands
        COUNTS["encodeDecodeRoundTripsB"] += 1
        # C. A's primary-decoded instruction -> encoder -> identical primary input.
        reconstructed = shared.EncoderRequest(result_a.reviewed_form_id, result_a.typed_operands,
                                               result_a.incoming_dd, result_a.origin_pc)
        encoded_c = encode(shared, reconstructed)
        assert type(encoded_c) is shared.EncodedInstruction
        assert encoded_c.encoded_bytes == payload
        COUNTS["decodeEncodePrimaryRoundTripsC"] += 1
    except AssertionError as error:
        if FIRST_MISMATCH is None:
            FIRST_MISMATCH = dict(group=group, primaryPayload=list(payload), incomingDD=dd,
                                  originPC=origin, independentlyExpected=repr(expected), failure=str(error))
        raise


def check_error(decoder, payload, dd, origin, expected_code, group):
    key = (type(payload).__name__, repr(payload), type(dd).__name__, repr(dd),
           type(origin).__name__, repr(origin))
    COVERAGE[group] += 1
    if key in NEGATIVE_SEEN:
        COUNTS["negativeOverlapAttemptsDeduplicated"] += 1
        return
    NEGATIVE_SEEN.add(key)
    request = decoder.DecoderRequest(payload, dd, origin)
    actual = decode(decoder, request)
    assert type(actual) is decoder.ExplicitDecodeError, actual
    assert type(actual.code) is decoder.DecodeErrorCode and actual.code.value == expected_code
    assert tuple(field.name for field in dataclasses.fields(actual)) == ("code",)
    assert type(actual.input_classification) is decoder.DecodeInputClassification
    assert actual.input_classification.value == primary.ERROR_CLASSIFICATIONS[expected_code]
    assert not hasattr(actual, "__dict__")
    for forbidden in ("encoded_bytes", "typed_operands", "partial_instruction", "reviewed_form_id",
                      "length", "relative_target_pc", "warning"):
        assert not hasattr(actual, forbidden)
    assert decode(decoder, request) == actual
    COUNTS["negativeDecodeCases"] += 1
    ERRORS[expected_code] += 1
    CLASSES[actual.input_classification.value] += 1


def classify_case(decoder, shared, payload, dd, origin, group):
    expected = primary.classify_primary(payload, dd, origin)
    if type(expected) is primary.ExpectedDecoded:
        check_positive(decoder, shared, payload, dd, origin, group)
        return True
    check_error(decoder, payload, dd, origin, expected, group)
    return False


def exhaust_domains(decoder, shared):
    for literal in primary.LITERALS:
        check_positive(decoder, shared, bytes(literal.payload), literal.dd, literal.origin,
                       "sealedLiteralCases", literal)
        COUNTS["primaryLiteralCases"] += 1
    for row in primary.ROWS:
        for dd in row.allowed_dd:
            classify_case(decoder, shared, primary.primary_payload(row.form_id), dd, 4096, "formDDContexts")
        if row.dd0_required:
            check_error(decoder, primary.primary_payload(row.form_id), 1, 4096, "WrongDD", "wrongDD")
        if "offset" in row.frame:
            for offset in range(256):
                payload = primary.primary_payload(row.form_id, offset=offset)
                for dd in row.allowed_dd:
                    classify_case(decoder, shared, payload, dd, 4096,
                                  "allEvenAndOddCmpOffsets" if row.form_id == "cmp-page-imm16" else "allByteOffsets")
        if "imm8" in row.frame:
            for immediate in range(256):
                payload = primary.primary_payload(row.form_id, immediate8=immediate)
                for dd in row.allowed_dd:
                    classify_case(decoder, shared, payload, dd, 4096, "allImmediate8")
        if "low" in row.frame:
            for immediate in range(65536):
                payload = primary.primary_payload(row.form_id, offset=54, immediate16=immediate)
                for dd in row.allowed_dd:
                    classify_case(decoder, shared, payload, dd, 4096, "allImmediate16")
        if "delta" in row.frame:
            for origin in (128, 4096, 65405):
                for delta in range(-128, 128):
                    payload = primary.primary_payload(row.form_id, delta=delta)
                    for dd in row.allowed_dd:
                        classify_case(decoder, shared, payload, dd, origin, "allSignedRel8")
            for dd in row.allowed_dd:
                classify_case(decoder, shared, primary.primary_payload(row.form_id, delta=0),
                              dd, 65535-row.length, "lastValidBranchNextFFFF")
                check_error(decoder, primary.primary_payload(row.form_id, delta=0), dd,
                            65536-row.length, "OriginSpanOutsideProfile", "firstInvalidBranchNext10000")
                check_error(decoder, primary.primary_payload(row.form_id, delta=-128), dd, 0,
                            "RelativeTargetOutsideProfile", "negativeReconstructedTarget")
                check_error(decoder, primary.primary_payload(row.form_id, delta=127), dd,
                            65535-row.length, "RelativeTargetOutsideProfile", "targetAboveFFFF")
        else:
            for dd in row.allowed_dd:
                classify_case(decoder, shared, primary.primary_payload(row.form_id), dd,
                              65536-row.length, "lastInstructionByteFFFF")
        if row.length > 1:
            for dd in row.allowed_dd:
                check_error(decoder, primary.primary_payload(row.form_id), dd,
                            65537-row.length, "OriginSpanOutsideProfile", "extentOverflow")
    for offset in range(256):
        for immediate in range(256):
            payload = primary.primary_payload("orb-page-imm8", offset=offset, immediate8=immediate)
            for dd in (0, 1):
                classify_case(decoder, shared, payload, dd, 4096, "orbOffsetImmediateCrossProduct")


def syntax_and_mutations(decoder, shared):
    for row in primary.ROWS:
        full = primary.primary_payload(row.form_id, offset=54)
        for dd in (0, 1):
            for missing_length in range(row.length):
                shortened = full[:missing_length]
                classify_case(decoder, shared, shortened, dd, 4096, "everyTruncatedPrefix")
            for trailer in (bytes((0,)), bytes((255,)), full):
                classify_case(decoder, shared, full + trailer, dd, 4096, "trailingAndInstructionStreams")
            for bad_dd in (None, True, False, -1, 2, 0.0, "0", [], {}):
                check_error(decoder, full, bad_dd, 4096, "IncomingDDInvalid", "invalidDD")
            for bad_origin in (None, True, False, -1, 65536, 0.0, "0", [], {}):
                check_error(decoder, full, dd, bad_origin, "OriginInvalid", "invalidOrigin")
    for invalid in (None, True, False, 0, 0.0, "", [], {}, (120,), bytearray((120,)), memoryview(bytes((120,)))):
        check_error(decoder, invalid, 0, 256, "EncodedBytesInvalid", "nonImmutableBytes")
    for payload in (b"", bytes((120,)) * 6, bytes((0,)) * 32768):
        check_error(decoder, payload, 0, 256, "EncodedLengthOutsideProfile", "emptyAndOversized")
    for opcode in range(256):
        classify_case(decoder, shared, bytes((opcode,)), 0, 256, "allSingleByteHeaders")
    for suffix in range(256):
        for length in (3, 4, 5):
            payload = bytes((196, 55, suffix)) + bytes((166,)) * (length-3)
            for dd in (0, 1):
                classify_case(decoder, shared, payload, dd, 4096, "allC4SuffixLengthContexts")
            payload = bytes((180, 54, suffix)) + bytes((90, 165))[:length-3]
            classify_case(decoder, shared, payload, 0, 4096, "allB4ThirdByteLengths")
    # Every literal one-octet mutation uses ACTUAL independent grammar outcome.
    for literal in primary.LITERALS:
        for index in range(len(literal.payload)):
            for changed in range(256):
                if changed == literal.payload[index]:
                    continue
                cells = list(literal.payload)
                cells[index] = changed
                accepted = classify_case(decoder, shared, bytes(cells), literal.dd, literal.origin,
                                         "oneByteMutationActualGrammar")
                COUNTS["mutationAcceptedAttempts" if accepted else "mutationRefusedAttempts"] += 1


def malformed_requests_and_immutability(decoder, shared):
    for malformed in (None, True, False, 0, 0.0, "request", [], {},
                      {"encoded_bytes": bytes((120,)), "requested_form": "lb-a-r0"}):
        actual = decode(decoder, malformed)
        assert type(actual) is decoder.ExplicitDecodeError and actual.code.value == "RequestShape"
        assert actual.input_classification.value == "MalformedRequest"
        assert tuple(field.name for field in dataclasses.fields(actual)) == ("code",)
        assert decode(decoder, malformed) == actual
        COUNTS["negativeDecodeCases"] += 1
        COUNTS["requestShapeCases"] += 1
        ERRORS["RequestShape"] += 1
    missing = object.__new__(decoder.DecoderRequest)
    actual = decode(decoder, missing)
    assert type(actual) is decoder.ExplicitDecodeError and actual.code.value == "RequestShape"
    COUNTS["negativeDecodeCases"] += 1
    COUNTS["requestShapeCases"] += 1
    ERRORS["RequestShape"] += 1
    for field in ("requested_form", "opcode", "rom", "LRB", "execute", "firmware"):
        try:
            decoder.DecoderRequest(encoded_bytes=bytes((120,)), incoming_dd=0, origin_pc=256,
                                   **{field: True})
        except TypeError:
            COUNTS["constructorRefusals"] += 1
        else:
            raise AssertionError("Unknown request field accepted")
    request = decoder.DecoderRequest(bytes((244, 55)), 1, 256)
    result = decode(decoder, request)
    assert request.incoming_dd == 1 and result.documented_dd_effect.value == "SetsDD0WhenExecuted"
    for value, attribute in ((request, "incoming_dd"), (result, "origin_pc"),
                             (result.typed_operands[1], "value")):
        try:
            setattr(value, attribute, 1)
        except (dataclasses.FrozenInstanceError, AttributeError):
            COUNTS["immutabilityChecks"] += 1
        else:
            raise AssertionError("Mutable decoder object")
        try:
            object.__setattr__(value, "unknown_extra_slot", 1)
        except AttributeError:
            COUNTS["constructorRefusals"] += 1
        else:
            raise AssertionError("Unknown slot accepted")
    wrong = decode(decoder, decoder.DecoderRequest(bytes((83,)), request.incoming_dd, 256))
    assert type(wrong) is decoder.ExplicitDecodeError and wrong.code.value == "WrongDD"
    COUNTS["documentedDDEffectStatelessChecks"] += 1
    assert type(result.typed_operands[1]) is shared.PageOffset8


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decoder", type=Path, default=Path(__file__).with_name("independent_decoder.py"))
    parser.add_argument("--observe-absent", action="store_true")
    args = parser.parse_args()
    if args.observe_absent:
        present = args.decoder.is_file()
        print(json.dumps(dict(milestone="M2bc",
                              phase="AbsentObservationInvalid" if present else "DecoderNotImplemented",
                              decoderImplementationExists=present, testsRun=0, actualDecodeCalls=0,
                              primaryLiteralCasesPrepared=30, inventedRedFailure=False,
                              decoderPath=str(args.decoder.resolve())), sort_keys=True))
        return 2 if present else 0
    literal_count = primary.verify_literal_fixtures()
    grammar_proof = primary.verify_closed_header_uniqueness()
    assert args.decoder.is_file(), "DecoderNotImplemented: no fake byte failures"
    shared = importlib.import_module("independent_encoder")  # Types and B/C compatibility only.
    decoder = load_decoder(args.decoder)
    assert tuple(member.value for member in shared.FormId) == primary.FORM_IDS
    assert set(member.value for member in decoder.DecodeErrorCode) == set(primary.ERROR_CLASSIFICATIONS)
    exhaust_domains(decoder, shared)
    syntax_and_mutations(decoder, shared)
    malformed_requests_and_immutability(decoder, shared)
    assert len(POSITIVE_SEEN) == COUNTS["positiveDecodeCases"]
    assert COUNTS["primaryDecodeChecksA"] == COUNTS["encodeDecodeRoundTripsB"] == COUNTS["decodeEncodePrimaryRoundTripsC"] == len(POSITIVE_SEEN)
    assert COUNTS["primaryLiteralCases"] == literal_count == 30
    assert all(FORMS_DD[row.form_id] == set(row.allowed_dd) for row in primary.ROWS)
    print(json.dumps(dict(milestone="M2bc", domain="IndependentDecodeEncode", passed=True,
                          failed=0, skipped=0, firstMismatch=FIRST_MISMATCH,
                          primaryLiteralCases=literal_count, positiveDecodeCases=len(POSITIVE_SEEN),
                          encodeDecodeRoundTrips=COUNTS["encodeDecodeRoundTripsB"],
                          decodeEncodePrimaryRoundTrips=COUNTS["decodeEncodePrimaryRoundTripsC"],
                          negativeDecodeCases=COUNTS["negativeDecodeCases"],
                          counts=dict(COUNTS), coverageMembershipAttempts=dict(COVERAGE),
                          coverageCountsAreNotDisjointTotals=True, errors=dict(ERRORS),
                          negativeInputClassifications=dict(CLASSES), prefixGrammarProof=grammar_proof,
                          observedAmbiguousProfileMatches=ERRORS["AmbiguousProfileMatch"],
                          actualDecodeCalls=COUNTS["actualDecodeCalls"],
                          actualEncodeCalls=COUNTS["actualEncodeCalls"],
                          syntheticEncodedSequences=COUNTS["syntheticEncodedSequences"],
                          syntheticEncodedOctets=COUNTS["syntheticEncodedOctets"],
                          forms=15, secondaryRust="NotRun", actualRomExecutions=0,
                          asm662Executions=0, targetAssemblyObjectHex=0,
                          persistentMachineCodeFiles=0, firmwareBin=0, runtimePermission=False),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError, TypeError, AttributeError, ImportError, OSError) as error:
        print(json.dumps(dict(milestone="M2bc", passed=False, failed=1,
                              firstMismatch=FIRST_MISMATCH, error=str(error),
                              completedCounts=dict(COUNTS)), sort_keys=True))
        raise SystemExit(1)
