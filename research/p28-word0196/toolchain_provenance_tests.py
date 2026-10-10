"""Independent invented-only gate tests; never downloads or invokes toolchains.

Expected policies below are authored separately from validator implementation.
Mock component hashes/versions/manifests describe only an invented classification
model. Positive tests cannot establish actual MAC66K acquisition or operation.
Existing IR/context hashes and form metadata are checked without changing them.
"""

from pathlib import Path
import copy
import hashlib
import itertools
import json
import sys
import unittest

sys.dont_write_bytecode = True

import validate_toolchain_provenance as policy


HERE = Path(__file__).resolve().parent
RESEARCH = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else HERE
BASE = policy.load_contract(HERE / "toolchain_provenance_contract.json")
PROPERTY_VECTORS = 0
IR_HASH = "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"
CONTEXT_HASH = "1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"
EXPECTED_FORMS = [
    (747, "LB A, off N8", 2, "R", ["556F", "5592"]),
    (2198, "SLLB A", 1, "0", ["5571"]), (1862, "ROLB off N8", 3, "U", ["5572"]),
    (739, "LB A, r0", 1, "R", ["5575"]), (333, "ANDB A, off N8", 2, "0", ["5576"]),
    (498, "CMP off N8, #N16", 5, "U", ["5578"]), (719, "JLT rel8", 2, "U", ["557D"]),
    (1504, "MOVB r1, off N8", 3, "U", ["557F"]),
    (349, "ANDB off N8, A", 3, "U", ["5582", "558B"]),
    (716, "JBS off N8.7, rel8", 3, "U", ["5585"]), (714, "JBS off N8.5, rel8", 3, "U", ["5588"]),
    (1678, "ORB off N'8, #N8", 4, "U", ["558E"]), (1619, "ORB A, #N8", 2, "0", ["5594"]),
    (738, "LB A, #N8", 2, "R", ["55BF"]), (2301, "STB A, off N8", 2, "0", ["55C1", "55C3"]),
]
MANDATORY_NEGATIVES = [
    "wrong_package_version", "missing_ras66k", "missing_rl66k", "missing_dcl", "wrong_target_dcl",
    "modified_dcl", "unknown_archive_origin", "crc_failure", "unsupported_file_format",
    "duplicate_artifacts_claimed_independent", "unverified_embedded_version", "incompatible_object_formats",
    "cross_family_nx8_500_package", "m66207_automatically_m66201", "invented_license_approval",
    "unknown_executable_claimed_verified", "search_snippet_claimed_bytes", "manual_claimed_runtime",
    "derived_asm662_claimed_manufacturer", "fake_successful_listing", "host_compilation_claimed_native",
    "target_object_without_target_verification", "unknown_package_claimed_production_ready",
]


def invented_package():
    """A metadata fixture, not files, vendor attestations or operational success."""
    return {
        "scope": "InventedPolicyModel",
        "package": {"version": "4.01", "core": "nX-8/200", "origin": "MockVendorDistribution",
                    "originKnown": True, "bytesAcquired": True, "usageRights": "ModelUsePermitted",
                    "rightsEvidence": "MockExplicitTerms", "versionEvidence": "MockIndependentReleaseManifest",
                    "independence": "MockIndependentPublisherRecords"},
        "archive": {"format": "ZIP", "crc": "Verified", "traversalSafe": True,
                    "complete": True, "repaired": False, "repacked": False},
        "components": {
            "RAS66K": {"present": True, "version": "4.11", "versionEvidence": "MockIndependentReleaseManifest", "compatibleRelease": "4.01",
                       "objectFormat": "MAC66Kv4", "sourceKind": "MockVendorPackage", "sha256": "1" * 64, "evidenceId": "mock:ras"},
            "RL66K": {"present": True, "version": "3.02", "versionEvidence": "MockIndependentReleaseManifest", "compatibleRelease": "4.01",
                      "objectFormat": "MAC66Kv4", "sourceKind": "MockVendorPackage", "sha256": "2" * 64, "evidenceId": "mock:rl"},
            "LIB66K": {"present": True, "version": "5.10", "versionEvidence": "MockIndependentReleaseManifest", "compatibleRelease": "4.01",
                       "objectFormat": "MAC66Kv4", "sourceKind": "MockVendorPackage", "sha256": "3" * 64, "evidenceId": "mock:lib"},
            "OH66K": {"present": True, "version": "1.25", "versionEvidence": "MockIndependentReleaseManifest", "compatibleRelease": "4.01",
                      "objectFormat": "MAC66Kv4", "sourceKind": "MockVendorPackage", "sha256": "4" * 64, "evidenceId": "mock:oh"},
            "MP": {"present": True, "version": "2.30", "versionEvidence": "MockIndependentReleaseManifest", "compatibleRelease": "4.01",
                   "objectFormat": "MAC66Kv4", "sourceKind": "MockVendorPackage", "sha256": "6" * 64, "evidenceId": "mock:mp"},
        },
        "dcl": {"present": True, "filename": "mock-device-description.dat", "target": "MSM66201",
                "formatEstablished": True, "modified": False, "versionCompatible": True,
                "compatibleRelease": "4.01", "identityEvidence": "MockIndependentDeviceManifest", "sourceKind": "MockVendorPackage",
                "sha256": "5" * 64, "evidenceId": "mock:dcl"},
        "dependencies": {"diskFilesManifest": True, "postManualChanges": True,
                         "dclFormatExplanation": True, "releaseRestrictions": True},
        "claims": {"runtimeVerified": False, "targetAssemblySupported": False, "listingVerified": False,
                   "hostCompilationIsNative": False, "targetObjectCreated": False, "firmwareReady": False},
    }


def set_path(record, path, value):
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def leaves(value, prefix=()):
    if type(value) is dict:
        for key, item in value.items():
            yield from leaves(item, prefix + (key,))
    elif type(value) is list and value:
        for index, item in enumerate(value):
            yield from leaves(item, prefix + (index,))
    else:
        yield prefix, value


class PolicyTests(unittest.TestCase):
    def model_blocked(self, path, value, blocker):
        model = invented_package()
        set_path(model, path, value)
        result = policy.classify_model(model)
        self.assertEqual(result["classification"], "ModelBlocked")
        self.assertIn(blocker, result["blockers"])
        self.assertFalse(result["executionPermission"])

    def forbidden_claim(self, name):
        model = invented_package()
        model["claims"][name] = True
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_positive_actual_documentation_only_contract(self):
        result = policy.validate(copy.deepcopy(BASE))
        self.assertEqual(result["actualArtifacts"], 0)
        self.assertFalse(result["runtimeVerified"])
        self.assertEqual(BASE["result"]["classification"], "M2axToolchainAcquisitionResearchBlocked")

    def test_positive_model_complete_classification_only(self):
        self.assertEqual(policy.classify_model(invented_package()), {
            "scope": "InventedPolicyModel", "classification": "ModelVersionMatchedArtifactsOnly",
            "blockers": [], "authenticatesActualArtifacts": False, "runtimeVerified": False,
            "targetCodeGenerationReady": False, "executionPermission": False, "firmwareReady": False})

    def test_positive_individual_versions_distinct_from_package_release(self):
        model = invented_package()
        self.assertTrue(all(row["version"] != model["package"]["version"] for row in model["components"].values()))
        self.assertEqual(policy.classify_model(model)["classification"], "ModelVersionMatchedArtifactsOnly")

    def test_positive_model_unknown_rights_stays_blocked(self):
        self.model_blocked(("package", "usageRights"), "Unknown", "UsageRightsNotEstablished")

    def test_positive_model_unknown_dcl_format_stays_blocked(self):
        self.model_blocked(("dcl", "formatEstablished"), False, "DclFormatNotEstablished")

    def test_positive_model_missing_converter_stays_blocked(self):
        self.model_blocked(("components", "OH66K", "present"), False, "MissingOH66K")

    def test_positive_model_no_dcl_filename_inference(self):
        model = invented_package()
        model["dcl"]["filename"] = "not-M66201.DCL"
        self.assertEqual(policy.classify_model(model)["classification"], "ModelVersionMatchedArtifactsOnly")
        self.assertIsNone(BASE["dcl"]["actualFilename"])

    def test_positive_model_tar_integrity_not_crc(self):
        model = invented_package()
        model["archive"].update(format="TAR", crc="NotApplicable")
        self.assertEqual(policy.classify_model(model)["classification"], "ModelVersionMatchedArtifactsOnly")

    def test_positive_model_7z_verified_integrity(self):
        model = invented_package()
        model["archive"]["format"] = "7z"
        self.assertEqual(policy.classify_model(model)["classification"], "ModelVersionMatchedArtifactsOnly")

    def test_positive_no_unknown_zero_defaults(self):
        self.assertIsNone(BASE["package"]["actualVersion"])
        self.assertIsNone(BASE["dcl"]["modified"])
        self.assertIsNone(BASE["archive"]["affectedMembers"])

    def test_positive_preserved_ir_context_hashes(self):
        self.assertEqual(hashlib.sha256((RESEARCH / "word0196_ir.json").read_bytes()).hexdigest(), IR_HASH)
        self.assertEqual(hashlib.sha256((RESEARCH / "target_abi_contract.json").read_bytes()).hexdigest(), CONTEXT_HASH)

    def test_positive_15_forms_18_sites_independent_ir_match(self):
        ir = json.loads((RESEARCH / "word0196_ir.json").read_text(encoding="utf-8"))
        actual = {}
        for row in ir["instructions"]:
            form = row["form"]
            index = form["pinnedPatternIndex"]
            if index not in actual:
                actual[index] = [index, form["mnemonic"], form["length"], form["ddMode"], []]
            actual[index][4].append(f'{row["pc"]:04X}')
        self.assertEqual(list(actual.values()), [list(row) for row in EXPECTED_FORMS])
        self.assertEqual(len(ir["instructions"]), 18)
        self.assertEqual(len(actual), 15)
        caps = BASE["capabilities"]
        self.assertEqual([(r["patternIndex"], r["form"], r["instructionLength"], r["ddMode"], r["historicalSites"]) for r in caps], EXPECTED_FORMS)
        self.assertTrue(all(not r["toolRuntimeVerified"] and not r["exactGeneratedEncodingVerified"]
                            and not r["generatedNativeBehaviorVerified"] for r in caps))

    def test_negative_wrong_package_version(self):
        self.model_blocked(("package", "version"), "2.01", "WrongPackageVersion")

    def test_negative_missing_ras66k(self):
        self.model_blocked(("components", "RAS66K", "present"), False, "MissingRAS66K")

    def test_negative_missing_rl66k(self):
        self.model_blocked(("components", "RL66K", "present"), False, "MissingRL66K")

    def test_negative_missing_dcl(self):
        self.model_blocked(("dcl", "present"), False, "MissingDcl")

    def test_negative_wrong_target_dcl(self):
        self.model_blocked(("dcl", "target"), "MSM66507", "DclTargetIdentityNotEstablished")

    def test_negative_modified_dcl(self):
        self.model_blocked(("dcl", "modified"), True, "ModifiedDclRejected")

    def test_negative_unknown_archive_origin(self):
        self.model_blocked(("package", "originKnown"), False, "PackageProvenanceNotEstablished")

    def test_negative_crc_failure(self):
        self.model_blocked(("archive", "crc"), "Failed", "ArchiveIntegrityFailedOrUnknown")

    def test_negative_unsupported_file_format(self):
        self.model_blocked(("archive", "format"), "EXE", "UnsupportedArchiveFormat")

    def test_negative_duplicate_artifacts_claimed_independent(self):
        self.model_blocked(("components", "RL66K", "sha256"), "1" * 64, "DuplicateArtifactsNotIndependent")

    def test_negative_unverified_embedded_version(self):
        self.model_blocked(("components", "RAS66K", "versionEvidence"), "EmbeddedTimestamp", "PackageVersionMatchIncomplete:RAS66K")

    def test_negative_incompatible_object_formats(self):
        self.model_blocked(("components", "RL66K", "objectFormat"), "MAC66Kv2", "ObjectFormatIncompatible:RL66K")

    def test_negative_cross_family_nx8_500_package(self):
        self.model_blocked(("package", "core"), "nX-8/500", "WrongTargetFamily")

    def test_negative_m66207_automatically_m66201(self):
        self.model_blocked(("dcl", "target"), "MSM66207", "DclTargetIdentityNotEstablished")

    def test_negative_invented_license_approval(self):
        self.model_blocked(("package", "rightsEvidence"), "UserGuessedLicense", "UsageRightsNotEstablished")

    def test_negative_unknown_executable_claimed_verified(self):
        self.forbidden_claim("runtimeVerified")

    def test_negative_search_snippet_claimed_bytes(self):
        self.model_blocked(("package", "bytesAcquired"), False, "AcquiredBytesNotEstablished")

    def test_negative_manual_claimed_runtime(self):
        contract = copy.deepcopy(BASE)
        contract["result"]["runtime"] = "RuntimeVerifiedByManufacturerManual"
        with self.assertRaises(ValueError):
            policy.validate(contract)

    def test_negative_derived_asm662_claimed_manufacturer(self):
        self.model_blocked(("components", "RAS66K", "sourceKind"), "DerivedASM662", "VendorComponentProvenanceNotEstablished:RAS66K")

    def test_negative_fake_successful_listing(self):
        self.forbidden_claim("listingVerified")

    def test_negative_host_compilation_claimed_native(self):
        self.forbidden_claim("hostCompilationIsNative")

    def test_negative_target_object_without_target_verification(self):
        self.forbidden_claim("targetObjectCreated")

    def test_negative_unknown_package_claimed_production_ready(self):
        self.forbidden_claim("firmwareReady")

    def test_negative_target_assembly_support_claimed_from_presence(self):
        self.forbidden_claim("targetAssemblySupported")

    def test_negative_archive_traversal_risk(self):
        self.model_blocked(("archive", "traversalSafe"), False, "DirectoryTraversalRisk")

    def test_negative_archive_incomplete(self):
        self.model_blocked(("archive", "complete"), False, "ArchiveCompletenessNotEstablished")

    def test_negative_repaired_archive_is_not_original(self):
        self.model_blocked(("archive", "repaired"), True, "OriginalDistributionNotEstablished")

    def test_negative_repacked_archive_is_not_original(self):
        self.model_blocked(("archive", "repacked"), True, "OriginalDistributionNotEstablished")

    def test_negative_missing_librarian(self):
        self.model_blocked(("components", "LIB66K", "present"), False, "MissingLIB66K")

    def test_negative_missing_macroprocessor(self):
        self.model_blocked(("components", "MP", "present"), False, "MissingMP")

    def test_negative_missing_vendor_disk_file_list(self):
        self.model_blocked(("dependencies", "diskFilesManifest"), False, "ReleaseDependencyNotEstablished:diskFilesManifest")

    def test_negative_missing_dcl_format_explanation(self):
        self.model_blocked(("dependencies", "dclFormatExplanation"), False, "ReleaseDependencyNotEstablished:dclFormatExplanation")

    def test_negative_dcl_version_mismatch(self):
        self.model_blocked(("dcl", "versionCompatible"), False, "DclVersionMatchIncomplete")

    def test_negative_component_release_binding_mismatch(self):
        self.model_blocked(("components", "RL66K", "compatibleRelease"), "2.01", "PackageVersionMatchIncomplete:RL66K")

    def test_negative_dcl_release_binding_mismatch(self):
        self.model_blocked(("dcl", "compatibleRelease"), "4.20", "DclVersionMatchIncomplete")

    def test_negative_duplicate_source_identity(self):
        self.model_blocked(("dcl", "evidenceId"), "mock:ras", "DuplicateArtifactsNotIndependent")

    def test_negative_filename_cannot_prove_identity(self):
        model = invented_package()
        model["dcl"].update(filename="M66201.DCL", target="Unknown", identityEvidence="FilenameOnly")
        self.assertIn("DclTargetIdentityNotEstablished", policy.classify_model(model)["blockers"])

    def test_negative_actual_assets_rejected_by_model_scope(self):
        model = invented_package()
        model["scope"] = "ActualVendorArtifacts"
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_negative_real_evidence_ids_rejected_by_model(self):
        model = invented_package()
        model["dcl"]["evidenceId"] = "vendor:real"
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_negative_archival_execution_path_hidden(self):
        model = invented_package()
        model["components"]["RAS66K"]["executablePath"] = "do-not-execute"
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_negative_model_integer_bool(self):
        model = invented_package()
        model["archive"]["complete"] = 1
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_negative_hash_not_sha256(self):
        model = invented_package()
        model["dcl"]["sha256"] = "unverified"
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_negative_component_schema_removed(self):
        model = invented_package()
        del model["components"]["RL66K"]
        with self.assertRaises(ValueError):
            policy.classify_model(model)

    def test_negative_actual_source_evidence_substitution(self):
        contract = copy.deepcopy(BASE)
        contract["sources"][0].update(kind="SearchSnippet", sha256="1" * 64)
        with self.assertRaises(ValueError):
            policy.validate(contract)

    def test_negative_safety_prose_weakened(self):
        contract = copy.deepcopy(BASE)
        contract["sources"][0]["scope"] = "ManufacturerManualProvesWorkingToolchain"
        with self.assertRaises(ValueError):
            policy.validate(contract)

    def test_negative_missing_blocker(self):
        contract = copy.deepcopy(BASE)
        contract["result"]["remainingBlockers"].pop()
        with self.assertRaises(ValueError):
            policy.validate(contract)

    def test_negative_unknown_filename_guessed(self):
        contract = copy.deepcopy(BASE)
        contract["dcl"]["actualFilename"] = "M66201.DCL"
        with self.assertRaises(ValueError):
            policy.validate(contract)

    def test_negative_duplicate_json_property(self):
        with self.assertRaises(ValueError):
            policy.parse_contract(b'{"schemaVersion":1,"schemaVersion":1}')

    def test_negative_noncanonical_json(self):
        with self.assertRaises(ValueError):
            policy.parse_contract(json.dumps(BASE).encode("utf-8"))

    def test_property_all_actual_leaf_promotions_rejected(self):
        global PROPERTY_VECTORS
        for path, value in list(leaves(BASE)):
            if type(value) is bool:
                changed = not value
            elif value is None:
                changed = 0
            elif type(value) is int:
                changed = value + 1
            elif type(value) is str:
                changed = "InventedPromotion"
            else:
                changed = ["InventedPromotion"]
            contract = copy.deepcopy(BASE)
            set_path(contract, path, changed)
            with self.assertRaises(ValueError, msg=str(path)):
                policy.validate(contract)
            PROPERTY_VECTORS += 1

    def test_property_every_actual_dictionary_is_closed(self):
        global PROPERTY_VECTORS
        def dictionaries(value, path=()):
            if type(value) is dict:
                yield path
                for key, item in value.items():
                    yield from dictionaries(item, path + (key,))
            elif type(value) is list:
                for index, item in enumerate(value):
                    yield from dictionaries(item, path + (index,))
        for path in dictionaries(BASE):
            contract = copy.deepcopy(BASE)
            target = contract
            for key in path:
                target = target[key]
            target["hiddenExecutionPermission"] = True
            with self.assertRaises(ValueError, msg=str(path)):
                policy.validate(contract)
            PROPERTY_VECTORS += 1

    def test_property_model_required_gate_boolean_cross_product(self):
        global PROPERTY_VECTORS
        paths = [("package", "originKnown"), ("package", "bytesAcquired"), ("archive", "traversalSafe"),
                 ("archive", "complete"), ("components", "RAS66K", "present"), ("components", "RL66K", "present"),
                 ("components", "LIB66K", "present"), ("components", "OH66K", "present"), ("dcl", "present"),
                 ("dcl", "formatEstablished"), ("dcl", "versionCompatible"), ("components", "MP", "present"),
                 ("dependencies", "diskFilesManifest"), ("dependencies", "postManualChanges"),
                 ("dependencies", "dclFormatExplanation"), ("dependencies", "releaseRestrictions")]
        for bits in itertools.product([False, True], repeat=len(paths)):
            model = invented_package()
            for path, value in zip(paths, bits):
                set_path(model, path, value)
            result = policy.classify_model(model)
            self.assertEqual(result["classification"], "ModelVersionMatchedArtifactsOnly" if all(bits) else "ModelBlocked")
            self.assertFalse(result["authenticatesActualArtifacts"])
            self.assertFalse(result["runtimeVerified"])
            self.assertFalse(result["executionPermission"])
            self.assertFalse(result["firmwareReady"])
            PROPERTY_VECTORS += 1

    def test_property_model_versions_and_archive_formats(self):
        global PROPERTY_VECTORS
        for version, fmt, crc in itertools.product(["4.00", "4.01", "2.01", "4.XX", "Unknown"],
                                                   ["ZIP", "7z", "TAR", "EXE", "Unknown"],
                                                   ["Verified", "NotApplicable", "Failed", "Unknown"]):
            model = invented_package()
            model["package"]["version"] = version
            for row in model["components"].values():
                row["compatibleRelease"] = version
            model["dcl"]["compatibleRelease"] = version
            model["archive"].update(format=fmt, crc=crc)
            result = policy.classify_model(model)
            acceptable = version in {"4.00", "4.01"} and ((fmt in {"ZIP", "7z"} and crc == "Verified")
                                                        or (fmt == "TAR" and crc == "NotApplicable"))
            self.assertEqual(result["classification"], "ModelVersionMatchedArtifactsOnly" if acceptable else "ModelBlocked")
            self.assertFalse(result["executionPermission"])
            PROPERTY_VECTORS += 1

    def test_property_five_layers_cannot_be_promoted(self):
        global PROPERTY_VECTORS
        for index in range(15):
            for key, value in [("documentedAssemblerCapability", "OperationalAssemblerVerified"),
                               ("deviceDclSpecificCapability", "DclVerified"), ("toolRuntimeVerified", True),
                               ("exactGeneratedEncodingVerified", True), ("generatedNativeBehaviorVerified", True)]:
                contract = copy.deepcopy(BASE)
                contract["capabilities"][index][key] = value
                with self.assertRaises(ValueError):
                    policy.validate(contract)
                PROPERTY_VECTORS += 1


def run():
    names = unittest.defaultTestLoader.getTestCaseNames(PolicyTests)
    mandatory = {"test_negative_" + name for name in MANDATORY_NEGATIVES}
    if not mandatory <= set(names):
        raise ValueError("A requested negative policy case is missing")
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests))
    failed = {test._testMethodName for test, _ in result.failures + result.errors}
    skipped = {test._testMethodName for test, _ in result.skipped}
    cases = [{"name": name, "kind": "Positive" if name.startswith("test_positive_") else
              "Negative" if name.startswith("test_negative_") else "Property",
              "passed": name not in failed and name not in skipped} for name in names]
    receipt = {"milestone": "M2ax", "passed": result.wasSuccessful(), "inventedOnly": True,
               "tests": result.testsRun, "positiveCases": sum(c["kind"] == "Positive" for c in cases),
               "negativeCases": sum(c["kind"] == "Negative" for c in cases),
               "propertyCases": sum(c["kind"] == "Property" for c in cases), "propertyVectors": PROPERTY_VECTORS,
               "mandatoryNegativeCases": len(MANDATORY_NEGATIVES), "failures": len(result.failures) + len(result.errors),
               "skipped": len(result.skipped), "cases": cases, "actualRomExecutions": 0,
               "targetToolExecutions": 0, "targetAssemblerExecutions": 0, "targetLinkerExecutions": 0,
               "firmwareBin": 0, "targetObjects": 0, "targetCodeGenerationReady": False,
               "actualRuntimeVerified": False, "actualClassification": BASE["result"]["classification"],
               "positiveProofScope": "InventedClassificationModelOnly;NeverActualArtifactOrOperationalProof"}
    print(json.dumps(receipt, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise ValueError("Accepts only optional unchanged research-root path")
    sys.exit(run())
