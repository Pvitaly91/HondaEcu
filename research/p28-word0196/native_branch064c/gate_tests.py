"""Invented-only M2ca static semantic/refusal checks.

These tests cannot provide original-ROM execution or production CPU refusals.
The33 requirement categories explicitly separate metadata/provenance refusals
from mutations of fabricated static expected traces. No old result is replaced.
"""
from copy import deepcopy
import unittest

from .gate_model import (
    INVENTED, STATIC, StaticReviewRefusal, build_review_envelope,
    primary_expected_trace, validate_review_envelope,
)
from .gate_reference_oracle import reference_outcome


def vector(route, *, psw=0xB5A7, neighbors=0xA4):
    neighbors &= 0xF6
    values = {
        "A": (0xAD, 0x00, neighbors | 8),
        "B": (0xA5, 0x80, neighbors),
        "C": (0xA5, 0x00, neighbors),
        "D": (0xA5, 0x00, neighbors | 1),
    }
    f, b, a = values[route]
    return {"classification": INVENTED, "case_id": "invented-m2ca-" + route.lower(),
        "gate_bytes": {"011F": f, "011B": b, "012A": a},
        "retained": {"a": 0xC35A, "psw": psw, "lrb": 0x0021, "scb": psw & 7,
            "ssp": 0x07FE, "pointing": [0x1357, 0x2468, 0x369A, 0xABCD],
            "local_r": [0, 0x55, 0xAA, 0xFF, 0x31, 0x72, 0xA3, 0xB4]}}


def _step(envelope, pc):
    return next(row for row in envelope["expected_trace"]["expected_steps"] if row["pc"] == pc)


def negative_fixtures():
    """Yield33 invented mutations; labels state the actual scope of each proof."""
    def item(number, requirement, kind, change, route="A"):
        value = build_review_envelope(vector(route))
        change(value)
        return {"id": number, "requirement": requirement, "proof_kind": kind, "mutated": value}

    metadata = "InventedMetadataRefusal_NotOriginalRomAdmissionProof"
    provenance = "StaticSourceAuthorityRefusal_NotCpuExecution"
    trace = "FabricatedStaticExpectedTraceComparator_NotObservedCpuTrace"
    fixtures = [
        item(1, "Wrong original-ROM SHA.", metadata,
             lambda x: x["expected_bindings"]["rom"].update(sha256="0" * 64)),
        item(2, "Modified original branch opcode.", metadata,
             lambda x: x["instruction_contract"][0].update(form="JBR off011F.3,rel8")),
        item(3, "Wrong source fingerprint.", metadata,
             lambda x: x["expected_bindings"]["source"].update(sha256="0" * 64)),
        item(4, "Direct host entry064C.", provenance,
             lambda x: x["runtime_authority"].update(entry_mode="HostSetPC064C")),
        item(5, "Host branch selector.", provenance, lambda x: x.update(host_branch_selector="A")),
        item(6, "Artificial DATA011F.3.", provenance,
             lambda x: x["source_admission"]["sources"]["011F"].update(new_seed_allowed=True)),
        item(7, "Artificial DATA011B.7.", provenance,
             lambda x: x["source_admission"]["sources"]["011B"].update(new_seed_allowed=True)),
        item(8, "Artificial DATA012A.0/.3.", provenance,
             lambda x: x["source_admission"]["new_source_inputs"].append("initial012A.0_or_3")),
        item(9, "Historical M2ag source imported as current.", provenance,
             lambda x: x["source_admission"]["historical_source_transfers"].append("M2agGeneration")),
        item(10, "Unowned A5 promoted to native owner.", provenance,
             lambda x: x["source_admission"]["sources"]["011F"].update(classification="NativeCurrentSessionWriterEstablished")),
        item(11, "Wrong branch predicate.", trace,
             lambda x: _step(x, 0x064C).update(branch_taken=False)),
        item(12, "Wrong successor PC.", trace,
             lambda x: _step(x, 0x064C)["after"].update(pc=0x0652)),
        item(13, "Wrong exact budget.", trace,
             lambda x: x["expected_trace"].update(expected_full_route_retirements=53)),
        item(14, "Wrong JBS source address.", trace,
             lambda x: _step(x, 0x064C)["expected_reads"][0].update(address=0x011B)),
        item(15, "Incorrect bit mask.", metadata,
             lambda x: x["instruction_contract"][0].update(bit=2)),
        item(16, "Wrong DD interpretation.", trace,
             lambda x: _step(x, 0x064C)["after"].update(psw=_step(x, 0x064C)["after"]["psw"] ^ 0x1000)),
        item(17, "Incorrect RB ZF.", trace,
             lambda x: _step(x, 0x065F)["after"].update(psw=_step(x, 0x065F)["after"]["psw"] ^ 0x4000)),
        item(18, "JNE uses cleared bit instead of actual ZF.", trace,
             lambda x: _step(x, 0x0662)["after"].update(pc=0x0664)),
        item(19, "DATA012A neighbor corruption.", trace,
             lambda x: _step(x, 0x065F)["expected_writes"][0].update(value=_step(x, 0x065F)["expected_writes"][0]["value"] ^ 0x20)),
        item(20, "Unexpected DATA013C write.", trace,
             lambda x: _step(x, 0x064C)["expected_writes"].append({"address": 0x013C, "value": 0})),
        item(21, "Stale selector generation.", metadata,
             lambda x: x["retained_selector_identity"].update(generation=0)),
        item(22, "Stale CAL/RT frame.", metadata,
             lambda x: x["retained_frame_identity"].update(consumed_before_gates=False)),
        item(23, "Second CPU/Bus.", provenance,
             lambda x: x["runtime_authority"].update(cpu_instances=2, bus_instances=2)),
        item(24, "Host reseed after063B.", provenance,
             lambda x: x["runtime_authority"]["host_reseed_events"].append({"pc": 0x063B, "address": 0x011F})),
        item(25, "Execute0657.", trace,
             lambda x: x["expected_trace"]["excluded_instruction_retirements"].append(0x0657)),
        item(26, "Execute0664.", trace,
             lambda x: x["expected_trace"]["excluded_instruction_retirements"].append(0x0664)),
        item(27, "Execute0667.", trace,
             lambda x: x["expected_trace"]["excluded_instruction_retirements"].append(0x0667)),
        item(28, "Fake CAL0664 frame.", metadata,
             lambda x: x["retained_frame_identity"].update(writer_pc=0x0664, return_pc=0x0667)),
        item(29, "Fake producer56BE entry.", provenance,
             lambda x: x["runtime_authority"].update(producer56be_entries=1)),
        item(30, "Fabricated TMR2/IRQH observations.", provenance,
             lambda x: x["runtime_authority"]["observed_peripherals"].append({"tmr2": 1, "irqh": 1})),
        item(31, "New source accepted silently.", provenance,
             lambda x: x["source_admission"].update(new_source_field=0)),
        item(32, "Duplicate completed case after resume.", metadata,
             lambda x: x["analysis_case_ids"].append(x["analysis_case_ids"][0])),
        item(33, "Protected Cargo target collision.", metadata,
             lambda x: x["cargo_authority"].update(owned_target_token="HistoricalProtectedRunnerTarget")),
    ]
    return fixtures


class InventedGateSemanticsTests(unittest.TestCase):
    def test_four_independently_derived_routes_and_exact_conditional_budgets(self):
        specifications = {
            "A": ([0x064C, 0x065F, 0x0662], 0x0667, 52),
            "B": ([0x064C, 0x064F, 0x065F, 0x0662], 0x0664, 53),
            "C": ([0x064C, 0x064F, 0x0652, 0x0655, 0x065F, 0x0662], 0x0664, 55),
            "D": ([0x064C, 0x064F, 0x0652, 0x0655], 0x0657, 53),
        }
        for route, (sequence, terminal, budget) in specifications.items():
            with self.subTest(route=route):
                case = vector(route)
                actual_model, independent = primary_expected_trace(case), reference_outcome(case)
                self.assertEqual(actual_model, independent)
                self.assertEqual(actual_model["expected_pc_sequence"], sequence)
                self.assertEqual(actual_model["expected_terminal_pc"], terminal)
                self.assertEqual(actual_model["expected_full_route_retirements"], budget)
                self.assertEqual(actual_model["cpu_executions"], 0)
                self.assertFalse(actual_model["original_rom_route_admitted"])

    def test_full_psw_and_register_preservation_at_every_expected_boundary(self):
        for route in "ABCD":
            for high_flags in range(16):
                psw = (high_flags << 12) | 0x05A7
                case = vector(route, psw=psw)
                with self.subTest(route=route, psw=psw):
                    result = primary_expected_trace(case)
                    self.assertEqual(result, reference_outcome(case))
                    for step in result["expected_steps"]:
                        before, after = step["before"], step["after"]
                        retained_mask = 0xBFFF if step["pc"] in (0x0652, 0x065F) else 0xFFFF
                        self.assertEqual(before["psw"] & retained_mask, after["psw"] & retained_mask)
                        for key in ("a", "lrb", "scb", "ssp", "pointing", "local_r"):
                            self.assertEqual(before[key], after[key])

    def test_rb_old_bit_zf_same_value_writes_and_neighbors_are_independent(self):
        for route in "ABCD":
            for neighbor_pattern in (0, 0x24, 0xA4, 0xF6):
                case = vector(route, neighbors=neighbor_pattern)
                with self.subTest(route=route, neighbors=neighbor_pattern):
                    result = primary_expected_trace(case)
                    self.assertEqual(result, reference_outcome(case))
                    for step in result["expected_steps"]:
                        if step["pc"] not in (0x0652, 0x065F):
                            continue
                        bit = 0 if step["pc"] == 0x0652 else 3
                        old, new = step["before"]["data"]["012A"], step["after"]["data"]["012A"]
                        self.assertEqual(bool(step["after"]["psw"] & 0x4000), not bool(old & (1 << bit)))
                        self.assertEqual(new, old & ~(1 << bit))
                        self.assertEqual((old ^ new) & ~(1 << bit), 0)
                        self.assertEqual(len(step["expected_writes"]), 1)
                        self.assertEqual(step["expected_writes"][0]["same_value"], old == new)
        taken = primary_expected_trace(vector("A"))
        self.assertEqual(taken["expected_final_state"]["data"]["012A"] & 8, 0)
        self.assertEqual(taken["expected_terminal_pc"], 0x0667)
        self.assertFalse(next(step for step in taken["expected_steps"] if step["pc"] == 0x065F)["after"]["psw"] & 0x4000)

    def test_suppressed_reads_exact_stop_before_and_no_original_route_admission(self):
        a = primary_expected_trace(vector("A"))
        b = primary_expected_trace(vector("B"))
        self.assertFalse(any(step["pc"] == 0x064F for step in a["expected_steps"]))
        self.assertFalse(any(step["pc"] == 0x0652 for step in b["expected_steps"]))
        for route in "ABCD":
            envelope = build_review_envelope(vector(route))
            self.assertTrue(validate_review_envelope(envelope)["passed"])
            self.assertEqual(envelope["classification"], STATIC)
            self.assertEqual(envelope["source_admission"]["original_rom_routes_admitted"], [])
            self.assertEqual(envelope["source_admission"]["first_blocked_reader_pc"], 0x064C)
            self.assertEqual(envelope["expected_trace"]["excluded_instruction_retirements"], [])
            self.assertFalse(any(step["pc"] in (0x0657, 0x0664, 0x0667)
                for step in envelope["expected_trace"]["expected_steps"]))

    def test_all33_named_negative_categories_refuse_without_runtime_authority(self):
        cases = negative_fixtures()
        self.assertEqual([row["id"] for row in cases], list(range(1, 34)))
        self.assertEqual(len({row["requirement"] for row in cases}), 33)
        for row in cases:
            with self.subTest(requirement=row["id"], proof_kind=row["proof_kind"]):
                with self.assertRaises(StaticReviewRefusal):
                    validate_review_envelope(row["mutated"])

    def test_no_silent_unknown_inputs_or_outside_conditional_route_promotion(self):
        case = vector("A")
        case["gate_bytes"]["012A"] &= ~8
        with self.assertRaises(StaticReviewRefusal):
            primary_expected_trace(case)
        with self.assertRaises(ValueError):
            reference_outcome(case)
        bad = vector("A")
        bad["gate_bytes"]["013C"] = 0
        with self.assertRaises(StaticReviewRefusal):
            primary_expected_trace(bad)
        unknown = deepcopy(vector("A"))
        unknown["native_generation"] = "fabricated"
        with self.assertRaises(StaticReviewRefusal):
            primary_expected_trace(unknown)
        # Python's loose equality equates True/1 and False/0. The contract
        # comparator must preserve the declared type at every nested boundary.
        type_forgeries = [
            lambda e: e.update(schemaVersion=True),
            lambda e: e["runtime_authority"].update(cpu_instances=False),
            lambda e: e["runtime_authority"].update(firmware_ready=0),
            lambda e: e["source_admission"]["sources"]["011F"].update(new_seed_allowed=0),
            lambda e: _step(e, 0x064C).update(expected_index=True),
            lambda e: e["retained_frame_identity"].update(unknown_nested_key="ignored"),
        ]
        for index, forge in enumerate(type_forgeries):
            with self.subTest(strict_nested_type=index):
                envelope = build_review_envelope(vector("A"))
                forge(envelope)
                with self.assertRaises(StaticReviewRefusal):
                    validate_review_envelope(envelope)


if __name__ == "__main__":
    unittest.main()
