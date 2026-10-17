"""M2bo pre-runtime tests of independent expectations, never CPU observations."""

from collections import Counter
from copy import deepcopy
import json
import io
import re
import unittest

import production_exec_parity_corpus as corpus
import production_exec_parity_oracle as oracle


class IndependentOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = corpus.build_corpus()
        cls.base = corpus.build_base_contexts()
        cls.expected = [oracle.expected_case(row) for row in cls.cases]

    def test_historical_source_hashes_are_exact(self):
        self.assertEqual(len(oracle.source_bindings()), 10)

    def test_original_51_literals_reproduced_without_cpu(self):
        self.assertIsNone(oracle.reproduce_sealed_literals())
        self.assertEqual(len(corpus.sealed_cases()), 51)

    def test_finite_family_and_unique_identity_counts(self):
        self.assertEqual(len(self.base), 234)
        self.assertEqual(len(self.cases), 468)
        self.assertEqual(len({row["case_id"] for row in self.cases}), 468)
        self.assertEqual(Counter(row["family"] for row in self.base), Counter(corpus.FAMILY_COUNTS))

    def test_every_context_has_two_independently_initialized_sf_variants(self):
        for index in range(0, len(self.cases), 2):
            false, true = deepcopy(self.cases[index]), deepcopy(self.cases[index + 1])
            self.assertFalse(false.pop("internal_sf"))
            self.assertTrue(true.pop("internal_sf"))
            false.pop("case_id")
            true.pop("case_id")
            self.assertEqual(false, true)
            self.assertEqual(false["entry"]["sf"], corpus.UNKNOWN_SF)

    def test_all_16_forms_have_all_flags_and_scb_selectors(self):
        rows = [row for row in self.base if row["family"] == "flags-scb"]
        self.assertEqual(set(oracle.FORM_IDENTITIES), {row["form"] for row in rows})
        for form in oracle.FORM_IDENTITIES:
            subset = [row for row in rows if row["form"] == form]
            self.assertEqual(len(subset), 8)
            self.assertEqual({row["entry"]["scb"] for row in subset}, set(range(8)))
            self.assertEqual({(row["entry"]["cf"], row["entry"]["zf"], row["entry"]["hc"])
                              for row in subset},
                             {(bool(flags & 1), bool(flags & 2), bool(flags & 4)) for flags in range(8)})
            self.assertEqual({row["entry"]["dd"] for row in subset},
                             {False} if form in corpus.DD_ZERO_FORMS else {False, True})
            for bit in (9, 8, 5, 4):
                self.assertEqual({bool(row["entry"]["other_psw"] & (1 << bit)) for row in subset},
                                 {False, True})

    def test_meaningful_five_byte_edge_inputs_for_ten_forms(self):
        rows = [row for row in self.base if row["family"] == "byte-edges"]
        data_addresses = {"lb-a-page": 0x117, "rolb-page": 0x18E,
                          "lb-a-r0": 0x108, "andb-a-page": 0x117,
                          "movb-r1-page": 0x117, "andb-page-a": 0x117,
                          "orb-page-imm8": 0x12A}
        for form in corpus.BYTE_EDGE_FORMS:
            subset = [row for row in rows if row["form"] == form]
            values = {row["data"][str(data_addresses[form])] if form in data_addresses
                      else row["entry"]["al"] for row in subset}
            self.assertEqual(values, set(corpus.BYTE_EDGES))

    def test_word_boundaries_do_not_change_sealed_cmp_immediate(self):
        rows = [row for row in self.base if row["family"] == "cmp-word-boundaries"]
        self.assertEqual({row["data"][str(0x196)] + 256 * row["data"][str(0x197)] for row in rows},
                         set(corpus.WORD_EDGES))
        self.assertEqual({tuple(row["bytes"]) for row in rows}, {(0xB4, 0x96, 0xC0, 0x35, 0x12)})
        self.assertEqual({oracle.expected_decode(row)["n16"] for row in rows}, {0x1235})

    def test_representable_psw_domain_is_not_silently_normalized(self):
        counts = Counter(corpus.is_representable(value) for value in range(65536))
        self.assertEqual(counts, {True: 2048, False: 63488})
        for row in self.cases:
            self.assertTrue(corpus.is_representable(row["entry"]["psw"]))

    def test_exact_instruction_and_guards_remain_sealed(self):
        fixtures = {row["id"]: row for row in corpus.sealed_cases()}
        for row in self.base:
            literal = fixtures[row["fixture_id"]]
            self.assertEqual(row["bytes"], [int(byte, 16) for byte in literal["bytesHex"]])
            self.assertEqual(len(row["bytes"]) + len(row["guards"]), 6)
            self.assertIsNone(oracle.validate_request(row))

    def test_decoded_identity_matches_frozen_source_rows_not_runtime(self):
        # This verifies a table/source identity, not primary instruction meaning.
        source = (corpus.HERE.parents[1] / "rust/p28-slice-runner/src/full_decoder.rs").read_text(encoding="utf-8")
        pattern = r'OpcodePattern\s*\{\s*mnemonic:\s*"([^"\n]+)",\s*dd_mode:\s*\x27([01RUS])\x27,\s*bytes_pat:\s*&\[([^\]]*)\]\s*\}'
        rows = [(mnemonic, dd, re.findall(r'"([^"\n]*)"', code))
                for mnemonic, dd, code in re.findall(pattern, source)]
        self.assertEqual(len(rows), 2623)
        for request in self.base:
            decoded = oracle.expected_decode(request)
            mnemonic, dd, tokens = rows[decoded["index"]]
            self.assertEqual(mnemonic, decoded["mnemonic"])
            self.assertEqual(len(tokens), decoded["len"])
            self.assertEqual(dd == "R", decoded["dd_after_option"] is False)
            fields = {name: 0 for name in ("n8", "n8_alt", "n16", "n16_alt", "s8", "addr16", "rel8")}
            for token, value in zip(tokens, request["bytes"]):
                if re.fullmatch(r"[0-9A-F]{2}", token):
                    self.assertEqual(int(token, 16), value)
                elif token in ("N8", "N'8"):
                    fields["n8" if token == "N8" else "n8_alt"] = value
                elif token in ("NL", "NH", "addrl", "addrh"):
                    field = "n16" if token in ("NL", "NH") else "addr16"
                    fields[field] |= value << (8 if token in ("NH", "addrh") else 0)
                elif token == "rel8":
                    fields["rel8"] = value if value < 128 else value - 256
                else:
                    self.fail("UnexpectedFrozenFormOperand:" + token)
            self.assertEqual(fields, {name: decoded[name] for name in fields})

    def test_full_ram_and_all_retained_context_are_compared(self):
        for request, expected in zip(self.cases, self.expected):
            result = oracle.reference_effect(request)
            changed = {int(write[0], 16) for write in result["writes"]}
            self.assertEqual(len(expected["before_ram"]), 3968)
            self.assertEqual(len(expected["after_ram"]), 3968)
            for index, (before, after) in enumerate(zip(expected["before_ram"], expected["after_ram"])):
                if index + 128 not in changed:
                    self.assertEqual(before, after)
            for key in ("ah", "hc", "other_psw", "lrb", "scb", "ssp", "pointing_banks", "halted", "sf"):
                self.assertEqual(expected["before"][key], expected["after"][key])
            self.assertEqual(expected["cpu_after"]["instructions"], 1)
            self.assertEqual(expected["cpu_after"]["cycles"], result["cycles"])
            self.assertEqual(expected["internal_sf_before"], expected["internal_sf_after"])

    def test_taken_not_taken_carry_and_same_value_controls_remain(self):
        for form in ("jlt-rel8", "jbs-page-bit7", "jbs-page-bit5"):
            self.assertEqual({result["branch_taken"] for result in self.expected if result["form"] == form},
                             {False, True})
        rol = [oracle.reference_effect(row) for row in self.base if row["form"] == "rolb-page"]
        self.assertTrue(any(row["before"]["cf"] and row["writes"][0][2] == "81" for row in rol))
        self.assertTrue(any(not row["before"]["cf"] and row["writes"][0][2] == "00" for row in rol))
        same = {row["form"] for row in self.base
                if any(write[-1] for write in oracle.reference_effect(row)["writes"])}
        self.assertTrue({"rolb-page", "movb-r1-page", "andb-page-a", "orb-page-imm8", "stb-a-page"} <= same)

    def test_no_hidden_journal_or_full_composite_claim(self):
        for result in self.expected:
            self.assertEqual(result["observation_capabilities"], oracle.CAPABILITIES)
            self.assertEqual(result["production_bus_composite_integration"], "NotEstablished")
            self.assertEqual(result["production_composite_executions"], 0)
            self.assertEqual(result["original_rom_executions"], 0)
            self.assertFalse(result["firmware_ready"])
            self.assertEqual(result["production_program_data_reads"], [])

    def test_strict_comparator_sensitivity_is_not_a_runtime_observation(self):
        expected = self.expected[0]
        mutations = [
            ("after", "a"), ("after", "ah"), ("after", "cf"), ("after", "zf"),
            ("after", "hc"), ("after", "dd"), ("after", "pc"),
            ("after", "ssp"), ("after", "lrb"), ("after", "other_psw"),
            ("cpu_after", "cycles"), ("cpu_after", "instructions"),
            ("cpu_after", "psw_other"), ("cpu_after", "sf"),
            ("decode", "index"), ("decode", "n8"), ("decode", "n16_alt"),
            ("decode", "s8"), ("decode", "cycles"),
        ]
        for section, field in mutations:
            actual = deepcopy(expected)
            old = actual[section][field]
            actual[section][field] = not old if type(old) is bool else old + 1
            mismatch = oracle.compare(expected, actual)
            self.assertIsNotNone(mismatch)
            self.assertEqual(mismatch["field"], f"$.{section}.{field}")
        for key in ("before_ram", "after_ram"):
            actual = deepcopy(expected)
            actual[key][-1] ^= 1
            self.assertIsNotNone(oracle.compare(expected, actual))
        actual = deepcopy(expected)
        actual["after"]["pointing_banks"][7]["usp"] ^= 1
        self.assertIsNotNone(oracle.compare(expected, actual))
        actual = deepcopy(expected)
        actual["after"]["local_er"][0] ^= 256
        self.assertIsNotNone(oracle.compare(expected, actual))
        actual = deepcopy(expected)
        actual["observation_capabilities"]["ordered_data_journal"] = "InferredButFalselyObserved"
        self.assertIsNotNone(oracle.compare(expected, actual))
        actual = deepcopy(expected)
        actual["production_bus_composite_integration"] = "Verified"
        self.assertIsNotNone(oracle.compare(expected, actual))
        actual = deepcopy(expected)
        actual["step_calls"] = 0
        self.assertIsNotNone(oracle.compare(expected, actual))
        self.assertIsNone(oracle.compare(expected, deepcopy(expected)))

    def test_admission_mutations_refuse_before_any_cpu(self):
        mutations = [
            lambda row: row.update(form="invented-form"),
            lambda row: row["bytes"].pop(),
            lambda row: row["bytes"].__setitem__(1, row["bytes"][1] ^ 1),
            lambda row: row["entry"].update(al=0),
            lambda row: row["entry"].update(psw=0),
            lambda row: row["entry"]["local_r"].__setitem__(0, 0),
            lambda row: row.update(physical_entry_pc=4096),
            lambda row: row.update(budget=16),
            lambda row: row.update(expected_length=5),
            lambda row: row.update(expected_decoded_index=748),
        ]
        for mutate in mutations:
            request = deepcopy(self.cases[0])
            mutate(request)
            with self.assertRaises(ValueError):
                oracle.validate_request(request)
        request = deepcopy(next(row for row in self.cases if row["form"] == "sllb-a"))
        corpus.own_aliases(request["entry"], request["data"], psw=request["entry"]["psw"] | 0x1000)
        with self.assertRaisesRegex(ValueError, "DdMismatch"):
            oracle.validate_request(request)

    def test_two_capability_expectations_are_separate_failed_steps(self):
        mapping, partial = oracle.expected_capabilities(self.cases[0])
        for result in (mapping, partial):
            self.assertFalse(result["positive_parity_case"])
            self.assertEqual(result["successful_step_calls"], 0)
            self.assertEqual(result["failed_step_calls"], 1)
            self.assertEqual(result["successful_instruction_retirements"], 0)
            self.assertEqual(result["before_ram"], result["after_ram"])
            self.assertFalse(result["actual_decoder_returned"])
            self.assertFalse(result["atomic_refusal_claimed"])
            self.assertEqual(result["program"]["prefix_padding_bytes"], 0)
            self.assertFalse(result["program"]["is_m2bj_composite"])
        self.assertEqual(mapping["before"], mapping["after"])
        self.assertEqual(mapping["cpu_before"], mapping["cpu_after"])
        self.assertEqual(mapping["instruction_counter_delta"], 0)
        self.assertEqual([row["value"] for row in mapping["public_peeks"]], [165, 165, None, None])
        self.assertEqual(partial["before"]["pc"], 0)
        self.assertEqual(partial["after"]["pc"], 2)
        self.assertEqual(partial["after"]["a"], 0xA500)
        self.assertTrue(partial["after"]["dd"])
        self.assertEqual(partial["after"]["local_er"], [0x37A1, 0, 0xFCCB, 0xA500])
        self.assertEqual(partial["cpu_after"]["cycles"], 4)
        self.assertEqual(partial["instruction_counter_delta"], 1)

    def test_frozen_negative_generators_are_finite_and_meaningful(self):
        mutations = oracle.admission_mutations(self.cases)
        self.assertEqual(len(mutations), 24)
        self.assertEqual(len({item["id"] for item in mutations}), 24)
        for item in mutations:
            with self.assertRaises(ValueError):
                oracle.validate_request(item["request"])
            if item["id"] in ("wrong-opcode", "wrong-operand", "wrong-guard"):
                from hashlib import sha256
                row = item["request"]
                self.assertEqual(row["content_digest"], sha256(bytes(row["bytes"] + row["guards"])).hexdigest())
        # A model-only comparator unit test. These are NOT CPU observations and
        # do not replace root's required mutations of real runtime records.
        checked = oracle.semantic_mutations(self.cases[0], deepcopy(self.expected[0]))
        self.assertGreaterEqual(len(checked), 100)
        self.assertLessEqual(len(checked), 140)
        self.assertTrue(all(row["firstMismatch"] is not None for row in checked))


def static_checks():
    """Run this entire independent suite; no production Cpu exists here."""
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentOracleTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.expectedFailures or result.unexpectedSuccesses:
        raise AssertionError("IndependentPreRuntimeOracleTestsFailed:" + stream.getvalue())
    return {"passed": True, "tests": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "skipped": len(result.skipped),
            "productionExecCalls": 0, "cpuInstances": 0,
            "sealedLiteralContextsReproduced": 51, "firstMismatch": None,
            "coverage": corpus.coverage(), "sourceBindings": oracle.source_bindings(),
            "scope": "IndependentPreRuntimeReferenceOnly", "details": stream.getvalue()}


if __name__ == "__main__":
    unittest.main()
