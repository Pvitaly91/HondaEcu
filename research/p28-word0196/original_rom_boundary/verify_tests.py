"""Invented-only verifier controls; no private ROM or historical fixture input."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from original_rom_boundary.verify import (
    BoundaryError, ReadOnlyImage, canonical, listing_extents, load_contract,
    load_profile, local_path, preflight_outputs, read_bound, strict_json,
    verify_expected_extent, verify_extents,
)


def invented_row():
    return {"pc": 0x2000, "formId": "lb-a-imm8", "length": 2,
            "allowedIncomingDd": [0, 1],
            "typedOperands": [{"kind": "AccumulatorA"}, {"kind": "Immediate8", "value": 0x35}],
            "successors": [0x2002], "dataReads": [], "dataWrites": [],
            "flagsRead": [], "flagsWritten": ["ZF", "DD"], "flagsSelectionRead": []}


class VerificationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[3] / ".tmp" / "m2bs-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "invented.snapshot"
        self.bytes = bytes((number * 17 + 31) & 255 for number in range(32768))
        self.source.write_bytes(self.bytes)
        self.digest = sha256(self.bytes).hexdigest()

    def refuses(self, code, fn, *args):
        with self.assertRaisesRegex(BoundaryError, "^" + code + "$"):
            fn(*args)

    def test_invented_readonly_capture_and_post_fence(self):
        image = ReadOnlyImage(self.source, 32768, self.digest)
        self.assertEqual(image.data, self.bytes)
        self.assertTrue(image.assert_unchanged())

    def test_wrong_sha(self):
        self.refuses("RomSourceIdentityMismatch", ReadOnlyImage, self.source, 32768, "0" * 64)

    def test_truncated_candidate(self):
        self.source.write_bytes(self.bytes[:-1])
        self.refuses("RomSizeMismatch", ReadOnlyImage, self.source, 32768, self.digest)

    def test_oversized_candidate(self):
        self.source.write_bytes(self.bytes + b"x")
        self.refuses("RomSizeMismatch", ReadOnlyImage, self.source, 32768, self.digest)

    def test_missing_candidate(self):
        self.refuses("RomInputUnavailable", ReadOnlyImage, self.root / "missing", 32768, self.digest)

    def test_source_mutation_during_verification(self):
        image = ReadOnlyImage(self.source, 32768, self.digest)
        self.source.write_bytes(self.bytes[:-1] + b"z")
        self.refuses("RomSourceChanged", image.assert_unchanged)

    def test_source_replacement_even_with_equal_bytes(self):
        image = ReadOnlyImage(self.source, 32768, self.digest)
        replacement = self.root / "replacement.snapshot"
        replacement.write_bytes(self.bytes)
        os.replace(replacement, self.source)
        self.refuses("RomSourceChanged", image.assert_unchanged)

    def test_output_cannot_overwrite_input(self):
        self.refuses("OutputWouldOverwriteRom", preflight_outputs, self.source, [self.source])

    def test_hardlink_alias_cannot_overwrite_input(self):
        alias = self.root / "alias.json"
        os.link(self.source, alias)
        self.refuses("OutputWouldOverwriteRom", preflight_outputs, self.source, [alias])

    def test_existing_or_duplicate_output_refused(self):
        existing = self.root / "existing.json"
        existing.write_text("{}", encoding="utf-8")
        self.refuses("FreshJsonOutputRequired", preflight_outputs, self.source, [existing])
        fresh = self.root / "fresh.json"
        self.refuses("OutputAliasesAnotherOutput", preflight_outputs, self.source, [fresh, fresh])

    def test_no_firmware_output_format(self):
        for name in ("output.bin", "output.hex", "output.obj"):
            self.refuses("FreshJsonOutputRequired", preflight_outputs, self.source, [self.root / name])

    def test_unavailable_nas_is_refused_without_probe(self):
        with patch.object(Path, "open", side_effect=AssertionError("must not contact network")):
            self.refuses("NetworkSourceRequiresControlledRestore", local_path, r"\\unavailable.invalid\evidence\rom")
            self.refuses("NetworkSourceRequiresControlledRestore", local_path, "https://unavailable.invalid/rom")

    def test_duplicate_and_nonfinite_json_refused(self):
        self.refuses("DuplicateJsonKey", strict_json, b'{"x":1,"x":2}')
        self.refuses("NonfiniteJson", strict_json, b'{"x":NaN}')
        self.refuses("MalformedJson", strict_json, b'{')

    def test_wrong_profile_refused_before_historical_access(self):
        profile = self.root / "profile.json"
        value = {"schemaVersion": 1, "milestone": "M2bs", "profileId": "wrong",
                 "baselineBinding": {}, "dossier": {}, "listing": {}, "historical": {},
                 "provenanceClassification": "ArchiveByteContinuityCandidate_FactoryOriginUnknown"}
        profile.write_bytes(canonical(value))
        self.refuses("WrongCandidateProfile", load_profile, profile)

    def test_boolean_schema_version_refused(self):
        profile = self.root / "profile.json"
        value = {"schemaVersion": True, "milestone": "M2bs", "profileId": "p28-304",
                 "baselineBinding": {}, "dossier": {}, "listing": {}, "historical": {},
                 "provenanceClassification": "ArchiveByteContinuityCandidate_FactoryOriginUnknown"}
        profile.write_bytes(canonical(value))
        self.refuses("WrongCandidateProfile", load_profile, profile)

    def test_invented_extent_positive(self):
        result = verify_expected_extent(bytes((0x77, 0x35)), invented_row(), 1)
        self.assertEqual(result["resultingDd"], 0)
        self.assertFalse(result["actualExecutionObserved"])

    def test_wrong_entry_boundary(self):
        row = invented_row()
        row["pc"] = 0x2001
        self.refuses("RomInstructionSemanticMismatch_successors", verify_expected_extent,
                     bytes((0x77, 0x35)), row, 0)

    def test_dd_mismatch_refused_without_expected_repair(self):
        row = invented_row()
        row["allowedIncomingDd"] = [0]
        self.refuses("ExpectedDdMismatch", verify_expected_extent, bytes((0x77, 0x35)), row, 1)

    def test_altered_instruction_byte(self):
        self.refuses("RomInstructionSemanticMismatch_typedOperands", verify_expected_extent,
                     bytes((0x77, 0x36)), invented_row(), 0)

    def test_trailing_instruction_bytes(self):
        self.refuses("InstructionDecodeRefused_TrailingBytes", verify_expected_extent,
                     bytes((0x77, 0x35, 0x23)), invented_row(), 0)

    def test_wrong_flag_contract(self):
        row = invented_row()
        row["flagsWritten"] = ["ZF"]
        self.refuses("RomInstructionSemanticMismatch_flagsWritten", verify_expected_extent,
                     bytes((0x77, 0x35)), row, 0)

    def test_immediate_is_not_data_read(self):
        row = invented_row()
        row["dataReads"] = [{"address": 0x35, "widthBits": 8}]
        self.refuses("RomInstructionSemanticMismatch_dataReads", verify_expected_extent,
                     bytes((0x77, 0x35)), row, 0)

    def test_listing_binding_compares_exact_selected_bytes(self):
        row = invented_row()
        image = bytes(0x2000) + bytes((0x77, 0x35))
        frozen = listing_extents(b" label: LB A, #invented ; 2000 0 108 280 7735\n", {0x2000})
        self.assertEqual(verify_extents(image, {"instructionExtents": [row]}, frozen)["extentCount"], 1)
        altered = image[:-1] + b"6"
        self.refuses("ROM_SOURCE_MISMATCH", verify_extents, altered, {"instructionExtents": [row]}, frozen)

    def test_missing_or_duplicate_frozen_boundary(self):
        self.refuses("MissingFrozenListingBoundary", listing_extents, b"", {0x2000})
        line = b" LB A,#invented ; 2000 0 108 280 7735\n"
        self.refuses("DuplicateFrozenListingBoundary", listing_extents, line + line, {0x2000})

    def test_frozen_listing_dd_annotation_must_match_expected_context(self):
        row = invented_row()
        row["allowedIncomingDd"] = [0]
        image = bytes(0x2000) + bytes((0x77, 0x35))
        frozen = listing_extents(b" LB A,#invented ; 2000 1 108 280 7735\n", {0x2000})
        self.refuses("FrozenListingDdMismatch", verify_extents, image, {"instructionExtents": [row]}, frozen)

    def test_source_binding_change_or_unavailable(self):
        row = {"path": str(self.source), "bytes": 32768, "sha256": self.digest}
        self.assertEqual(read_bound(row), self.bytes)
        row["sha256"] = "f" * 64
        self.refuses("SelectedSourceIdentityMismatch", read_bound, row)
        row["path"] = str(self.root / "missing")
        self.refuses("SelectedSourceUnavailable", read_bound, row)

    def test_contract_has_only_static_no_execution_scope(self):
        contract = load_contract()
        self.assertEqual(len(contract["instructionExtents"]), 27)
        self.assertEqual(len(contract["algorithmPcs"]), 18)
        self.assertNotIn("romHash", json.dumps(contract))


if __name__ == "__main__":
    unittest.main()
