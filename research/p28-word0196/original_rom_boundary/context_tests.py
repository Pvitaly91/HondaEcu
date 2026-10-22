"""Invented-only context/evidence refusal regressions; no ROM or CPU execution.

Temporary JSON fixtures mimic selected records solely to exercise trust-boundary
checks.  Their successful tests are PublicSyntheticValidatorRegression, never
LocalOriginalRomReadOnlyVerification or actual historical observations.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

try:
    from .context import (
        CLASSIFICATIONS, ContextError, FIELD_NAMES, build_context_matrix,
        select_source, validate_evidence_record, verify_data0196_lineage,
    )
except ImportError:
    from context import (
        CLASSIFICATIONS, ContextError, FIELD_NAMES, build_context_matrix,
        select_source, validate_evidence_record, verify_data0196_lineage,
    )


class ContextTests(unittest.TestCase):
    """Independent invented fixtures; no original source payload is embedded."""

    def setUp(self):
        # Keep invented fixtures under the checkout's controlled scratch area,
        # not a platform-dependent global/private evidence directory.
        scratch = Path(__file__).resolve().parents[3] / ".tmp"
        scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="m2bs-context-invented-", dir=scratch)
        self.directory = Path(self.temporary.name)
        self.sources = []

    def tearDown(self):
        self.temporary.cleanup()

    def select(self, source_id, document, kind):
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        path = self.directory / (source_id + ".json")
        path.write_bytes(encoded)
        source = select_source(path, source_id, hashlib.sha256(encoded).hexdigest(), len(encoded), kind)
        self.sources.append(source)
        return source

    def observation(self, classification="HistoricalReplay", value=0x42, field="AL", path="B"):
        data = {"value": value, "machine": "invented-machine", "session": "invented-session",
                "event": 2, "pc": 0x5575, "read": 17, "write": None, "path": path}
        kinds = {"HistoricalReplay": "HistoricalOfflineModel",
                 "ObservedNative": "HistoricalSourceCpuObservations",
                 "StaticRomDerived": "VerifiedOriginalRomSourceReceipt",
                 "SyntheticOnly": "SyntheticTestResults"}
        if classification in ("StaticRomDerived", "SyntheticOnly"):
            data["machine"] = data["session"] = None
        self.select("invented-observation", data, kinds[classification])
        locators = {"value": "/value", "machine_id": "/machine", "session_id": "/session",
                    "event_ordinal": "/event", "pc": "/pc", "read_ordinal": "/read",
                    "write_ordinal": "/write", "path": "/path"}
        domains = {"HistoricalReplay": "HistoricalOfflineModelOnly",
                   "ObservedNative": "HistoricalSourceCpuOnly",
                   "StaticRomDerived": "ReadOnlyStaticRomSemantics",
                   "SyntheticOnly": "InventedSyntheticOnly"}
        return {"field": field, "classification": classification, "value": value,
                "source_id": "invented-observation", "locators": locators,
                "execution_domain": domains[classification], "native_ownership": False,
                "physical_execution": False, "authority_id": None}

    def native_receipt(self, record):
        validator = self.select("invented-validator", {"independent": "invented-test-only"},
                                "ReviewedHistoricalValidator")
        source = next(item for item in self.sources if item.source_id == record["source_id"])
        receipt = {"schema_version": 1,
                   "classification": "HistoricalSourceCpuObservationVerification", "passed": True,
                   "observed_source_binding": source.public_binding(),
                   "validator_source_binding": validator.public_binding(),
                   "observations": [{"field": record["field"], "locators": record["locators"],
                                     "native_ownership": record["native_ownership"]}],
                   "physical_execution": False, "model_only": False,
                   "independent_expected_comparison": True}
        self.select("invented-receipt", receipt, "HistoricalNativeVerificationReceipt")
        record["authority_id"] = "invented-receipt"

    def test_default_matrix_is_closed_exhaustive_unknown_not_zero(self):
        matrix = build_context_matrix()
        self.assertEqual(matrix["field_count"], len(FIELD_NAMES))
        self.assertEqual([row["field"] for row in matrix["fields"]], list(FIELD_NAMES))
        for row in matrix["fields"]:
            self.assertEqual(row["classifications"], ["Unknown"])
            self.assertIsNone(row["actual_value"])
            self.assertFalse(row["native_ownership_established"])
        self.assertEqual(len([name for name in FIELD_NAMES if name.startswith("pointingBank")]), 32)
        self.assertEqual(CLASSIFICATIONS,
                         ("ObservedNative", "StaticRomDerived", "HistoricalReplay", "SyntheticOnly", "Unknown"))
        self.assertEqual(matrix["new_original_rom_executions"], 0)
        self.assertEqual(matrix["physical_ecu_executions"], 0)
        self.assertFalse(matrix["firmware_ready"])
        obligations = matrix["architectural_obligations"]
        self.assertEqual(obligations["entry_pc"], 0x556F)
        self.assertEqual(obligations["stop_before_pcs"], [0x5596, 0x55C5])
        self.assertEqual(obligations["physical_sf_meaning_or_storage"], "Unknown")
        self.assertTrue(obligations["all_pointing_banks_preserved"])

    def test_historical_replay_is_not_native_ownership(self):
        record = self.observation()
        matrix = build_context_matrix([record], self.sources)
        row = next(row for row in matrix["fields"] if row["field"] == "AL")
        self.assertEqual(row["classifications"], ["HistoricalReplay"])
        self.assertIsNone(row["actual_value"])
        self.assertFalse(row["native_ownership_established"])
        self.assertEqual(row["observations"][0]["actual_observation"]["machine_id"], "invented-machine")

    def test_verified_source_cpu_observation_is_not_physical_execution(self):
        record = self.observation("ObservedNative")
        self.native_receipt(record)
        result = validate_evidence_record(record, self.sources)
        self.assertEqual(result["classification"], "ObservedNative")
        self.assertFalse(result["physical_execution"])
        self.assertFalse(result["physical_ownership_established"])

    def test_runtime_generation_scope_can_be_historical_source_cpu_only(self):
        record = self.observation("ObservedNative", field="DATA0196", value=0x4242)
        record["native_ownership"] = True
        self.native_receipt(record)
        result = validate_evidence_record(record, self.sources)
        self.assertEqual(result["ownership_scope"], "HistoricalSourceCpuOnly")
        self.assertFalse(result["physical_ownership_established"])

    def test_static_fact_needs_selected_bytes_but_not_native_machine(self):
        record = self.observation("StaticRomDerived", value=0x556F, field="PC", path=None)
        result = validate_evidence_record(record, self.sources)
        self.assertEqual(result["classification"], "StaticRomDerived")
        self.assertFalse(result["native_ownership"])

    def test_synthetic_fact_retains_no_native_machine_or_owner(self):
        record = self.observation("SyntheticOnly")
        result = validate_evidence_record(record, self.sources)
        self.assertEqual(result["execution_domain"], "InventedSyntheticOnly")
        self.assertIsNone(result["actual_observation"]["machine_id"])

    def test_private_paths_never_appear_in_matrix(self):
        record = self.observation()
        serialized = json.dumps(build_context_matrix([record], self.sources))
        self.assertNotIn(str(self.directory), serialized)
        self.assertNotIn("private_path", serialized)

    def test_native_label_alone_is_not_observation_authority(self):
        record = self.observation("ObservedNative")
        with self.assertRaisesRegex(ContextError, "separate selected verification receipt"):
            validate_evidence_record(record, self.sources)

    def test_closed_metadata_and_malformed_evidence_refusals(self):
        record = self.observation()
        for mutation in (
            lambda item: item.update(extra=True),
            lambda item: item.pop("source_id"),
            lambda item: item.update(field="NotARegister"),
            lambda item: item.update(classification="NativeBecauseEqual"),
            lambda item: item.update(value=0x43),
            lambda item: item.update(value=True),
            lambda item: item.update(source_id="absent-source"),
            lambda item: item["locators"].update(value="/does-not-exist"),
            lambda item: item["locators"].update(value="/bad~2escape"),
            lambda item: item["locators"].update(value=None),
            lambda item: item["locators"].update(extra="/value"),
            lambda item: item.update(physical_execution=True),
            lambda item: item.update(execution_domain="PhysicalECU"),
        ):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(record)
                mutation(changed)
                with self.assertRaises(ContextError):
                    validate_evidence_record(changed, self.sources)

    def test_synthetic_promotion_false_native_owner_and_transfer_ticket_refused(self):
        record = self.observation("SyntheticOnly")
        record["classification"] = "ObservedNative"
        record["execution_domain"] = "HistoricalSourceCpuOnly"
        with self.assertRaisesRegex(ContextError, "source class promotion"):
            validate_evidence_record(record, self.sources)
        record["classification"] = "SyntheticOnly"
        record["execution_domain"] = "InventedSyntheticOnly"
        record["native_ownership"] = True
        with self.assertRaisesRegex(ContextError, "false native ownership"):
            validate_evidence_record(record, self.sources)
        record["native_ownership"] = False
        record["transfer_ticket"] = "invented-ticket"
        with self.assertRaisesRegex(ContextError, "closed schema"):
            validate_evidence_record(record, self.sources)

    def test_unknown_sf_boolean_fake_stack_and_sfr_assumptions_refused(self):
        record = self.observation("SyntheticOnly")
        for field, value in (("SF", False), ("P2", 0), ("P2", 255),
                             ("NativeStackFrame", 0x07FE), ("RelevantDownstreamSFR", 0),
                             ("InterruptContext", 0), ("PeripheralContext", 0),
                             ("NativeScheduler", 0)):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(record)
                changed.update(field=field, value=value)
                with self.assertRaisesRegex(ContextError, "unresolved SF/stack/peripheral/scheduler"):
                    validate_evidence_record(changed, self.sources)

    def test_technical_ssp_observation_does_not_establish_stack_ownership(self):
        record = self.observation("ObservedNative", value=0x07FE, field="SSP")
        self.native_receipt(record)
        self.assertFalse(validate_evidence_record(record, self.sources)["native_ownership"])
        record["native_ownership"] = True
        with self.assertRaisesRegex(ContextError, "false native ownership"):
            validate_evidence_record(record, self.sources)

    def test_path_c_cannot_be_fabricated_as_historical_native(self):
        record = self.observation("ObservedNative", path="C")
        self.native_receipt(record)
        with self.assertRaisesRegex(ContextError, "no historical native witness"):
            validate_evidence_record(record, self.sources)

    def test_witness_needs_actual_machine_session_and_ordinal_locators(self):
        record = self.observation("ObservedNative")
        self.native_receipt(record)
        for key in ("machine_id", "session_id", "event_ordinal", "pc"):
            changed = copy.deepcopy(record)
            changed["locators"][key] = None
            with self.subTest(key=key), self.assertRaises(ContextError):
                validate_evidence_record(changed, self.sources)

    def test_receipt_cannot_bind_another_observation_or_validator(self):
        record = self.observation("ObservedNative")
        self.native_receipt(record)
        source = self.sources[-1]
        for key, value in (("passed", False), ("model_only", True),
                           ("physical_execution", True), ("independent_expected_comparison", False),
                           ("schema_version", True), ("observed_source_binding", {}),
                           ("validator_source_binding", {}), ("observations", [])):
            changed = copy.deepcopy(source.document)
            changed[key] = value
            other_sources = self.sources[:-1]
            selected = self.select("receipt-mutation", changed, "HistoricalNativeVerificationReceipt")
            changed_record = copy.deepcopy(record)
            changed_record["authority_id"] = selected.source_id
            with self.subTest(key=key), self.assertRaises(ContextError):
                validate_evidence_record(changed_record, other_sources + [selected])

    def test_duplicate_observation_identity_and_duplicate_selected_source_refused(self):
        record = self.observation()
        with self.assertRaisesRegex(ContextError, "duplicate observation"):
            build_context_matrix([record, record], self.sources)
        with self.assertRaisesRegex(ContextError, "duplicate source"):
            build_context_matrix([record], self.sources + self.sources)

    def test_source_identity_json_and_length_checks(self):
        source = self.select("identity-source", {"one": 1}, "HistoricalOfflineModel")
        path = Path(source.private_path)
        for digest, length in (("0" * 64, source.size_bytes), (source.sha256, source.size_bytes + 1)):
            with self.subTest(digest=digest, length=length), self.assertRaises(ContextError):
                select_source(path, "identity-source", digest, length, "HistoricalOfflineModel")
        for encoded in (b'{"x":1,"x":2}', b'{bad', b'{"x":NaN}', b'\xff'):
            path.write_bytes(encoded)
            with self.subTest(payload=encoded), self.assertRaises(ContextError):
                select_source(path, "identity-source", hashlib.sha256(encoded).hexdigest(),
                              len(encoded), "HistoricalOfflineModel")
        with self.assertRaisesRegex(ContextError, "unavailable"):
            select_source(self.directory / "missing.json", "missing", "0" * 64, 1,
                          "HistoricalOfflineModel")

    def journal(self):
        def access(ordinal, kind, pc, address, width, value, write, generation=None):
            return {"ordinal": ordinal, "kind": kind, "pc": pc, "address": address,
                    "width": width, "value": value, "write_ordinal": write,
                    "generation_write_ordinal": generation, "origin": "HistoricalSourceCpuOnly"}
        return {"machine_id": "invented-machine", "session_id": "invented-session",
                "event_ordinal": 3, "complete_event_writes": True, "accesses": [
                    access(0, "write", 0x05DF, 0x0108, 16, 0x0042, 0),
                    access(1, "write", 0x05EB, 0x0196, 16, 0x0042, 1),
                    access(2, "read", 0x54FA, 0x0196, 16, 0x0042, None, 1),
                    access(3, "write", 0x54FC, 0x010A, 16, 0x0042, 2),
                    access(4, "read", 0x5578, 0x0196, 16, 0x0042, None, 1),
                ]}

    def test_data0196_exact_current_generation_reader_pair(self):
        result = verify_data0196_lineage(self.journal())
        self.assertTrue(result["passed"])
        self.assertEqual([read["reader_pc"] for read in result["readers"]], [0x54FA, 0x5578])
        self.assertEqual(len(result["all_native_writes"]), 3)
        self.assertFalse(result["indirect_alias_absence_established"])
        self.assertFalse(result["recovered_scheduler_established"])
        self.assertFalse(result["physical_execution_claimed"])

    def test_same_value_writes_remain_distinct_generations(self):
        journal = self.journal()
        extra = copy.deepcopy(journal["accesses"][1])
        extra.update(ordinal=2, write_ordinal=2)
        journal["accesses"].insert(2, extra)
        for access in journal["accesses"][3:]:
            access["ordinal"] += 1
            if access["write_ordinal"] is not None:
                access["write_ordinal"] += 1
            if access["generation_write_ordinal"] is not None:
                access["generation_write_ordinal"] = 2
        result = verify_data0196_lineage(journal)
        generations = [write for write in result["all_native_writes"] if write["pc"] == 0x05EB]
        self.assertEqual([item["write_ordinal"] for item in generations], [1, 2])
        self.assertEqual([item["value"] for item in generations], [0x42, 0x42])
        self.assertEqual(result["readers"][0]["write_ordinal"], 2)

    def test_stale_equal_generation_and_cross_reader_replacement_refused(self):
        journal = self.journal()
        journal["accesses"][-1]["generation_write_ordinal"] = 0
        with self.assertRaisesRegex(ContextError, "current exact05EB generation"):
            verify_data0196_lineage(journal)
        journal = self.journal()
        extra = copy.deepcopy(journal["accesses"][1])
        extra.update(ordinal=4, write_ordinal=3)
        journal["accesses"].insert(4, extra)
        journal["accesses"][-1].update(ordinal=5, generation_write_ordinal=3)
        with self.assertRaisesRegex(ContextError, "same-generation pair"):
            verify_data0196_lineage(journal)

    def test_overlap_odd_word_alias_host_seed_and_fake_reader_refused(self):
        for address, width, origin in ((0x0197, 8, "HistoricalSourceCpuOnly"),
                                       (0x0197, 16, "HistoricalSourceCpuOnly"),
                                       (0x0196, 16, "HostSeed"),
                                       (0x0196, 16, "InventedSyntheticOnly")):
            journal = self.journal()
            journal["accesses"][1].update(address=address, width=width, origin=origin)
            with self.subTest(address=address, width=width, origin=origin), self.assertRaises(ContextError):
                verify_data0196_lineage(journal)
        for mutation in (
            lambda item: item.update(complete_event_writes=False),
            lambda item: item["accesses"][1].update(write_ordinal=0),
            lambda item: item["accesses"][2].update(address=0x00C0),
            lambda item: item["accesses"][2].update(width=8),
            lambda item: item["accesses"][2].update(ordinal=1),
            lambda item: item["accesses"][2].update(value=0x43),
            lambda item: item["accesses"][2].update(generation_write_ordinal=True),
            lambda item: item["accesses"][2].update(generation_write_ordinal=1.0),
            lambda item: item["accesses"][-1].update(pc=0x5579),
            lambda item: item["accesses"][-1].update(extra="fabricated"),
        ):
            journal = self.journal()
            mutation(journal)
            with self.subTest(mutation=mutation), self.assertRaises(ContextError):
                verify_data0196_lineage(journal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
