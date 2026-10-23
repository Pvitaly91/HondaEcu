"""Closed declaration mutations and invented source rows; no CPU/ROM input."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from original_rom_execution import contract_validation as validation


def invented_bindings():
    by_name = {name: {"path": name, "mode": "100644", "bytes": 1, "sha256": "a" * 64}
               for name in validation.REQUIRED_CURRENT_PATHS}
    for frozen in validation.FROZEN_INPUTS:
        by_name[frozen["path"]] = {"mode": "100644", **frozen}
    index = 0
    while len(by_name) < 934:
        name = f"invented/source-{index:04d}.py"
        by_name[name] = {"path": name, "mode": "100644", "bytes": 0, "sha256": "b" * 64}
        index += 1
    return [by_name[name] for name in sorted(by_name)]


class ContractValidationTests(unittest.TestCase):
    def setUp(self):
        self.contract = validation.load_contract()

    def mutation(self, section, name, value):
        changed = deepcopy(self.contract)
        changed[section][name] = value
        with self.assertRaisesRegex(ValueError, "ReviewedClosedProtocolDeclarationChanged"):
            validation.validate_contract(changed)

    def test_closed_declaration_and_actual_mathematical_corpus(self):
        result = validation.validate_contract()
        self.assertTrue(result["passed"])
        self.assertEqual(result["publicCasesSpecifiedAndMathematicallyChecked"], 64)
        self.assertEqual(result["privateCasesSpecified"], 70)
        self.assertEqual(result["originalSites"], 18)
        self.assertEqual(result["pathInstructionCounts"], {"A": 10, "B": 12, "C": 13, "D": 15})
        self.assertFalse(result["sourceBindingsVerified"])
        self.assertFalse(result["privateHistoricalCompletionsVerifiedByThisFunction"])
        self.assertFalse(result["preservationExceptionAuthorizedByThisContract"])
        self.assertEqual(result["actualCpuExecutions"], 0)

    def test_supplied_complete_source_join_bound(self):
        rows = invented_bindings()
        result = validation.validate_contract(source_bindings=rows)
        self.assertTrue(result["sourceBindingsVerified"])
        self.assertEqual(result["sourceBindingCount"], 934)
        self.assertEqual(result["sourceFingerprintSha256"], sha256(validation.canonical(rows)[:-1]).hexdigest())

    def test_source_fingerprint_matches_unchanged_raw_git_join_protocol(self):
        from original_rom_execution import source_guard
        rows = invented_bindings()
        result = validation.validate_contract(source_bindings=rows)
        self.assertEqual(result["sourceFingerprintSha256"], sha256(source_guard.canonical(rows)).hexdigest())

    def test_private_case_count_mutation_refused(self):
        self.mutation("corpus", "privateCases", 64)

    def test_public_case_count_mutation_refused(self):
        self.mutation("corpus", "publicCases", 63)

    def test_entry_pc_mutation_refused(self):
        self.mutation("program", "entryPc", 0x1000)

    def test_stop_boundary_mutation_refused(self):
        self.mutation("program", "stopBeforePcs", [0x5597, 0x55C5])

    def test_selected_site_removed_refused(self):
        self.mutation("program", "algorithmPcs", self.contract["program"]["algorithmPcs"][:-1])

    def test_terminal_execution_promotion_refused(self):
        self.mutation("program", "terminalInstructionsRetired", 1)

    def test_p2_access_promotion_refused(self):
        self.mutation("program", "p2FunctionalReads", 1)

    def test_path_budget_mutation_refused(self):
        self.mutation("paths", "A", {**self.contract["paths"]["A"], "retirements": 11})

    def test_native_context_promotion_refused(self):
        self.mutation("modes", "nativeInputOwnership", True)

    def test_physical_sf_promotion_refused(self):
        self.mutation("entry", "physicalSf", "KnownFalse")

    def test_seed_after_execution_promotion_refused(self):
        self.mutation("entry", "seedAfterExecution", True)

    def test_default_feature_promotion_refused(self):
        self.mutation("delivery", "featureDefaultOff", False)

    def test_contract_not_preservation_authority(self):
        self.mutation("delivery", "contractCreatesRuntimeOrPreservationAuthority", True)

    def test_raw_mismatch_concealment_refused(self):
        self.mutation("delivery", "rawPreservationMismatchMustRemainReported", False)

    def test_ordinary_accepted_verdict_refused(self):
        self.mutation("delivery", "successfulVerdictWithException", "M2bt ACCEPTED")

    def test_private_fixture_substitution_refused(self):
        self.mutation("publicFixture", "containsOriginalRomBytes", True)

    def test_unknown_contract_field_refused(self):
        self.contract["automaticPromotion"] = True
        with self.assertRaisesRegex(ValueError, "ReviewedClosedProtocolDeclarationChanged"):
            validation.validate_contract(self.contract)

    def test_small_join_refused(self):
        with self.assertRaisesRegex(ValueError, "CompleteActiveSourceJoinRequired"):
            validation.validate_contract(source_bindings=invented_bindings()[:-1])

    def test_duplicate_join_path_refused(self):
        rows = invented_bindings()
        rows[-1] = rows[0]
        with self.assertRaisesRegex(ValueError, "DuplicateSourceBindingPath"):
            validation.validate_contract(source_bindings=rows)

    def test_unordered_join_refused(self):
        with self.assertRaisesRegex(ValueError, "OrderedSourceBindingsRequired"):
            validation.validate_contract(source_bindings=list(reversed(invented_bindings())))

    def test_unknown_join_field_refused(self):
        rows = invented_bindings()
        rows[0]["authority"] = "native"
        with self.assertRaisesRegex(ValueError, "ClosedSourceBindingRow"):
            validation.validate_contract(source_bindings=rows)

    def test_missing_execution_dependency_refused(self):
        rows = invented_bindings()
        target = validation.PACKAGE + "oracle.py"
        rows = [row for row in rows if row["path"] != target]
        rows.append({"path": "invented/replacement.py", "mode": "100644", "bytes": 1, "sha256": "c" * 64})
        rows.sort(key=lambda row: row["path"])
        with self.assertRaisesRegex(ValueError, "RequiredExecutionSourceBindingMissing"):
            validation.validate_contract(source_bindings=rows)

    def test_frozen_independent_source_identity_refused(self):
        rows = invented_bindings()
        next(row for row in rows if row["path"] == validation.FROZEN_INPUTS[0]["path"])["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "FrozenIndependentSourceIdentityChanged"):
            validation.validate_contract(source_bindings=rows)

    def test_private_path_refused(self):
        rows = invented_bindings()
        rows[0]["path"] = "private/forbidden.json"
        with self.assertRaisesRegex(ValueError, "CanonicalSourceBindingPath"):
            validation.validate_contract(source_bindings=rows)

    def test_only_three_frozen_one_lf_private_directory_placeholders_allowed(self):
        rows = invented_bindings()
        for name in sorted(validation.FROZEN_DIRECTORY_PLACEHOLDERS):
            rows.append({"path": name, "mode": "100644", "bytes": 1,
                         "sha256": sha256(b"\n").hexdigest()})
        rows.sort(key=lambda row: row["path"])
        self.assertTrue(validation.validate_contract(source_bindings=rows)["sourceBindingsVerified"])
        rows[next(i for i, row in enumerate(rows) if row["path"] in validation.FROZEN_DIRECTORY_PLACEHOLDERS)]["bytes"] = 2
        with self.assertRaisesRegex(ValueError, "CanonicalSourceBindingPath"):
            validation.validate_contract(source_bindings=rows)

    def test_boolean_byte_count_refused(self):
        rows = invented_bindings()
        rows[0]["bytes"] = True
        with self.assertRaisesRegex(ValueError, "SourceBindingDomain"):
            validation.validate_contract(source_bindings=rows)

    def test_current_source_change_changes_external_fingerprint(self):
        rows = invented_bindings()
        before = validation.validate_source_bindings(rows)["sourceFingerprintSha256"]
        row = next(row for row in rows if row["path"] == validation.PACKAGE + "oracle.py")
        row["sha256"] = "c" * 64
        self.assertNotEqual(before, validation.validate_source_bindings(rows)["sourceFingerprintSha256"])

    def test_corpus_budget_drift_is_not_accepted_from_json(self):
        cases = list(validation.corpus.iter_cases())
        cases[0]["budget"] += 1
        with patch.object(validation.corpus, "iter_cases", return_value=iter(cases)):
            with self.assertRaises(ValueError):
                validation.validate_contract()


if __name__ == "__main__":
    unittest.main()
