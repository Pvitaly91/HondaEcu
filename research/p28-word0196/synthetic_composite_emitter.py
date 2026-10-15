"""Atomic research-only in-memory composite emitter. No I/O or execution.

Validation/error precedence was frozen before implementation. Only fixed
reviewed upstream plans and approved scalar-DD requests are accepted. A success
object is constructed once, after every primary/decode/structural check.
"""
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum, unique

import independent_encoder as route_a
import independent_decoder as decode_a
import direct_j_encoder as route_b
import direct_j_decoder as decode_b
import direct_j_types as jtypes
from composite_emission_eligibility_analysis import (
    prepare_composite_emission_plan, EligibilityError,
)
from synthetic_composite_primary_oracle import (
    NODES, EXACT_BASE, SCOPE, expected_instruction,
)


@unique
class CompositeEmissionErrorCode(str, Enum):
    SourceIdentity = "SourceIdentity"
    RequestShape = "RequestShape"
    EligibilityRejected = "EligibilityRejected"
    InventoryMismatch = "InventoryMismatch"
    NodeOrderMismatch = "NodeOrderMismatch"
    TypedOperandMismatch = "TypedOperandMismatch"
    CodecRouteMismatch = "CodecRouteMismatch"
    CodecError = "CodecError"
    EncodedLengthMismatch = "EncodedLengthMismatch"
    CompositeLengthMismatch = "CompositeLengthMismatch"
    InstructionBoundaryMismatch = "InstructionBoundaryMismatch"
    PrimaryByteMismatch = "PrimaryByteMismatch"
    IndependentDecodeError = "IndependentDecodeError"
    DecodedFormMismatch = "DecodedFormMismatch"
    DecodedOperandMismatch = "DecodedOperandMismatch"
    DecodedTargetMismatch = "DecodedTargetMismatch"
    DDContextMismatch = "DDContextMismatch"
    BranchTargetMismatch = "BranchTargetMismatch"
    CFGInvariantViolation = "CFGInvariantViolation"
    ContextObligationMismatch = "ContextObligationMismatch"
    OrderedEffectMismatch = "OrderedEffectMismatch"
    AtomicityViolation = "AtomicityViolation"
    UnexpectedOutput = "UnexpectedOutput"
    PermissionViolation = "PermissionViolation"
    InternalInvariant = "InternalInvariant"


@unique
class EmissionPhase(str, Enum):
    Identity = "Identity"
    Request = "Request"
    Preflight = "Preflight"
    Plan = "Plan"
    TypedRequests = "TypedRequests"
    Encoding = "Encoding"
    Primary = "Primary"
    Assembly = "Assembly"
    Decoding = "Decoding"
    Structure = "Structure"
    FinalLength = "FinalLength"
    FinalMetadata = "FinalMetadata"
    Publication = "Publication"


@dataclass(frozen=True, slots=True)
class ExplicitEmissionError:
    code: CompositeEmissionErrorCode
    phase: EmissionPhase
    node_id: int | str | None
    diagnostic: str = "Closed synthetic experiment refused; no output published."


@dataclass(frozen=True, slots=True)
class InstructionBoundary:
    node_id: int | str
    original_logical_site_id: int | None
    route: str
    form: str
    offset: int
    length: int
    origin: int
    incoming_dd: int
    target: int | None


@dataclass(frozen=True, slots=True)
class VerifiedSyntheticComposite:
    encoded_bytes: bytes = field(repr=False)
    synthetic_base: int
    length: int
    boundaries: tuple[InstructionBoundary, ...]
    initial_dd: int
    internal_targets: tuple[tuple[int, int], ...]
    external_continuations: tuple[tuple[str, int], ...]
    edges: tuple[tuple[int | str, int | str, str], ...]
    path_counts: tuple[int, ...]
    ordered_write_counts: tuple[int, ...]
    primary_verdict: str = "ManufacturerPrimaryBytesVerified"
    decoder_verdict: str = "IndependentDecodeCompatibilityVerified"
    cfg_classification: str = "StaticDecodedCFGOnly_NotExecutedPaths"
    effects_classification: str = "RetainedReviewedStaticObligations_NotNativeWriteJournal"
    classification: str = "SyntheticCompositeMachineCodeOnly"


class _Refusal(Exception):
    def __init__(self, code):
        self.code = CompositeEmissionErrorCode(code)


def _need(condition, code):
    if not condition:
        raise _Refusal(code)


def _exact(actual, expected):
    """Exact recursive type-and-value equality, not bool/int dataclass equality."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(_exact(actual[k], v) for k, v in expected.items())
    if type(expected) in (tuple, list):
        return len(actual) == len(expected) and all(_exact(a, b) for a, b in zip(actual, expected))
    if is_dataclass(expected):
        return all(_exact(getattr(actual, f.name), getattr(expected, f.name)) for f in fields(expected))
    return actual == expected


# Declared immutable identities; actual file hashing belongs to the fixed loader.
_UPSTREAM = [{"file":"research/p28-word0196/continuation_transfer_analysis.py","bytes":78628,"sha256":"86eb302ae13138aef5a64b192e5d4b63982afa1e4bb3e9c4b3d71b9f927c355c"},{"file":"research/p28-word0196/continuation_transfer_oracle.py","bytes":12784,"sha256":"5c250c75ee7d950e766cf747381efc125545b192a5c7d7b0e8b01a1c6b3909fb"},{"file":"research/p28-word0196/continuation_transfer_tests.py","bytes":19256,"sha256":"e47b4e34bf2ee42e5e5f7c118becb9dffb71864e1a57030a9aedd2fbb83b833d"},{"file":"research/p28-word0196/direct_j_contract.json","bytes":23868,"sha256":"1be70eb96f4c75c8f42729f2b41aacc2f43b4923c3db0aacccd1b5bc2a2a8c35"},{"file":"research/p28-word0196/direct_j_decoder.py","bytes":2006,"sha256":"32738de208889d288856feda6f030c78b08d5cf3cf7ca0154120b32fc788c3a4"},{"file":"research/p28-word0196/direct_j_encoder.py","bytes":1926,"sha256":"1149ba3fcc142fa1fb78677ddd14b8c4bbab1ee333ef926aaffe22839d7f6f60"},{"file":"research/p28-word0196/direct_j_primary_oracle.py","bytes":4051,"sha256":"91793837663e8d0341ce0d4e224fc97e256c549409807ea9b43e8d9266f55f39"},{"file":"research/p28-word0196/direct_j_tests.py","bytes":18346,"sha256":"c5a3cbb6f10b9cafaf342a0ed5b5bd86921f58fcfa9af1f469f1b741f6cc8d7c"},{"file":"research/p28-word0196/direct_j_types.py","bytes":3021,"sha256":"f11877a07340b88a7c222acec250767524778955a96235a6dd147207fa99467b"},{"file":"research/p28-word0196/external_continuation_contract.json","bytes":58097,"sha256":"bce975c6427e0ab9294af8227933f0b2553efa13a47b89383f53fc4ac6138660"},{"file":"research/p28-word0196/independent_decode_encode_contract.json","bytes":17800,"sha256":"547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d"},{"file":"research/p28-word0196/independent_decoder_primary_oracle.py","bytes":12745,"sha256":"9154ceac6709d8ad93fa71ab77f5b1e5c601dbaa812d60d4e3681b08f4b8e1df"},{"file":"research/p28-word0196/independent_decoder_tests.py","bytes":19933,"sha256":"cdc5d43ee866dba4fb619fc6169e2ec5e869d4050f98137bb67e62ca0a2bdb64"},{"file":"research/p28-word0196/independent_decoder.py","bytes":11036,"sha256":"e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404"},{"file":"research/p28-word0196/independent_encoder_contract.json","bytes":12182,"sha256":"414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47"},{"file":"research/p28-word0196/independent_encoder_design.json","bytes":21765,"sha256":"9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9"},{"file":"research/p28-word0196/independent_encoder_oracle.py","bytes":7092,"sha256":"6575f802c0703da087f1f06fdff095dcf4c4b948b7fe59e8fb35972210cb6361"},{"file":"research/p28-word0196/independent_encoder_tests.py","bytes":18429,"sha256":"76ca001260dbf07b0c5ad99f72e156732b940756af2c177e2b97311acba3b62c"},{"file":"research/p28-word0196/independent_encoder.py","bytes":9868,"sha256":"603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879"},{"file":"research/p28-word0196/layout_feasibility_analysis.py","bytes":40569,"sha256":"840320c5eed83d2a393dd3d1f4c8b90cb0aa7608c5c2ba721384265e79d151db"},{"file":"research/p28-word0196/layout_feasibility_contract.json","bytes":66622,"sha256":"9d1baf1e4914fa1b611924ff48b75854e9fc7d2e06e6e05542c56c14e18abb2f"},{"file":"research/p28-word0196/layout_feasibility_oracle.py","bytes":10843,"sha256":"be17e854a1b474b3800b09d74219ba097fc48bd2a2a53db93752169c3da06394"},{"file":"research/p28-word0196/layout_feasibility_tests.py","bytes":26061,"sha256":"55377f7bd6c6c0ad1b5c29e7cc66eeb32aa63a3db8d1b849318c98326d74cd5e"},{"file":"research/p28-word0196/target_abi_contract.json","bytes":40753,"sha256":"1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"},{"file":"research/p28-word0196/transfer_form_evidence.json","bytes":37225,"sha256":"f4279b5c86cc78be18f641e0638ea58892329f0b8903db28a8b6b77d69d34194"},{"file":"research/p28-word0196/typed_lowering_analysis.py","bytes":31589,"sha256":"bd0ad1ee186cb76922926a957c21bacafc601e77200ff3bdcdc09fd866143bc5"},{"file":"research/p28-word0196/typed_lowering_contract.json","bytes":44984,"sha256":"6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4"},{"file":"research/p28-word0196/typed_lowering_oracle.py","bytes":12601,"sha256":"2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a"},{"file":"research/p28-word0196/typed_lowering_tests.py","bytes":29917,"sha256":"1e46516c85b1d0b0593b67e59943b7b2d459725a073f29f23d385f59f73d7c6a"},{"file":"research/p28-word0196/validate_direct_j_contract.py","bytes":37218,"sha256":"207b658479da79f911e317df8a71402370e7336f3ddcaa7f65a28de6efad8e85"},{"file":"research/p28-word0196/validate_external_continuation_contract.py","bytes":76985,"sha256":"6dfd2a85c6fa5187e4bb2649d8b96db2b61ffe584f0b9b7b4124fc058550da7e"},{"file":"research/p28-word0196/validate_layout_feasibility_contract.py","bytes":48319,"sha256":"e6656112d6272adeac3f382ee672a4ddd3b01fe645dcab356444b0cefd6d51ea"},{"file":"research/p28-word0196/word0196_equivalent.c","bytes":8507,"sha256":"4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3"},{"file":"research/p28-word0196/word0196_equivalent.h","bytes":2390,"sha256":"df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e"},{"file":"research/p28-word0196/word0196_ir.json","bytes":32188,"sha256":"4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"},{"file":"src/HondaEcu.Core/P28Word0196AlternateModel.cs","bytes":3464,"sha256":"ac3162dfc6255e25ac24d7430531243f7856090ce55bab8b46e20d07f06fd74f"},{"file":"research/p28-word0196/static_composition_contract.json","bytes":106872,"sha256":"3c3b0448e0bc2c232663fd9607b9d576a074238c7c823de50eafd6dcc2da2eb3"},{"file":"research/p28-word0196/static_composition_analysis.py","bytes":130811,"sha256":"338f08abc06e27dffb2e64246cadcd8119727a05e448a5099cf9f539f3181547"},{"file":"research/p28-word0196/static_composition_oracle.py","bytes":22613,"sha256":"bde29d3150c9f9d6918435f08fc1edf051869f523c7c0e4dc6f0b52f24244462"},{"file":"research/p28-word0196/static_composition_tests.py","bytes":28389,"sha256":"3cbddb0b82b4a851317a8fdc9c51a8e96bffc526fcfde846181e863d5c9391ce"},{"file":"research/p28-word0196/validate_static_composition_contract.py","bytes":121642,"sha256":"f04d149e15658aca6c9d2fcdd633916703fb412f9a1995dc2adf0f22366cd915"}]
_IDS = tuple(n.node_id for n in NODES)


def _identity(eligibility):
    _need(type(eligibility) is dict, "RequestShape")
    _need(_exact(eligibility.get("upstreamBindings"), _UPSTREAM), "SourceIdentity")


def _request(request):
    _need(type(request) is dict, "RequestShape")
    forbidden = {"romInput", "outputPath", "FirmwareReady", "targetCPUExecution",
                 "nativeOwner", "compilerABI", "callbacks", "codec", "ROM", "flashing"}
    _need(not forbidden.intersection(request), "PermissionViolation")
    _need(set(request) == {"exactBase", "scope", "syntheticBase", "gap", "initialDD"}, "RequestShape")
    _need(type(request["exactBase"]) is str and request["exactBase"] == EXACT_BASE, "SourceIdentity")
    _need(type(request["scope"]) is str and request["scope"] == SCOPE, "EligibilityRejected")
    _need(type(request["syntheticBase"]) is int and request["syntheticBase"] == 4096
          and type(request["gap"]) is int and request["gap"] == 0, "EligibilityRejected")
    _need(type(request["initialDD"]) is int and request["initialDD"] in (0, 1), "DDContextMismatch")


def _preflight_error(code):
    if code.startswith("Source") or code == "ExactBaseMismatch":
        return "SourceIdentity"
    if code in ("NodeInventoryMismatch", "OriginalSiteMismatch", "TransferInventoryMismatch"):
        return "InventoryMismatch"
    if code in ("CodecRouteMismatch",):
        return "CodecRouteMismatch"
    if code.startswith("DD") or code == "FlagFlowMismatch":
        return "DDContextMismatch"
    if code in ("BranchTargetMismatch", "ContinuationMismatch", "Rel8OutOfRange"):
        return "BranchTargetMismatch"
    if code.startswith("Operand") or code in ("FixedOperandMismatch", "OddWordOffsetOutsideProfile", "UnsupportedForm"):
        return "TypedOperandMismatch"
    if code in ("InstructionLengthMismatch", "OriginProjectionMismatch", "NodeSpanMismatch"):
        return "InstructionBoundaryMismatch"
    if "CFG" in code or code in ("PathMismatch", "SuccessorMismatch"):
        return "CFGInvariantViolation"
    if "Context" in code or "ABI" in code or "Retain" in code or code == "TransferSpecificationMismatch":
        return "ContextObligationMismatch"
    if "Effect" in code or "Write" in code or "Memory" in code:
        return "OrderedEffectMismatch"
    if "Atomicity" in code:
        return "AtomicityViolation"
    if "Runtime" in code or "Permission" in code or "Owner" in code:
        return "PermissionViolation"
    if code == "InputShape":
        return "RequestShape"
    return "EligibilityRejected"


def _inventory(eligibility):
    rows = eligibility.get("typedRequestMapping")
    _need(type(rows) is list and len(rows) == 20
          and all(type(r) is dict for r in rows), "InventoryMismatch")
    ids = tuple(r.get("nodeId") for r in rows)
    _need(all(type(x) in (int, str) for x in ids)
          and len(set(ids)) == 20 and set(ids) == set(_IDS), "InventoryMismatch")
    _need(_exact(ids, _IDS), "NodeOrderMismatch")


def _preflight_node(location):
    """Reduce old safe locations to closed identities; never echo arbitrary input."""
    if type(location) is not str:
        return None
    segments = location.split("/")
    for identity in _IDS:
        if str(identity) in segments:
            return identity
    for label in ("typedRequestMapping", "instructions", "originalIRInstructions"):
        if label in segments:
            position = segments.index(label) + 1
            if position < len(segments) and segments[position].isdigit():
                index = int(segments[position])
                candidates = _IDS if label == "typedRequestMapping" else tuple(x for x in _IDS if type(x) is int)
                if 0 <= index < len(candidates):
                    return candidates[index]
    return None


def _operand(descriptor):
    _need(type(descriptor) is dict and set(descriptor) == {"kind", "fields"}, "TypedOperandMismatch")
    kind, f = descriptor["kind"], descriptor["fields"]
    _need(type(kind) is str and type(f) is dict, "TypedOperandMismatch")
    if kind == "AccumulatorA":
        _need(f == {}, "TypedOperandMismatch")
        return route_a.AccumulatorA()
    if kind in ("PageBit7", "PageBit5"):
        _need(set(f) == {"offset", "bit"} and type(f["offset"]) is int
              and 0 <= f["offset"] <= 255 and type(f["bit"]) is int
              and f["bit"] == (7 if kind == "PageBit7" else 5), "TypedOperandMismatch")
        if kind == "PageBit7":
            return route_a.PageBit7(f["offset"], f["bit"])
        return route_a.PageBit5(f["offset"], f["bit"])
    _need(set(f) == {"value"} and type(f["value"]) is int, "TypedOperandMismatch")
    value = f["value"]
    _need(0 <= value <= (65535 if kind in ("Immediate16", "TargetPC16", "ProgramTarget16") else 255),
          "TypedOperandMismatch")
    if kind == "Register0":
        _need(value == 0, "TypedOperandMismatch")
        return route_a.Register0(value)
    if kind == "Register1":
        _need(value == 1, "TypedOperandMismatch")
        return route_a.Register1(value)
    if kind == "PageOffset8":
        return route_a.PageOffset8(value)
    if kind == "EvenPageOffset8":
        _need(value % 2 == 0, "TypedOperandMismatch")
        return route_a.EvenPageOffset8(value)
    if kind == "Immediate8":
        return route_a.Immediate8(value)
    if kind == "Immediate16":
        return route_a.Immediate16(value)
    if kind == "TargetPC16":
        return route_a.TargetPC16(value)
    if kind == "ProgramTarget16":
        return jtypes.ProgramTarget16(value)
    raise _Refusal("TypedOperandMismatch")


def _construct_requests(plans, initial_dd):
    requests = []
    for i, (plan, fact) in enumerate(zip(plans, NODES)):
        expected_dd = initial_dd if i == 0 else 0
        _need(_exact(plan["incomingDDDomain"], [expected_dd]), "DDContextMismatch")
        operands = tuple(_operand(d) for d in plan["typedOperands"])
        _need(len(plan["requestVariants"]) == 1, "TypedOperandMismatch")
        variant = plan["requestVariants"][0]
        if plan["routeId"] == "A":
            _need(plan["formId"] != "j-address" and all(type(o) is not jtypes.ProgramTarget16 for o in operands),
                  "CodecRouteMismatch")
            req = route_a.EncoderRequest(route_a.FormId(plan["formId"]), operands, expected_dd, plan["assignedPC"])
            wanted_variant = {"requestClass": "EncoderRequest", "fields": {
                "reviewed_form_id": {"enumClass": "FormId", "value": fact.form},
                "typed_operands": {"container": "tuple", "items": plan["typedOperands"]},
                "incoming_dd": expected_dd, "origin_pc": plan["assignedPC"]}}
        else:
            _need(plan["routeId"] == "B" and plan["formId"] == "j-address"
                  and len(operands) == 1 and type(operands[0]) is jtypes.ProgramTarget16, "CodecRouteMismatch")
            req = jtypes.DirectJEncodeRequest(operands[0], plan["assignedPC"], expected_dd)
            wanted_variant = {"requestClass": "DirectJEncodeRequest", "fields": {
                "target": plan["typedOperands"][0], "origin_pc": plan["assignedPC"], "incoming_dd": expected_dd}}
        _need(_exact(variant, wanted_variant), "TypedOperandMismatch")
        requests.append(req)
    return tuple(requests)


# Private call sites are patchable ONLY by trusted tests; no API callback inputs.
def _encode_a(request):
    return route_a.encode_instruction(request)


def _encode_b(request):
    return route_b.encode_direct_j(request)


def _decode_a(request):
    return decode_a.decode_instruction(request)


def _decode_b(request):
    return decode_b.decode_direct_j(request)


def _primary_expected(index):
    return expected_instruction(index)


def _assemble(parts):
    return b"".join(parts)


def _check_final_length(payload):
    _need(type(payload) is bytes and len(payload) == 51, "CompositeLengthMismatch")


def _check_final_metadata(boundaries, edges, paths, writes):
    _need(len(boundaries) == 20 and len(edges) == 23
          and paths == (11, 13, 14, 16) and writes == (3, 3, 3, 5), "InternalInvariant")


def _encoded_check(result, request, plan):
    if type(result) in (route_a.ExplicitError, jtypes.DirectJEncodeError):
        raise _Refusal("CodecError")
    if plan["routeId"] == "A":
        _need(type(result) is route_a.EncodedInstruction, "UnexpectedOutput")
        _need(_exact(result.reviewed_form_id, request.reviewed_form_id)
              and _exact(result.typed_operands, request.typed_operands), "TypedOperandMismatch")
        _need(result.classification == "SyntheticInstructionEncodingOnly", "UnexpectedOutput")
    else:
        _need(type(result) is jtypes.EncodedDirectJ, "UnexpectedOutput")
        _need(_exact(result.target, request.target), "BranchTargetMismatch")
        _need(result.form is jtypes.DirectJForm.J_ADDRESS
              and type(result.end_exclusive) is int and result.end_exclusive == plan["endExclusive"]
              and result.pc_effect == "DocumentedPCReplacement"
              and result.dd_effect == "DocumentedDDPreservedWhenExecuted"
              and result.noninterference_scope == "ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence"
              and result.classification == "SyntheticDirectJEncodingOnly", "UnexpectedOutput")
    _need(_exact(result.origin_pc, request.origin_pc), "InstructionBoundaryMismatch")
    _need(_exact(result.incoming_dd, request.incoming_dd), "DDContextMismatch")
    _need(type(result.encoded_bytes) is bytes, "UnexpectedOutput")
    _need(type(result.length) is int and result.length == plan["plannedLength"]
          and len(result.encoded_bytes) == plan["plannedLength"], "EncodedLengthMismatch")
    return result.encoded_bytes


def _decoded_check(result, request, plan, payload):
    if type(result) in (decode_a.ExplicitDecodeError, jtypes.DirectJDecodeError):
        raise _Refusal("IndependentDecodeError")
    if plan["routeId"] == "A":
        _need(type(result) is decode_a.DecodedInstruction, "UnexpectedOutput")
        _need(_exact(result.reviewed_form_id, request.reviewed_form_id), "DecodedFormMismatch")
        targets = tuple(o.value for o in request.typed_operands if type(o) is route_a.TargetPC16)
        _need(_exact(result.relative_target_pc, targets[0] if targets else None), "DecodedTargetMismatch")
        _need(_exact(result.typed_operands, request.typed_operands), "DecodedOperandMismatch")
        effect = (decode_a.DDEffect.SETS_DD0_WHEN_EXECUTED if plan["formId"].startswith("lb-a-")
                  else decode_a.DDEffect.PRESERVES_DD_WHEN_EXECUTED)
        _need(result.documented_dd_effect is effect, "DDContextMismatch")
        _need(result.classification == "SyntheticInstructionDecodingOnly"
              and result.input_classification is decode_a.DecodeInputClassification.EXACT_SUPPORTED_FORM,
              "UnexpectedOutput")
        target = result.relative_target_pc
    else:
        _need(type(result) is jtypes.DecodedDirectJ, "UnexpectedOutput")
        _need(result.form is jtypes.DirectJForm.J_ADDRESS, "DecodedFormMismatch")
        _need(_exact(result.target, request.target), "DecodedTargetMismatch")
        _need(type(result.end_exclusive) is int and result.end_exclusive == plan["endExclusive"]
              and result.pc_effect == "DocumentedPCReplacement"
              and result.dd_effect == "DocumentedDDPreservedWhenExecuted"
              and result.noninterference_scope == "ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence"
              and result.classification == "SyntheticDirectJDecodingOnly", "UnexpectedOutput")
        target = result.target.value
    _need(_exact(result.origin_pc, request.origin_pc), "InstructionBoundaryMismatch")
    _need(_exact(result.incoming_dd, request.incoming_dd), "DDContextMismatch")
    _need(type(result.length) is int and result.length == len(payload) == plan["plannedLength"],
          "InstructionBoundaryMismatch")
    return target


def _structure(boundaries, static):
    by_origin = {b.origin: b.node_id for b in boundaries}
    edges = []
    for i, b in enumerate(boundaries):
        if b.route == "B":
            edges.append((b.node_id, b.target, "ExternalTransfer"))
        else:
            if b.target is not None:
                _need(b.target in by_origin, "BranchTargetMismatch")
                edges.append((b.node_id, by_origin[b.target], "ConditionalTaken"))
            _need(i + 1 < 20 and boundaries[i + 1].origin == b.origin + b.length, "InstructionBoundaryMismatch")
            edges.append((b.node_id, boundaries[i + 1].node_id, "Fallthrough"))
    expected = {(e["from"], e["to"], e["kind"]) for e in static["edgeRows"]}
    _need(set(edges) == expected and len(edges) == 23, "CFGInvariantViolation")
    adjacency = {b.node_id: [] for b in boundaries}
    for start, end, _ in edges:
        adjacency[start].append(end)
    complete = []
    def visit(node, path):
        _need(node not in path and len(path) < 20, "CFGInvariantViolation")
        path = path + (node,)
        for end in adjacency[node]:
            if end not in adjacency:
                _need(sum(type(n) is str for n in path) == 1, "CFGInvariantViolation")
                complete.append(path)
            else:
                visit(end, path)
    visit(boundaries[0].node_id, ())
    actual_paths = set(complete)
    _need(actual_paths == {tuple(p["nodeIds"]) for p in static["paths"]}, "CFGInvariantViolation")
    paths = tuple(len(p["nodeIds"]) for p in static["paths"])
    writes = tuple(len(p["orderedWrites"]) for p in static["paths"])
    _need(paths == (11, 13, 14, 16) and writes == (3, 3, 3, 5), "OrderedEffectMismatch")
    return tuple(edges), paths, writes


def emit_synthetic_composite(reviewed_ir, reviewed_composition, reviewed_eligibility, request):
    """One closed transaction; error returns contain no partial result or bytes."""
    phase, node_id = EmissionPhase.Identity, None
    try:
        _identity(reviewed_eligibility)
        phase = EmissionPhase.Request
        _request(request)
        phase = EmissionPhase.Preflight
        old_request = {"syntheticBase": 4096, "gap": 0, "initialDD": [request["initialDD"]],
                       "nodeAssignments": None, "classification": "InventedOnlyCompositeEmissionEligibility"}
        try:
            static = prepare_composite_emission_plan(
                reviewed_ir, reviewed_composition, reviewed_eligibility, old_request)
        except EligibilityError as error:
            node_id = _preflight_node(error.location)
            if error.code == "NodeInventoryMismatch":
                _inventory(reviewed_eligibility)
            raise _Refusal(_preflight_error(error.code)) from None
        phase = EmissionPhase.Plan
        _inventory(reviewed_eligibility)
        plans = static["nodePlans"]
        _need(len(plans) == 20 and _exact(tuple(p["nodeId"] for p in plans), _IDS), "NodeOrderMismatch")
        for plan, fact in zip(plans, NODES):
            node_id = fact.node_id
            _need(_exact(plan["formId"], fact.form)
                  and plan["assignedPC"] == 4096 + fact.offset and plan["plannedLength"] == fact.length
                  and plan["endExclusive"] == 4096 + fact.offset + fact.length, "InstructionBoundaryMismatch")
            _need(plan["routeId"] == ("B" if fact.form == "j-address" else "A"), "CodecRouteMismatch")
        phase, node_id = EmissionPhase.TypedRequests, None
        requests = _construct_requests(plans, request["initialDD"])
        phase = EmissionPhase.Encoding
        parts = []
        for plan, codec_request in zip(plans, requests):
            node_id = plan["nodeId"]
            result = _encode_a(codec_request) if plan["routeId"] == "A" else _encode_b(codec_request)
            parts.append(_encoded_check(result, codec_request, plan))
        phase = EmissionPhase.Primary
        for i, (part, plan) in enumerate(zip(parts, plans)):
            node_id = plan["nodeId"]
            expected = _primary_expected(i)
            _need(type(expected) is bytes and part == expected, "PrimaryByteMismatch")
        phase, node_id = EmissionPhase.Assembly, None
        payload = _assemble(tuple(parts))
        _need(type(payload) is bytes, "UnexpectedOutput")
        _need(len(payload) == 51, "CompositeLengthMismatch")
        # Concatenation checked separately; even equal-length reorders are refused.
        cursor = 0
        for part in parts:
            _need(payload[cursor:cursor + len(part)] == part, "InstructionBoundaryMismatch")
            cursor += len(part)
        _need(cursor == 51, "CompositeLengthMismatch")
        phase = EmissionPhase.Decoding
        boundaries = []
        for i, (plan, codec_request) in enumerate(zip(plans, requests)):
            node_id = plan["nodeId"]
            offset, length = NODES[i].offset, plan["plannedLength"]
            part = payload[offset:offset + length]
            _need(len(part) == length and part == parts[i], "InstructionBoundaryMismatch")
            if plan["routeId"] == "A":
                decoded = _decode_a(decode_a.DecoderRequest(part, codec_request.incoming_dd, codec_request.origin_pc))
            else:
                decoded = _decode_b(jtypes.DirectJDecodeRequest(part, codec_request.origin_pc, codec_request.incoming_dd))
            target = _decoded_check(decoded, codec_request, plan, part)
            boundaries.append(InstructionBoundary(node_id, plan["originalLogicalSiteId"],
                              plan["routeId"], plan["formId"], offset, length,
                              decoded.origin_pc, decoded.incoming_dd, target))
        boundaries = tuple(boundaries)
        phase, node_id = EmissionPhase.Structure, None
        edges, paths, writes = _structure(boundaries, static)
        phase = EmissionPhase.FinalLength
        _check_final_length(payload)
        phase = EmissionPhase.FinalMetadata
        _check_final_metadata(boundaries, edges, paths, writes)
        phase = EmissionPhase.Publication
        return VerifiedSyntheticComposite(
            payload, 4096, 51, boundaries, request["initialDD"],
            tuple((b.node_id, b.target) for b in boundaries if b.route == "A" and b.target is not None),
            tuple((b.node_id, b.target) for b in boundaries if b.route == "B"),
            edges, paths, writes)
    except _Refusal as refusal:
        return ExplicitEmissionError(refusal.code, phase, node_id)
    except Exception:
        # No exception text, traceback or partial bytes escape this transaction.
        return ExplicitEmissionError(CompositeEmissionErrorCode.InternalInvariant, phase, node_id)
