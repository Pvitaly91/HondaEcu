"""Independent M2cm controls; author did not execute analyzer to set expectations."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from . import analysis, compatibility, provenance
from .reference_oracle import (
    EXPECTED_DOCUMENTARY,
    canonical_bytes,
    expected_claim_comparison,
    expected_compatibility,
    expected_records,
)


def evidence(kind="ProjectArchiveAcquisition", source="M1aPublicReport"):
    return {
        "kind": kind,
        "sourceId": source,
        "scope": kind,
        "actualEcuId": None,
        "sameUnitLink": None,
        "romExtractionLinked": False,
        "maskRevisionConfirmed": False,
        "safeStackConfirmed": False,
        "rxAckConfirmed": False,
        "actualHardwareObservation": None,
    }


def claim(value="P28-A01", group="Catalogue", unit=None, exclusive=False,
          subject="code304", prop="EcuAssociation"):
    return {"subject": subject, "property": prop, "value": value,
            "unitScope": unit, "exclusive": exclusive, "independenceGroup": group}


class CompatibilityTests(unittest.TestCase):
    def test_all_sixty_selected_premises_match_independent_capacity_reference(self):
        count = 0
        for ecu in ("P28-A01", "P28-A51", "P28-A02", "P28-A52", "Unknown"):
            for mcu in ("MSM66201", "MSM66207", "MSM66P201", "MSM66P207"):
                for config in ("InternalOnly32K", "ExternalProgramSupported", "Unknown"):
                    with self.subTest(ecu=ecu, mcu=mcu, config=config):
                        self.assertEqual(compatibility.classify(ecu, mcu, config),
                                         expected_compatibility(ecu, mcu, config))
                    count += 1
        self.assertEqual(count, 60)

    def test_internal_only_201_capacity_conflict_is_premise_not_actual_unit_refusal(self):
        for mcu in ("MSM66201", "MSM66P201"):
            row = compatibility.classify("Unknown", mcu, "InternalOnly32K")
            self.assertEqual(row["status"], "ConflictsWithStatedStandardPremise")
            self.assertEqual(row["standardInternalProgramBytes"], 16384)
            self.assertFalse(row["actualEcuRuledOut"])

    def test_external_program_support_does_not_rule_out_201_or_prove_actual_map(self):
        for mcu in ("MSM66201", "MSM66207", "MSM66P201", "MSM66P207"):
            row = compatibility.classify("P28-A01", mcu, "ExternalProgramSupported")
            self.assertEqual(row["status"], "ConditionallyCompatible")
            self.assertTrue(row["externalProgramDocumented"])
            self.assertFalse(row["physicalUnitBound"])
            self.assertEqual(row["peripheralApplicability"], "Unestablished")

    def test_32k_internal_capacity_fit_does_not_identify_207_or_a_donor(self):
        row = compatibility.classify("P28-A51", "MSM66207", "InternalOnly32K")
        self.assertEqual(row["status"], "ConditionallyCompatible")
        self.assertEqual(row["standardInternalProgramBytes"], 32768)
        for key in ("actualSiliconConfirmed", "physicalUnitBound", "executionAdmission", "firmwareReady"):
            self.assertFalse(row[key])

    def test_otp_pairing_is_not_programming_mode_or_physical_package_proof(self):
        for mcu in ("MSM66P201", "MSM66P207"):
            row = compatibility.classify("Unknown", mcu, "Unknown")
            self.assertEqual(row["otpQualification"], "PairedNominalCounterpart_NotProgrammingModeProof")
            self.assertEqual(row["status"], "Unknown")

    def test_typed_invalid_ecu_mcu_and_configuration_are_not_coerced(self):
        valid = ["P28-A01", "MSM66207", "Unknown"]
        for index in range(3):
            for bad in (None, True, 32768, [], {}, "", "unknown", "MSM66207-251"):
                args = valid.copy()
                args[index] = bad
                with self.subTest(index=index, bad=bad), self.assertRaises(ValueError):
                    compatibility.classify(*args)


class ProvenanceTests(unittest.TestCase):
    def test_all_ten_evidence_classes_are_source_scoped_not_hardware_admission(self):
        kinds = (
            ("ProjectArchiveAcquisition", "M1aPublicReport", "ProjectAcquisitionOnly"),
            ("CatalogueAssociation", "ArchiveCatalogue", "NonExclusiveCatalogueAssociation"),
            ("ShopLoggedUnit", "HALoggedList", "UnlinkedShopReportedUnit"),
            ("UnlinkedDrawing", "BomarcSchematic", "UnlinkedThirdPartyDrawing"),
            ("UnlinkedPhotoA01", "EbayA01Photo", "UnlinkedVisibleCommercialUnit"),
            ("UnlinkedPhotoA02", "DGTuneA02Photo", "UnlinkedVisibleCommercialUnit"),
            ("StandardManufacturer", "JapaneseY3", "StandardNamedDeviceOnly"),
            ("RomLength", "M1aPublicReport", "PayloadPropertyOnly"),
            ("Checksum", "M1fPublicReport", "PayloadPropertyOnly"),
            ("IsaCompatibility", "ISA1991", "ReviewedStandardIsaOnly"),
        )
        for kind, source, classification in kinds:
            with self.subTest(kind=kind):
                self.assertEqual(provenance.classify_evidence(evidence(kind, source)), {
                    "evidenceClass": classification,
                    "projectAcquisitionScopeOnly": kind == "ProjectArchiveAcquisition",
                    "privateSourceBytesVerifiedByThisClassifier": False,
                    "actualSiliconConfirmed": False, "executionAdmission": False,
                    "firmwareReady": False,
                })

    def test_p28_a51_drawing_cannot_be_promoted_to_a01_or_studied_donor(self):
        x = evidence("UnlinkedDrawing", "BomarcSchematic")
        for field, value in (("actualEcuId", "P28-A01"), ("sameUnitLink", "invented-owner"),
                             ("romExtractionLinked", True), ("actualHardwareObservation", {})):
            mutated = {**x, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                provenance.classify_evidence(mutated)

    def test_cpu_suffix_without_primary_bridge_cannot_confirm_mask_revision(self):
        x = evidence("ShopLoggedUnit", "HALoggedList")
        x["maskRevisionConfirmed"] = True
        with self.assertRaises(ValueError):
            provenance.classify_evidence(x)

    def test_isa_compatibility_cannot_become_physical_identity(self):
        x = evidence("IsaCompatibility", "ISA1991")
        x["actualEcuId"] = "InventedSameUnit"
        with self.assertRaises(ValueError):
            provenance.classify_evidence(x)

    def test_correct_checksum_and_length_do_not_establish_factory_originality(self):
        for kind, source in (("Checksum", "M1fPublicReport"), ("RomLength", "M1aPublicReport")):
            x = evidence(kind, source)
            self.assertFalse(provenance.classify_evidence(x)["actualSiliconConfirmed"])
            x["factoryOriginal"] = True
            with self.assertRaises(ValueError):
                provenance.classify_evidence(x)

    def test_unlinked_commercial_photos_are_not_same_unit_or_native_observations(self):
        for kind, source in (("UnlinkedPhotoA01", "EbayA01Photo"),
                             ("UnlinkedPhotoA02", "DGTuneA02Photo")):
            for key, value in (("sameUnitLink", True), ("actualHardwareObservation", "pixels"),
                               ("romExtractionLinked", True)):
                with self.subTest(kind=kind, key=key), self.assertRaises(ValueError):
                    provenance.classify_evidence({**evidence(kind, source), key: value})

    def test_standard_manufacturer_family_does_not_prove_rx_ack_or_safe_ssp(self):
        for key in ("rxAckConfirmed", "safeStackConfirmed"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                provenance.classify_evidence({**evidence("StandardManufacturer", "JapaneseY3"), key: True})

    def test_synthetic_controls_cannot_turn_unknown_board_into_confirmed_hardware(self):
        x = evidence()
        x["actualHardwareObservation"] = {"kind": "SyntheticOnly", "board": "Invented"}
        with self.assertRaises(ValueError):
            provenance.classify_evidence(x)

    def test_kind_source_scope_types_and_extra_authority_are_closed(self):
        x = evidence()
        for field, value in (("kind", "Unknown"), ("kind", []), ("sourceId", "JapaneseY3"),
                             ("scope", "SameUnit"), ("maskRevisionConfirmed", 0),
                             ("romExtractionLinked", None), ("actualEcuId", False)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                provenance.classify_evidence({**x, field: value})
        for mutated in (None, [], {**x, "runtimeAdmission": True}, {k:v for k,v in x.items() if k != "scope"}):
            with self.subTest(mutated=mutated), self.assertRaises(ValueError):
                provenance.classify_evidence(mutated)

    def test_invented_byte_identity_positive_never_authenticates_hardware(self):
        raw = b"invented-only-m2cm-byte-control"
        self.assertEqual(provenance.verify_bytes(raw, sha256(raw).hexdigest(), len(raw)), {
            "byteIdentityVerified": True, "hardwareAuthenticityEstablished": False,
            "actualSiliconConfirmed": False, "executionAdmission": False,
        })

    def test_byte_digest_size_and_type_mismatches_are_refused(self):
        raw = b"invented-control"
        digest = sha256(raw).hexdigest()
        for args in ((raw+b"x", digest, len(raw)), (raw, "0"*64, len(raw)),
                     (raw, digest.upper(), len(raw)), (raw, digest, len(raw)+1),
                     (bytearray(raw), digest, len(raw)), (None, digest, len(raw)),
                     (raw, digest, True), (raw, digest, 0), (raw, None, len(raw))):
            with self.subTest(args=args), self.assertRaises(ValueError):
                provenance.verify_bytes(*args)


class AttributionTests(unittest.TestCase):
    def test_six_real_unlinked_attribution_relations_match_independent_reference(self):
        for pair in EXPECTED_DOCUMENTARY["attributionPairs"]:
            keys=("subject","property","value","unitScope","exclusive","independenceGroup")
            left={key:pair["left"][key] for key in keys}
            right={key:pair["right"][key] for key in keys}
            self.assertEqual(provenance.compare_claims(left, right),
                             expected_claim_comparison(left, right))

    def test_nonexclusive_catalogue_shop_difference_is_not_exclusive_same_unit_conflict(self):
        result = provenance.compare_claims(claim(), claim("P28-A02", "Shop"))
        self.assertEqual(result["relation"], "NonExclusiveAttributionDifference")
        self.assertFalse(result["studiedUnitIdentityEstablished"])

    def test_same_source_difference_is_dependent_not_independent_confirmation(self):
        result = provenance.compare_claims(claim(), claim("P28-A02"))
        self.assertEqual(result["relation"], "DependentSourceDifference_NotIndependentConfirmation")

    def test_synthetic_exclusive_same_unit_contradiction_detected_under_declared_premises(self):
        left = claim("P28-A01", "InventedA", "InventedUnitOnly", True)
        right = claim("P28-A02", "InventedB", "InventedUnitOnly", True)
        result = provenance.compare_claims(left, right)
        self.assertEqual(result["relation"], "ExclusiveSameUnitConflict_UnderDeclaredPremises")
        self.assertFalse(result["authenticityEstablishedByComparison"])
        self.assertFalse(result["executionAdmission"])

    def test_conflict_requires_each_same_unit_exclusive_independence_relation(self):
        left = claim("P28-A01", "InventedA", "InventedUnitOnly", True)
        right = claim("P28-A02", "InventedB", "InventedUnitOnly", True)
        for changed in ({**right, "unitScope": None}, {**right, "unitScope": "OtherUnit"},
                        {**right, "exclusive": False}, {**right, "independenceGroup": "InventedA"}):
            self.assertNotEqual(provenance.compare_claims(left, changed)["relation"],
                                "ExclusiveSameUnitConflict_UnderDeclaredPremises")

    def test_same_value_and_different_subjects_do_not_establish_identity(self):
        self.assertEqual(provenance.compare_claims(claim(), claim(group="Other"))["relation"],
                         "SameValue_NotIndependentIdentityProof")
        for changed in (claim(subject="code251"), claim(prop="DifferentProperty")):
            self.assertEqual(provenance.compare_claims(claim(), changed)["relation"],
                             "DifferentSubjectsOrProperties")

    def test_claim_type_missing_extra_empty_and_bool_fields_are_not_coerced(self):
        for field, bad in (("subject", []), ("property", ""), ("value", None),
                           ("unitScope", True), ("exclusive", 1), ("independenceGroup", "")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                provenance.compare_claims({**claim(), field:bad}, claim())
        for bad in (None, [], {**claim(), "actual": True}, {k:v for k,v in claim().items() if k != "value"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                provenance.compare_claims(bad, claim())

    def test_attribution_source_hashes_and_registry_independence_are_not_host_labels(self):
        for field, value in (("independenceGroup", "InventedIndependentSource"),
                             ("sourceRefs", [])):
            x=deepcopy(EXPECTED_DOCUMENTARY)
            x["attributionPairs"][0]["left"][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.validate_contract(x)
        x=deepcopy(EXPECTED_DOCUMENTARY)
        x["attributionPairs"][0]["left"]["sourceRefs"][0]["sourceHash"]="0"*64
        with self.assertRaises(ValueError):
            analysis.validate_contract(x)


class DocumentaryTests(unittest.TestCase):
    def test_full_nine_record_canonical_stream_equals_preanalysis_frozen_reference(self):
        actual = list(analysis.canonical_records())
        self.assertEqual(actual, expected_records())
        self.assertEqual(canonical_bytes(actual), canonical_bytes(expected_records()))
        self.assertEqual(len(actual), 9)

    def test_all_canonical_unknowns_and_execution_exclusions_are_retained(self):
        for row in analysis.canonical_records():
            self.assertIsNone(row["actualHardwareObservation"])
            self.assertIs(row["executionBlocked"], True)
            self.assertIs(row["firmwareReady"], False)
        authority = EXPECTED_DOCUMENTARY["authority"]
        for key in ("actualEcuIdentity", "actualMcuIdentity", "currentSsp", "safeActualFrame", "actualData03f3Generation"):
            self.assertIsNone(authority[key])
        self.assertEqual(authority["newCpuRomIrqRtiExecutions"], 0)

    def test_graph_contains_fourteen_source_bound_nodes_eighteen_edges_and_no_admission(self):
        result = analysis.validate_graph(deepcopy(EXPECTED_DOCUMENTARY["graph"]),
                                         deepcopy(EXPECTED_DOCUMENTARY["sourceInventory"]))
        self.assertEqual(result, {"validatedNodes": 14, "validatedEdges": 18,
                                  "actualSiliconConfirmed": False, "executionAdmission": False})

    def test_graph_each_required_node_or_edge_cannot_be_removed(self):
        for kind in ("nodes", "edges"):
            for index in range(len(EXPECTED_DOCUMENTARY["graph"][kind])):
                x = deepcopy(EXPECTED_DOCUMENTARY["graph"])
                x[kind].pop(index)
                with self.subTest(kind=kind, index=index), self.assertRaises(ValueError):
                    analysis.validate_graph(x, EXPECTED_DOCUMENTARY["sourceInventory"])

    def test_unknown_physical_graph_nodes_cannot_be_filled_by_host_assertion(self):
        graph = EXPECTED_DOCUMENTARY["graph"]
        unknown = {"observed_ecu_label", "pcb_revision", "observed_mcu_marking", "actual_hardware_identity",
                   "extraction_custody", "board_memory_configuration", "peripheral_applicability"}
        self.assertEqual(len(unknown), 7)
        for index, row in enumerate(graph["nodes"]):
            if row["nodeId"] in unknown:
                self.assertIsNone(row["value"])
                x = deepcopy(graph)
                x["nodes"][index]["value"] = "InventedHostAssertion"
                with self.subTest(node=row["nodeId"]), self.assertRaises(ValueError):
                    analysis.validate_graph(x, EXPECTED_DOCUMENTARY["sourceInventory"])

    def test_graph_duplicate_dangling_cycle_same_unit_and_authority_mutations_refused(self):
        base = EXPECTED_DOCUMENTARY["graph"]
        mutations = []
        x=deepcopy(base); x["nodes"].append(deepcopy(x["nodes"][0])); mutations.append(x)
        x=deepcopy(base); x["edges"][0]["to"]="missing-node"; mutations.append(x)
        x=deepcopy(base); x["edges"][0]["to"]=x["edges"][0]["from"]; mutations.append(x)
        x=deepcopy(base); x["edges"][0]["sameUnitEstablished"]=True; mutations.append(x)
        x=deepcopy(base); x["actualSiliconConfirmed"]=True; mutations.append(x)
        x=deepcopy(base); x["executionAdmission"]=True; mutations.append(x)
        for x in mutations:
            with self.subTest(graph=x), self.assertRaises(ValueError):
                analysis.validate_graph(x, EXPECTED_DOCUMENTARY["sourceInventory"])

    def test_graph_source_hash_locator_and_inventory_bindings_cannot_be_fabricated(self):
        for key, value in (("sourceHash", "0"*64), ("sourceId", "UnboundSource"), ("locator", "")):
            x=deepcopy(EXPECTED_DOCUMENTARY["graph"])
            x["edges"][0]["sourceRefs"][0][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):
                analysis.validate_graph(x, EXPECTED_DOCUMENTARY["sourceInventory"])

    def test_graph_typed_malformed_structures_are_value_errors(self):
        for bad in (None, [], {}, {"nodes": None}, {**EXPECTED_DOCUMENTARY["graph"], "edges": [None]}):
            with self.subTest(graph=bad), self.assertRaises(ValueError):
                analysis.validate_graph(bad, EXPECTED_DOCUMENTARY["sourceInventory"])

    def test_contract_source_inventory_schema_and_authority_promotions_refused(self):
        mutations=[]
        x=deepcopy(EXPECTED_DOCUMENTARY); x["sourceInventory"][0]["sha256"]="0"*64; mutations.append(x)
        x=deepcopy(EXPECTED_DOCUMENTARY); x["sourceInventory"][0]["bytes"]=True; mutations.append(x)
        x=deepcopy(EXPECTED_DOCUMENTARY); x["schemaVersion"]=True; mutations.append(x)
        x=deepcopy(EXPECTED_DOCUMENTARY); x["authority"]["actualSiliconConfirmed"]=True; mutations.append(x)
        x=deepcopy(EXPECTED_DOCUMENTARY); x["authority"]["firmwareReady"]=True; mutations.append(x)
        x=deepcopy(EXPECTED_DOCUMENTARY); x["authority"]["runtimeAdmission"]=True; mutations.append(x)
        x=deepcopy(EXPECTED_DOCUMENTARY); x["ActualSiliconConfirmed"]=True; mutations.append(x)
        for x in mutations:
            with self.subTest(contract=x), self.assertRaises(ValueError):
                analysis.validate_contract(x)

    def test_hardware_examples_stay_unlinked_and_do_not_merge_a01_a02_and_a51(self):
        examples=EXPECTED_DOCUMENTARY["hardwareExamples"]
        self.assertEqual(len(examples), 3)
        self.assertEqual(examples[0]["observedLabel"], "37820-P28-A02")
        self.assertEqual(examples[1]["observedLabel"], "37820-P28-A01")
        for row in examples:
            for field in ("sameUnitAsStudiedRom", "linkedDumpDigest", "actualStudiedHardwareObservation",
                          "exactPackageCode", "externalProgramSelection", "factoryUnmodifiedStatus"):
                self.assertIsNone(row[field])
        for index in range(len(examples)):
            x=deepcopy(EXPECTED_DOCUMENTARY)
            x["hardwareExamples"][index]["sameUnitAsStudiedRom"]=True
            with self.subTest(index=index), self.assertRaises(ValueError):
                analysis.validate_contract(x)

    def test_archive_project_acquisition_and_unknown_original_donor_are_distinct(self):
        chain=EXPECTED_DOCUMENTARY["provenanceChain"]
        self.assertEqual(chain["projectAcquisitionCategory"], "B_PublicFirmwareArchive")
        self.assertEqual(chain["prearchiveDonorCategory"], "E_Unknown")
        self.assertEqual(chain["historicalHttpMetadata"], "RecordedLiteralFields_NoPreservedRawGetTranscriptFound")
        self.assertFalse(chain["sameUnitIdentityEstablished"])
        self.assertFalse(chain["privateAcquisitionRecordsPublished"])
        self.assertEqual(chain["factoryOriginality"], "Unknown")

    def test_local_audit_declaration_is_not_an_original_http_or_hardware_source(self):
        rows=EXPECTED_DOCUMENTARY["sourceInventory"]
        self.assertEqual(len(rows),24)
        row=next(r for r in rows if r["sourceId"] == "M2cmLocalAuditDeclaration")
        self.assertEqual(row["sourceKind"], "PublicRedactedLocalAuditDeclaration_NotIndependentAcquisitionTranscript")
        self.assertEqual(row["scope"], "SourceQualifiedLocalAuditSummary_PrivateRawBindingsNotReverifiedByPublicCI")
        self.assertFalse(EXPECTED_DOCUMENTARY["provenanceChain"]["sameUnitIdentityEstablished"])

    def test_backlog_all_five_categories_are_bounded_and_not_new_execution(self):
        rows=EXPECTED_DOCUMENTARY["backlog"]
        self.assertEqual([r["category"] for r in rows], ["A","A","A","B","C","D","D","E"])
        self.assertEqual([r["priority"] for r in rows], list(range(1,9)))
        for row in rows:
            self.assertFalse(row["newDisassemblyPerformed"])
            self.assertFalse(row["newExecutionAuthorized"])
            self.assertTrue(row["nextBoundedArtifact"])
            self.assertTrue(row["missingForPhysicalPromotion"])
            self.assertTrue(row["mustNotClaim"])

    def test_physical_checklist_no_item_is_sufficient_or_requests_intervention(self):
        rows=EXPECTED_DOCUMENTARY["physicalChecklist"]
        self.assertEqual(len(rows),10)
        for row in rows:
            self.assertFalse(row["sufficientAlone"])
            self.assertFalse(row["physicalInterventionRequested"])
            for field in ("removesUnknown","additionalEvidence","romLinkVerification","remainingConditions"):
                self.assertTrue(row[field])

    def test_research_only_success_cannot_enable_execution_or_firmware(self):
        self.assertEqual(EXPECTED_DOCUMENTARY["classification"], "ROM_PROVENANCE_ESTABLISHED_HARDWARE_UNBOUND")
        for field in ("runtimeAdmission","firmwareReady","actualSiliconConfirmed"):
            self.assertFalse(EXPECTED_DOCUMENTARY["authority"][field])
            x=deepcopy(EXPECTED_DOCUMENTARY); x["authority"][field]=True
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.validate_contract(x)


if __name__ == "__main__":
    unittest.main()
