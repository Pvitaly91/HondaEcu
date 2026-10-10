"""Invented-only design/admission tests. No encoder/byte emitter exists here."""
import copy
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import validate_independent_encoder_design as design

COUNTS = dict(positive=0, negative=0, properties=0, propertyVectors=0)
CASES = []


def positive(name, action):
    action()
    COUNTS["positive"] += 1
    CASES.append(name)


def refused(name, action):
    try:
        action()
    except (ValueError, TypeError, UnicodeError, RecursionError):
        COUNTS["negative"] += 1
        if name not in CASES:
            CASES.append(name)
        return
    raise AssertionError("Expected refusal: " + name)


def assert_model(request, code=None):
    result = design.specification_request_model(request)
    assert set(result).isdisjoint({"bytes", "encodedBytes", "assembly", "object", "firmware"})
    if code is None:
        assert result["status"] == "SpecificationAccepts", result
    else:
        assert result == dict(status="ExplicitError", code=code), result


def bad_request(name, request, code):
    assert_model(request, code)
    COUNTS["negative"] += 1
    CASES.append(name)


def leaf_paths(value, path=()):
    if type(value) is dict:
        for key, child in value.items():
            yield from leaf_paths(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from leaf_paths(child, path + (index,))
    else:
        yield path, value


def main():
    profile = design.profile()
    positive("exactClosedPrimaryProfile", lambda: design.validate(profile))
    positive("boundedStrictJSON", lambda: design.validate(design.parse_contract(Path(__file__).with_name("independent_encoder_design.json").read_bytes())))
    for fact in design.FACTS:
        positive("primaryExample:" + fact[0], lambda f=fact: assert_model(design.example_request(f)))
        assert len(fact[7]) == len(fact[10])
        for dd in (0, 1):
            request = design.example_request(fact, dd)
            if fact[5] == "Requires0" and dd == 1:
                bad_request("wrongDD:" + fact[0], request, "WrongDD")
            else:
                positive("allowedDD:" + fact[0] + ":" + str(dd), lambda r=request: assert_model(r))
        for index, kind in enumerate(fact[6]):
            for invalid in (None, True, False, 1.0, "1", [], {}):
                request = design.example_request(fact)
                request["typedOperands"][index] = invalid
                bad_request("unsupportedOperandKind:" + fact[0], request, "OperandKind")
            request = design.example_request(fact)
            request["typedOperands"][index]["unexpected"] = 0
            bad_request("unexpectedOperandField:" + fact[0], request, "OperandShape")
            request = design.example_request(fact)
            request["typedOperands"] = request["typedOperands"][:-1]
            bad_request("operandCount:" + fact[0], request, "OperandCount")
            if kind == "AccumulatorA":
                continue
            field = "offset" if kind.startswith("PageBit") else "value"
            maximum = 65535 if kind in ("Immediate16", "TargetPC16") else 255
            for value in (-1, maximum + 1, True, False, 0.0, "0", None):
                request = design.example_request(fact)
                request["typedOperands"][index][field] = value
                bad_request("widthOrType:" + fact[0], request, "OperandRange")
            if kind.startswith("Register") or kind.startswith("PageBit"):
                request = design.example_request(fact)
                fixed_field = "bit" if kind.startswith("PageBit") else "value"
                request["typedOperands"][index][fixed_field] = 2
                bad_request("fixedOperand:" + fact[0], request, "FixedOperandMismatch")
            if kind == "EvenPageOffset8":
                request = design.example_request(fact)
                request["typedOperands"][index]["value"] = 55
                bad_request("oddCMPIsNarrowProfileNotISAFault", request, "OddWordOffsetOutsideProfile")
        for dd in (-1, 2, True, None, 0.0, "0"):
            request = design.example_request(fact)
            request["incomingDD"] = dd
            bad_request("unknownDD:" + fact[0], request, "IncomingDDInvalid")
        for origin in (-1, 65536, True, None, 0.0, "0"):
            request = design.example_request(fact)
            request["originPC"] = origin
            bad_request("invalidOrigin:" + fact[0], request, "OriginInvalid")
        request = design.example_request(fact)
        request["originPC"] = 65535
        if len(fact[10]) > 1 or "rel8" in fact[7]:
            bad_request("originSpanOverflow:" + fact[0], request, "OriginSpanOutsideProfile")
        else:
            positive("singleByteAtFFFF", lambda r=request: assert_model(r))
    # Mutate every reviewed leaf, not a new identity/permission claim from JSON.
    for path, value in leaf_paths(profile):
        alternatives = [None, True, False, "forged", -1, 0.0, [], {}]
        for changed in alternatives:
            if design.equal(value, changed):
                continue
            mutant = copy.deepcopy(profile)
            parent = mutant
            for step in path[:-1]:
                parent = parent[step]
            parent[path[-1]] = changed
            refused("closedProfileLeafMutation", lambda m=mutant: design.validate(m))
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'\xef\xbb\xbf{}', b'[]junk', b' '*65537):
        refused("malformedDuplicateNonFiniteOrUnboundedJSON", lambda r=raw: design.parse_contract(r))
    for form in ("jgt-c8", "add-er3-a", "arbitrary-rN", "firmware", None, True, []):
        request = design.example_request(design.FACTS[0])
        request["reviewedFormId"] = form
        bad_request("unsupportedFormNoDerivedFallback", request, "UnsupportedForm")
    for field in ("preload", "rom", "linker", "placement", "abi", "padToLength", "generatedBytes"):
        request = design.example_request(design.FACTS[0])
        request[field] = True
        bad_request("noExpandedPipeline:" + field, request, "RequestShape")
    # Operand-first deterministic precedence is explicit, not global stage priority.
    request = design.example_request(design.FACTS[5])
    request["typedOperands"][0]["value"] = 55
    request["typedOperands"][1]["value"] = 65536
    bad_request("leftToRightOddBeforeLaterOverflow", request, "OddWordOffsetOutsideProfile")
    request = design.example_request(design.FACTS[5])
    request["typedOperands"][0]["value"] = -1
    request["typedOperands"][1]["kind"] = "PageOffset8"
    bad_request("leftToRightRangeBeforeLaterKind", request, "OperandRange")
    request = design.example_request(design.FACTS[7])
    request["typedOperands"][0]["value"] = 2
    request["typedOperands"][1]["extra"] = 0
    bad_request("leftToRightFixedBeforeLaterShape", request, "FixedOperandMismatch")
    # Exhaustive invented scalar policy checks; outputs are metadata, never bytes.
    vectors = 0
    for fact in design.FACTS:
        for index, kind in enumerate(fact[6]):
            if kind not in ("PageOffset8", "EvenPageOffset8", "Immediate8", "Immediate16", "PageBit7", "PageBit5"):
                continue
            maximum = 65535 if kind == "Immediate16" else 255
            for value in range(maximum + 1):
                request = design.example_request(fact)
                request["typedOperands"][index]["offset" if kind.startswith("PageBit") else "value"] = value
                assert_model(request, "OddWordOffsetOutsideProfile" if kind == "EvenPageOffset8" and value % 2 else None)
                vectors += 1
    COUNTS["properties"] += 1
    COUNTS["propertyVectors"] += vectors
    CASES.append("exhaustiveScalarWidthsNoEmitter")
    vectors = 0
    for fact in design.FACTS:
        if "rel8" not in fact[7]:
            continue
        for dd in (0, 1):
            for delta in range(-257, 258):
                request = design.example_request(fact, dd)
                request["originPC"] = 4096
                request["typedOperands"][-1]["value"] = 4096 + len(fact[10]) + delta
                assert_model(request, None if -128 <= delta <= 127 else "Rel8OutOfRange")
                if -128 <= delta <= 127:
                    assert design.specification_request_model(request)["displacement"] == delta
                vectors += 1
        request = design.example_request(fact)
        request["originPC"] = 65536 - len(fact[10])
        bad_request("nextPCWrapForbidden", request, "OriginSpanOutsideProfile")
        request = design.example_request(fact)
        request["originPC"] = 0
        request["typedOperands"][-1]["value"] = 65535
        bad_request("noModuloRelativeRepair", request, "Rel8OutOfRange")
    COUNTS["properties"] += 1
    COUNTS["propertyVectors"] += vectors
    CASES.append("exhaustiveSignedRel8FromNextPCNoWrap")
    # Determinism and no buffer/default bytes even on multiply invalid requests.
    for fact in design.FACTS:
        request = design.example_request(fact)
        for field, invalid in (("reviewedFormId", "unknown"), ("incomingDD", True), ("originPC", -1), ("typedOperands", [])):
            request[field] = invalid
            first = design.specification_request_model(request)
            assert first == design.specification_request_model(copy.deepcopy(request))
            assert set(first) == {"status", "code"}
            COUNTS["propertyVectors"] += 1
    COUNTS["properties"] += 1
    CASES.append("deterministicErrorsAndNoBytesOnFailure")
    assert COUNTS["positive"] > 0 and COUNTS["negative"] > 0
    print(json.dumps(dict(milestone="M2ba", domain="EncoderDesign", passed=True,
                          **COUNTS, cases=sorted(set(CASES)), encoderImplemented=False,
                          runtimeVerified=False, actualRomExecutions=0, assemblerExecutions=0,
                          targetBytes=0, firmwareBin=0), sort_keys=True))


if __name__ == "__main__":
    main()
