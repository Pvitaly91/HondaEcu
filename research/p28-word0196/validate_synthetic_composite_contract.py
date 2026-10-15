"""Trusted fixed-path adapter and independently pinned M2bj safety validator.

No arbitrary paths, binary output, ROM inputs or metadata-established success.
The CLI runs the actual two scalar-DD emissions and closed mutation/injection
suite. Only source hashes and safe evidence JSON are printed.
"""
import ast
import json
import hashlib
from pathlib import Path

EXACT_BASE = "7585bfc164929c19fa044664c4d8173244a426fa"
ORACLE_SHA256 = "b3aecd90e3ef159b9aeec04ec6a46324a245bdcfb23a5ef80ad8d3d11b921c47"
PRIMARY_REFERENCE_SHA256 = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
REPO = Path(__file__).resolve().parents[2]
DIR = REPO / "research" / "p28-word0196"
UPSTREAM = [{"file":"research/p28-word0196/continuation_transfer_analysis.py","bytes":78628,"sha256":"86eb302ae13138aef5a64b192e5d4b63982afa1e4bb3e9c4b3d71b9f927c355c"},{"file":"research/p28-word0196/continuation_transfer_oracle.py","bytes":12784,"sha256":"5c250c75ee7d950e766cf747381efc125545b192a5c7d7b0e8b01a1c6b3909fb"},{"file":"research/p28-word0196/continuation_transfer_tests.py","bytes":19256,"sha256":"e47b4e34bf2ee42e5e5f7c118becb9dffb71864e1a57030a9aedd2fbb83b833d"},{"file":"research/p28-word0196/direct_j_contract.json","bytes":23868,"sha256":"1be70eb96f4c75c8f42729f2b41aacc2f43b4923c3db0aacccd1b5bc2a2a8c35"},{"file":"research/p28-word0196/direct_j_decoder.py","bytes":2006,"sha256":"32738de208889d288856feda6f030c78b08d5cf3cf7ca0154120b32fc788c3a4"},{"file":"research/p28-word0196/direct_j_encoder.py","bytes":1926,"sha256":"1149ba3fcc142fa1fb78677ddd14b8c4bbab1ee333ef926aaffe22839d7f6f60"},{"file":"research/p28-word0196/direct_j_primary_oracle.py","bytes":4051,"sha256":"91793837663e8d0341ce0d4e224fc97e256c549409807ea9b43e8d9266f55f39"},{"file":"research/p28-word0196/direct_j_tests.py","bytes":18346,"sha256":"c5a3cbb6f10b9cafaf342a0ed5b5bd86921f58fcfa9af1f469f1b741f6cc8d7c"},{"file":"research/p28-word0196/direct_j_types.py","bytes":3021,"sha256":"f11877a07340b88a7c222acec250767524778955a96235a6dd147207fa99467b"},{"file":"research/p28-word0196/external_continuation_contract.json","bytes":58097,"sha256":"bce975c6427e0ab9294af8227933f0b2553efa13a47b89383f53fc4ac6138660"},{"file":"research/p28-word0196/independent_decode_encode_contract.json","bytes":17800,"sha256":"547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d"},{"file":"research/p28-word0196/independent_decoder_primary_oracle.py","bytes":12745,"sha256":"9154ceac6709d8ad93fa71ab77f5b1e5c601dbaa812d60d4e3681b08f4b8e1df"},{"file":"research/p28-word0196/independent_decoder_tests.py","bytes":19933,"sha256":"cdc5d43ee866dba4fb619fc6169e2ec5e869d4050f98137bb67e62ca0a2bdb64"},{"file":"research/p28-word0196/independent_decoder.py","bytes":11036,"sha256":"e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404"},{"file":"research/p28-word0196/independent_encoder_contract.json","bytes":12182,"sha256":"414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47"},{"file":"research/p28-word0196/independent_encoder_design.json","bytes":21765,"sha256":"9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9"},{"file":"research/p28-word0196/independent_encoder_oracle.py","bytes":7092,"sha256":"6575f802c0703da087f1f06fdff095dcf4c4b948b7fe59e8fb35972210cb6361"},{"file":"research/p28-word0196/independent_encoder_tests.py","bytes":18429,"sha256":"76ca001260dbf07b0c5ad99f72e156732b940756af2c177e2b97311acba3b62c"},{"file":"research/p28-word0196/independent_encoder.py","bytes":9868,"sha256":"603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879"},{"file":"research/p28-word0196/layout_feasibility_analysis.py","bytes":40569,"sha256":"840320c5eed83d2a393dd3d1f4c8b90cb0aa7608c5c2ba721384265e79d151db"},{"file":"research/p28-word0196/layout_feasibility_contract.json","bytes":66622,"sha256":"9d1baf1e4914fa1b611924ff48b75854e9fc7d2e06e6e05542c56c14e18abb2f"},{"file":"research/p28-word0196/layout_feasibility_oracle.py","bytes":10843,"sha256":"be17e854a1b474b3800b09d74219ba097fc48bd2a2a53db93752169c3da06394"},{"file":"research/p28-word0196/layout_feasibility_tests.py","bytes":26061,"sha256":"55377f7bd6c6c0ad1b5c29e7cc66eeb32aa63a3db8d1b849318c98326d74cd5e"},{"file":"research/p28-word0196/target_abi_contract.json","bytes":40753,"sha256":"1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"},{"file":"research/p28-word0196/transfer_form_evidence.json","bytes":37225,"sha256":"f4279b5c86cc78be18f641e0638ea58892329f0b8903db28a8b6b77d69d34194"},{"file":"research/p28-word0196/typed_lowering_analysis.py","bytes":31589,"sha256":"bd0ad1ee186cb76922926a957c21bacafc601e77200ff3bdcdc09fd866143bc5"},{"file":"research/p28-word0196/typed_lowering_contract.json","bytes":44984,"sha256":"6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4"},{"file":"research/p28-word0196/typed_lowering_oracle.py","bytes":12601,"sha256":"2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a"},{"file":"research/p28-word0196/typed_lowering_tests.py","bytes":29917,"sha256":"1e46516c85b1d0b0593b67e59943b7b2d459725a073f29f23d385f59f73d7c6a"},{"file":"research/p28-word0196/validate_direct_j_contract.py","bytes":37218,"sha256":"207b658479da79f911e317df8a71402370e7336f3ddcaa7f65a28de6efad8e85"},{"file":"research/p28-word0196/validate_external_continuation_contract.py","bytes":76985,"sha256":"6dfd2a85c6fa5187e4bb2649d8b96db2b61ffe584f0b9b7b4124fc058550da7e"},{"file":"research/p28-word0196/validate_layout_feasibility_contract.py","bytes":48319,"sha256":"e6656112d6272adeac3f382ee672a4ddd3b01fe645dcab356444b0cefd6d51ea"},{"file":"research/p28-word0196/word0196_equivalent.c","bytes":8507,"sha256":"4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3"},{"file":"research/p28-word0196/word0196_equivalent.h","bytes":2390,"sha256":"df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e"},{"file":"research/p28-word0196/word0196_ir.json","bytes":32188,"sha256":"4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"},{"file":"src/HondaEcu.Core/P28Word0196AlternateModel.cs","bytes":3464,"sha256":"ac3162dfc6255e25ac24d7430531243f7856090ce55bab8b46e20d07f06fd74f"},{"file":"research/p28-word0196/static_composition_contract.json","bytes":106872,"sha256":"3c3b0448e0bc2c232663fd9607b9d576a074238c7c823de50eafd6dcc2da2eb3"},{"file":"research/p28-word0196/static_composition_analysis.py","bytes":130811,"sha256":"338f08abc06e27dffb2e64246cadcd8119727a05e448a5099cf9f539f3181547"},{"file":"research/p28-word0196/static_composition_oracle.py","bytes":22613,"sha256":"bde29d3150c9f9d6918435f08fc1edf051869f523c7c0e4dc6f0b52f24244462"},{"file":"research/p28-word0196/static_composition_tests.py","bytes":28389,"sha256":"3cbddb0b82b4a851317a8fdc9c51a8e96bffc526fcfde846181e863d5c9391ce"},{"file":"research/p28-word0196/validate_static_composition_contract.py","bytes":121642,"sha256":"f04d149e15658aca6c9d2fcdd633916703fb412f9a1995dc2adf0f22366cd915"},{"file":"research/p28-word0196/composite_emission_eligibility_contract.json","bytes":83058,"sha256":"bf274d3c2dc33b02b333bb9af335b22b30e0ddb81102715af3d6c11e621afece"},{"file":"research/p28-word0196/composite_emission_eligibility_analysis.py","bytes":76150,"sha256":"67f0a444a8e6c79ad71b648610ff7e34fce985190aa56511676dfafee649d713"},{"file":"research/p28-word0196/composite_emission_eligibility_oracle.py","bytes":28776,"sha256":"6e6dfda1f1ebfc3b7f4ccf181dd7e17437454a7d481a354616ee40c5ec073857"},{"file":"research/p28-word0196/composite_emission_eligibility_tests.py","bytes":36105,"sha256":"a348a4560954dabc1fe1455b6d47180211f47c88f73538bcc7e2bd74865fd67e"},{"file":"research/p28-word0196/validate_composite_emission_eligibility_contract.py","bytes":33484,"sha256":"70531ba86e395aefd9aee71b5a2e2e2f2f11cc225db84095d477816773da2e17"}]
PURE_IMPORTS = {
    "synthetic_composite_emitter.py": {"dataclasses", "enum", "independent_encoder",
        "independent_decoder", "direct_j_encoder", "direct_j_decoder", "direct_j_types",
        "composite_emission_eligibility_analysis", "synthetic_composite_primary_oracle"},
    "synthetic_composite_primary_oracle.py": {"dataclasses", "hashlib",
        "independent_encoder_oracle", "independent_decoder_primary_oracle", "direct_j_primary_oracle"},
}
BANNED_CALLS = {"open", "eval", "exec", "compile", "__import__", "getattr_dynamic",
                "print", "write", "write_bytes", "write_text", "read_bytes", "read_text",
                "system", "popen", "run", "encode_instruction_dynamic"}
EXCLUSIONS = {
    "ActualTargetExecution": "NotObserved", "NativeExitIsolation": "NotEstablished",
    "ActualDownstreamRejoin": "NotEstablished", "PhysicalROMPlacement": "NotEstablished",
    "TargetProgramEquivalence": "NotEstablished", "FirmwareIntegration": "NotEstablished",
    "FirmwareReady": False, "actualROMExecutions": 0, "CPUExecutions": 0,
    "targetAssemblyFiles": 0, "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0,
    "GUIHardwareFullBoot": "NotRun", "inquiries": "NotSent",
}
SAFETY = {
    "scope": "word0196SoftwareAlternate18PlusTwoDirectJ",
    "requestKeys": ["exactBase", "scope", "syntheticBase", "gap", "initialDD"],
    "syntheticBase": 4096, "gap": 0, "scalarDD": [0, 1],
    "length": 51, "nodes": 20, "routeA": 18, "routeB": 2,
    "internalTargets": [[21885, 4138], [21893, 4131], [21896, 4131]],
    "externalTargets": [["DirectJ_NotBelow", 21910], ["DirectJ_Below", 21957]],
    "edges": 23, "edgeCounts": [18, 3, 2], "paths": [11, 13, 14, 16],
    "originalPaths": [10, 12, 13, 15], "orderedWrites": [3, 3, 3, 5],
    "classification": "SyntheticCompositeMachineCodeOnly",
    "output": "ImmutableInMemoryOnly_NoRaw51ByteLoggingOrPersistence",
    "atomicity": "AllChecksBeforeSinglePublication_NoPartialErrorPayload",
    "decoder": "Exact20BoundarySlices_CoverAll51Octets_PrimaryProofSeparate",
    "effectProof": "StaticObligationsOnly_NotExecutedRAMJournal",
}
STAGES = ["Identity", "Request", "Preflight", "Plan", "TypedRequests", "Encoding",
          "Primary", "Assembly", "Decoding", "Structure", "FinalLength", "FinalMetadata", "Publication"]
CODES = ["SourceIdentity","RequestShape","EligibilityRejected","InventoryMismatch","NodeOrderMismatch","TypedOperandMismatch","CodecRouteMismatch","CodecError","EncodedLengthMismatch","CompositeLengthMismatch","InstructionBoundaryMismatch","PrimaryByteMismatch","IndependentDecodeError","DecodedFormMismatch","DecodedOperandMismatch","DecodedTargetMismatch","DDContextMismatch","BranchTargetMismatch","CFGInvariantViolation","ContextObligationMismatch","OrderedEffectMismatch","AtomicityViolation","UnexpectedOutput","PermissionViolation","InternalInvariant"]


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(exact(actual[k], v) for k, v in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected))
    return actual == expected


def require(condition, diagnostic):
    if not condition:
        raise ValueError(diagnostic)  # No byte or input repr in diagnostics.


def source_policy():
    checked = 0
    for filename, allowed in PURE_IMPORTS.items():
        tree = ast.parse((DIR / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            checked += 1
            if isinstance(node, ast.Import):
                require(all(x.name in allowed for x in node.names), "Pure import allowlist")
            if isinstance(node, ast.ImportFrom):
                require(node.module in allowed and node.level == 0
                        and all(x.name != "*" for x in node.names), "Pure import-from allowlist")
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else "")
                require(name not in BANNED_CALLS, "Pure API forbidden operation")
            if isinstance(node, ast.Constant) and type(node.value) is bytes:
                require(len(node.value) <= 5, "Persistent composite literal forbidden")
        if filename.endswith("emitter.py"):
            entry = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                         and n.name == "emit_synthetic_composite")
            require([a.arg for a in entry.args.args] ==
                    ["reviewed_ir", "reviewed_composition", "reviewed_eligibility", "request"]
                    and not entry.args.vararg and not entry.args.kwarg
                    and not entry.args.defaults, "Closed API signature")
            require(sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "VerifiedSyntheticComposite" for n in ast.walk(entry)) == 1,
                    "Single final publication required")
    return checked


def validate_metadata(contract):
    require(type(contract) is dict and set(contract) == {
        "schemaVersion", "milestone", "exactBase", "upstreamBindings", "primaryEvidence",
        "safety", "stages", "errorCodes", "nodeInventory", "sourceBindings",
        "contextAndEffects", "runtimeExclusions", "historicalPreservation",
        "negativeGates", "evidenceClassification"}, "Contract closed groups")
    require(exact(contract["schemaVersion"], 1) and contract["milestone"] == "M2bj"
            and contract["exactBase"] == EXACT_BASE, "Contract exact identity")
    require(exact(contract["safety"], SAFETY) and exact(contract["runtimeExclusions"], EXCLUSIONS),
            "Safety rules pinned independently of metadata")
    require(exact(contract["stages"], STAGES) and exact(contract["errorCodes"], CODES), "Closed lifecycle/errors")
    require(exact(contract["upstreamBindings"], UPSTREAM), "Upstream inventory and identities")
    from synthetic_composite_primary_oracle import preparation_receipt
    primary = preparation_receipt()
    require(exact(contract["nodeInventory"], primary["nodes"]), "Primary exact20 boundaries")
    require(exact(contract["primaryEvidence"], {
        "manualSha256": primary["manualSha256"], "oracleSha256": ORACLE_SHA256,
        "referenceSha256": PRIMARY_REFERENCE_SHA256,
        "sealedFixtureSha256": "2d042717180777b7a3e43d72d27b5af127539c0f09c67aeed72c94a62dc08311",
        "expectedDerivedBeforeEmitterImplementation": True,
        "independence": "PrimaryManualAndPriorSealedFacts_NoOperationalCodecs",
        "fullStreamSerialized": False}), "Independent primary identity")
    eligibility = json.loads((DIR / "composite_emission_eligibility_contract.json").read_text(encoding="utf-8"))
    require(exact(contract["contextAndEffects"], eligibility["inheritedContextAndEffectObligations"]),
            "Context/effects cannot be asserted by editable new metadata")
    require(exact(contract["historicalPreservation"], eligibility["historicalPreservation"]),
            "Historical statuses unchanged")
    require(contract["evidenceClassification"] ==
            "SourceBoundActualEncoderPrimaryDecoderAndAtomicTestsRequired_NotMetadataVerdict",
            "Metadata cannot establish success")
    require(exact(contract["negativeGates"], ["SemanticInputMutations", "ActualByteMutations",
        "DecoderMetadataMutations", "AtomicFailureInjections", "NoIOOrPartialOutputs",
        "ExactScalarDDAndCrossVariantIdentity", "SourcePolicyAST", "EditableContractRefusals"]),
        "All test gates required")


def load_inputs():
    """Fixed repository files only, actual hashes before model loading/emission."""
    bindings = []
    for row in UPSTREAM:
        payload = (REPO / row["file"]).read_bytes()
        require(len(payload) == row["bytes"] and hashlib.sha256(payload).hexdigest() == row["sha256"],
                "Actual upstream source identity changed")
        bindings.append(row)
    oracle = (DIR / "synthetic_composite_primary_oracle.py").read_bytes()
    require(hashlib.sha256(oracle).hexdigest() == ORACLE_SHA256, "Sealed oracle changed")
    contract = json.loads((DIR / "synthetic_composite_contract.json").read_text(encoding="utf-8"))
    validate_metadata(contract)
    expected_sources = {"synthetic_composite_emitter.py", "synthetic_composite_primary_oracle.py",
                        "synthetic_composite_tests.py"}
    require(type(contract["sourceBindings"]) is list and
            {r["file"] for r in contract["sourceBindings"]} == expected_sources
            and len(contract["sourceBindings"]) == 3, "New source-binding inventory")
    for row in contract["sourceBindings"]:
        require(type(row) is dict and set(row) == {"file", "bytes", "sha256"}, "Source-binding shape")
        payload = (DIR / row["file"]).read_bytes()
        require(exact(len(payload), row["bytes"]) and hashlib.sha256(payload).hexdigest() == row["sha256"],
                "Actual new source binding changed")
    source_policy()
    models = tuple(json.loads((DIR / name).read_text(encoding="utf-8")) for name in (
        "word0196_ir.json", "static_composition_contract.json", "composite_emission_eligibility_contract.json"))
    return models, contract, bindings


def main():
    from synthetic_composite_tests import run_suite
    evidence = run_suite()
    print("M2BJ_EVIDENCE_JSON=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
