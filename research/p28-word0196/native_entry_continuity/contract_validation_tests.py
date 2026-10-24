"""Static meaningful contract mutations; no execution or delivery authority."""
from copy import deepcopy
import json
import unittest

from native_entry_continuity import contract_validation as validation


class ContractValidationTests(unittest.TestCase):
    def test_current_contract_and_independent_counts(self):
        result = validation.validate_contract()
        self.assertTrue(result["passed"])
        self.assertEqual(result["positiveCases"], 32)
        self.assertEqual(result["positiveRetirements"], 592)
        self.assertEqual(result["actualCpuExecutions"], 0)
        self.assertFalse(result["runtimeOrAcceptanceAuthorityCreated"])

    def test_semantic_and_authority_mutations_refuse(self):
        original = json.loads(validation.PATH.read_bytes())
        changes = [
            ("program", "entryPc", 0x556F), ("program", "segmentBytes", 207),
            ("program", "executionPermissionFromClosedCfgOnly", False), ("program", "p2FunctionalReads", 1),
            ("predecessor", "positiveGateBitValue", 0), ("predecessor", "jneTakenDestination", 0x5503),
            ("predecessor", "wordLoadOverwritesAH", False), ("predecessor", "wordStoreLocalAddress", 0x0108),
            ("predecessor", "wordStoreWidthBits", 8), ("predecessor", "er1ReadBySuffix", True),
            ("entry", "hostPcSetAfterEntry", True), ("entry", "midExecutionReseed", True),
            ("entry", "secondMachineStateTransfer", True), ("entry", "nativeStackFrameClaimed", True),
            ("entry", "physicalSf", "Established"), ("corpus", "boundaryControlsCountedAsPositive", True),
            ("corpus", "positiveBelow0117StoreCanBeSameValue", True),
            ("provenance", "current05ebProducerExecuted", True), ("provenance", "nativeSchedulerEstablished", True),
            ("comparison", "oracleUsesActualRuntimeOutput", True), ("comparison", "canonicalFieldExclusions", ["psw"]),
            ("delivery", "maximumBudget", 22), ("delivery", "legacyMaximumBudget", 21),
            ("delivery", "strictHistoricalPreservationPass", True), ("delivery", "newUnauthorizedProtectedDifferencesAllowed", 1),
        ]
        for section, field, value in changes:
            with self.subTest(section=section, field=field):
                changed = deepcopy(original)
                changed[section][field] = value
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    validation.validate_contract(changed)
        for mutate in (lambda v: v["paths"]["D"].update(retirements=20),
                       lambda v: v["branchControls"]["JneAlternate"].update(positiveCompleted=True),
                       lambda v: v.update(firmwareReady=True),
                       lambda v: v.update(runtimePassed=True),
                       lambda v: v["sourceBindings"][0].update(sha256="0" * 64)):
            changed = deepcopy(original)
            mutate(changed)
            with self.assertRaises((ValueError, KeyError, TypeError)):
                validation.validate_contract(changed)
        self.assertEqual(original, json.loads(validation.PATH.read_bytes()))


if __name__ == "__main__":
    unittest.main()
