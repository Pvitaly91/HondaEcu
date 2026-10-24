"""Static invented oracle/validator tests, NOT actual execution evidence.

The deliberately manufactured report below is explicitly a test-only shape
fixture. It is never returned by a production runner or saved as runtime proof.
"""
from copy import deepcopy
import unittest

from native_entry_continuity import corpus, oracle


def _invented_validator_fixture_not_actual_execution(case):
    expected = oracle.expected_case(case, "public_fixture")
    identity = oracle.public_program_identity()

    def snap(value):
        ram = [0xA5] * 3968
        for address, byte in value["owned_ram"].items():
            ram[int(address) - 128] = byte
        return {"cpu": deepcopy(value["cpu"]), "ram": ram, "ram_range": [128, 4096]}

    logical, raw, spans = oracle._data_expected(case, expected, "public_fixture")
    program_events, steps = [], []
    for index, (step, span) in enumerate(zip(expected["steps"], spans), 1):
        start = len(program_events)
        for offset in range(step["length"]):
            program_events.append({"ordinal": len(program_events), "pc": step["pc"], "address": step["pc"] + offset,
                "segment_offset": step["pc"] + offset - identity["program_base"], "instruction_offset": offset,
                "acquired_purpose": "ArchitecturalSelectedFetch", "selection_association": None,
                "selected_length": step["length"], "serviced": True, "refusal": None})
        steps.append({"index": index, "node_identity": f"ClosedSite_{step['pc']:04X}",
            "full_psw_before": step["before"]["full_psw"], "full_psw_after": step["after"]["full_psw"],
            "before": snap(step["before"]), "after": snap(step["after"]),
            "outcome": {"pc_before": step["pc"], "pc_after": step["next_pc"], "decoded_index": step["decoded_index"],
                "mnemonic": step["mnemonic"], "len": step["length"], "decoded": oracle._decoded(step, "public_fixture"),
                "selected_extent": [step["pc"], step["pc"] + step["length"]],
                "selected_extent_sha256": identity["selected_extent_sha256"][str(step["pc"])], "retired": True, "external_exit": None},
            "program_span": [start, len(program_events)], **span})
    audit = {"entry_pc": 0x6200, "current_pc": expected["stop_before_pc"],
        **{key: identity[key] for key in ("program_base", "program_end_exclusive", "program_sha256")},
        "program_events": program_events, "data_events": logical, "raw_data_events": raw,
        "diagnostic_events": [{"ordinal": i, "kind": "RawRamSnapshot", "range": [128, 4096], "byte_count": 3968}
            for i in range(oracle.diagnostic_snapshot_count(case["budget"]))], "data_admission_refusals": [],
        "permissions": oracle.previous._permissions(expected), "phase": "Sealed", "budget": case["budget"],
        "successful_retirements": case["budget"], "step_calls": case["budget"], "execution_calls": case["budget"],
        "shared_execution_calls": case["budget"], "sealed": True, "terminal_reason": "OriginalStopBeforeReached",
        "external_exit": None, "first_fault": None}
    return {"kind": "entry_continuity_observation", "case_id": case["case_id"], "family": case["family"],
        "internal_sf": case["internal_sf"], "accepted": True, "error": None, "actual_successful_step_returns": case["budget"],
        "report": {"classification": "ExplicitInventedPublicEntryFixture", "source_binding": None,
            "program_node_count": 24, "path": case["path"], "entry": snap(expected["entry"]),
            "current": snap(expected["terminal"]), "full_psw": expected["terminal"]["full_psw"], "steps": steps,
            "completed": True, "stop_before_pc": expected["stop_before_pc"], "audit": audit,
            "positive_completed": expected["positive_completed"], "boundary_only": expected["boundary_only"],
            "actual_handoff_observed": expected["handoff_expected"],
            "native_predecessor_retirements": expected["native_predecessor_retirements"],
            "algorithm_retirements": expected["algorithm_retirements"]}}


class OracleTests(unittest.TestCase):
    def test_all_source_formulas_and_preservation(self):
        for case in corpus.iter_cases():
            untouched = deepcopy(case)
            expected = oracle.expected_case(case)
            self.assertEqual(case, untouched)
            self.assertEqual([step["pc"] for step in expected["steps"][:6]], list(corpus.PREFIX))
            self.assertEqual(expected["steps"][5]["next_pc"], 0x556F)
            self.assertEqual(expected["steps"][2]["after"]["cpu"]["a"], corpus.word0196(case))
            self.assertTrue(expected["steps"][2]["after"]["cpu"]["dd"])
            self.assertTrue(expected["steps"][5]["after"]["cpu"]["dd"])
            self.assertFalse(expected["steps"][6]["after"]["cpu"]["dd"])
            final = expected["terminal"]
            self.assertEqual(final["cpu"]["a"] >> 8, corpus.word0196(case) >> 8)
            self.assertEqual(final["owned_ram"][str(0x0108)], 255)
            self.assertEqual(final["owned_ram"][str(0x010A)] | final["owned_ram"][str(0x010B)] << 8, corpus.word0196(case))
            self.assertEqual(final["full_psw"], case["entry"]["psw"] & 0x2FFF | (0x8000 if case["path"] == "A" else 0))
            self.assertEqual(final["cpu"]["sf"], case["internal_sf"])
            self.assertEqual(final["cpu"]["ssp"], case["entry"]["ssp"])
            self.assertEqual(expected["actual_cpu_executions_by_oracle"], 0)
            self.assertFalse(expected["native_input_ownership"])
            writes = [event for event in expected["ordered_data_events"] if event["operation"] == "Write"]
            self.assertEqual([(event["pc"], event["address"], event["width"]) for event in writes[:2]],
                             [(0x54F8, 0x0108, 8), (0x54FC, 0x010A, 16)])
            self.assertFalse(any(event["operation"] == "Read" and event["address"] == 0x010A for event in expected["ordered_data_events"]))
            if case["path"] == "B":
                self.assertFalse(any(event["address"] == 0x0124 for event in expected["ordered_data_events"]))
            if case["path"] == "A":
                self.assertFalse(next(event for event in writes if event["pc"] == 0x55C1)["same_value"])

    def test_word0196_same_pair_two_reads_and_no_writer(self):
        for case in corpus.iter_cases():
            events = oracle.expected_case(case)["ordered_data_events"]
            reads = [event for event in events if event["address"] == 0x0196]
            self.assertEqual([(event["pc"], event["width"], event["value"]) for event in reads],
                             [(0x54FA, 16, corpus.word0196(case)), (0x5578, 16, corpus.word0196(case))])
            self.assertTrue(all(event["operation"] == "Read" for event in reads))

    def test_branch_controls_stop_without_algorithm_or_peripheral(self):
        first, second = [oracle.expected_case(case) for case in corpus.iter_branch_controls()]
        self.assertEqual((first["instruction_count"], first["stop_before_pc"], first["write_count"]), (1, 0x5533, 0))
        self.assertEqual((second["instruction_count"], second["stop_before_pc"], second["write_count"]), (6, 0x5503, 2))
        self.assertEqual(first["terminal"]["full_psw"], first["entry"]["full_psw"])
        self.assertFalse(first["positive_completed"])
        self.assertFalse(second["positive_completed"])
        self.assertEqual(second["terminal"]["full_psw"] & 0xD000, 0x5000)

    def test_public_identity_is_invented_closed_24_and_payload_free(self):
        identity = oracle.public_program_identity()
        self.assertEqual((identity["program_base"], identity["program_end_exclusive"]), (0x6200, 0x62D0))
        self.assertEqual(len(identity["selected_extent_sha256"]), 24)
        self.assertEqual(identity["source_binding"], None)
        self.assertNotIn("segment_bytes", identity)
        self.assertEqual(identity, oracle.public_program_identity())

    def test_logical_word_and_raw_byte_writer_ordinals(self):
        case = next(corpus.iter_cases())
        expected = oracle.expected_case(case)
        logical, raw, spans = oracle._data_expected(case, expected, "private")
        self.assertEqual(sum(event["phase"] == "Seed" for event in logical), 48)
        store = [event for event in logical if event["phase"] == "Functional" and event["pc"] == 0x54FC]
        self.assertEqual(len(store), 1)
        self.assertEqual((store[0]["width"], store[0]["write_ordinal"]), (16, 49))
        pieces = [event for event in raw if event["logical_ordinal"] == store[0]["ordinal"]]
        self.assertEqual([event["address"] for event in pieces], [0x010A, 0x010B])
        self.assertEqual([event["write_ordinal"] for event in pieces], [81, 82])
        self.assertEqual(len(spans), 16)

    def test_invented_shape_fixtures_are_not_actual_runtime(self):
        for case in [next(corpus.iter_cases()), *corpus.iter_branch_controls()]:
            result = oracle.compare_observation(case, _invented_validator_fixture_not_actual_execution(case), "public_fixture")
            self.assertTrue(result["passed"])
            self.assertEqual(result["comparison"]["positiveCompleted"], case["path"] in ("A", "B", "C", "D"))

    def test_validator_refuses_meaningful_state_and_journal_mutations(self):
        case = next(corpus.iter_cases())
        original = _invented_validator_fixture_not_actual_execution(case)
        mutations = [
            lambda v: v["report"]["steps"][5]["after"]["cpu"].update(pc=0x627B),
            lambda v: v["report"]["steps"][2]["after"]["cpu"].update(dd=False),
            lambda v: v["report"]["steps"][2]["after"]["cpu"].update(a=1),
            lambda v: v["report"]["steps"][3]["after"]["ram"].__setitem__(0x010A - 128, 99),
            lambda v: v["report"]["audit"]["data_events"].pop(),
            lambda v: v["report"]["audit"]["raw_data_events"].reverse(),
            lambda v: v["report"].update(actual_handoff_observed=False),
            lambda v: v["report"].update(positive_completed=False),
            lambda v: v["report"]["current"]["cpu"].update(instructions=17),
            lambda v: v["report"]["audit"].update(successful_retirements=17),
            lambda v: v["report"]["audit"]["program_events"].append(deepcopy(v["report"]["audit"]["program_events"][-1])),
            lambda v: v["report"]["audit"].update(external_exit={"fake": True}),
            lambda v: v["report"].update(native_stack_frame={"invented": True}),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                changed = deepcopy(original)
                mutate(changed)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    oracle.compare_observation(case, changed, "public_fixture")


if __name__ == "__main__":
    unittest.main()
