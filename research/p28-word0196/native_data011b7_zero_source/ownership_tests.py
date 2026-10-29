"""Bounded relation tests against an independently frozen M2cg oracle."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from native_data011b7_zero_source import analysis
from native_data011b7_zero_source.producer_prefix import producer_analysis
from native_data011b7_zero_source.reference_oracle import (
    REASONS,
    curated_controls,
    independent_check,
    reference_case,
    reviewed_case,
)
from native_data011b7_zero_source.route_lineage import route_analysis


class NativeData011B7ZeroSourceTests(unittest.TestCase):
    def compare(self, case, reason=None):
        expected = reference_case(case)
        self.assertEqual(expected["firstMismatch"], reason)
        self.assertEqual(analysis.evaluate_case(case), expected)
        self.assertEqual(expected["valid"], reason is None)
        return expected

    def test_complete_curated_results_match_independent_oracle(self):
        controls = curated_controls()
        self.assertEqual(len(controls), 37)
        self.assertEqual(len({row["caseId"] for row in controls}), 37)
        for row in controls:
            with self.subTest(caseId=row["caseId"]):
                reason = row["caseId"].removeprefix("negative-") if row["caseId"].startswith("negative-") else None
                self.compare(row["input"], reason)
        self.assertEqual(
            [row["caseId"].removeprefix("negative-") for row in controls[6:]],
            list(REASONS),
        )

    def test_six_positive_controls_keep_at_write_and_current_copy_distinct(self):
        for row in curated_controls()[:6]:
            with self.subTest(caseId=row["caseId"]):
                case = row["input"]
                result = self.compare(case)
                self.assertEqual(result["packetChecksum"], 0)
                self.assertEqual(result["flagBit0"], 1)
                self.assertEqual(result["branch2919ConditionalNext"], 0x291B)
                self.assertEqual(result["writerWordValue"], 0)
                self.assertEqual(result["semanticZeroOwner"], "model:" + case["caseId"] + ":CLR291B")
                expected_writer = {"A": 0x291C, "B-serial": 0x0400, "B-int1": 0x5C2D}[case["route"]["kind"]]
                self.assertEqual(result["latestStorageWriterPC"], expected_writer)
                self.assertEqual(result["conditionalReaderSuccessor"], 0x0652)

    def test_clr_word_kills_incoming_dd_without_inventing_native_context(self):
        case = reviewed_case()
        original = self.compare(case)
        for incoming in (0, 1):
            with self.subTest(incomingDD=incoming):
                case["producer"]["incomingDD"] = incoming
                self.assertEqual(self.compare(case), original)
        case["producer"]["ddAfterCLR"] = 0
        self.compare(case, "WrongDD")

    def test_command21_cut_is_independent_of_checksum_acceptance(self):
        for header in (0x20, 0x30):
            with self.subTest(header=header):
                case = reviewed_case()
                case["source"]["reads"][0]["value"] = header
                case["source"]["reads"][3]["value"] = (-(header + 4 + 1)) % 256
                self.compare(case, "Command21PredicateNotSatisfied")

    def test_even_flag_and_startup_zero_do_not_reach_clr(self):
        for flag in (0, 2, 0x80, 0xFE):
            with self.subTest(flag=flag):
                self.compare(reviewed_case(flag=flag), "CurrentFlagBit0BypassesCLR")

    def test_four_read_packet_requires_actual_arithmetic_relation(self):
        case = reviewed_case()
        case["source"]["reads"][3]["value"] ^= 1
        self.compare(case, "PacketChecksumNotAccepted")
        case = reviewed_case()
        case["source"]["reads"][1]["value"] = 3
        case["source"]["reads"][3]["value"] = (-(0x21 + 3 + 1)) % 256
        self.compare(case, "Length3CannotWriteFlagAt0269")

    def test_read_and_invocation_identities_cannot_be_reused(self):
        for field in ("readId", "invocation"):
            with self.subTest(field=field):
                case = reviewed_case()
                case["source"]["reads"][2][field] = case["source"]["reads"][0][field]
                self.compare(case, "PacketReadIdentityReused")

    def test_mode0356_bit1_is_a_separate_required_unknown_owner(self):
        case = reviewed_case()
        case["handler"]["mode0356Bit1"] = 0
        self.compare(case, "ParserModeGateNotSatisfied")
        case = reviewed_case()
        case["handler"]["actualModeOwner"] = "fabricated:mode-owner"
        self.compare(case, "FalseOriginalRomExecution")

    def test_source_irq_factor_is_not_the_reader_input_irqh_gate(self):
        case = reviewed_case(route="B-int1")
        self.assertEqual(case["handler"]["irqWordBit"], 1)
        self.assertEqual(case["reader"]["irqH1WordBit"], 9)
        case["reader"]["irqH1WordBit"] = case["handler"]["irqWordBit"]
        self.compare(case, "SourceIrqBit1IsNotInputGateBit9")
        case = reviewed_case(route="B-int1")
        case["reader"]["oldIrqH1"] = 1
        self.compare(case, "SourceIrqBit1IsNotInputGateBit9")

    def test_second_read_requires_its_own_observation(self):
        case = reviewed_case()
        case["producer"]["read2966Token"] = case["producer"]["read2917Token"]
        self.compare(case, "Later2966ReadBorrowed2917")
        case = reviewed_case()
        case["producer"]["read2966ActualValue"] = 1
        self.compare(case, "Later2966ReadBorrowed2917")

    def test_unknown_alias_stays_unknown_without_a_fabricated_write(self):
        case = reviewed_case(route="B-serial")
        case["route"]["unknownAlias"] = True
        result = self.compare(case)
        self.assertEqual(result["preservation"], "UnresolvedAlias")
        self.assertIsNone(result["readerBit7"])
        self.assertIsNone(result["conditionalReaderSuccessor"])
        self.assertIsNone(result["latestStorageWriterPC"])
        self.assertIsNone(result["latestStorageGeneration"])
        self.assertEqual(result["writerWordValue"], 0)
        case["route"]["claimedActualOverwrite"] = True
        self.compare(case, "UnknownAliasIsNotActualOverwrite")

    def test_direct_generation_is_replaced_by_the_selected_receiver_copy(self):
        case = reviewed_case()
        case["route"]["directBeforeReceiverCopy"] = True
        self.compare(case, "DirectGenerationDominatedByReceiverCopy")

    def test_011f_gate_and_caller_history_are_separate_from_012a_value(self):
        case = reviewed_case()
        case["history"]["data012AValue"] = 0
        case["reader"]["gate011F3"] = None
        self.compare(case, "MissingIndependent011F3Gate")
        case = reviewed_case()
        case["history"]["caller"] = "model:different-history"
        self.compare(case, "UncorrelatedCallerHistory")

    def test_refusal_never_supplies_a_conditional_runtime_result(self):
        for row in curated_controls()[6:]:
            with self.subTest(caseId=row["caseId"]):
                result = reference_case(row["input"])
                for field in ("packetChecksum", "flagBit0", "branch2919ConditionalNext",
                              "writerWordValue", "semanticZeroOwner", "latestStorageWriterPC",
                              "latestStorageGeneration", "readerBit7", "conditionalReaderSuccessor"):
                    self.assertIsNone(result[field])
                self.assertEqual(result["writerAddresses"], [])

    def test_actual_event_authority_is_never_created_by_a_static_fixture(self):
        for row in curated_controls():
            with self.subTest(caseId=row["caseId"]):
                result = reference_case(row["input"])
                self.assertEqual(result["actualCpuExecutions"], 0)
                self.assertEqual(result["actualOriginalRomExecutions"], 0)
                self.assertEqual(result["actualIRQDeliveries"], 0)
                self.assertTrue(all(value is None for value in result["actualSourceOwners"].values()))
                self.assertIsNone(result["actualMachineId"])
                self.assertIsNone(result["actualNativeInstructionIndex"])
                self.assertIsNone(result["actualWriterOrdinal"])
                self.assertFalse(result["actualBranch064FExecuted"])
                self.assertFalse(result["firmwareReady"])
                self.assertEqual(result["runtimeAdmission"], "Blocked")

    def test_static_source_projections_match_independent_literals(self):
        result = independent_check(producer_analysis(), route_analysis())
        self.assertTrue(result["valid"], result["firstMismatch"])
        self.assertGreaterEqual(result["comparedFactCount"], 100)

    def test_independent_literal_check_rejects_semantic_mutations(self):
        producer, route = producer_analysis(), route_analysis()
        mutations = (
            ("producer", ("standardSource", "address"), 0x03F3),
            ("producer", ("handlerContext", "standardIrqWordBit"), 9),
            ("producer", ("parserContext", "requiredSCB"), 2),
            ("producer", ("predicate", "branchTarget"), 0x291B),
            ("producer", ("packetConstraints", "readOrder"), [0x0277] * 4),
            ("producer", ("zero", "DD"), 0),
            ("producer", ("zero", "stores", 0, "widthBits"), 8),
            ("producer", ("zero", "stores", 0, "footprint"), [0x011A]),
            ("producer", ("zero", "sameValueStoreCreatesFreshGeneration"), False),
            ("producer", ("actualNative", "actualCpuExecutions"), 1),
            ("route", ("zeroInt1Gate", "wordBit"), 1),
            ("route", ("second03F3Read", "canBorrow2917ReadValueOrGeneration"), True),
            ("route", ("postZero", "c8PrimaryConflictResolved"), True),
            ("route", ("firmwareReady",), True),
        )
        for target, path, replacement in mutations:
            with self.subTest(target=target, path=path):
                mutated_producer, mutated_route = deepcopy(producer), deepcopy(route)
                document = mutated_producer if target == "producer" else mutated_route
                for key in path[:-1]:
                    document = document[key]
                document[path[-1]] = replacement
                self.assertFalse(independent_check(mutated_producer, mutated_route)["valid"])

    def test_malformed_case_refuses_without_supplying_owner_or_values(self):
        self.compare({}, "ClosedCaseShapeRequired")
        case = reviewed_case()
        del case["history"]["frame"]
        self.compare(case, "ClosedCaseShapeRequired")


if __name__ == "__main__":
    unittest.main()
