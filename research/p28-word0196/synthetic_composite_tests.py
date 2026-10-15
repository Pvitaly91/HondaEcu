"""Actual in-memory M2bj tests. Diagnostics never serialize machine payloads."""
import ast
import copy
import hashlib
import json
from contextlib import ExitStack
from dataclasses import replace, fields, FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import synthetic_composite_emitter as e
import synthetic_composite_primary_oracle as primary
import validate_synthetic_composite_contract as validator
from composite_emission_eligibility_tests import CASES as OLD_CASES, materialize

C = e.CompositeEmissionErrorCode
P = e.EmissionPhase


def check(condition, label):
    if not condition:
        raise AssertionError(label)  # Fixed metadata diagnostic; never actual bytes.


def request(dd=0):
    return {"exactBase": e.EXACT_BASE, "scope": e.SCOPE, "syntheticBase": 4096, "gap": 0, "initialDD": dd}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def exercise(models, req, hooks=()):
    """Trusted instrumentation only; public API never receives executable hooks."""
    counts = {"encoderA": 0, "encoderB": 0, "decoderA": 0, "decoderB": 0,
              "primary": 0, "publication": 0, "io": 0}
    originals = (e.route_a.encode_instruction, e.route_b.encode_direct_j,
                 e.decode_a.decode_instruction, e.decode_b.decode_direct_j,
                 e.expected_instruction, e.VerifiedSyntheticComposite)
    def counted(name, fn):
        def call(*args):
            counts[name] += 1
            return fn(*args)
        return call
    def no_io(*args, **kwargs):
        counts["io"] += 1
        raise AssertionError("Pure emitter attempted forbidden I/O")
    before = digest([*models, req])
    with ExitStack() as stack:
        for target, original, name in (
            ("synthetic_composite_emitter.route_a.encode_instruction", originals[0], "encoderA"),
            ("synthetic_composite_emitter.route_b.encode_direct_j", originals[1], "encoderB"),
            ("synthetic_composite_emitter.decode_a.decode_instruction", originals[2], "decoderA"),
            ("synthetic_composite_emitter.decode_b.decode_direct_j", originals[3], "decoderB"),
            ("synthetic_composite_emitter.expected_instruction", originals[4], "primary"),
            ("synthetic_composite_emitter.VerifiedSyntheticComposite", originals[5], "publication")):
            stack.enter_context(patch(target, counted(name, original)))
        for target in ("builtins.open", "pathlib.Path.open", "os.open", "os.system",
                       "subprocess.run", "subprocess.Popen"):
            stack.enter_context(patch(target, no_io))
        for name, hook in hooks:
            stack.enter_context(patch.object(e, name, hook))
        result = e.emit_synthetic_composite(*models, req)
    check(counts["io"] == 0 and digest([*models, req]) == before, "No I/O or caller data mutation")
    return result, counts


def safe_error(result, counts, code, phase, node=None):
    check(type(result) is e.ExplicitEmissionError, "Refusal must be explicit error")
    check(result.code is C(code) and result.phase is P(phase),
          "Exact error code/stage: " + result.code.value + "/" + result.phase.value)
    if node is not None:
        check(result.node_id == node, "Exact logical failure identity")
    check(counts["publication"] == 0, "No partial success publication on any error")
    check(tuple(f.name for f in fields(result)) == ("code", "phase", "node_id", "diagnostic"),
          "Closed byte-free error shape")
    check(not hasattr(result, "__dict__") and not hasattr(result, "encoded_bytes"),
          "No error payload or extension state")
    check(result.diagnostic == "Closed synthetic experiment refused; no output published.", "Safe fixed diagnostic")
    return {"code": result.code.value, "phase": result.phase.value, "node": result.node_id}


def encode_change(node_index, change):
    wanted = 4096 + primary.NODES[node_index].offset
    orig_a, orig_b = e._encode_a, e._encode_b
    def wrap(fn):
        def call(req):
            actual = fn(req)
            return change(actual, req) if req.origin_pc == wanted else actual
        return call
    return (("_encode_a", wrap(orig_a)), ("_encode_b", wrap(orig_b)))


def decode_change(node_index, change):
    wanted = 4096 + primary.NODES[node_index].offset
    orig_a, orig_b = e._decode_a, e._decode_b
    def wrap(fn):
        def call(req):
            actual = fn(req)
            return change(actual, req) if req.origin_pc == wanted else actual
        return call
    return (("_decode_a", wrap(orig_a)), ("_decode_b", wrap(orig_b)))


def run_suite():
    models, contract, upstream = validator.load_inputs()
    baseline = digest(models)
    positive = []
    totals = {name: 0 for name in ("encoderA", "encoderB", "decoderA", "decoderB", "primary", "publication", "io")}
    receipts = []
    def add_counts(counts):
        for key in totals:
            totals[key] += counts[key]
    results = []
    for dd in (0, 1):
        result, counts = exercise(models, request(dd))
        add_counts(counts)
        check(type(result) is e.VerifiedSyntheticComposite, "Scalar DD emission must succeed")
        check(type(result.encoded_bytes) is bytes and result.length == len(result.encoded_bytes) == 51,
              "Immutable exact51 emitted bytes")
        check(result.encoded_bytes == primary.expected_reference_for_test(dd), "All51 independently match reference")
        check(counts == {"encoderA":18,"encoderB":2,"decoderA":18,"decoderB":2,
                         "primary":20,"publication":1,"io":0}, "Exact positive actual call counts")
        check(len(result.boundaries) == 20 and all(type(b) is e.InstructionBoundary for b in result.boundaries),
              "Twenty frozen boundaries")
        cursor = 0
        for i, (b, fact) in enumerate(zip(result.boundaries, primary.NODES)):
            check((b.node_id, b.offset, b.length, b.origin, b.target) ==
                  (fact.node_id, fact.offset, fact.length, 4096+fact.offset, fact.target),
                  "Exact decoded boundary and target")
            check(b.offset == cursor and b.incoming_dd == (dd if i == 0 else 0), "Complete coverage/scalar DD")
            cursor += b.length
            check(result.encoded_bytes[b.offset:b.offset+b.length] == primary.expected_instruction(i),
                  "Per-form manufacturer primary match")
        check(cursor == 51 and result.internal_targets == ((21885,4138),(21893,4131),(21896,4131))
              and result.external_continuations == (("DirectJ_NotBelow",21910),("DirectJ_Below",21957)),
              "Three internal and two absolute targets")
        check(result.path_counts == (11,13,14,16) and result.ordered_write_counts == (3,3,3,5)
              and len(result.edges) == 23, "Actual decoded CFG and separate static effects")
        check([sum(edge[2] == kind for edge in result.edges)
               for kind in ("Fallthrough","ConditionalTaken","ExternalTransfer")] == [18,3,2],
              "Exact edge-kind counts")
        check(not any(hasattr(result,n) for n in ("FirmwareReady","nativeOwner","ROMPlacement","CPUExecution")),
              "No integration permission in success result")
        check("encoded_bytes" not in repr(result), "Payload suppressed from result repr")
        try:
            result.length = 52
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("Verified result must be frozen")
        results.append(result)
        positive.append({"initialDD":dd,"length":51,"sha256":hashlib.sha256(result.encoded_bytes).hexdigest(),
                         "primaryComparisons":20,"decoderComparisons":20,"boundaries":20,"octets":51})
    check(results[0].encoded_bytes == results[1].encoded_bytes and positive[0]["sha256"] == positive[1]["sha256"],
          "Actual streams independently compared across DD variants")

    # New scalar request and source/policy mutations, never old domain arrays.
    req_cases = (
        ("WrongExactBase", "exactBase", "0"*40, "SourceIdentity"),
        ("WrongInventedBase", "syntheticBase", 65485, "EligibilityRejected"),
        ("Gap1", "gap", 1, "EligibilityRejected"),
        ("WrongScalarDD", "initialDD", 2, "DDContextMismatch"),
        ("DomainInsteadOfScalar", "initialDD", [0,1], "DDContextMismatch"),
        ("BoolDD", "initialDD", True, "DDContextMismatch"),
        ("BoolBase", "syntheticBase", True, "EligibilityRejected"),
        ("WrongScope", "scope", "OtherFragment", "EligibilityRejected"),
        ("ROMInput", "romInput", "Forbidden", "PermissionViolation"),
        ("OutputBIN", "outputPath", "synthetic.bin", "PermissionViolation"),
        ("OutputHEX", "outputPath", "synthetic.hex", "PermissionViolation"),
        ("FirmwareReady", "FirmwareReady", True, "PermissionViolation"),
        ("CPUExecution", "targetCPUExecution", True, "PermissionViolation"),
        ("NativeOwner", "nativeOwner", "Fabricated", "PermissionViolation"),
        ("CABI", "compilerABI", "Invented", "PermissionViolation"),
        ("UserCodec", "codec", "OtherImplementation", "PermissionViolation"),
        ("Callback", "callbacks", "Forbidden", "PermissionViolation"),
        ("UnknownRequestField", "extra", 0, "RequestShape"),
    )
    for label, key, value, code in req_cases:
        req = request()
        req[key] = value
        result, counts = exercise(models, req)
        add_counts(counts)
        receipts.append({"label":label,"domain":"Request",**safe_error(result,counts,code,"Request")})
        check(sum(counts[k] for k in ("encoderA","encoderB","decoderA","decoderB","primary")) == 0,
              "Request refusal before codecs")

    # Prior independently declared semantic mutations reuse unchanged fixtures,
    # but exercise the NEW API/preflight with scalar DD, not historical tests.
    selected = {
        "WrongSourceSHA","MissingOriginalNode","DuplicateOriginalNode","MissingDirectJSlot","ThirdTransferSlot",
        "WrongM2bbCodecRoute","WrongDirectJCodecRoute","WrongTypedOperand","CMPImmediate00C0Changed",
        "OddCMPPageOffset","WrongDDAt5571","MissingLBReset","WrongJLTTarget","OldJLT64Reused",
        "JBSChangedTarget","NotBelowJTargets55C5","BelowJTargets5596","NotBelowFallsIntoBelow",
        "GateOrderChanged","LostSameValueStore","AddedStackPrologue","AddedRAMPointerRead","ChangedSCBLRB",
        "OutputAllowedAfterCodecError","PartialCompositeBufferSuccess","UnexpectedPadding",
    }
    check(selected <= {c["label"] for c in OLD_CASES}, "All selected semantic cases exist")
    for case in OLD_CASES:
        if case["label"] not in selected:
            continue
        mutant = materialize(*models, case)
        mutated_models = (mutant["ir"],mutant["composition"],mutant["eligibility"])
        code = e._preflight_error(case["expectedCode"])
        if case["label"] == "WrongSourceSHA":
            phase, code = "Identity", "SourceIdentity"
        else:
            phase = "Preflight"
        result, counts = exercise(mutated_models, request(1 if case["label"] == "MissingLBReset" else 0))
        add_counts(counts)
        receipts.append({"label":case["label"],"domain":"SemanticPlan",
                         **safe_error(result,counts,code,phase)})
        check(counts["encoderA"] + counts["encoderB"] == 0, "Semantic mismatch before first codec")

    # Additional reviewed operand, original logical target, node-order mutations.
    for label, mutation, code in (
        ("WrongPageOffset", lambda x:x[2]["typedRequestMapping"][0]["operandDescriptors"][1]["fields"].update(value=143),
         "TypedOperandMismatch"),
        ("OriginalJLTTarget55BF", lambda x:x[2]["typedRequestMapping"][6]["operandDescriptors"][0]["fields"].update(value=21951),
         "BranchTargetMismatch"),
        ("WrongNodeOrder", lambda x:x[2]["typedRequestMapping"].reverse(), "NodeOrderMismatch"),
        ("JPassedToRouteA", lambda x:x[2]["typedRequestMapping"][15].update(routeId="A"), "CodecRouteMismatch"),
        ("OriginalPassedToRouteB", lambda x:x[2]["typedRequestMapping"][0].update(routeId="B"), "CodecRouteMismatch"),
    ):
        mutated = copy.deepcopy(models)
        mutation(mutated)
        result, counts = exercise(mutated, request())
        add_counts(counts)
        receipts.append({"label":label,"domain":"SemanticPlan",**safe_error(result,counts,code,"Preflight")})

    # Delete a store from actual IR projections; reorder path write obligations.
    for label in ("MissingRAMWrite", "ReorderedRAMEffects"):
        mutated = copy.deepcopy(models)
        if label == "MissingRAMWrite":
            for inst in (mutated[0]["instructions"][17],mutated[1]["originalIRInstructions"][17]):
                inst["effects"].pop(0)
        else:
            mutated[1]["paths"][0]["originalPath"]["orderedWrites"].reverse()
        result, counts = exercise(mutated, request())
        add_counts(counts)
        receipts.append({"label":label,"domain":"SemanticPlan",
                         **safe_error(result,counts,"OrderedEffectMismatch","Preflight")})

    # Real encoded-byte corruptions: all twenty codecs really run before primary.
    byte_cases = (
        ("WrongJHeader",15,lambda b:bytes((2,))+b[1:]),
        ("SwappedJLowHigh",19,lambda b:b[:1]+b[2:3]+b[1:2]),
        ("ChangedORBImmediate",12,lambda b:b[:-1]+bytes((2,))),
        ("ChangedROLBSuffix",2,lambda b:b[:-1]+bytes((182,))),
        ("OldJLTDelta64Bytes",6,lambda b:b[:1]+bytes((64,))),
        ("JBSDeltaChangedBytes",9,lambda b:b[:-1]+bytes((11,))),
    )
    for label, index, corrupt in byte_cases:
        hooks = encode_change(index,lambda result, req:replace(result,encoded_bytes=corrupt(result.encoded_bytes)))
        result,counts = exercise(models,request(),hooks)
        add_counts(counts)
        receipts.append({"label":label,"domain":"ActualEncodedBytes",
                         **safe_error(result,counts,"PrimaryByteMismatch","Primary",primary.NODES[index].node_id)})
        check(counts["encoderA"]+counts["encoderB"] == 20 and counts["primary"] == index+1
              and counts["decoderA"]+counts["decoderB"] == 0, "Byte mutation reaches authoritative primary stage")

    # Legal alternate instruction really passes unchanged codec; semantic plan
    # disagrees with returned typed operand, not a blanket standalone rejection.
    def legal_other(result,req):
        other = replace(req,typed_operands=(e.route_a.AccumulatorA(),e.route_a.PageOffset8(143)))
        changed = e.route_a.encode_instruction(other)
        check(type(changed) is e.route_a.EncodedInstruction, "Changed legal standalone instruction accepted")
        return changed
    result,counts = exercise(models,request(),encode_change(0,legal_other))
    add_counts(counts)
    receipts.append({"label":"LegalOtherOperand","domain":"ActualLegalCodecResult",
                     **safe_error(result,counts,"TypedOperandMismatch","Encoding",21871)})

    for label,index,change,code in (
        ("WrongEncodedLength",5,lambda r,q:replace(r,length=4),"EncodedLengthMismatch"),
        ("TruncatedInstruction",19,lambda r,q:replace(r,encoded_bytes=r.encoded_bytes[:-1]),"EncodedLengthMismatch"),
        ("UnexpectedCodecOutput",0,lambda r,q:None,"UnexpectedOutput"),
        ("WrongCodecDD",1,lambda r,q:replace(r,incoming_dd=1),"DDContextMismatch"),
        ("WrongCodecOrigin",0,lambda r,q:replace(r,origin_pc=4097),"InstructionBoundaryMismatch"),
    ):
        result,counts = exercise(models,request(),encode_change(index,change))
        add_counts(counts)
        receipts.append({"label":label,"domain":"EncodedResultMetadata",
                         **safe_error(result,counts,code,"Encoding",primary.NODES[index].node_id)})

    assembly_cases = (
        ("AddedPadding",lambda parts:b"".join(parts)+bytes(13),"CompositeLengthMismatch"),
        ("TrailingByte",lambda parts:b"".join(parts)+bytes(1),"CompositeLengthMismatch"),
        ("RemovedByte",lambda parts:b"".join(parts)[:-1],"CompositeLengthMismatch"),
        ("DuplicatedByte",lambda parts:b"".join(parts)+parts[0][:1],"CompositeLengthMismatch"),
        ("ReorderedAdjacentInstructions",lambda parts:b"".join((parts[1],parts[0],*parts[2:])),
         "InstructionBoundaryMismatch"),
    )
    for label,hook,code in assembly_cases:
        result,counts = exercise(models,request(),(("_assemble",hook),))
        add_counts(counts)
        receipts.append({"label":label,"domain":"ActualAssembly",**safe_error(result,counts,code,"Assembly")})
        check(counts["primary"] == 20 and counts["encoderA"]+counts["encoderB"] == 20
              and counts["decoderA"]+counts["decoderB"] == 0, "Assembly mutation not metadata-only refusal")

    for label,index,change,code in (
        ("DecodedFormChanged",0,lambda r,q:replace(r,reviewed_form_id=e.route_a.FormId.LB_A_IMM8),
         "DecodedFormMismatch"),
        ("DecodedOperandChanged",0,lambda r,q:replace(r,typed_operands=(e.route_a.AccumulatorA(),e.route_a.PageOffset8(143))),
         "DecodedOperandMismatch"),
        ("DecodedInternalTargetChanged",6,lambda r,q:replace(r,relative_target_pc=4139),"DecodedTargetMismatch"),
        ("DecodedExternalTargetChanged",19,lambda r,q:replace(r,target=e.jtypes.ProgramTarget16(21910)),
         "DecodedTargetMismatch"),
        ("MissingDecodedLBReset",0,lambda r,q:replace(r,documented_dd_effect=e.decode_a.DDEffect.PRESERVES_DD_WHEN_EXECUTED),
         "DDContextMismatch"),
        ("DecodedLengthChanged",0,lambda r,q:replace(r,length=1),"InstructionBoundaryMismatch"),
        ("UnexpectedDecoderOutput",19,lambda r,q:None,"UnexpectedOutput"),
    ):
        result,counts = exercise(models,request(),decode_change(index,change))
        add_counts(counts)
        receipts.append({"label":label,"domain":"ActualDecoderResult",
                         **safe_error(result,counts,code,"Decoding",primary.NODES[index].node_id)})
        check(counts["primary"] == 20 and counts["encoderA"]+counts["encoderB"] == 20,
              "Decoder mutations reach real independent decode stage")

    # Closed deterministic fault cases; no retries or recovery, one call each.
    injections = []
    result,counts = exercise(models,{**request(),"scope":"Forbidden"})
    add_counts(counts)
    injections.append({"label":"BeforeFirstCodec",**safe_error(result,counts,"EligibilityRejected","Request"),
                       "counts":counts})
    for ordinal in (1,7,12,13,16,19,20):
        def injected(r,q):
            return (e.route_a.ExplicitError(e.route_a.ErrorCode.REQUEST_SHAPE)
                    if type(q) is e.route_a.EncoderRequest else
                    e.jtypes.DirectJEncodeError(e.jtypes.EncodeErrorCode.RequestShape))
        result,counts = exercise(models,request(),encode_change(ordinal-1,injected))
        add_counts(counts)
        injections.append({"label":"Instruction"+str(ordinal),
                           **safe_error(result,counts,"CodecError","Encoding",primary.NODES[ordinal-1].node_id),
                           "counts":counts})
        check(counts["encoderA"]+counts["encoderB"] == ordinal and counts["primary"] == 0
              and counts["decoderA"]+counts["decoderB"] == 0, "Exact no-fallback codec stop")
    original_primary = e._primary_expected
    def bad_primary(index):
        return bytes(1) if index == 19 else original_primary(index)
    result,counts = exercise(models,request(),(("_primary_expected",bad_primary),))
    add_counts(counts)
    injections.append({"label":"After20EncodersPrimaryLast",
                       **safe_error(result,counts,"PrimaryByteMismatch","Primary","DirectJ_Below"),"counts":counts})
    check(counts["encoderA"]+counts["encoderB"] == 20 and counts["decoderA"]+counts["decoderB"] == 0,
          "Primary failure after all20 calls, no decoder or bypass")
    result,counts = exercise(models,request(),decode_change(19,lambda r,q:
        e.jtypes.DirectJDecodeError(e.jtypes.DecodeErrorCode.UnsupportedEncoding)))
    add_counts(counts)
    injections.append({"label":"DecoderLast",**safe_error(result,counts,"IndependentDecodeError","Decoding","DirectJ_Below"),
                       "counts":counts})
    for hook_name,label,code,phase in (
        ("_check_final_length","FinalLength","CompositeLengthMismatch","FinalLength"),
        ("_check_final_metadata","FinalMetadata","InternalInvariant","FinalMetadata")):
        def fail(*args, error_code=code):
            raise e._Refusal(error_code)
        result,counts = exercise(models,request(),((hook_name,fail),))
        add_counts(counts)
        injections.append({"label":label,**safe_error(result,counts,code,phase),"counts":counts})
        check(counts["encoderA"]+counts["encoderB"] == 20 and counts["decoderA"]+counts["decoderB"] == 20,
              "Late refusal after all real codecs, no partial success")
    def unexpected(req):
        raise RuntimeError("Private exception suppressed")
    result,counts = exercise(models,request(),(("_encode_a",unexpected),))
    add_counts(counts)
    injections.append({"label":"UnexpectedException",**safe_error(result,counts,"InternalInvariant","Encoding",21871),
                       "counts":counts})

    # Independently pinned contract refusal, never accept a Verified=true status.
    metadata_refusals = 0
    for group,key,value in (
        ("safety","length",64),("safety","syntheticBase",65485),("safety","routeB",3),
        ("safety","output","PersistentBinaryAllowed"),("runtimeExclusions","FirmwareReady",True),
        ("runtimeExclusions","CPUExecutions",1),("runtimeExclusions","actualROMExecutions",1),
    ):
        mutated = copy.deepcopy(contract)
        mutated[group][key] = value
        try:
            validator.validate_metadata(mutated)
        except ValueError:
            metadata_refusals += 1
        else:
            raise AssertionError("Pinned contract mutation accepted")
    mutated = copy.deepcopy(contract)
    mutated["Verified"] = True
    try:
        validator.validate_metadata(mutated)
    except ValueError:
        metadata_refusals += 1
    else:
        raise AssertionError("Metadata success claim accepted")
    check(digest(models) == baseline and len(injections) == 13, "Inputs unchanged and all fault cases exercised")
    check(len(receipts) == len({r["label"] for r in receipts}), "Distinct mutation labels, no retries")
    sources = {}
    for filename in ("synthetic_composite_emitter.py","synthetic_composite_primary_oracle.py",
                     "synthetic_composite_tests.py","validate_synthetic_composite_contract.py",
                     "synthetic_composite_contract.json"):
        sources[filename] = hashlib.sha256((validator.DIR/filename).read_bytes()).hexdigest()
    return {"milestone":"M2bj","passed":True,"failed":0,"skipped":0,
            "status":"M2bj Atomic 51-Byte Synthetic Composite Encoding Verified",
            "positiveScalarDDRuns":2,"successfullyEmittedSequences":2,"distinctAcceptedInputs":2,
            "positive":positive,"ddStreamsEqual":True,"positiveEncoderCalls":40,"positiveRouteA":36,"positiveRouteB":4,
            "positiveDecoderCalls":40,"positivePrimaryComparisons":40,"positiveBoundaries":40,
            "positiveEmittedOctets":102,"negativeMutations":len(receipts),
            "negativeReceipts":receipts,"failureInjectionCases":len(injections),"injectionReceipts":injections,
            "atomicRefusals":len(receipts)+len(injections),"contractMutationRefusals":metadata_refusals,
            "actualTotalCalls":totals,"observedErrorCodes":sorted({r["code"] for r in receipts+injections}),
            "sourcePolicyASTNodes":validator.source_policy(),"firstMismatch":None,
            "sourceBindings":sources,"upstreamBindingCount":len(upstream),
            "persistentTargetObjects":0,"actualROMExecutions":0,"CPUExecutions":0,"FirmwareBIN":0,
            "effectProof":"StaticOnly_NoFabricatedNativeWriteJournal"}


if __name__ == "__main__":
    print("M2BJ_EVIDENCE_JSON="+json.dumps(run_suite(),sort_keys=True,separators=(",",":")))
