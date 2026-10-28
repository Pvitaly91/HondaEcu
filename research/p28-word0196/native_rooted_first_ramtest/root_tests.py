"""Small invented relation corpus, independent of any CPU execution results."""

import unittest

from .analysis import canonical, canonical_records, evaluate_case, root_frontier
from .frame_obligations import frame_analysis
from .gate_sources import gate_analysis
from .reference_oracle import REASONS, curated_controls, independent_check, validate_integrated_case


class RootedFirstRamtestTests(unittest.TestCase):
    def test_independent_reviewed_static_obligations(self):
        comparison = independent_check(gate_analysis(), frame_analysis())
        self.assertEqual(comparison["independentOracle"], "PASS")
        self.assertIsNone(comparison["firstMismatch"])
        self.assertEqual(comparison["runtimeAdmission"], "Blocked")

    def test_all_curated_relations_match_independent_reference(self):
        controls = curated_controls()
        self.assertEqual(len(controls), 39)
        self.assertEqual(len({c["caseId"] for c in controls}), len(controls))
        for index, row in enumerate(controls):
            with self.subTest(case=row["caseId"]):
                actual = evaluate_case(row["input"])
                expected = validate_integrated_case(row["input"])
                self.assertEqual(canonical(actual), canonical(expected))
                self.assertEqual(actual["valid"], index == 0)
                self.assertEqual(actual["firstMissingObligation"], None if index == 0 else REASONS[index - 1])
                self.assertEqual(actual["actualCpuExecutions"], 0)
                self.assertEqual(actual["actualRomExecutions"], 0)
                self.assertIsNone(actual["actualMachineId"])
                self.assertIsNone(actual["actualInstructionIndex"])
                self.assertIsNone(actual["actualWriteOrdinal"])
                self.assertFalse(actual["firmwareReady"])

    def test_canonical_keeps_every_input_and_unknown(self):
        records = canonical_records()
        self.assertEqual(len(records), 43)
        controls = records[4:]
        self.assertEqual([r["caseId"] for r in controls], [r["caseId"] for r in curated_controls()])
        positive = controls[0]["data"]["input"]
        for key in ("hardwareSafe", "readback"):
            self.assertIsNone(positive["wdt"][key])
        self.assertIsNone(positive["external"]["readCompletion"])
        self.assertIsNone(positive["external"]["sideEffects"])
        for row in controls:
            self.assertIn("input", row["data"])
            self.assertEqual(row["data"]["independentComparison"], "PASS")
            self.assertEqual(row["actualCpuExecutions"], 0)
            self.assertEqual(row["actualOriginalRomExecutions"], 0)

    def test_final_dp_must_retain_unknown_old_word(self):
        frame = frame_analysis()
        frame["terminalProjection"]["dp"]["value"] = 0x268C
        with self.assertRaisesRegex(ValueError, "retained-unknown-dp"):
            independent_check(gate_analysis(), frame)

    def test_rt_cannot_read_interrupted_original_generation(self):
        frame = frame_analysis()
        cal = next(r for r in frame["symbolicChronology"] if r["action"] == "ConditionalFrameStore")
        reader = next(r for r in frame["symbolicChronology"] if r["action"] == "ConditionalRead_NotWriteGeneration")
        reader["sourceToken"] = cal["outputToken"]
        with self.assertRaisesRegex(ValueError, "rt-reads-current-restored-generation"):
            independent_check(gate_analysis(), frame)

    def test_pwm0_cannot_supply_enabled_irq_under_reviewed_configuration(self):
        gates = gate_analysis()
        gates["freshIrq"]["enabledStandardFactorSource"] = "PWM0OrPWM1Overflow"
        with self.assertRaisesRegex(ValueError, "pwm-source-refinement"):
            independent_check(gates, frame_analysis())

    def test_static_projection_rejects_fabricated_native_observation(self):
        frame = frame_analysis()
        frame["instructionInventory"][0]["actualInstructionIndex"] = 1
        with self.assertRaisesRegex(ValueError, "actualInstructionIndex"):
            independent_check(gate_analysis(), frame)

    def test_logical_pswh_flags_do_not_supply_known_halfcarry(self):
        frame = frame_analysis()
        frame["terminalProjection"]["hc"] = 0
        with self.assertRaisesRegex(ValueError, "terminal.hc"):
            independent_check(gate_analysis(), frame)

    def test_admission_dependencies_remain_ordered_and_unobserved(self):
        frontier = root_frontier()
        preceding = set()
        for condition in frontier["admissionDag"]:
            self.assertTrue(set(condition["dependsOn"]).issubset(preceding))
            self.assertNotIn(condition["conditionId"], preceding)
            self.assertFalse(condition["actuallyObserved"])
            self.assertTrue(condition["source"])
            self.assertTrue(condition["missingOwnerOrEvent"])
            preceding.add(condition["conditionId"])
        self.assertEqual(frontier["firstMissingObligation"], "ApplicableResetTransition")
        self.assertEqual(frontier["OriginalRomExecutionAdmission"], "Blocked")
        self.assertTrue(frontier["nearestFutureSlice"]["entryMustBeReachedThroughSameRootHistory"])
        self.assertFalse(frontier["nearestFutureSlice"]["hostEntryBypassesRootAllowed"])
        self.assertFalse(frontier["nearestFutureSlice"]["admittedNow"])
        self.assertIsNone(frontier["standardReset"]["physicalSf"])
        self.assertIsNone(frontier["actualMachineId"])
        self.assertEqual(frontier["actualCpuExecutions"], 0)
        self.assertFalse(frontier["firmwareReady"])


if __name__ == "__main__":
    unittest.main()
