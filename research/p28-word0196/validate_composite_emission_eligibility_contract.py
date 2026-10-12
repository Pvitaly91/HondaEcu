"""Closed M2bi metadata, current-source and bounded pure-policy checks.

This validator is trusted-source defense in depth, not an arbitrary Python
sandbox. Independent novel mathematical expectations live in the separately
sealed oracle/tests. No codec is imported or called and no instruction bytes,
composite buffer, CPU or native evidence are produced here.
"""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys

EXPECTED_CONTRACT_FILE_SHA256 = "bf274d3c2dc33b02b333bb9af335b22b30e0ddb81102715af3d6c11e621afece"
EXPECTED_CONTRACT_METADATA_SHA256 = "e6704d024df2e04e07d0d387946a04bb107fefb4b675895d3e1a12fda24861bf"
UPSTREAM_BINDINGS = json.loads("[{\"file\":\"research/p28-word0196/continuation_transfer_analysis.py\",\"bytes\":78628,\"sha256\":\"86eb302ae13138aef5a64b192e5d4b63982afa1e4bb3e9c4b3d71b9f927c355c\"},{\"file\":\"research/p28-word0196/continuation_transfer_oracle.py\",\"bytes\":12784,\"sha256\":\"5c250c75ee7d950e766cf747381efc125545b192a5c7d7b0e8b01a1c6b3909fb\"},{\"file\":\"research/p28-word0196/continuation_transfer_tests.py\",\"bytes\":19256,\"sha256\":\"e47b4e34bf2ee42e5e5f7c118becb9dffb71864e1a57030a9aedd2fbb83b833d\"},{\"file\":\"research/p28-word0196/direct_j_contract.json\",\"bytes\":23868,\"sha256\":\"1be70eb96f4c75c8f42729f2b41aacc2f43b4923c3db0aacccd1b5bc2a2a8c35\"},{\"file\":\"research/p28-word0196/direct_j_decoder.py\",\"bytes\":2006,\"sha256\":\"32738de208889d288856feda6f030c78b08d5cf3cf7ca0154120b32fc788c3a4\"},{\"file\":\"research/p28-word0196/direct_j_encoder.py\",\"bytes\":1926,\"sha256\":\"1149ba3fcc142fa1fb78677ddd14b8c4bbab1ee333ef926aaffe22839d7f6f60\"},{\"file\":\"research/p28-word0196/direct_j_primary_oracle.py\",\"bytes\":4051,\"sha256\":\"91793837663e8d0341ce0d4e224fc97e256c549409807ea9b43e8d9266f55f39\"},{\"file\":\"research/p28-word0196/direct_j_tests.py\",\"bytes\":18346,\"sha256\":\"c5a3cbb6f10b9cafaf342a0ed5b5bd86921f58fcfa9af1f469f1b741f6cc8d7c\"},{\"file\":\"research/p28-word0196/direct_j_types.py\",\"bytes\":3021,\"sha256\":\"f11877a07340b88a7c222acec250767524778955a96235a6dd147207fa99467b\"},{\"file\":\"research/p28-word0196/external_continuation_contract.json\",\"bytes\":58097,\"sha256\":\"bce975c6427e0ab9294af8227933f0b2553efa13a47b89383f53fc4ac6138660\"},{\"file\":\"research/p28-word0196/independent_decode_encode_contract.json\",\"bytes\":17800,\"sha256\":\"547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d\"},{\"file\":\"research/p28-word0196/independent_decoder_primary_oracle.py\",\"bytes\":12745,\"sha256\":\"9154ceac6709d8ad93fa71ab77f5b1e5c601dbaa812d60d4e3681b08f4b8e1df\"},{\"file\":\"research/p28-word0196/independent_decoder_tests.py\",\"bytes\":19933,\"sha256\":\"cdc5d43ee866dba4fb619fc6169e2ec5e869d4050f98137bb67e62ca0a2bdb64\"},{\"file\":\"research/p28-word0196/independent_decoder.py\",\"bytes\":11036,\"sha256\":\"e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404\"},{\"file\":\"research/p28-word0196/independent_encoder_contract.json\",\"bytes\":12182,\"sha256\":\"414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47\"},{\"file\":\"research/p28-word0196/independent_encoder_design.json\",\"bytes\":21765,\"sha256\":\"9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9\"},{\"file\":\"research/p28-word0196/independent_encoder_oracle.py\",\"bytes\":7092,\"sha256\":\"6575f802c0703da087f1f06fdff095dcf4c4b948b7fe59e8fb35972210cb6361\"},{\"file\":\"research/p28-word0196/independent_encoder_tests.py\",\"bytes\":18429,\"sha256\":\"76ca001260dbf07b0c5ad99f72e156732b940756af2c177e2b97311acba3b62c\"},{\"file\":\"research/p28-word0196/independent_encoder.py\",\"bytes\":9868,\"sha256\":\"603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879\"},{\"file\":\"research/p28-word0196/layout_feasibility_analysis.py\",\"bytes\":40569,\"sha256\":\"840320c5eed83d2a393dd3d1f4c8b90cb0aa7608c5c2ba721384265e79d151db\"},{\"file\":\"research/p28-word0196/layout_feasibility_contract.json\",\"bytes\":66622,\"sha256\":\"9d1baf1e4914fa1b611924ff48b75854e9fc7d2e06e6e05542c56c14e18abb2f\"},{\"file\":\"research/p28-word0196/layout_feasibility_oracle.py\",\"bytes\":10843,\"sha256\":\"be17e854a1b474b3800b09d74219ba097fc48bd2a2a53db93752169c3da06394\"},{\"file\":\"research/p28-word0196/layout_feasibility_tests.py\",\"bytes\":26061,\"sha256\":\"55377f7bd6c6c0ad1b5c29e7cc66eeb32aa63a3db8d1b849318c98326d74cd5e\"},{\"file\":\"research/p28-word0196/target_abi_contract.json\",\"bytes\":40753,\"sha256\":\"1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66\"},{\"file\":\"research/p28-word0196/transfer_form_evidence.json\",\"bytes\":37225,\"sha256\":\"f4279b5c86cc78be18f641e0638ea58892329f0b8903db28a8b6b77d69d34194\"},{\"file\":\"research/p28-word0196/typed_lowering_analysis.py\",\"bytes\":31589,\"sha256\":\"bd0ad1ee186cb76922926a957c21bacafc601e77200ff3bdcdc09fd866143bc5\"},{\"file\":\"research/p28-word0196/typed_lowering_contract.json\",\"bytes\":44984,\"sha256\":\"6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4\"},{\"file\":\"research/p28-word0196/typed_lowering_oracle.py\",\"bytes\":12601,\"sha256\":\"2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a\"},{\"file\":\"research/p28-word0196/typed_lowering_tests.py\",\"bytes\":29917,\"sha256\":\"1e46516c85b1d0b0593b67e59943b7b2d459725a073f29f23d385f59f73d7c6a\"},{\"file\":\"research/p28-word0196/validate_direct_j_contract.py\",\"bytes\":37218,\"sha256\":\"207b658479da79f911e317df8a71402370e7336f3ddcaa7f65a28de6efad8e85\"},{\"file\":\"research/p28-word0196/validate_external_continuation_contract.py\",\"bytes\":76985,\"sha256\":\"6dfd2a85c6fa5187e4bb2649d8b96db2b61ffe584f0b9b7b4124fc058550da7e\"},{\"file\":\"research/p28-word0196/validate_layout_feasibility_contract.py\",\"bytes\":48319,\"sha256\":\"e6656112d6272adeac3f382ee672a4ddd3b01fe645dcab356444b0cefd6d51ea\"},{\"file\":\"research/p28-word0196/word0196_equivalent.c\",\"bytes\":8507,\"sha256\":\"4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3\"},{\"file\":\"research/p28-word0196/word0196_equivalent.h\",\"bytes\":2390,\"sha256\":\"df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e\"},{\"file\":\"research/p28-word0196/word0196_ir.json\",\"bytes\":32188,\"sha256\":\"4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4\"},{\"file\":\"src/HondaEcu.Core/P28Word0196AlternateModel.cs\",\"bytes\":3464,\"sha256\":\"ac3162dfc6255e25ac24d7430531243f7856090ce55bab8b46e20d07f06fd74f\"},{\"file\":\"research/p28-word0196/static_composition_contract.json\",\"bytes\":106872,\"sha256\":\"3c3b0448e0bc2c232663fd9607b9d576a074238c7c823de50eafd6dcc2da2eb3\"},{\"file\":\"research/p28-word0196/static_composition_analysis.py\",\"bytes\":130811,\"sha256\":\"338f08abc06e27dffb2e64246cadcd8119727a05e448a5099cf9f539f3181547\"},{\"file\":\"research/p28-word0196/static_composition_oracle.py\",\"bytes\":22613,\"sha256\":\"bde29d3150c9f9d6918435f08fc1edf051869f523c7c0e4dc6f0b52f24244462\"},{\"file\":\"research/p28-word0196/static_composition_tests.py\",\"bytes\":28389,\"sha256\":\"3cbddb0b82b4a851317a8fdc9c51a8e96bffc526fcfde846181e863d5c9391ce\"},{\"file\":\"research/p28-word0196/validate_static_composition_contract.py\",\"bytes\":121642,\"sha256\":\"f04d149e15658aca6c9d2fcdd633916703fb412f9a1995dc2adf0f22366cd915\"}]")
# Exact identities are set only after independent review of these new sources.
# Until sealed, the CLI refuses; placeholders cannot grant a validation PASS.
NEW_SOURCE_BINDINGS = [{"file":"research/p28-word0196/composite_emission_eligibility_analysis.py","bytes":76150,"sha256":"67f0a444a8e6c79ad71b648610ff7e34fce985190aa56511676dfafee649d713"},{"file":"research/p28-word0196/composite_emission_eligibility_oracle.py","bytes":28776,"sha256":"6e6dfda1f1ebfc3b7f4ccf181dd7e17437454a7d481a354616ee40c5ec073857"},{"file":"research/p28-word0196/composite_emission_eligibility_tests.py","bytes":36105,"sha256":"a348a4560954dabc1fe1455b6d47180211f47c88f73538bcc7e2bd74865fd67e"}]
CONTRACT_KEYS = frozenset((
    "schemaVersion", "milestone", "exactBase", "scope", "upstreamBindings",
    "primaryEvidence", "routes", "operandTypes", "exactForms",
    "typedRequestMapping", "allowedSyntheticGeometry", "atomicity",
    "futurePrimaryVerification", "futureDecodeVerification",
    "futureOrderedEffectsVerification", "inheritedContextAndEffectObligations",
    "proofLevels", "runtimeExclusions", "nativeOwnerRestrictions",
    "historicalPreservation", "eligibilityVerdict", "decisionMatrix",
))
MAPPING_KEYS = frozenset((
    "nodeId", "originalLogicalSiteId", "nodeKind", "routeId", "formId",
    "plannedLength", "originOffset", "gapCoefficient", "operandDescriptors",
    "incomingDDDomain", "relocatedTargetNodeId", "successorIds", "primary",
))
NODE_ROWS = (
    (21871, 2, 0, "A"), (21873, 1, 2, "A"), (21874, 3, 3, "A"),
    (21877, 1, 6, "A"), (21878, 2, 7, "A"), (21880, 5, 9, "A"),
    (21885, 2, 14, "A"), (21887, 3, 16, "A"), (21890, 3, 19, "A"),
    (21893, 3, 22, "A"), (21896, 3, 25, "A"), (21899, 3, 28, "A"),
    (21902, 4, 31, "A"), (21906, 2, 35, "A"), (21908, 2, 37, "A"),
    ("DirectJ_NotBelow", 3, 39, "B"), (21951, 2, 42, "A"),
    (21953, 2, 44, "A"), (21955, 2, 46, "A"),
    ("DirectJ_Below", 3, 48, "B"),
)
RUNTIME_STATUS = {
    "ActualCompositeEmission": "NotRun", "CompositeMachineCode": "NotGenerated",
    "ActualTargetExecution": "NotObserved", "NativeExitIsolation": "NotEstablished",
    "ActualDownstreamRejoin": "NotEstablished", "PhysicalROMPlacement": "NotEstablished",
    "TargetProgramEquivalence": "NotEstablished", "FirmwareIntegration": "NotEstablished",
    "FirmwareReady": False,
}


class ValidationError(ValueError):
    __slots__ = ("code", "location")

    def __init__(self, code, location):
        self.code, self.location = code, location
        self.args = (code, location)


def _need(condition, code, location):
    if not condition:
        raise ValidationError(code, location)


def _exact_json(value, location, depth=0):
    _need(depth <= 64, "InputShape", location)
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _exact_json(item, location + "/" + str(index), depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            _need(type(key) is str, "InputShape", location)
            _exact_json(item, location + "/" + key, depth + 1)
        return
    _need(False, "InputShape", location)


def _same(actual, expected, code, location):
    _need(type(actual) is type(expected), code, location)
    if type(expected) is dict:
        _need(set(actual) == set(expected), code, location)
        for key in expected:
            _same(actual[key], expected[key], code, location + "/" + key)
    elif type(expected) is list:
        _need(len(actual) == len(expected), code, location)
        for index, item in enumerate(expected):
            _same(actual[index], item, code, location + "/" + str(index))
    else:
        _need(actual == expected, code, location)


def validate_contract(contract):
    """Closed metadata and pinned documentary safeguards, not byte/ISA proof."""
    _exact_json(contract, "eligibility_contract")
    _need(type(contract) is dict, "InputShape", "eligibility_contract")
    _need("upstreamBindings" in contract, "SourceBindingMissing", "upstreamBindings")
    _same(contract["upstreamBindings"], UPSTREAM_BINDINGS,
          "SourceIdentityMismatch", "upstreamBindings")
    _need(set(contract) == CONTRACT_KEYS, "MetadataMismatch", "eligibility_contract/keys")
    rows = contract["typedRequestMapping"]
    _need(type(rows) is list and len(rows) == 20, "NodeInventoryMismatch", "typedRequestMapping")
    for index, ((node, length, offset, route), row) in enumerate(zip(NODE_ROWS, rows)):
        location = "typedRequestMapping/" + str(index)
        _need(type(row) is dict and set(row) == MAPPING_KEYS, "NodeInventoryMismatch", location)
        _need(type(row["nodeId"]) is type(node) and row["nodeId"] == node,
              "NodeInventoryMismatch", location + "/nodeId")
        _need(row["routeId"] == route, "CodecRouteMismatch", location + "/routeId")
        _need(type(row["plannedLength"]) is int and row["plannedLength"] == length,
              "InstructionLengthMismatch", location + "/plannedLength")
        _need(type(row["originOffset"]) is int and row["originOffset"] == offset,
              "OriginProjectionMismatch", location + "/originOffset")
        _same(row["incomingDDDomain"], [0, 1] if index == 0 else [0],
              "DDProjectionMismatch", location + "/incomingDDDomain")
    geometry = contract["allowedSyntheticGeometry"]
    _need(type(geometry) is dict, "MetadataMismatch", "allowedSyntheticGeometry")
    _same(geometry.get("allowlist"), [{"syntheticBase": 4096, "gap": 0}],
          "LayoutNotAllowlisted", "allowedSyntheticGeometry/allowlist")
    _need(geometry.get("physicalPlacementAuthorized") is False
          and geometry.get("otherMathematicalSuccessDoesNotAuthorizeEmission") is True,
          "RuntimePolicyMismatch", "allowedSyntheticGeometry")
    atomicity = contract["atomicity"]
    _need(type(atomicity) is dict and atomicity.get("onAnyError") == "NoPartialCompositeBufferPublished"
          and atomicity.get("allPreflightBeforeAnyCodecCall") is True
          and atomicity.get("allPerInstructionChecksBeforeCompositePublication") is True
          and atomicity.get("sumExactLengthRequired") == 51
          and atomicity.get("implementationStatus") == "NotImplemented"
          and type(atomicity.get("actualCalls")) is int and atomicity["actualCalls"] == 0,
          "AtomicityPolicyMismatch", "atomicity")
    for group, code in (("futurePrimaryVerification", "FuturePrimaryVerificationMismatch"),
                        ("futureDecodeVerification", "FutureDecodeVerificationMismatch"),
                        ("futureOrderedEffectsVerification", "EffectVerificationPolicyMismatch")):
        policy = contract[group]
        _need(type(policy) is dict and policy.get("implementationStatus") == "NotImplemented"
              and type(policy.get("actualCalls")) is int and policy["actualCalls"] == 0,
              code, group)
    runtime = contract["runtimeExclusions"]
    matrix = contract["decisionMatrix"]
    _same(matrix, {
        "classification": "RequiredFormalEligibilityGates_NotObservedEvidence",
        "requiredProperties": ["source", "inventory", "typedProjection", "routes", "dense51",
            "spans20", "relative3", "absolute2", "DD", "CFG", "flags", "orderedEffects",
            "noAnchorCollision", "futureIndependentVerification", "atomicity", "noUnexpectedDependencies"],
        "success": "SyntheticCompositeEmissionEligibleForSeparateMilestone",
        "fail": "SyntheticCompositeEmissionEligibilityBlocked",
        "anyMissingIsBlocked": True, "runtimePermissions": False, "emissionInM2bi": False,
    }, "RuntimePolicyMismatch", "decisionMatrix")
    _need(type(runtime) is dict, "RuntimePolicyMismatch", "runtimeExclusions")
    for key, value in RUNTIME_STATUS.items():
        _same(runtime.get(key), value, "RuntimePolicyMismatch", "runtimeExclusions/" + key)
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    actual = hashlib.sha256(payload.encode("ascii")).hexdigest()
    _need(actual == EXPECTED_CONTRACT_METADATA_SHA256, "MetadataMismatch", "closedMetadata")
    return {
        "passed": True, "classification": "ClosedEligibilityMetadataAndDocumentaryPoliciesOnly",
        "typedMappings": 20, "routeANodes": 18, "routeBNodes": 2, "genericPrimaryRules": 16,
        "compositeEmissionVerified": False, "actualCompositeEmission": "NotRun",
    }


FORBIDDEN_NAMES = frozenset((
    "bytes", "bytearray", "memoryview", "open", "input", "print", "help",
    "breakpoint", "eval", "exec", "compile", "__import__", "getattr", "setattr",
    "delattr", "hasattr", "globals", "locals", "vars", "dir", "object",
    "type.__new__", "Cpu", "CPU", "Opcode", "FULL_OPCODES", "OPCODES",
    "_FORM_SHAPES", "encode_instruction", "decode_instruction",
    "encode_direct_j", "decode_direct_j", "EncoderRequest", "DecoderRequest",
    "DirectJEncodeRequest", "DirectJDecodeRequest", "ProgramTarget16",
    "TargetPC16", "FormId", "ctypes", "struct", "socket", "requests", "subprocess",
    "importlib", "pathlib", "sys", "os", "pickle", "marshal", "inspect",
))
FORBIDDEN_ATTRIBUTES = FORBIDDEN_NAMES.union((
    "encoded_bytes", "to_bytes", "from_bytes", "encode", "decode", "pack",
    "unpack", "read_bytes", "write_bytes", "read_text", "write_text", "read",
    "write", "load", "dump", "system", "popen", "run", "call", "connect",
    "send", "recv", "__dict__", "__class__", "__globals__", "__code__",
    "__getattribute__", "__subclasses__", "__mro__", "__bases__", "__builtins__",
))
ALLOWED_BUILTINS = frozenset((
    "type", "len", "set", "frozenset", "list", "tuple", "dict", "str", "int",
    "bool", "range", "enumerate", "zip", "sum", "all", "any", "sorted",
    "min", "max", "next", "iter", "reversed", "isinstance", "ValueError",
))
ALLOWED_METHODS = frozenset((
    "get", "keys", "values", "items", "copy", "append", "extend", "update",
    "add", "union", "difference", "difference_update", "intersection",
    "intersection_update", "setdefault", "pop", "issubset", "index", "sort",
))
INPUT_NAMES = frozenset(("original_ir", "composition_contract", "eligibility_contract", "request"))
MUTATING_METHODS = frozenset((
    "append", "extend", "update", "add", "difference_update", "intersection_update",
    "setdefault", "pop", "sort", "clear", "remove", "discard", "insert",
))


def _root_name(node):
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _conversion_handler(node):
    """Only the narrow inherited CompositionError -> atomic EligibilityError."""
    if len(node.handlers) != 1 or node.orelse or node.finalbody:
        return False
    handler = node.handlers[0]
    if not isinstance(handler.type, ast.Name) or handler.type.id != "CompositionError" or not handler.name:
        return False
    if len(handler.body) != 1 or not isinstance(handler.body[0], ast.Raise):
        return False
    call = handler.body[0].exc
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "EligibilityError":
        return False
    if call.keywords or len(call.args) != 2:
        return False
    return all(isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name)
               and arg.value.id == handler.name and arg.attr == attribute
               for arg, attribute in zip(call.args, ("code", "path")))


def validate_source(source, source_name="analysis"):
    """Parse only; never execute supplied source or malicious fixture bodies."""
    _need(type(source) is str and source_name in ("analysis", "oracle"),
          "SourcePolicy", "source")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise ValidationError("SourcePolicy", "syntax") from error
    allowed_import = {
        "analysis": {"static_composition_analysis": ("CompositionError", "evaluate_composition")},
        "oracle": {"static_composition_oracle": ("expected_result",)},
    }[source_name]
    allowed_slots_targets = set()
    for declaration in tree.body:
        if isinstance(declaration, ast.ClassDef) and declaration.name == "EligibilityError":
            for statement in declaration.body:
                if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                        and isinstance(statement.targets[0], ast.Name)
                        and statement.targets[0].id == "__slots__"
                        and isinstance(statement.value, ast.Tuple)
                        and [item.value for item in statement.value.elts if isinstance(item, ast.Constant)]
                            == ["code", "location"]
                        and len(statement.value.elts) == 2):
                    allowed_slots_targets.add(id(statement.targets[0]))
    declared = {node.name for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    imports = {"json"}
    imports.update(name for names in allowed_import.values() for name in names)
    if source_name == "oracle":
        imports.add("inherited_expected_result")
    allowed_calls = ALLOWED_BUILTINS.union(declared).union(imports)
    for node in ast.walk(tree):
        location = "source/" + str(getattr(node, "lineno", 0))
        if isinstance(node, ast.Import):
            _need(all(item.name == "json" and item.asname is None for item in node.names),
                  "SourcePolicy", location + "/import")
        elif isinstance(node, ast.ImportFrom):
            exact_oracle_alias = (source_name == "oracle"
                and node.module == "static_composition_oracle"
                and len(node.names) == 1 and node.names[0].name == "expected_result"
                and node.names[0].asname == "inherited_expected_result")
            _need(node.level == 0 and node.module in allowed_import
                  and tuple(item.name for item in node.names) == allowed_import[node.module]
                  and (all(item.asname is None for item in node.names) or exact_oracle_alias),
                  "SourcePolicy", location + "/from")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith,
                               ast.With, ast.Lambda, ast.Global, ast.Nonlocal, ast.Delete,
                               ast.Yield, ast.YieldFrom)):
            _need(False, "SourcePolicy", location + "/syntax")
        elif isinstance(node, ast.Try):
            _need(source_name == "analysis" and _conversion_handler(node),
                  "SourcePolicy", location + "/handler")
        elif isinstance(node, ast.Constant):
            _need(type(node.value) is not bytes, "SourcePolicy", location + "/bytes")
        elif isinstance(node, ast.Name):
            _need(node.id not in FORBIDDEN_NAMES
                  and (not node.id.startswith("__") or id(node) in allowed_slots_targets),
                  "SourcePolicy", location + "/name")
        elif isinstance(node, ast.Attribute):
            _need(node.attr not in FORBIDDEN_ATTRIBUTES and not node.attr.startswith("__"),
                  "SourcePolicy", location + "/attribute")
            if isinstance(node.ctx, ast.Store):
                _need(isinstance(node.value, ast.Name) and node.value.id == "self"
                      and node.attr in ("code", "location", "args"),
                      "SourcePolicy", location + "/attributeStore")
        elif isinstance(node, ast.Subscript):
            oracle_span_suffix = (source_name == "oracle"
                and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name)
                and node.value.id == "spans" and isinstance(node.slice, ast.Slice)
                and node.slice.upper is None and node.slice.step is None
                and isinstance(node.slice.lower, ast.BinOp) and isinstance(node.slice.lower.op, ast.Add)
                and isinstance(node.slice.lower.left, ast.Name) and node.slice.lower.left.id == "index"
                and isinstance(node.slice.lower.right, ast.Constant)
                and type(node.slice.lower.right.value) is int and node.slice.lower.right.value == 1)
            _need(not isinstance(node.slice, ast.Slice) or oracle_span_suffix,
                  "SourcePolicy", location + "/slice")
            if isinstance(node.ctx, ast.Store):
                _need(_root_name(node) not in INPUT_NAMES, "SourcePolicy", location + "/inputStore")
        elif isinstance(node, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift,
                               ast.Invert, ast.FloorDiv, ast.MatMult)):
            _need(False, "SourcePolicy", location + "/byteArithmetic")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            _need(isinstance(node.right, ast.Constant) and type(node.right.value) is int
                  and node.right.value == 2, "SourcePolicy", location + "/mod")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                _need(node.func.id in allowed_calls, "SourcePolicy", location + "/callee")
            elif isinstance(node.func, ast.Attribute):
                owner = _root_name(node.func)
                method = node.func.attr
                json_call = isinstance(node.func.value, ast.Name) and node.func.value.id == "json" and method in ("loads", "dumps")
                exception_init = method == "__init__" and isinstance(node.func.value, ast.Name) and node.func.value.id == "ValueError"
                _need(json_call or exception_init or method in ALLOWED_METHODS,
                      "SourcePolicy", location + "/method")
                _need(not (owner in INPUT_NAMES and method in MUTATING_METHODS),
                      "SourcePolicy", location + "/inputMutation")
            else:
                _need(False, "SourcePolicy", location + "/dynamicCallee")
    return {
        "passed": True, "classification": "ParsedTrustedSourceDefenseInDepth_NotPythonSandbox",
        "source": source_name, "fixtureExecuted": False, "codecCalls": 0,
    }


def _binding(root, file):
    raw = (root / file).read_bytes()
    return {"file": file, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load_inputs():
    root = Path(__file__).resolve().parents[2]
    for expected in UPSTREAM_BINDINGS:
        _same(_binding(root, expected["file"]), expected, "SourceIdentityMismatch", expected["file"])
    contract_file = "research/p28-word0196/composite_emission_eligibility_contract.json"
    _need(_binding(root, contract_file)["sha256"] == EXPECTED_CONTRACT_FILE_SHA256,
          "SourceIdentityMismatch", contract_file)
    _need(type(NEW_SOURCE_BINDINGS) is list and len(NEW_SOURCE_BINDINGS) == 3,
          "SourceClosureNotSealed", "newSources")
    for expected in NEW_SOURCE_BINDINGS:
        _same(_binding(root, expected["file"]), expected, "SourceIdentityMismatch", expected["file"])
    contract = json.loads((root / contract_file).read_text(encoding="utf-8"))
    ir = json.loads((root / "research/p28-word0196/word0196_ir.json").read_text(encoding="utf-8"))
    composition = json.loads((root / "research/p28-word0196/static_composition_contract.json").read_text(encoding="utf-8"))
    source_checks = [
        validate_source((root / "research/p28-word0196/composite_emission_eligibility_analysis.py").read_text(encoding="utf-8"), "analysis"),
        validate_source((root / "research/p28-word0196/composite_emission_eligibility_oracle.py").read_text(encoding="utf-8"), "oracle"),
    ]
    return contract, ir, composition, source_checks


def validate_semantic_controls(contract, ir, composition):
    """Bounded actual plan regressions; separate from primary byte/ISA proof."""
    analyzer = importlib.import_module("composite_emission_eligibility_analysis")
    assignments = [{"nodeId": node, "assignedPC": 4096 + offset}
                   for node, _, offset, _ in NODE_ROWS]
    counts = {"positiveRequests": 0, "negativeRequests": 0, "planCalls": 0}
    for initial in ([0], [1], [0, 1]):
        for supplied in (None, assignments, list(reversed(assignments))):
            request = {"syntheticBase": 4096, "gap": 0, "initialDD": initial,
                       "nodeAssignments": supplied,
                       "classification": "InventedOnlyCompositeEmissionEligibility"}
            before = json.dumps((contract, ir, composition, request), sort_keys=True)
            result = analyzer.prepare_composite_emission_plan(ir, composition, contract, request)
            counts["planCalls"] += 1
            _need(before == json.dumps((contract, ir, composition, request), sort_keys=True),
                  "InputMutation", "semanticControls")
            _need(set(result) == {"classification", "verdict", "nodePlans", "componentSpans",
                  "gap", "edgeRows", "branchRows", "paths", "ddFlow", "flagFlow",
                  "contextObligations", "anchorObservations", "counts",
                  "futureVerification", "permissions", "runtimeStatus"},
                  "ResultShape", "semanticControls")
            _need(result["classification"] == "ReviewedStatic20NodeTypedEmissionPlan"
                  and result["verdict"] == "SyntheticCompositeEmissionEligibleForSeparateMilestone",
                  "ResultMeaning", "semanticControls")
            _same(result["runtimeStatus"], RUNTIME_STATUS, "RuntimePolicyMismatch", "runtimeStatus")
            _need(len(result["nodePlans"]) == 20, "NodeInventoryMismatch", "nodePlans")
            for index, ((node, length, offset, route), row) in enumerate(zip(NODE_ROWS, result["nodePlans"])):
                _need(row["nodeId"] == node and row["routeId"] == route
                      and row["assignedPC"] == 4096 + offset and row["endExclusive"] == 4096 + offset + length
                      and row["plannedLength"] == length, "ResultGeometry", "nodePlans/" + str(index))
                domain = initial if index == 0 else [0]
                _same(row["incomingDDDomain"], domain, "DDProjectionMismatch", "nodePlans/" + str(index))
                _need(len(row["requestVariants"]) == len(domain), "DDProjectionMismatch", "requestVariants")
                for scalar, variant in zip(domain, row["requestVariants"]):
                    fields = variant["fields"]
                    _need(fields["incoming_dd"] == scalar and type(fields["incoming_dd"]) is int
                          and fields["origin_pc"] == 4096 + offset, "ResultProjection", "requestVariants")
                    if route == "A":
                        _need(variant["requestClass"] == "EncoderRequest"
                              and set(fields) == {"reviewed_form_id", "typed_operands", "incoming_dd", "origin_pc"}
                              and fields["typed_operands"]["container"] == "tuple",
                              "CodecRouteMismatch", "requestVariants/A")
                    else:
                        _need(variant["requestClass"] == "DirectJEncodeRequest"
                              and set(fields) == {"target", "origin_pc", "incoming_dd"}
                              and fields["target"]["kind"] == "ProgramTarget16",
                              "CodecRouteMismatch", "requestVariants/B")
            _same([row["signedDelta"] for row in result["branchRows"]], [26, 10, 7],
                  "BranchTargetMismatch", "branchRows")
            _same([row["composedNodeCount"] for row in result["paths"]], [11, 13, 14, 16],
                  "CFGRelationMismatch", "paths")
            _same([len(row["orderedWrites"]) for row in result["paths"]], [3, 3, 3, 5],
                  "MemoryEffectMismatch", "paths")
            _same(result["contextObligations"], composition["context"],
                  "ContextObligationMismatch", "context")
            _need(result["counts"]["totalRequestVariants"] == (21 if initial == [0, 1] else 20)
                  and result["counts"]["codecCalls"] == 0,
                  "ResultCountMismatch", "counts")
            counts["positiveRequests"] += 1
    for base, gap, code in ((8192, 0, "LayoutNotAllowlisted"), (65485, 0, "LayoutNotAllowlisted"),
                            (65384, 101, "LayoutNotAllowlisted"), (65486, 0, "SpanOutsideProfile"),
                            (65385, 101, "SpanOutsideProfile"), (4096, 102, "Rel8OutOfRange")):
        request = {"syntheticBase": base, "gap": gap, "initialDD": [0, 1],
                   "nodeAssignments": None, "classification": "InventedOnlyCompositeEmissionEligibility"}
        try:
            analyzer.prepare_composite_emission_plan(ir, composition, contract, request)
        except analyzer.EligibilityError as error:
            counts["planCalls"] += 1
            _need(error.code == code and type(error.location) is str and bool(error.location),
                  "UnexpectedRefusal", "semanticControls/" + code)
            _need(not hasattr(error, "partialPlan"), "PartialError", "semanticControls")
        else:
            _need(False, "MissingRefusal", "semanticControls/" + code)
        counts["negativeRequests"] += 1
    return {**counts, "passed": True, "meaning": "BoundedPlanControls_NotIndependentISAOrByteProof",
            "codecCalls": 0, "compositeEmissionCalls": 0, "CPUExecutions": 0}


def main():
    _need(len(sys.argv) == 1, "InputShape", "CLI/arguments")
    contract, ir, composition, source_checks = load_inputs()
    metadata = validate_contract(contract)
    controls = validate_semantic_controls(contract, ir, composition)
    print(json.dumps({
        "milestone": "M2bi", "passed": True,
        "classification": "ClosedMetadataSourceAndBoundedStaticPlanControls_NotCompositeBytesOrCPUProof",
        "upstreamBindingCount": len(UPSTREAM_BINDINGS), "newSourceBindingCount": len(NEW_SOURCE_BINDINGS),
        "metadata": metadata, "sourcePolicy": source_checks, "staticControls": controls,
        "actualCompositeEmission": "NotRun", "compositeBytes": 0, "encoderCalls": 0,
        "decoderCalls": 0, "CPUExecutions": 0, "actualROMExecutions": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
