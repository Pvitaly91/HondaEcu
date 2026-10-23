"""Invented fixtures only: comparator sensitivity, not execution observations."""

from copy import deepcopy
import unittest

from . import corpus, oracle


def invented_observation(case):
    """Manufactured public DTO solely to test validation; never CPU evidence."""
    expected = oracle.expected_case(case, "public_fixture")
    identity = oracle.public_program_identity()
    logical, raw, spans = oracle._data_expected(case, expected, "public_fixture")

    def snapshot(source):
        ram = [0xA5] * 3968
        for address, value in source["owned_ram"].items():
            ram[int(address) - 128] = value
        return {"cpu": deepcopy(source["cpu"]), "ram": ram, "ram_range": [128, 4096]}

    steps, program = [], []
    for index, source in enumerate(expected["steps"]):
        start = len(program)
        for purpose in ("DecoderProbe", "ArchitecturalSelectedFetch"):
            for address in range(source["pc"], source["pc"] + source["length"]):
                program.append({"ordinal": len(program), "pc": source["pc"], "address": address,
                                "segment_offset": address - identity["program_base"],
                                "instruction_offset": address - source["pc"],
                                "acquired_purpose": purpose,
                                "selection_association": "SelectedExtent" if purpose == "DecoderProbe" else None,
                                "selected_length": source["length"], "serviced": True, "refusal": None})
        outcome = {"pc_before": source["pc"], "pc_after": source["next_pc"],
                   "decoded_index": source["decoded_index"], "mnemonic": source["mnemonic"],
                   "len": source["length"], "decoded": oracle._decoded(source, "public_fixture"),
                   "selected_extent": [source["pc"], source["pc"] + source["length"]],
                   "selected_extent_sha256": identity["selected_extent_sha256"][str(source["pc"])],
                   "retired": True, "external_exit": None}
        steps.append({"index": index + 1, "node_identity": f"ClosedSite_{source['pc']:04X}",
                      "full_psw_before": source["before"]["full_psw"],
                      "full_psw_after": source["after"]["full_psw"],
                      "before": snapshot(source["before"]), "after": snapshot(source["after"]),
                      "outcome": outcome, "program_span": [start, len(program)], **spans[index]})
    count = case["budget"]
    audit = {"entry_pc": expected["entry"]["cpu"]["pc"], "current_pc": expected["stop_before_pc"],
             **{key: identity[key] for key in ("program_base", "program_end_exclusive", "program_sha256")},
             "program_events": program, "data_events": logical, "raw_data_events": raw,
             "diagnostic_events": [{"ordinal": i, "kind": "RawRamSnapshot", "range": [128, 4096], "byte_count": 3968}
                                   for i in range(2 * count + 2)],
             "data_admission_refusals": [], "permissions": oracle._permissions(expected),
             "phase": "Sealed", "budget": count, "successful_retirements": count,
             "step_calls": count, "execution_calls": count, "shared_execution_calls": count,
             "sealed": True, "terminal_reason": "OriginalStopBeforeReached", "external_exit": None, "first_fault": None}
    return {"kind": "original_rom_observation", "case_id": case["case_id"], "family": case["family"],
            "internal_sf": case["internal_sf"], "accepted": True, "error": None,
            "actual_successful_step_returns": count,
            "report": {"classification": "ExplicitInventedPublicFixture", "source_binding": None,
                       "program_node_count": 18, "path": case["path"],
                       "entry": snapshot(expected["entry"]), "current": snapshot(expected["terminal"]),
                       "full_psw": expected["terminal"]["full_psw"], "steps": steps, "completed": True,
                       "stop_before_pc": expected["stop_before_pc"], "audit": audit}}


class OracleTests(unittest.TestCase):
    def test_closed_corpus(self):
        cases = list(corpus.iter_cases())
        self.assertEqual(len(cases), 64)
        self.assertEqual(len({case["case_id"] for case in cases}), 64)
        summary = corpus.coverage_summary()
        self.assertEqual(summary["expectedRetirements"], 798)
        self.assertEqual(summary["expectedLogicalReads"], 570)
        self.assertEqual(summary["expectedWrites"], 228)
        self.assertEqual(summary["scbSelectors"], list(range(8)))
        self.assertEqual(summary["wordBoundaries"], [0, 191, 192, 193, 255, 256, 65535])
        self.assertEqual(summary["distinctOtherPswValues"], 16)
        self.assertFalse(summary["all2048RepresentablePswValuesExecuted"])

    def test_all_representable_psw_values_are_classified_without_cpu(self):
        represented = [value for value in range(65536) if corpus.is_representable(value)]
        self.assertEqual(len(represented), 2048)
        for value in (False, -1, 65536, "4040"):
            with self.assertRaises(ValueError):
                corpus.is_representable(value)

    def test_complete_independent_math_and_pairs(self):
        for case in corpus.iter_cases():
            with self.subTest(case=case["case_id"]):
                result = oracle.expected_case(case)
                data, initial = case["data"], case["entry"]
                below = (data["406"] | data["407"] << 8) < 192
                rotated = ((data["398"] << 1) & 255) | (data["398"] >> 7)
                mask = rotated & data["264"]
                final18f = 15 if below else data["399"] & mask if case["path"] == "D" else data["399"]
                self.assertEqual(result["terminal"]["cpu"]["a"], (initial["ah"] << 8) | (15 if below else final18f | 240))
                self.assertEqual(result["terminal"]["full_psw"], (initial["psw"] & 0x2FFF) | (0x8000 if below else 0))
                self.assertEqual(result["terminal"]["cpu"]["ssp"], initial["ssp"])
                self.assertEqual(result["terminal"]["cpu"]["instructions"], corpus.PATH_COUNTS[case["path"]][0])
                self.assertEqual(result["write_count"], corpus.PATH_COUNTS[case["path"]][2])
                self.assertEqual(result["logical_read_count"], corpus.PATH_COUNTS[case["path"]][1])
                self.assertEqual(result["terminal"]["owned_ram"]["398"], rotated)
                self.assertFalse(result["native_input_ownership"])
                self.assertEqual(result["actual_cpu_executions_by_oracle"], 0)
                self.assertTrue(oracle.compare_observation(case, invented_observation(case), "public_fixture")["passed"])

    def test_wire_mapping_is_explicit_and_inputs_unchanged(self):
        case = next(corpus.iter_cases())
        original = deepcopy(case)
        private, public = corpus.wire_case(case), corpus.wire_case(case, "public_fixture")
        self.assertEqual(len(private), 8)
        self.assertEqual(private["entry"]["pc"], 0x556F)
        self.assertEqual(public["entry"]["pc"], 0x6000)
        self.assertEqual(public["data"][str(0x19A)], private["data"][str(0x196)])
        self.assertNotIn(str(0x196), public["data"])
        self.assertEqual(public["entry"]["provenance"], "TechnicalSeeded_NoNativeGenerationOwner")
        self.assertEqual(case, original)

    def test_public_identity_independent_typed_encoder(self):
        identity = oracle.public_program_identity()
        self.assertEqual(identity["program_sha256"], "0b5381000436361a0de90ee4cd705bec5a36cb600d966fdadf5073546bedac0e")
        self.assertEqual(len(identity["selected_extent_sha256"]), 18)
        self.assertIsNone(identity["source_binding"])

    def test_original_jlt_delta_not_synthetic_delta(self):
        result = oracle.expected_case(next(corpus.iter_cases()))
        row = next(step for step in result["steps"] if step["native_site_identity"] == "557D")
        self.assertEqual(row["next_pc"] - row["pc"] - row["length"], 64)
        self.assertEqual(oracle._decoded(row, "private")["rel8"], 64)
        self.assertNotIn("j-address", [step["form"] for step in result["steps"]])

    def test_first_gate_suppresses_second_read(self):
        cases = [case for case in corpus.iter_cases() if case["family"] == "short-circuit-b" and not case["internal_sf"]]
        left, right = [oracle.expected_case(case) for case in cases]
        self.assertEqual(left["terminal"], right["terminal"] | {"owned_ram": left["terminal"]["owned_ram"]})
        self.assertTrue(all(row["address"] != 0x124 for row in left["ordered_data_events"]))

    def test_meaningful_observation_mutations_are_refused(self):
        case = next(case for case in corpus.iter_cases() if case["path"] == "D")
        actual = invented_observation(case)
        mutations = [
            ("intermediate-carry", lambda a: a["report"]["steps"][1]["after"]["cpu"].__setitem__(
                "cf", not a["report"]["steps"][1]["after"]["cpu"]["cf"])),
            ("intermediate-zf", lambda a: a["report"]["steps"][0]["after"]["cpu"].__setitem__("zf", True)),
            ("full-psw", lambda a: a["report"]["steps"][0].__setitem__("full_psw_after", 0)),
            ("ah", lambda a: a["report"]["current"]["cpu"].__setitem__("a", 0)),
            ("retained-hc", lambda a: a["report"]["current"]["cpu"].__setitem__("hc", True)),
            ("retained-ssp", lambda a: a["report"]["current"]["cpu"].__setitem__("ssp", 0)),
            ("pointing-bank", lambda a: a["report"]["current"]["ram"].__setitem__(0, 0)),
            ("ambient-write", lambda a: a["report"]["current"]["ram"].__setitem__(1000, 0)),
            ("lost-local-alias", lambda a: a["report"]["current"]["ram"].__setitem__(0x108-128, 123)),
            ("wrong-pc", lambda a: a["report"]["steps"][0]["outcome"].__setitem__("pc_after", 0)),
            ("wrong-form", lambda a: a["report"]["steps"][0]["outcome"].__setitem__("decoded_index", 1)),
            ("synthetic-rel8", lambda a: a["report"]["steps"][6]["outcome"]["decoded"].__setitem__("rel8", 26)),
            ("wrong-dd", lambda a: a["report"]["steps"][0]["after"]["cpu"].__setitem__("dd", True)),
            ("sf-owner", lambda a: a["report"]["current"]["cpu"].__setitem__("sf", not case["internal_sf"])),
            ("fake-direct-j", lambda a: a["report"].__setitem__("stop_before_pc", 0x5596)),
            ("extra-retirement", lambda a: a["report"]["audit"].__setitem__("successful_retirements", 16)),
            ("missing-step", lambda a: a["report"]["steps"].pop()),
            ("extra-read", lambda a: a["report"]["audit"]["data_events"].append(deepcopy(a["report"]["audit"]["data_events"][-1]))),
            ("missing-write", lambda a: a["report"]["audit"]["data_events"].pop()),
            ("write-order", lambda a: a["report"]["audit"]["data_events"].reverse()),
            ("raw-overlap", lambda a: a["report"]["audit"]["raw_data_events"][80].__setitem__("address", 0x128)),
            ("missing-program", lambda a: a["report"]["audit"]["program_events"].pop()),
            ("program-unserviced", lambda a: a["report"]["audit"]["program_events"][0].__setitem__("serviced", False)),
            ("program-data-confusion", lambda a: a["report"]["audit"]["program_events"][0].__setitem__("address", 0x192)),
            ("fake-native-promotion", lambda a: a["report"].__setitem__("classification", corpus.MODE)),
            ("reseed", lambda a: a["report"]["audit"]["data_events"][48].__setitem__("phase", "Seed")),
            ("permissive-right", lambda a: a["report"]["audit"]["permissions"]["raw_reads"].append(0x128)),
            ("unexpected-field", lambda a: a["report"].__setitem__("native_owner", True)),
            ("selected-hash", lambda a: a["report"]["steps"][0]["outcome"].__setitem__("selected_extent_sha256", "0"*64)),
            ("fake-handoff", lambda a: a["report"]["audit"].__setitem__("external_exit", 0x6027)),
        ]
        self.assertEqual(len(mutations), 30)
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                changed = deepcopy(actual)
                mutate(changed)
                with self.assertRaises(ValueError):
                    oracle.compare_observation(case, changed, "public_fixture")

    def test_case_authority_and_type_mutations_refused(self):
        base = next(corpus.iter_cases())
        mutations = [lambda c: c.__setitem__("native_input_claimed", True),
                     lambda c: c["entry"].__setitem__("sf", False),
                     lambda c: c["entry"].__setitem__("psw", c["entry"]["psw"] & ~8),
                     lambda c: c["entry"].__setitem__("local_er", [0]*4),
                     lambda c: c.__setitem__("budget", 11),
                     lambda c: c["data"].__setitem__("406", True)]
        for mutate in mutations:
            case = deepcopy(base)
            mutate(case)
            with self.assertRaises(ValueError):
                oracle.expected_case(case)


if __name__ == "__main__":
    unittest.main()
