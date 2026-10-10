"""M2bb independent primary-vector, exhaustive and atomic-error tests.

Only invented instructions and in-memory bytes. Expected values are sourced
from the separately sealed manufacturer oracle, never from the implementation.
--red-absent runs a real module-presence assertion and reports byte cases NotRun.
"""
import argparse
from collections import Counter
import dataclasses
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import independent_encoder_oracle as oracle

COUNTS = Counter()
GROUPS = Counter()
ERRORS = Counter()
FIRST_MISMATCH = None


def load_encoder(path):
    spec = importlib.util.spec_from_file_location("m2bb_encoder_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def operand_objects(encoder, fact, values):
    result = []
    for kind, value in zip(fact.operand_kinds, values):
        cls = getattr(encoder, kind)
        if kind == "AccumulatorA":
            result.append(cls())
        elif kind in ("PageBit7", "PageBit5"):
            result.append(cls(offset=value[0], bit=value[1]))
        else:
            result.append(cls(value=value))
    return tuple(result)


def request(encoder, fact, values=None, origin=None, dd=0):
    return encoder.EncoderRequest(
        reviewed_form_id=encoder.FormId(fact.form_id),
        typed_operands=operand_objects(encoder, fact, fact.old_values if values is None else values),
        incoming_dd=dd,
        origin_pc=fact.old_origin if origin is None else origin,
    )


def call_encoder(encoder, req):
    COUNTS["actualEncodeCalls"] += 1
    result = encoder.encode_instruction(req)
    if type(result) is encoder.EncodedInstruction:
        COUNTS["syntheticSequencesEmitted"] += 1
        COUNTS["syntheticOctetsEmitted"] += len(result.encoded_bytes)
    return result


def success(encoder, req, expected, group):
    global FIRST_MISMATCH
    before = repr(req)
    result = call_encoder(encoder, req)
    try:
        assert type(result) is encoder.EncodedInstruction, result
        assert type(result.encoded_bytes) is bytes
        assert tuple(result.encoded_bytes) == expected, (tuple(result.encoded_bytes), expected)
        assert type(result.length) is int and result.length == len(expected)
        assert result.reviewed_form_id is req.reviewed_form_id
        assert result.origin_pc == req.origin_pc and type(result.origin_pc) is int
        assert result.typed_operands == req.typed_operands
        assert result.incoming_dd == req.incoming_dd
        assert result.classification == "SyntheticInstructionEncodingOnly"
        assert type(result.typed_operands) is tuple
        assert repr(req) == before
        assert dataclasses.is_dataclass(result) and result.__dataclass_params__.frozen
        assert not hasattr(result, "__dict__")
    except AssertionError:
        if FIRST_MISMATCH is None:
            FIRST_MISMATCH = dict(group=group, form=req.reviewed_form_id.value,
                                  request=repr(req), result=repr(result), expected=list(expected))
        raise
    COUNTS["positive"] += 1
    GROUPS[group] += 1
    return result


def snapshot(value):
    try:
        return repr(value)
    except AttributeError:
        return "MalformedMissingSlots:" + type(value).__name__


def failure(encoder, req, code, group="negative"):
    before = snapshot(req)
    result = call_encoder(encoder, req)
    assert type(result) is encoder.ExplicitError, result
    assert type(result.code) is encoder.ErrorCode and result.code.value == code, result
    assert tuple(field.name for field in dataclasses.fields(result)) == ("code",)
    assert not hasattr(result, "__dict__")
    for forbidden in ("encoded_bytes", "bytes", "partial_bytes", "length", "origin_pc",
                      "classification", "typed_operands", "firmware", "warning"):
        assert not hasattr(result, forbidden), forbidden
    assert call_encoder(encoder, req) == result
    assert snapshot(req) == before
    COUNTS["negative"] += 1
    GROUPS[group] += 1
    ERRORS[code] += 1


def altered(req, **changes):
    return dataclasses.replace(req, **changes)


def static_api_tests(encoder):
    assert tuple(member.value for member in encoder.FormId) == oracle.FORM_IDS
    assert set(member.value for member in encoder.ErrorCode) == {
        "RequestShape", "UnsupportedForm", "IncomingDDInvalid", "WrongDD", "OriginInvalid",
        "OriginSpanOutsideProfile", "OperandCount", "OperandKind", "OperandShape",
        "OperandRange", "FixedOperandMismatch", "OddWordOffsetOutsideProfile", "Rel8OutOfRange",
    }
    for cls in (encoder.EncoderRequest, encoder.EncodedInstruction, encoder.ExplicitError,
                *(getattr(encoder, name) for name in {
                    "AccumulatorA", "Register0", "Register1", "PageOffset8", "EvenPageOffset8",
                    "Immediate8", "Immediate16", "PageBit7", "PageBit5", "TargetPC16"})):
        assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen
        assert hasattr(cls, "__slots__")
    COUNTS["api"] += 1


def scalar_negatives(encoder, fact):
    base = request(encoder, fact)
    for dd in (None, True, False, -1, 2, 0.0, "0", [], {}):
        failure(encoder, altered(base, incoming_dd=dd), "IncomingDDInvalid", "invalidDD")
    if fact.dd_values == (0,):
        failure(encoder, altered(base, incoming_dd=1), "WrongDD", "wrongDD")
    for origin in (None, True, False, -1, 65536, 0.0, "0", [], {}):
        failure(encoder, altered(base, origin_pc=origin), "OriginInvalid", "invalidOrigin")
    for operands in (None, [], list(base.typed_operands), {}, "operands",
                     base.typed_operands[:-1], base.typed_operands + base.typed_operands[:1]):
        failure(encoder, altered(base, typed_operands=operands), "OperandCount", "operandCount")
    for index, kind in enumerate(fact.operand_kinds):
        for wrong in (None, True, False, 0, 0.0, "0", {}, [], object(),
                      encoder.Immediate8(0) if kind != "Immediate8" else encoder.PageOffset8(0)):
            operands = list(base.typed_operands)
            operands[index] = wrong
            failure(encoder, altered(base, typed_operands=tuple(operands)), "OperandKind", "operandKind")
        # Missing slots are malformed exact typed objects, not substituted dictionaries.
        if kind != "AccumulatorA":
            missing = object.__new__(getattr(encoder, kind))
            operands = list(base.typed_operands)
            operands[index] = missing
            failure(encoder, altered(base, typed_operands=tuple(operands)), "OperandShape", "missingOperandSlot")
        if kind == "AccumulatorA":
            continue
        field = "offset" if kind in ("PageBit7", "PageBit5") else "value"
        limit = 65535 if kind in ("Immediate16", "TargetPC16") else 255
        for invalid in (None, True, False, -1, limit + 1, 0.0, "0", [], {}):
            operands = list(base.typed_operands)
            operands[index] = dataclasses.replace(operands[index], **{field: invalid})
            failure(encoder, altered(base, typed_operands=tuple(operands)), "OperandRange", "scalarWidthType")
        if kind in ("Register0", "Register1", "PageBit7", "PageBit5"):
            fixed_field = "bit" if kind.startswith("PageBit") else "value"
            for bad_fixed in (2,):
                operands = list(base.typed_operands)
                operands[index] = dataclasses.replace(operands[index], **{fixed_field: bad_fixed})
                failure(encoder, altered(base, typed_operands=tuple(operands)),
                        "FixedOperandMismatch", "fixedIdentity")
            if kind.startswith("PageBit"):
                for bad_bit in (None, True, False, 7.0, "7", -1, 8, [], {}):
                    operands = list(base.typed_operands)
                    operands[index] = dataclasses.replace(operands[index], bit=bad_bit)
                    failure(encoder, altered(base, typed_operands=tuple(operands)),
                            "FixedOperandMismatch", "fixedBitType")
        # Constructors cannot quietly accept unknown fields.
        try:
            getattr(encoder, kind)(unknown_field=0)
        except TypeError:
            COUNTS["constructorRefusals"] += 1
        else:
            raise AssertionError("Unknown operand constructor field accepted")


def exhaustive_vectors(encoder):
    for fact in oracle.FORMS:
        # Original and newly invented independently literal-expected examples.
        for values, origin, expected, group in (
            (fact.old_values, fact.old_origin, fact.old_expected, "sealedOriginalExamples"),
            (fact.new_values, fact.new_origin, fact.new_expected, "newInventedExamples"),
        ):
            for dd in fact.dd_values:
                success(encoder, request(encoder, fact, values, origin, dd), expected, group)
        scalar_negatives(encoder, fact)
        for index, kind in enumerate(fact.operand_kinds):
            if kind not in ("PageOffset8", "EvenPageOffset8", "PageBit7", "PageBit5"):
                continue
            for value in range(256):
                values = list(fact.old_values)
                values[index] = (value, int(kind[-1])) if kind.startswith("PageBit") else value
                for dd in fact.dd_values:
                    req = request(encoder, fact, tuple(values), dd=dd)
                    if kind == "EvenPageOffset8" and value % 2:
                        failure(encoder, req, "OddWordOffsetOutsideProfile", "allOddCmpOffsets")
                    else:
                        success(encoder, req, oracle.primary_expected(fact.form_id, tuple(values), req.origin_pc), "allAllowedOffsets")
        for index, kind in enumerate(fact.operand_kinds):
            if kind not in ("Immediate8", "Immediate16"):
                continue
            for value in range(256 if kind == "Immediate8" else 65536):
                values = list(fact.old_values)
                values[index] = value
                for dd in fact.dd_values:
                    req = request(encoder, fact, tuple(values), dd=dd)
                    success(encoder, req, oracle.primary_expected(fact.form_id, tuple(values), req.origin_pc),
                            "allImmediate8" if kind == "Immediate8" else "allImmediate16")
        if "TargetPC16" in fact.operand_kinds:
            for origin in (128, 4096, 65405):
                for delta in range(-128, 128):
                    values = list(fact.old_values)
                    values[-1] = origin + fact.length + delta
                    for dd in fact.dd_values:
                        req = request(encoder, fact, tuple(values), origin, dd)
                        success(encoder, req, oracle.primary_expected(fact.form_id, tuple(values), origin), "allRel8")
            for delta in (-129, 128):
                values = list(fact.old_values)
                values[-1] = 4096 + fact.length + delta
                for dd in fact.dd_values:
                    failure(encoder, request(encoder, fact, tuple(values), 4096, dd),
                            "Rel8OutOfRange", "rel8Boundaries")
            for dd in fact.dd_values:
                failure(encoder, request(encoder, fact, origin=65536-fact.length, dd=dd),
                        "OriginSpanOutsideProfile", "noWrapNextPC")
                values = list(fact.old_values)
                values[-1] = 65535
                failure(encoder, request(encoder, fact, tuple(values), 0, dd),
                        "Rel8OutOfRange", "noModuloRepair")
        else:
            for dd in fact.dd_values:
                last_start = 65536-fact.length
                success(encoder, request(encoder, fact, origin=last_start, dd=dd),
                        oracle.primary_expected(fact.form_id, fact.old_values, last_start), "lastByteFFFF")
        for dd in fact.dd_values:
            if fact.length > 1:
                failure(encoder, request(encoder, fact, origin=65537-fact.length, dd=dd),
                        "OriginSpanOutsideProfile", "extentOverflow")
    # Fully crossed ORB offset/immediate pairs, independently varied fields.
    fact = next(f for f in oracle.FORMS if f.form_id == "orb-page-imm8")
    for offset in range(256):
        for immediate in range(256):
            values = (offset, immediate)
            for dd in fact.dd_values:
                success(encoder, request(encoder, fact, values, dd=dd),
                        oracle.primary_expected(fact.form_id, values, fact.old_origin), "orbOffsetImmediateCrossProduct")


def malformed_and_purity(encoder):
    base = request(encoder, oracle.FORMS[0])
    for malformed in (None, True, False, 0, 1.0, "request", [], {},
                      {"reviewed_form_id": "lb-a-page", "opcode": [244, 55]}):
        failure(encoder, malformed, "RequestShape", "requestShape")
    missing = object.__new__(encoder.EncoderRequest)
    failure(encoder, missing, "RequestShape", "missingRequestSlots")
    for identity in (None, True, False, 0, "lb-a-page", "jgt-c8", "add-er3-a",
                     "cal", "rt", "other-rN", "other-JBS-bit", [], {}):
        failure(encoder, altered(base, reviewed_form_id=identity), "UnsupportedForm", "unsupportedForm")
    for key in ("opcode", "encoded_bytes", "preload", "rom", "placement", "abi"):
        try:
            encoder.EncoderRequest(**dict(reviewed_form_id=base.reviewed_form_id,
                                         typed_operands=base.typed_operands, incoming_dd=0,
                                         origin_pc=256, **{key: True}))
        except TypeError:
            COUNTS["constructorRefusals"] += 1
        else:
            raise AssertionError("Unknown request constructor field accepted")
    # Slot/frozen protection and duplicate operand identity refusal.
    for instance, field in ((base, "origin_pc"), (base.typed_operands[1], "value")):
        try:
            setattr(instance, field, 1)
        except (dataclasses.FrozenInstanceError, AttributeError):
            COUNTS["immutability"] += 1
        else:
            raise AssertionError("Mutable request/operand")
        try:
            object.__setattr__(instance, "unknown_extra_field", 1)
        except AttributeError:
            COUNTS["constructorRefusals"] += 1
        else:
            raise AssertionError("Unknown extra slot accepted")
    duplicated = (encoder.PageOffset8(55), encoder.PageOffset8(55))
    failure(encoder, altered(base, typed_operands=duplicated), "OperandKind", "duplicateWrongIdentities")
    # LB encoding leaves incoming DD1 unchanged for a later independent request.
    lb = request(encoder, oracle.FORMS[0], dd=1)
    success(encoder, lb, oracle.FORMS[0].old_expected, "statelessLB")
    failure(encoder, request(encoder, oracle.FORMS[1], dd=lb.incoming_dd), "WrongDD", "statelessLB")
    # Left-to-right deterministic malformed policy, not undocumented global rank.
    cmp = request(encoder, oracle.FORMS[5], values=(55, 65536))
    failure(encoder, cmp, "OddWordOffsetOutsideProfile", "multipleInvalid")
    # Returned objects are immutable, including their byte sequence.
    result = call_encoder(encoder, base)
    try:
        result.encoded_bytes = b""
    except (dataclasses.FrozenInstanceError, AttributeError):
        COUNTS["immutability"] += 1
    else:
        raise AssertionError("Mutable encoded result")
    error = call_encoder(encoder, None)
    try:
        error.code = encoder.ErrorCode.WRONG_DD
    except (dataclasses.FrozenInstanceError, AttributeError):
        COUNTS["immutability"] += 1
    else:
        raise AssertionError("Mutable error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoder", type=Path, default=Path(__file__).with_name("independent_encoder.py"))
    parser.add_argument("--red-absent", action="store_true")
    args = parser.parse_args()
    if args.red_absent:
        try:
            assert args.encoder.is_file(), "Typed encoder module does not exist"
        except AssertionError as error:
            print(json.dumps(dict(milestone="M2bb", phase="REDAbsentHarness",
                                  testsRun=1, failed=1, byteAssertionsRun=0,
                                  primaryByteCasesNotRun=15, implementationExists=False,
                                  failure=str(error), encoderPath=str(args.encoder.resolve())),
                             sort_keys=True))
            return 1
        print(json.dumps(dict(milestone="M2bb", phase="REDAbsentHarnessInvalid",
                              implementationExists=True, reason="Cannot manufacture absent-implementation RED"), sort_keys=True))
        return 2
    oracle_literals = oracle.check_literal_examples()
    assert args.encoder.is_file(), "Typed encoder module does not exist"
    encoder = load_encoder(args.encoder)
    static_api_tests(encoder)
    exhaustive_vectors(encoder)
    malformed_and_purity(encoder)
    print(json.dumps(dict(milestone="M2bb", domain="IndependentEncoder",
                          passed=True, failed=0, skipped=0, firstMismatch=FIRST_MISMATCH,
                          oracleLiteralCases=oracle_literals, counts=dict(COUNTS),
                          coverage=dict(GROUPS), errors=dict(ERRORS), forms=15,
                          syntheticEncodingVectors=COUNTS["positive"],
                          actualEncodeCalls=COUNTS["actualEncodeCalls"],
                          syntheticSequencesEmitted=COUNTS["syntheticSequencesEmitted"],
                          syntheticOctetsEmitted=COUNTS["syntheticOctetsEmitted"],
                          persistentMachineCodeFiles=0, actualRomExecutions=0,
                          asm662Executions=0, targetAssemblyObjectHex=0,
                          firmwareBin=0, runtimePermission=False),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError, TypeError, AttributeError, ImportError, OSError) as error:
        print(json.dumps(dict(milestone="M2bb", domain="IndependentEncoder", passed=False,
                              failed=1, firstMismatch=FIRST_MISMATCH, error=str(error),
                              completedCounts=dict(COUNTS), persistentMachineCodeFiles=0), sort_keys=True))
        raise SystemExit(1)
