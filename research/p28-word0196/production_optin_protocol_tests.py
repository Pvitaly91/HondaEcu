"""Pure pre-runtime M2bp protocol tests; no compiler, Cpu or Bus invocation.

These tests establish generator/schema/comparator obligations only. They never
claim that expected records are actual observations. Runtime evidence is the
separate validator's frozen-expectation versus actual compiled-output gate.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

import production_exec_parity_corpus as historical
import production_optin_corpus as corpus
import production_optin_oracle as oracle
import production_optin_capability_oracle as capabilities


ROOT = Path(__file__).resolve().parents[2]
LOGICAL_KEYS = {"ordinal", "phase", "pc", "instruction_index", "address", "width",
                "operation", "requested_value", "value", "old_value", "write_ordinal",
                "same_value", "serviced", "refusal"}
RAW_KEYS = {"ordinal", "logical_ordinal", "address", "operation", "requested_value",
            "value", "old_value", "write_ordinal", "same_value", "serviced", "refusal"}
PROGRAM_KEYS = {"ordinal", "pc", "address", "segment_offset", "instruction_offset",
                "acquired_purpose", "selection_association", "selected_length",
                "serviced", "refusal"}


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Both calls are independent pure source calculations, not execution.
        cls.rows = corpus.build_corpus()
        cls.patterns = oracle.instrumentation.load_instrumentation_patterns(ROOT)
        cls.capability_expected = capabilities.expected_capabilities(cls.rows, cls.patterns)

    def test_original_468_inputs_are_exactly_retained(self):
        original = [row["request"] for row in self.rows[:468]]
        self.assertEqual(original, historical.build_corpus())
        digest = sha256(b"".join(corpus.canonical(row) + b"\n" for row in original)).hexdigest()
        self.assertEqual(digest, "0d185fb533a9503ff88eee381d7617f7e1548aba06aa9d306d2afca90b1ff091")
        self.assertEqual(len(self.rows), 552)
        self.assertEqual(len({row["request"]["case_id"] for row in self.rows}), 552)
        self.assertEqual(sum(row["expected_admission"] == "Accepted" for row in self.rows), 468)
        self.assertEqual(sum(bool(row["denied_effects"]) for row in self.rows[:468]), 84)

    def test_supplemental_controls_are_new_explicit_data_predicates_only(self):
        originals = {row["request"]["case_id"]: row for row in self.rows[:468]}
        changed_data_addresses = {str(0x196), str(0x197), str(0x12a), str(0x124)}
        for row in self.rows[468:]:
            original = originals[row["source_case_id"]]
            self.assertTrue(original["denied_effects"])
            self.assertEqual(row["source_family"], "NewExplicitPredicateCompatibleControl")
            self.assertEqual(row["profile"], "D")
            self.assertEqual(corpus.derived_profile(row["request"]), "D")
            self.assertEqual(corpus.independent_incompatibility(row["request"]), [])
            left, right = deepcopy(original["request"]), deepcopy(row["request"])
            for value in (left, right):
                value.pop("case_id")
                value.pop("family")
                for address in changed_data_addresses:
                    value["data"].pop(address)
            self.assertEqual(left, right)

    def test_all_51_independent_historical_literals_reproduce(self):
        self.assertIsNone(oracle.reproduce_historical_literals())

    def test_closed_profiles_preserve_independent_direction_and_width(self):
        for row in self.rows:
            self.assertEqual(row["profile"], corpus.derived_profile(row["request"]))
            permission = oracle.permissions(row["profile"], row["request"]["form"])
            reads = {(item["address"], item["width"]) for item in permission["reads"]}
            writes = {(item["access"]["address"], item["access"]["width"])
                      for item in permission["writes"]}
            self.assertIn((0x196, 16), reads)
            self.assertNotIn((0x196, 8), reads)
            self.assertNotIn((0x196, 8), writes)
            self.assertNotIn((0x197, 8), writes)
            self.assertNotIn(0x196, permission["raw_writes"])
            self.assertNotIn(0x197, permission["raw_writes"])
            if row["profile"] == "B":
                self.assertNotIn((0x124, 8), reads)
            if row["profile"] != "D":
                self.assertNotIn((0x12a, 8), writes)

    def test_substantive_and_metadata_mutations_are_separate(self):
        mutations = corpus.admission_mutations(self.rows)
        self.assertEqual(len(mutations), 25)
        self.assertEqual(len({row["id"] for row in mutations}), 25)
        self.assertEqual(sum(row["metadata_only"] for row in mutations), 2)
        self.assertEqual(sum(not row["metadata_only"] for row in mutations), 23)
        for mutation in mutations:
            record = mutation["expected"]
            self.assertEqual(record["kind"], "admission_refusal")
            self.assertIs(record["accepted"], False)
            self.assertEqual(record["actual_step_calls"], 0)
            self.assertEqual(record["cpu_instances"], 0)
            self.assertEqual(record["bus_instances"], 0)

    def test_capability_inventory_and_all_event_keys_are_closed(self):
        records = self.capability_expected["records"]
        self.assertEqual(tuple(row["id"] for row in records), capabilities.CAPABILITY_IDS)
        self.assertEqual(len(records), 35)
        constructors = [row for row in records if row["classification"] == capabilities.CONSTRUCTOR_CLASSIFICATION]
        sessions = [row for row in records if row["classification"] == capabilities.CLASSIFICATION]
        self.assertEqual(len(constructors), 8)
        self.assertEqual(len(sessions), 27)
        for row in sessions:
            for name in ("before", "after"):
                self.assertEqual(row[name]["ram_range"], [128, 4096])
                self.assertEqual(len(row[name]["ram"]), 3968)
                self.assertEqual(set(row[name]["cpu"]), {"pc", "a", "ssp", "lrb", "zf", "cf", "hc", "dd",
                                                       "sf", "psw_other", "cycles", "instructions", "halted"})
            audit = row["audit"]
            for name, keys in (("data_events", LOGICAL_KEYS), ("raw_data_events", RAW_KEYS),
                               ("program_events", PROGRAM_KEYS)):
                self.assertEqual([event["ordinal"] for event in audit[name]], list(range(len(audit[name]))))
                for event in audit[name]:
                    self.assertEqual(set(event), keys)
            for event in audit["raw_data_events"]:
                parent = audit["data_events"][event["logical_ordinal"]]
                self.assertEqual(event["operation"], parent["operation"])
                self.assertIn(event["address"], range(parent["address"], parent["address"] + parent["width"] // 8))
            refusals = audit["data_admission_refusals"]
            if row["id"] == "data-write-after-seal":
                self.assertEqual(len(refusals), 1)
                refusal = refusals[0]
                self.assertEqual(refusal["classification"], "PreBusApiAdmissionRefusal")
                self.assertIs(refusal["production_bus_called"], False)
                self.assertIs(refusal["serviced"], False)
                self.assertEqual(refusal["pc"], row["after"]["cpu"]["pc"])
                self.assertEqual((refusal["address"], refusal["width"], refusal["operation"],
                                  refusal["requested_value"]), (0x117, 8, "Write", 0x55))
            else:
                self.assertEqual(refusals, [])

    def test_capability_counters_are_derived_from_records_not_status_labels(self):
        records = self.capability_expected["records"]
        sessions = [row for row in records if "audit" in row]
        self.assertEqual(sum(row["cpu_instances"] for row in records), 27)
        self.assertEqual(sum(row["bus_instances"] for row in records), 27)
        self.assertEqual(sum(row["audit"]["step_calls"] for row in sessions), 10)
        self.assertEqual(sum(row["audit"]["shared_execution_calls"] for row in sessions), 4)
        self.assertEqual(sum(row["audit"]["successful_retirements"] for row in sessions), 3)
        # Expected-only calculations above do not make these actual observations.
        self.assertEqual(self.capability_expected["full_production_composite_executions"], 0)
        self.assertEqual(self.capability_expected["original_rom_executions"], 0)

    def test_partial_word_failure_preserves_only_serviced_low_byte(self):
        row = next(item for item in self.capability_expected["records"]
                   if item["id"] == "word-high-write-refused-partial-low")
        before, after = row["before"]["ram"], row["after"]["ram"]
        self.assertEqual(after[0x108 - 128], 0xef)
        self.assertEqual(after[0x109 - 128], before[0x109 - 128])
        changed = [i for i, (left, right) in enumerate(zip(before, after)) if left != right]
        self.assertEqual(changed, [0x108 - 128])
        logical = row["audit"]["data_events"][-1]
        low, high = row["audit"]["raw_data_events"][-2:]
        self.assertIs(logical["serviced"], False)
        self.assertIsNone(logical["write_ordinal"])
        self.assertIs(low["serviced"], True)
        self.assertIsInstance(low["write_ordinal"], int)
        self.assertIs(high["serviced"], False)
        self.assertEqual(high["refusal"]["code"], "RawWriteDenied")
        self.assertEqual(row["audit"]["successful_retirements"], 0)

    def test_two_same_value_writes_have_fresh_distinct_ordinals(self):
        row = next(item for item in self.capability_expected["records"]
                   if item["id"] == "same-value-fresh-store-ordinals")
        logical = row["audit"]["data_events"][-2:]
        raw = row["audit"]["raw_data_events"][-2:]
        for pair in (logical, raw):
            self.assertTrue(all(event["operation"] == "Write" and event["same_value"] is True for event in pair))
            self.assertEqual(pair[1]["write_ordinal"], pair[0]["write_ordinal"] + 1)
        self.assertEqual(row["before"]["ram"], row["after"]["ram"])

    def test_comparator_rejects_types_keys_order_and_every_declared_leaf(self):
        # This invented schema sample is not an execution observation.
        sample = {"flag": False, "count": 0, "unknown": None,
                  "events": [{"address": 0x196, "width": 16, "serviced": True},
                             {"address": 0x197, "width": 8, "serviced": False}],
                  "ram": [0, 1, 255]}
        self.assertIsNone(oracle.difference(sample, deepcopy(sample)))
        changes = []
        changed = deepcopy(sample)
        changed["flag"] = 0
        changes.append(changed)
        changed = deepcopy(sample)
        changed["events"].reverse()
        changes.append(changed)
        changed = deepcopy(sample)
        changed["events"][0]["extra"] = "not-admitted"
        changes.append(changed)
        changed = deepcopy(sample)
        changed["events"][0].pop("width")
        changes.append(changed)
        changed = deepcopy(sample)
        changed["ram"].pop()
        changes.append(changed)
        changed = deepcopy(sample)
        changed["unknown"] = "invented"
        changes.append(changed)
        for changed in changes:
            with self.subTest(changed=changed):
                self.assertIsNotNone(oracle.difference(sample, changed))


if __name__ == "__main__":
    unittest.main()
