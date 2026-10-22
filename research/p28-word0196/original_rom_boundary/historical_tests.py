"""Invented-only public regression of the historical read-only evidence adapter.

Fixtures are deliberately fabricated test records, not an original ROM or an
actual historical observation.  Test success never establishes native provenance.
No emulator, original bytes, physical execution or independent model is run.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

try:
    from .historical import HistoricalError, reconcile_historical
    from .context import ContextError
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from original_rom_boundary.historical import HistoricalError, reconcile_historical
    from original_rom_boundary.context import ContextError


_COMMON = [0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D]
_FORMS = {
    0x54F5: "JBR off N8.2, rel8", 0x54F8: "MOVB r0, #N8", 0x54FA: "L A, off N8",
    0x54FC: "ST A, er1", 0x54FD: "CMPB off N'8, #N8", 0x5501: "JNE rel8",
    0x556F: "LB A, off N8", 0x5571: "SLLB A", 0x5572: "ROLB off N8", 0x5575: "LB A, r0",
    0x5576: "ANDB A, off N8", 0x5578: "CMP off N8, #N16", 0x557D: "JLT rel8",
    0x557F: "MOVB r1, off N8", 0x5582: "ANDB off N8, A", 0x5585: "JBS off N8.7, rel8",
    0x5588: "JBS off N8.5, rel8", 0x558B: "ANDB off N8, A", 0x558E: "ORB off N'8, #N8",
    0x5592: "LB A, off N8", 0x5594: "ORB A, #N8", 0x55BF: "LB A, #N8",
    0x55C1: "STB A, off N8", 0x55C3: "STB A, off N8",
}


def _snapshot(pc, accumulator, psw, registers):
    return {"pc": pc, "accumulator": accumulator, "psw": psw, "dd": bool(psw & 0x1000),
            "lrb": 0x21, "x1": 0, "x2": 0, "dp": 0, "usp": 0,
            "ssp": 0x07FE, "registers": list(registers)}


def _stage(pcs, entry, accumulator_after, psw_after, terminal, exit_registers, accesses, compare_value=None):
    """Render explicitly supplied invented scalar rows; not instruction execution."""
    events, trace = [], []
    accumulator, psw = entry["accumulator"], entry["psw"]
    for index, pc in enumerate(pcs):
        next_pc = pcs[index + 1] if index + 1 < len(pcs) else terminal
        operands = [compare_value, 192] if pc == 0x5578 else [65536, 65536]
        events.append([pc, next_pc, accumulator, accumulator_after[index], psw, psw_after[index], *operands])
        accumulator, psw = accumulator_after[index], psw_after[index]
        trace.append({"pc": pc, "nextPc": next_pc, "instruction": _FORMS[pc],
                      "psw": psw, "accumulator": accumulator})
    exit_state = _snapshot(terminal, accumulator, psw, exit_registers)
    return {"entry": entry, "exit": exit_state, "accesses": accesses,
            "stage": {"result": {"status": 0, "usedAssumptions": [], "steps": len(pcs),
                "stopPc": terminal, "programReads": [], "trace": trace}, "events": events,
                "writes": [[row[1], row[2], row[4]] for row in accesses if row[3] == 1], "sspAfter": 0x07FE}}


def _case(path, scratch):
    word = 191 if path == "A" else 4291
    initial = [scratch] * 8
    entry_registers = [255, scratch, word & 255, word >> 8, scratch, scratch, scratch, scratch]
    consumer_entry = _snapshot(0x54F5, word, 0x1002, initial)
    consumer_accesses = [[0x54F5, 0x0128, 8, 0, 4], [0x54F8, 0x0108, 8, 1, 255],
                         [0x54FA, 0x0196, 16, 0, word], [0x54FC, 0x010A, 16, 1, word],
                         [0x54FD, 0x0117, 8, 0, 14]]
    consumer = _stage([0x54F5, 0x54F8, 0x54FA, 0x54FC, 0x54FD, 0x5501], consumer_entry,
                       [word] * 6, [0x1002] * 4 + [0x9002] * 2, 0x556F, entry_registers, consumer_accesses)
    common_accesses = [[0x556F, 0x018E, 8, 0, scratch], [0x5572, 0x018E, 8, 0, scratch],
                       [0x5572, 0x018E, 8, 1, 85 if path == "B" else 0],
                       [0x5575, 0x0108, 8, 0, 255],
                       [0x5576, 0x018E, 8, 0, 85 if path == "B" else 0],
                       [0x5578, 0x0196, 16, 0, word]]
    exit_registers = list(entry_registers)
    if path == "A":
        pcs = _COMMON + [0x55BF, 0x55C1, 0x55C3]
        a_after = [0, 0, 0, 255, 0, 0, 0, 15, 15, 15]
        psw_after = [0xC002, 0x4002, 0x4002, 2, 0x4002, 0x8002, 0x8002, 0x8002, 0x8002, 0x8002]
        accesses = common_accesses + [[0x55C1, 0x0117, 8, 1, 15], [0x55C3, 0x018F, 8, 1, 15]]
    elif path == "B":
        pcs = _COMMON + [0x557F, 0x5582, 0x5585, 0x5592, 0x5594]
        a_after = [4266, 4180, 4180, 4351, 4181, 4181, 4181, 4181, 4181, 4181, 4266, 4346]
        psw_after = [0x8002] * 5 + [2] * 7
        accesses = common_accesses + [[0x557F, 0x0117, 8, 0, 14], [0x557F, 0x0109, 8, 1, 14],
            [0x5582, 0x0117, 8, 0, 14], [0x5582, 0x0117, 8, 1, 4], [0x5585, 0x012A, 8, 0, 170],
            [0x5592, 0x018F, 8, 0, 170]]
        exit_registers[1] = 14
    else:
        pcs = _COMMON + [0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E, 0x5592, 0x5594]
        a_after = [4096, 4096, 4096, 4351, 4096, 4096, 4096, 4096, 4096, 4096, 4096, 4096, 4096, 4096, 4336]
        psw_after = [0xC002, 0x4002, 0x4002, 2, 0x4002, 2, 2, 2, 0x4002, 0x4002, 0x4002, 0x4002, 2, 0x4002, 2]
        accesses = common_accesses + [[0x557F, 0x0117, 8, 0, 14], [0x557F, 0x0109, 8, 1, 14],
            [0x5582, 0x0117, 8, 0, 14], [0x5582, 0x0117, 8, 1, 0], [0x5585, 0x012A, 8, 0, 0],
            [0x5588, 0x0124, 8, 0, 201], [0x558B, 0x018F, 8, 0, 0], [0x558B, 0x018F, 8, 1, 0],
            [0x558E, 0x012A, 8, 0, 0], [0x558E, 0x012A, 8, 1, 1], [0x5592, 0x018F, 8, 0, 0]]
        exit_registers[1] = 14
    terminal = 0x55C5 if path == "A" else 0x5596
    alternate = _stage(pcs, copy.deepcopy(consumer["exit"]), a_after, psw_after,
                       terminal, exit_registers, accesses, word)
    generation = {"writerPc": 0x05EB, "eventIndex": 0, "writeOrder": 1, "value": word}
    quartet = {"writerPc": 0x22A5, "eventIndex": 0, "writeOrder": 0, "value": word}
    journal = [[1, 0x05DF, 0x0100, 16, 1, 0], [1, 0x05EB, 0x0196, 16, 1, word]]
    journal += [[1, *row] for row in consumer_accesses + accesses]
    event = {"index": 0, "machineId": 1, "prefix": {"index": 0, "machineId": 1,
                "resultGeneration": generation, "selectedGeneration": quartet,
                "after": {**consumer_entry, "pc": 0x05ED}}, "consumer": consumer, "alternate": alternate,
             "disposition": "QuartetDerived0196AlternateStrict", "provenance": "QuartetDerived0196",
             "producerGeneration0196": generation, "readerGeneration0196": generation,
             "compareGeneration0196": generation, "abiWrites": [[0, 0x05ED, 0x54F5]],
             "after": alternate["exit"], "continuityJournal": journal,
             "stateBefore": {"byte0128": 4, "byte0117": 14, "byte018e": scratch,
                             "byte018f": scratch, "byte012a": scratch, "byte0124": 209}}
    native_writes = [(index, row) for index, row in enumerate(journal) if row[0] == 1 and row[4] == 1]
    software_writes = []
    memory = {0x018E: scratch, 0x018F: scratch, 0x0109: scratch, 0x0117: 14, 0x012A: scratch}
    for row in accesses:
        if row[3] == 1:
            order = next(index for index, (_, item) in enumerate(native_writes) if item[1:] == row)
            software_writes.append({"address": row[1], "width": row[2], "writerPc": row[0],
                "oldValue": memory[row[1]], "newValue": row[4],
                "generation": {"writerPc": row[0], "eventIndex": 0, "writeOrder": order, "value": row[4]}})
            memory[row[1]] = row[4]
    proof = {"reader54fa": generation, "reader5578": generation, "generation0196": generation,
             "nativeJne5501": consumer["stage"]["events"][-1], "no0196Overlap": True,
             "jlt557d": alternate["stage"]["events"][6], "stopBefore": terminal, "image": "A",
             "cmpCf": path == "A", "cmpZf": False, "selectedQuartetGeneration": quartet,
             "corpus": "threshold191" if path == "A" else "slots", "softwareWrites": software_writes,
             "cmp5578": alternate["stage"]["events"][5], "noSfr": True, "hcRetained": True,
             "continuous556fBoundary": alternate["entry"], "ddRetained": True,
             "journalPositions": {str(0x05EB): 1,
                **{str(pc): next(index for index, item in enumerate(journal) if item[1] == pc and item[4] == 0)
                   for pc in (0x54FA, 0x5578)}}, "scratchPattern": scratch, "cfProducer": 0x5578,
             "cmpRightImmediate": 192, "eventIndex": 0, "cmpLeft": word}
    return {"scratchPattern": scratch, "machineInstances": 1, "checkpoints": [event]}, proof


class HistoricalAdapterTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[3] / ".tmp"
        scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="m2bs-invented-history-", dir=scratch)
        self.directory = Path(self.temporary.name)
        d, pd = _case("D", 0)
        b, pb = _case("B", 170)
        a, pa = _case("A", 0)
        def raw(sequences):
            return {"protocolVersion": 1, "operation": "word0196SoftwareAlternateChain", "runnerVersion": "0.33.0",
                    "syntheticResult": None, "word0196AlternateSequences": sequences,
                    "entryContracts": [{"classification": "InventedPublicAdapterFixture_NotRom"}]}
        proofs = [pd, pb, pa]
        for index in range(39):
            item = copy.deepcopy(pd)
            item.update(image="B" if index < 6 else "A",
                        corpus="fuel-ab" if index < 6 else "upstream-gate" if index < 9 else "invented-unselected",
                        scratchPattern=index + 1, eventIndex=index + 1)
            proofs.append(item)
        self.documents = {"slots": raw([d, b]), "below": raw([a]), "proof": {"passed": True,
            "quartetDerived": 39, "gateControls": 3, "strictEvents": 42, "proofs": proofs,
            "classification": "Independent C# validated actual event-wide native proof;no new execution"}}
        self.rom_sha = "f" * 64  # Invented test identity, never a private ROM digest.
        def checked_report(native, matched_proofs):
            sequences = []
            for sequence, proof in zip(native["word0196AlternateSequences"], matched_proofs):
                event = sequence["checkpoints"][0]
                checked = {key: event[key] for key in ("index", "disposition", "provenance",
                    "producerGeneration0196", "readerGeneration0196", "compareGeneration0196")}
                checked.update({key: proof[key] for key in ("cmpLeft", "cmpRightImmediate", "cmpCf", "cmpZf", "softwareWrites")})
                checked.update(actual=event, stopPc=event["alternate"]["exit"]["pc"], branchPc=0x557D,
                               branchTaken=proof["cmpCf"], branchTarget=event["alternate"]["stage"]["events"][6][1])
                sequences.append({"image": "A", "scratchPattern": sequence["scratchPattern"], "checkpoints": [checked]})
            return {"formatVersion": 1, "purpose": "word0196-software-alternate-test", "profileId": "p28-304",
                    "runnerVersion": "0.33.0", "originalHash": {"sha256": self.rom_sha, "crc32": "00000000"},
                    "hasFailure": False, "mutation": None, "changedOffsets": [],
                    "word0196AlternateSoftwareChain": "Validated", "cmp5578": "Validated",
                    "timerContinuation": "NotRun", "p2": "NotRun", "physicalOutput": "NotRun",
                    "firmwareBin": 0, "physicalRpmAvailable": False,
                    "entryContract": native["entryContracts"], "sequences": sequences}
        self.documents["slotsReport"] = checked_report(self.documents["slots"], [pd, pb])
        self.documents["belowReport"] = checked_report(self.documents["below"], [pa])

    def tearDown(self):
        self.temporary.cleanup()

    def profile(self):
        result = {}
        for role, document in self.documents.items():
            payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
            path = self.directory / (role + ".json")
            path.write_bytes(payload)
            result[role] = {"path": str(path), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        return result

    def event(self):
        return self.documents["slots"]["word0196AlternateSequences"][0]["checkpoints"][0]

    def test_invented_adapter_regression_has_no_execution_authority(self):
        result = reconcile_historical(self.profile(), self.rom_sha)
        self.assertTrue(result["passed"])
        summary = result["publicSummary"]
        self.assertEqual(summary["freshReconciledPaths"], ["A", "B", "D"])
        self.assertEqual(summary["priorIndependentProofRows"], 42)
        self.assertEqual(summary["freshReconciledOriginalASamples"], 3)
        self.assertEqual(summary["historicalNativePathCWitnesses"], 0)
        self.assertEqual(summary["newOriginalRomExecutions"], 0)
        self.assertEqual(summary["newCsharpOrModelReplays"], 0)
        self.assertTrue(summary["actualRomIdentityJoinedToOldCsharpReports"])
        self.assertEqual(summary["romBoundFullRawCheckpointProjectionComparisons"], 3)
        self.assertFalse(summary["firmwareReady"])
        self.assertNotIn(str(self.directory), json.dumps(summary))
        self.assertNotIn("sha256", json.dumps(summary))
        matrix = {row["field"]: row for row in result["matrix"]["fields"]}
        self.assertEqual(matrix["SF"]["classifications"], ["Unknown"])
        self.assertEqual(matrix["P2"]["classifications"], ["Unknown"])
        self.assertEqual(matrix["NativeStackFrame"]["classifications"], ["Unknown"])
        self.assertEqual(matrix["pointingBank7.X1"]["classifications"], ["Unknown"])
        self.assertEqual(matrix["CF"]["classifications"], ["StaticRomDerived"])
        self.assertIn("ObservedNative", matrix["A"]["classifications"])
        self.assertIn("ObservedNative", matrix["DATA0117"]["classifications"])
        self.assertIn("ObservedNative", matrix["DATA0124"]["classifications"])
        self.assertIn("ObservedNative", matrix["DATA018F"]["classifications"])
        self.assertFalse(matrix["SSP"]["native_ownership_established"])
        self.assertTrue(result["privateEvidence"]["no_new_independent_csharp_execution"])

    def test_wrong_source_identity_missing_file_and_closed_profile_refused(self):
        profile = self.profile()
        changed = copy.deepcopy(profile)
        changed["slots"]["sha256"] = "0" * 64
        with self.assertRaises(ContextError):
            reconcile_historical(changed, self.rom_sha)
        changed = copy.deepcopy(profile)
        changed["slots"]["path"] += ".missing"
        with self.assertRaises(ContextError):
            reconcile_historical(changed, self.rom_sha)
        changed = copy.deepcopy(profile)
        changed["slots"]["mode"] = "synthetic-native-promotion"
        with self.assertRaises(ContextError):
            reconcile_historical(changed, self.rom_sha)

    def test_network_source_is_refused_before_any_open(self):
        for path in ("//invented-server/share/evidence.json", "\\\\invented-server\\share\\evidence.json",
                     "https://example.invalid/evidence.json", "file://invented-server/evidence.json"):
            profile = self.profile()
            profile["slots"]["path"] = path
            with self.subTest(path=path), self.assertRaisesRegex(HistoricalError, "NetworkSourceRequiresControlledRestore"):
                reconcile_historical(profile, self.rom_sha)

    def test_rom_candidate_hash_is_mandatory_and_not_inferred_from_historical_labels(self):
        for digest in (None, "", "not-a-digest", "F" * 64, "0" * 64):
            with self.subTest(digest=digest), self.assertRaises(ContextError):
                reconcile_historical(self.profile(), digest)
        self.documents["belowReport"]["originalHash"]["sha256"] = "e" * 64
        with self.assertRaisesRegex(HistoricalError, "different original ROM candidate"):
            reconcile_historical(self.profile(), self.rom_sha)

    def test_independent_csharp_report_must_pass_and_contain_exact_full_actual_projection(self):
        mutations = (
            lambda: self.documents["slotsReport"].update(hasFailure=True),
            lambda: self.documents["slotsReport"].update(mutation={"invented": True}),
            lambda: self.documents["slotsReport"]["sequences"][0].update(image="B"),
            lambda: self.documents["slotsReport"]["sequences"].pop(),
            lambda: self.documents["slotsReport"]["sequences"][0]["checkpoints"][0].update(actual={}),
            lambda: self.documents["slotsReport"].update(entryContract=[]),
            lambda: self.documents["slotsReport"]["sequences"][0]["checkpoints"][0].update(cmpLeft=99),
            lambda: self.documents["slotsReport"]["sequences"][0]["checkpoints"][0].update(branchTarget=0x55C5),
        )
        for mutation in mutations:
            original = copy.deepcopy(self.documents)
            mutation()
            with self.subTest(mutation=mutation), self.assertRaises(ContextError):
                reconcile_historical(self.profile(), self.rom_sha)
            self.documents = original

    def test_false_native_source_synthetic_promotion_and_second_machine_refused(self):
        for mutate in (
            lambda: self.documents["slots"].update(operation="syntheticTransfer"),
            lambda: self.documents["slots"].update(syntheticResult={"passed": True}),
            lambda: self.documents["slots"]["word0196AlternateSequences"][0].update(machineInstances=2),
            lambda: self.event().update(machineId=2),
            lambda: self.event()["prefix"].update(machineId=True),
        ):
            original = copy.deepcopy(self.documents)
            mutate()
            with self.subTest(mutation=mutate), self.assertRaises(ContextError):
                reconcile_historical(self.profile(), self.rom_sha)
            self.documents = original

    def test_fake_stack_hidden_seed_and_fabricated_pc_path_refused(self):
        for mutate in (
            lambda: self.event().update(abiWrites=[[0, 0x05ED, 0x556F]]),
            lambda: self.event()["prefix"]["after"].update(ssp=0x0700),
            lambda: self.event()["alternate"]["entry"].update(ssp=0),
            lambda: self.event()["consumer"]["stage"]["events"][-1].__setitem__(1, 0x5596),
            lambda: self.event()["alternate"]["stage"]["result"]["trace"][0].update(instruction="Invented HALT"),
            lambda: self.event()["alternate"]["stage"]["events"][10].__setitem__(1, 0x5592),
        ):
            original = copy.deepcopy(self.documents)
            mutate()
            with self.subTest(mutation=mutate), self.assertRaises(ContextError):
                reconcile_historical(self.profile(), self.rom_sha)
            self.documents = original

    def test_old_independent_proof_missing_or_mismatched_refused(self):
        for mutate in (
            lambda: self.documents["proof"].update(passed=False),
            lambda: self.documents["proof"]["proofs"].pop(),
            lambda: self.documents["proof"]["proofs"][0].update(image="B"),
            lambda: self.documents["proof"]["proofs"][0].update(no0196Overlap=False),
            lambda: self.documents["proof"]["proofs"][0]["journalPositions"].update({str(0x05EB): 0}),
            lambda: self.documents["proof"]["proofs"][0].update(continuous556fBoundary={}),
            lambda: self.documents["proof"]["proofs"][0]["softwareWrites"][0].update(oldValue=99),
        ):
            original = copy.deepcopy(self.documents)
            mutate()
            with self.subTest(mutation=mutate), self.assertRaises(ContextError):
                reconcile_historical(self.profile(), self.rom_sha)
            self.documents = original

    def test_old_image_b_and_gate_control_domains_are_disjoint_not_added_counters(self):
        # Keep all old headline counters intact; change the actual row relation.
        self.documents["proof"]["proofs"][3]["corpus"] = "invented-wrong-B-family"
        with self.assertRaisesRegex(HistoricalError, "outside the recorded fuel-ab family"):
            reconcile_historical(self.profile(), self.rom_sha)
        self.documents["proof"]["proofs"][3]["corpus"] = "fuel-ab"
        # Exchange one B row and one A control: still six B, three controls,
        # forty-two rows, but controls are no longer an original-A-only domain.
        self.documents["proof"]["proofs"][3]["image"] = "A"
        self.documents["proof"]["proofs"][9]["image"] = "B"
        with self.assertRaisesRegex(HistoricalError, "outside the recorded fuel-ab family|disjoint original-A"):
            reconcile_historical(self.profile(), self.rom_sha)

    def test_stale_generation_host_seed_overlap_and_missing_same_value_write_refused(self):
        for mutate in (
            lambda: self.event()["producerGeneration0196"].update(writeOrder=0),
            lambda: self.event()["continuityJournal"][1].__setitem__(0, 0),
            lambda: self.event()["continuityJournal"][1].__setitem__(2, 0x0197),
            lambda: self.event()["alternate"]["accesses"].pop(2),
            lambda: self.event()["continuityJournal"].pop(-2),
            lambda: self.event()["alternate"]["stage"]["events"][5].__setitem__(7, 0x0196),
        ):
            original = copy.deepcopy(self.documents)
            mutate()
            with self.subTest(mutation=mutate), self.assertRaises(ContextError):
                reconcile_historical(self.profile(), self.rom_sha)
            self.documents = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
