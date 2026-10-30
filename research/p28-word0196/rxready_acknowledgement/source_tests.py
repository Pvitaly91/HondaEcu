"""Independent static/provenance tests; none starts a CPU or receiver."""

from copy import deepcopy
import hashlib
import importlib
import unittest

from .reference_oracle import REFUSED_HYPOTHESES, expected_claims, expected_document_identities, expected_records


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Delayed until the parent freezes independent expected bytes.
        cls.analysis = importlib.import_module(__package__ + ".analysis")
        cls.provenance = importlib.import_module(__package__ + ".provenance")

    def refuse(self, topic, value):
        with self.assertRaises(ValueError):
            self.analysis.claim(topic, value)

    def test_full_documentary_stream_equals_independent_reference(self):
        self.assertEqual(expected_records(), self.analysis.canonical_records())

    def test_closed_inventory_and_no_actual_runtime_claims(self):
        records = self.analysis.canonical_records()
        self.assertEqual(28, len(records))
        self.assertEqual(28, len({record["recordId"] for record in records}))
        self.assertEqual(28, len({record["topic"] for record in records}))
        for record in records:
            self.assertIsNone(record["actualObservation"])
            self.assertIs(record["executionBlocked"], True)
            self.assertIs(record["firmwareReady"], False)

    def test_all_supported_qualified_claims(self):
        for topic, value in expected_claims().items():
            with self.subTest(topic=topic):
                self.assertEqual(value, self.analysis.claim(topic, value))

    def test_substantive_unsupported_hypotheses_refused(self):
        self.assertEqual(38, len(REFUSED_HYPOTHESES))
        for topic, value in REFUSED_HYPOTHESES:
            with self.subTest(topic=topic, value=value):
                self.refuse(topic, value)

    def test_readonly_does_not_choose_either_read_side_effect_hypothesis(self):
        for value in (True, False, "ReadClearsRQSRRDY", "ReadNeverClearsRQSRRDY"):
            self.refuse("srbuf-read-ack", value)
        self.assertIn("Unknown", self.analysis.claim("srbuf-read-ack", expected_claims()["srbuf-read-ack"]))

    def test_entry_ack_is_not_srbuf_read_ack_or_all_factor_clear(self):
        self.refuse("srbuf-read-ack", expected_claims()["entry-generic-ack"])
        self.refuse("entry-generic-ack", "EntryClearsEveryPendingFactor")
        self.refuse("entry-rx-ack", "NativeRXIRQObserved")

    def test_no_reassertion_or_collision_priority_promoted(self):
        for value in ("UnreadBufferAutomaticallyReasserts", "FreshCompletionIsAlwaysRequiredForReentry"):
            self.refuse("reassert-without-completion", value)
        for value in ("HardwareSetAlwaysWins", "SoftwareClearAlwaysWins", "SRBUFReadAlwaysPrecedesEntryAcknowledgement", "NewCompletionAlwaysOverridesAcknowledgement"):
            self.refuse("collision-priority", value)

    def test_error_presence_is_not_request_suppression_authority(self):
        for error in ("MERR", "PERR", "FERR"):
            self.refuse("error-request-suppression", error + "SuppressesEveryRXRequest")

    def test_ie_conflict_and_pending_delivery_separation(self):
        for value in ("IE1VerifiedForActualEcu", "IE0VerifiedForActualEcu", "Page167DescribesPostEntryIEClear"):
            self.refuse("ie-polarity", value)
        self.refuse("pending-enable", "IEWriteGeneratesRXRequest")
        self.refuse("pending-enable", "RequestBeforeEnableProvesUnlimitedLifetime")

    def test_receive_filter_retention_and_permit_require_qualified_owners(self):
        self.refuse("mpc-filter", "EveryReceiveCompletionGeneratesRequest")
        self.refuse("overrun-replacement", "UnreadBufferCannotBeReplaced")
        self.refuse("overrun-replacement", "NoNewOverrunImpliesFinalOERR0")
        self.refuse("receiver-permit", "ResetSRREN0ProvesCurrentReceiverDisabled")

    def test_completed_software_clear_and_actual_mask_ownership_not_conflated(self):
        self.refuse("software-clear54ea", "PreclearGenerationAloneSurvivesCompleted54EA")
        self.refuse("software-clear54ea", "CurrentPendingOwnerEstablished")
        self.refuse("mask-writers", "StaticMaskLiteralProvesCurrentIEAndMIEOwner")

    def test_static_handler_relations_not_actual_native_observations(self):
        for topic, value in (("read0262", "ActualCurrentSRBUFReadObserved"), ("compare0264", "CMPBComparesReceivedFWith2"), ("store0269", "OnlyOddFCanReach0269"), ("return029c", "RTIRestoresHost28AE"), ("return029c", "029CIsTheSavedForegroundPC")):
            self.refuse(topic, value)

    def test_physical_frame_source_index_and_crossfamily_promotions_refused(self):
        for topic, value in (("frame-safety", "UnknownSSPIsPhysicallySafe"), ("frame-safety", "NumericDisjointnessProvesPhysicalStackSafety"), ("limit-index", "NoSearchHitProvesDocumentDoesNotExist"), ("limit-crossfamily", "SameAssemblyCoreProvesSamePeripheral"), ("authority-execution", "FirmwareReady=true"), ("authority-execution", "StaticCanonicalIsActualECUTrace")):
            self.refuse(topic, value)

    def test_unknown_topic_and_malformed_claims_refused(self):
        for topic, value in (("unknown-source", "Known"), ("srbuf-read-ack", None), ("srbuf-read-ack", {}), ("entry-rx-ack", ["Native"]), ("authority-execution", 1)):
            self.refuse(topic, value)

    def test_document_registry_raw_identities_are_independently_pinned(self):
        actual = {record["sourceId"]: record for record in self.provenance.documents()}
        expected = expected_document_identities()
        self.assertEqual(set(expected), set(actual))
        for source_id, identity in expected.items():
            with self.subTest(sourceId=source_id):
                for field, value in identity.items():
                    self.assertEqual(value, actual[source_id][field])
                result = self.provenance.validate_document(actual[source_id])
                self.assertEqual({"sourceId": source_id, "byteIdentityVerified": False, "manufacturerSemanticsAuthenticated": False, "executionAdmission": False}, result)

    def test_document_claim_and_applicability_mutations_refused(self):
        records = {record["sourceId"]: record for record in self.provenance.documents()}
        mutations = (
            ("EnglishY4", "kind", "CompleteUserManual"),
            ("JapaneseY3", "kind", "ReceiveAcknowledgementErratum"),
            ("UserIncomplete", "editionAuthenticated", True),
            ("UserIncomplete", "integrity", "CompleteCleanArchive"),
            ("OldSpec66201", "models", ["MSM66207"]),
            ("OldSpec66201", "date", "November 1990 EntireDocument"),
            ("ISA1991", "applicability", "ActualEcuMaskVerified"),
            ("EnglishY4", "claims", ["SRBUFReadClearsRQSRRDY"]),
            ("JapaneseY3", "documentId", "E2E1027-27-Y4"),
        )
        for source_id, field, value in mutations:
            with self.subTest(sourceId=source_id, field=field):
                mutant = deepcopy(records[source_id])
                self.assertNotEqual(mutant[field], value)
                mutant[field] = value
                with self.assertRaises(ValueError):
                    self.provenance.validate_document(mutant)

    def test_document_extra_runtime_authority_and_unknown_source_refused(self):
        record = deepcopy(self.provenance.documents()[0])
        for field, value in (("executionAdmission", True), ("actualReceiveByte", 0), ("physicalSSP", 0x500)):
            mutant = dict(record, **{field: value})
            with self.assertRaises(ValueError):
                self.provenance.validate_document(mutant)
        record["sourceId"] = "UnknownNewDocument"
        with self.assertRaises(ValueError):
            self.provenance.validate_document(record)

    def test_invented_provenance_bytes_positive_without_semantic_promotion(self):
        raw = b"M2ck invented provenance fixture v1\n"
        expected_sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual({"byteIdentityVerified": True, "manufacturerSemanticsAuthenticated": False, "executionAdmission": False}, self.provenance.verify_bytes(raw, expected_sha, len(raw)))

    def test_invented_provenance_byte_digest_and_size_mutations_refused(self):
        raw = b"M2ck invented provenance fixture v1\n"
        sha = hashlib.sha256(raw).hexdigest()
        for value, digest, count in ((raw + b"x", sha, len(raw)), (raw[:-1], sha, len(raw)), (b"X" + raw[1:], sha, len(raw)), (raw, "0" * 64, len(raw)), (raw, sha, len(raw) + 1), (raw, sha, len(raw) - 1), (raw, sha.upper(), len(raw))):
            with self.subTest(bytes=len(value), sha=digest, count=count):
                with self.assertRaises(ValueError):
                    self.provenance.verify_bytes(value, digest, count)

    def test_provenance_types_and_missing_fields_are_not_coerced(self):
        record = deepcopy(self.provenance.documents()[0])
        for field in ("sha256", "bytes", "models", "claims", "applicability"):
            mutant = deepcopy(record)
            del mutant[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                self.provenance.validate_document(mutant)
        for raw, sha, count in (("not-bytes", "0" * 64, 9), (b"", "x" * 64, 0), (b"", "0" * 64, False), (b"", "0" * 64, -1), (b"", None, 0)):
            with self.subTest(raw=raw, sha=sha, count=count), self.assertRaises(ValueError):
                self.provenance.verify_bytes(raw, sha, count)


if __name__ == "__main__":
    unittest.main()
