"""Independent documentary expectations frozen before the allocation model ran.

The two full primary page images supply the row meanings. Historical M2ch
paraphrases and new model results supply none of these expected allocations.
This suite validates evidence relations; it does not simulate an interrupt.
"""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from native_irq000a_allocation import analysis


CLASSIFICATION = "DocumentaryStaticAllocationReview_NotExecution"
BASE = "f7c773394c66cbd604f60c8d7af117572fe79686"


def reference_documents():
    """Independent existing-source identities, with known integrity limits."""
    return [
        {
            "id": "A", "title": "MSM66201 Instruction Manual",
            "publisher": "OKI Semiconductor", "documentNumber": None,
            "edition": "First Edition", "date": "September 1991", "revision": None,
            "deviceScope": "Standard MSM66201; customer-specific ASIC allocation may differ",
            "sha256": "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271",
            "bytes": 4563117, "pages": 266,
            "reviewedTable": "Table1-1 / printed1-5 / PDF9",
            "pageImageSha256": "6e37518ff405f4cb8edee7b8392d9744c6a2e7385348d7f434c0e41a87736517",
            "visualMethod": "IndependentFullPageImageReview_NoOCR",
            "allocationEvidence": True, "newManufacturerDocument": False,
            "footnote": "Customer-specific ASIC internal I/O can change vector allocation",
        },
        {
            "id": "B", "title": "MSM66201/207 User Manual body",
            "publisher": "OKI manufacturer body attribution", "documentNumber": None,
            "edition": None, "date": None, "revision": None,
            "deviceScope": "MSM66201/207 body; exact edition and ECU applicability unknown",
            "sha256": "f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf",
            "bytes": 16203609, "pages": None,
            "reviewedTable": "Table17-1 / printed166",
            "pageImageSha256": "a61d26b3dc4d97f36a9c88ae4931d5c0718c9b4b61a1ae134558d295b936dd8f",
            "visualMethod": "IndependentFullPageImageReview_NoOCR",
            "allocationEvidence": True, "newManufacturerDocument": False,
            "integrity": {
                "wholeArchive": "ArchiveIntegrityMismatch", "crcVerifiedMembers": 59,
                "crcFailedMembers": 7, "selectedTablePageReadable": True,
                "completeManual": False, "titleEditionLeafRetained": False,
                "repaired": False,
            },
        },
        {
            "id": "C", "title": "MSM66201/66P201/66207/66P207 specification",
            "publisher": "OKI Semiconductor", "documentNumber": "E2E1027-27-Y4",
            "edition": None, "date": "January 1998", "previousDate": "November 1996",
            "revision": "Y4", "deviceScope": "Standard MSM66201/66P201/66207/66P207",
            "sha256": "247913724eb291e20c869d42ba40363268fba415ab787b7c843e2a094533f0fe",
            "bytes": 589158, "pages": 30,
            "allocationEvidence": False, "newManufacturerDocument": False,
            "finding": "General IRQ/IE SFR list and vector memory area; no three-factor allocation table or revision bridge",
        },
        {
            "id": "D", "title": "Microcontroller Data Book 1990/1991",
            "publisher": "OKI Semiconductor", "documentNumber": None,
            "edition": "Fifth Edition", "date": "June 1990",
            "revision": "Target sections Preliminary",
            "deviceScope": "MSM66201/66P201 and MSM66207/66P207 sections",
            "sha256": "88aae3b11782ae1b8bfea0f112b81c342232a98ed75e39b6aac6ea3ad5f54e82",
            "bytes": 25444912, "pages": 534,
            "allocationEvidence": False, "newManufacturerDocument": False,
            "finding": "Target PDF368-409 general IRQ/IE lists and vector memory regions; no three-factor source table or revision bridge",
            "integrity": "Non-zero-indexed xref warning retained; original not repaired",
        },
        {
            "id": "E", "title": "OLMS-66K Series Instruction List",
            "publisher": "OKI Semiconductor", "documentNumber": "E2E1025-27-Y2",
            "edition": None, "date": "January 1998", "previousDate": "November 1996",
            "revision": "Y2",
            "deviceScope": "Includes MSM66201/66P201 and MSM66207/66P207; other families not peripheral equivalence",
            "sha256": "5f8f3d12328c8811a9245974f7b6efd0d26687a50c22a2001c21ed88b3068a0f",
            "bytes": 28708, "pages": 5,
            "allocationEvidence": False, "newManufacturerDocument": False,
            "finding": "Mnemonic/function list only; no IRQ vector allocation",
        },
    ]


def reference_vectors():
    rows = []
    # Meaning and B bit/symbol association are independently transcribed.
    # PROGRAM targets are separately read-only source facts, not IRQ causes.
    for address, target, source_a, source_b, bit, request, enable in (
        (0x000A, 0x0213, "SerialReceivingReady", "SerialReceivingReady", 1, "RQSRRDY", "IESRRDY"),
        (0x000C, 0x24D6, "SerialTransmittingReady", "SerialTransmittingReady", 2, "RQSTRDY", "IESTRDY"),
        (0x000E, 0x03ED, "BRGForSerialReceive", "SerialReceiveBrgOverflow", 3, "RQSRGEN", "IESRGEN"),
    ):
        rows.append({
            "vectorAddress": address, "addressSpace": "PROGRAM", "widthBits": 16,
            "programVectorTarget": target,
            "targetEvidence": "ReadOnlyVerifiedOriginalRom_NotObservedDelivery",
            "A": {"interruptSource": source_a, "irqBit": None, "ieBit": None,
                  "irqSymbol": None, "ieSymbol": None},
            "B": {"interruptSource": source_b, "irqBit": bit, "ieBit": bit,
                  "irqSymbol": request, "ieSymbol": enable},
        })
    return rows


def reference_profiles():
    return [
        {"profile": "InstructionTable1_1", "source": "A",
         "vector000A": "SerialReceivingReady", "registerBitMapping": "NotEstablishedByThisTable",
         "ecuApplicability": "Unknown", "selectedForActualEcu": False},
        {"profile": "UserTable17_1", "source": "B",
         "vector000A": "SerialReceivingReady", "registerBitMapping": "Table17_1WordBits1_2_3_SourceQualified",
         "ecuApplicability": "Unknown", "selectedForActualEcu": False},
    ]


def reference_mask(entry, tail):
    # Only these independently reviewed mask pairs belong to this experiment.
    if type(entry) is not int or type(tail) is not int or (entry, tail) not in (
        (0x02A0, 0x2BAB), (0x00A0, 0xA9A3)
    ):
        raise ValueError("ClosedMaskPairRequired")
    return {
        "entryMask": entry, "tailMask": tail, "sourceProfile": "UserTable17_1",
        "rxBit": 1, "rxEntryEnabled": False, "rxTailEnabled": True,
        "txBit": 2, "txEntryEnabled": False, "txTailEnabled": False,
        "actualEnableStateKnown": False, "deliveryObserved": False,
        "interpretation": "ConditionalRxSelfMaskThenReenable_NotTxEnable",
        "enablePolaritySource": "UserSection17_2_2_Printed165_IESet1",
        "contradictoryEntryParagraph": "Printed167SaysIESet0_NotResolvedAsErratum",
    }


def reference_correction():
    return {
        "result": "PriorTranscriptionErrorCorrected", "newPrimaryConflict": False,
        "threeVectorRoleAgreement": True,
        "priorUser000ATransmitClaim": "RejectedAsPrintedTableTranscription",
        "priorUser000CErrorClaim": "RejectedAsPrintedTableTranscription",
        "priorUserBit1RQSTRDYClaim": "Rejected_RQSTRDYisBit2",
        "oldM2chReportsManifestsAndCodeRewritten": False,
        "newManufacturerErratum": False, "revisionSuccessionEstablished": False,
        "newManufacturerDocuments": 0, "knownMirrorCountsAsIndependentDocument": False,
        "sourceLabelsChosenFromFirmwareBehavior": False,
    }


def reference_authority():
    return {
        "actualEcuChipIdentified": False, "actualMaskRevision": None,
        "actualIrqSourceObserved": False, "actualIrqDeliveries": 0,
        "cpuExecutions": 0, "romExecutions": 0, "rtiExecutions": 0, "retiredInstructions": 0,
        "actualMachineId": None, "actualEventOrdinal": None, "actualWriteOrdinal": None,
        "actualIe": None, "actualPending": None, "actualMie": None,
        "srbufReadsSelectActualChip": False, "fourNativeInvocationsObserved": False,
        "actualSrbufPacketObserved": False, "nX8_500SMappingImported": False,
        "manufacturerInquiry": "DraftReady_NotSent", "manufacturerResponseReceived": False,
        "supportTicketCreated": False, "runtimeAdmission": "Blocked", "firmwareReady": False,
    }


def reference_evaluation():
    return {
        "schemaVersion": 1, "milestone": "M2ci", "classification": CLASSIFICATION,
        "documents": reference_documents(), "vectors": reference_vectors(),
        "profiles": reference_profiles(),
        "masks": [reference_mask(0x02A0, 0x2BAB), reference_mask(0x00A0, 0xA9A3)],
        "correction": reference_correction(), "authority": reference_authority(),
    }


def reference_contract():
    result = reference_evaluation()
    result["baseSha"] = BASE
    del result["masks"]
    result["maskPairs"] = [[0x02A0, 0x2BAB], [0x00A0, 0xA9A3]]
    return result


def reference_records():
    result = reference_evaluation()
    findings = []
    for document in result["documents"]:
        findings.append(("document:" + document["id"], "document", document))
    for row in result["vectors"]:
        findings.append((f"vector:{row['vectorAddress']:04X}", "vector", row))
    for profile in result["profiles"]:
        findings.append(("profile:" + profile["profile"], "profile", profile))
    for mask in result["masks"]:
        findings.append((f"mask:{mask['entryMask']:04X}:{mask['tailMask']:04X}", "mask", mask))
    findings.extend((name, name, result[name]) for name in ("correction", "authority"))
    return [{"caseId": case, "recordType": kind, "classification": CLASSIFICATION,
             "finding": finding} for case, kind, finding in findings]


def evidence_mutations():
    """Twenty-three user-required refusals; inputs, evidence or authority change."""
    return [
        ("WrongDocument", ("documents", 0, "sha256"), "0" * 64),
        ("WrongRevision", ("documents", 0, "edition"), "Second Edition"),
        ("WrongDevice", ("documents", 0, "deviceScope"), "MSM66509 / nX-8/500S"),
        ("WrongVector", ("vectors", 0, "vectorAddress"), 0x000C),
        ("ProgramDataConfusion", ("vectors", 0, "addressSpace"), "DATA"),
        ("RxTxSwapped", ("vectors", 0, "B", "interruptSource"), "SerialTransmittingReady"),
        ("BrgErrorInvented", ("vectors", 2, "B", "interruptSource"), "SerialTransmissionError"),
        ("DuplicatePdfIndependent", ("correction", "knownMirrorCountsAsIndependentDocument"), True),
        ("MissingAsicFootnote", ("documents", 0, "footnote"), ""),
        ("OcrOnlyTable", ("documents", 1, "visualMethod"), "OCR_Only"),
        ("DamagedArchiveComplete", ("documents", 1, "integrity", "completeManual"), True),
        ("WrongIrqBit", ("vectors", 0, "B", "irqBit"), 2),
        ("WrongIeBit", ("vectors", 0, "B", "ieBit"), 2),
        ("OtherCoreImported", ("authority", "nX8_500SMappingImported"), True),
        ("StandardAsActualAsic", ("profiles", 0, "selectedForActualEcu"), True),
        ("HandlerAsSiliconProof", ("authority", "actualEcuChipIdentified"), True),
        ("SrbufSelectsRxSilicon", ("authority", "srbufReadsSelectActualChip"), True),
        ("MaskAsActualIe", ("authority", "actualIe"), 0x2BAB),
        ("DraftAsResponse", ("authority", "manufacturerResponseReceived"), True),
        ("UnsentAsTicket", ("authority", "supportTicketCreated"), True),
        ("FakeHardwareEvent", ("authority", "actualIrqDeliveries"), 1),
        ("FakeCpuExecution", ("authority", "cpuExecutions"), 1),
        ("HistoricalIdentityRewrite", ("correction", "oldM2chReportsManifestsAndCodeRewritten"), True),
    ]


def changed(path, value):
    result = reference_contract()
    cursor = result
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return result


class AllocationEvidenceTests(unittest.TestCase):
    maxDiff = None

    def assert_exact(self, actual, expected):
        self.assertEqual(actual, expected)
        # Python equality alone would accept false for a zero execution count.
        self.assertEqual(json.dumps(actual, sort_keys=True, allow_nan=False),
                         json.dumps(expected, sort_keys=True, allow_nan=False))

    def test_full_result_equals_frozen_independent_reference(self):
        self.assert_exact(analysis.load_contract(), reference_contract())
        self.assertIsNone(analysis.validate_contract(reference_contract()))
        self.assert_exact(analysis.evaluate(reference_contract()), reference_evaluation())
        self.assert_exact(analysis.evaluate(), reference_evaluation())

    def test_all_fourteen_complete_canonical_records_match_reference(self):
        expected = reference_records()
        self.assertEqual(len(expected), 14)
        self.assertEqual(len({row["caseId"] for row in expected}), 14)
        self.assert_exact(analysis.canonical_records(reference_contract()), expected)
        self.assert_exact(analysis.canonical_records(), expected)

    def test_six_source_qualified_rows_are_accepted(self):
        for row in reference_vectors():
            for profile, key in (("InstructionTable1_1", "A"), ("UserTable17_1", "B")):
                with self.subTest(profile=profile, vector=row["vectorAddress"]):
                    claim = row[key]
                    self.assertEqual(
                        analysis.compare_claim(profile, row["vectorAddress"], **claim),
                        {"accepted": True, "refusal": None, "actualHardwareApplicabilityEstablished": False},
                    )

    def test_label_symbol_bit_and_vector_mutations_are_refused(self):
        valid = {"profile": "UserTable17_1", "vectorAddress": 10,
                 "interruptSource": "SerialReceivingReady", "irqBit": 1,
                 "ieBit": 1, "irqSymbol": "RQSRRDY", "ieSymbol": "IESRRDY"}
        mutations = {
            "profile": ("UserTable17_1_000A_TX", "OtherDeviceTable", None),
            "vectorAddress": (12, 11, 0x0213, "000A", True),
            "interruptSource": ("SerialTransmittingReady", "SerialTransmissionError", ""),
            "irqBit": (2, None, True), "ieBit": (2, None, True),
            "irqSymbol": ("RQSTRDY", "RQSRGEN", None),
            "ieSymbol": ("IESTRDY", "IESRGEN", None),
        }
        for field, values in mutations.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    claim = dict(valid)
                    claim[field] = value
                    self.assertEqual(analysis.compare_claim(**claim), {
                        "accepted": False, "refusal": "UnsupportedSourceQualifiedAllocationClaim",
                        "actualHardwareApplicabilityEstablished": False,
                    })

    def test_instruction_table_does_not_borrow_user_register_mapping(self):
        self.assertEqual(analysis.compare_claim(
            "InstructionTable1_1", 10, "SerialReceivingReady", 1, 1, "RQSRRDY", "IESRRDY"
        ), {"accepted": False, "refusal": "UnsupportedSourceQualifiedAllocationClaim",
            "actualHardwareApplicabilityEstablished": False})

    def test_brg_meanings_remain_source_qualified(self):
        for profile, meaning, bits in (
            ("InstructionTable1_1", "SerialReceiveBrgOverflow", (None, None, None, None)),
            ("UserTable17_1", "BRGForSerialReceive", (3, 3, "RQSRGEN", "IESRGEN")),
            ("UserTable17_1", "SerialTransmissionError", (3, 3, "RQSRGEN", "IESRGEN")),
        ):
            with self.subTest(profile=profile, meaning=meaning):
                self.assertFalse(analysis.compare_claim(profile, 14, meaning, *bits)["accepted"])

    def test_two_conditional_pairs_reenable_rx_not_tx(self):
        for entry, tail in ((0x02A0, 0x2BAB), (0x00A0, 0xA9A3)):
            with self.subTest(entry=entry, tail=tail):
                self.assertEqual((entry >> 1) & 1, 0)
                self.assertEqual((tail >> 1) & 1, 1)
                self.assertEqual((entry >> 2) & 1, 0)
                self.assertEqual((tail >> 2) & 1, 0)
                self.assertEqual(analysis.mask_implications(entry, tail), reference_mask(entry, tail))

    def test_unknown_mask_pairs_and_wrong_numeric_types_are_refused(self):
        for entry, tail in ((0x02A2, 0x2BAB), (0x02A0, 0x2BAF), (0x02A0, 0xA9A3),
                            (-1, 0x2BAB), (0x10000, 0x2BAB), (True, 0x2BAB),
                            (0x02A0, True), (672.0, 0x2BAB), ("02A0", 0x2BAB)):
            with self.subTest(entry=entry, tail=tail):
                with self.assertRaisesRegex(ValueError, "ClosedMaskPairRequired"):
                    analysis.mask_implications(entry, tail)

    def test_twenty_three_requested_evidence_relations_fail_closed(self):
        controls = evidence_mutations()
        self.assertEqual(len(controls), 23)
        self.assertEqual(len({row[0] for row in controls}), 23)
        for name, path, value in controls:
            with self.subTest(case=name):
                candidate = changed(path, value)
                with self.assertRaisesRegex(ValueError, "ClosedSourceQualifiedContractRequired"):
                    analysis.validate_contract(candidate)
                with self.assertRaisesRegex(ValueError, "ClosedSourceQualifiedContractRequired"):
                    analysis.evaluate(candidate)
                with self.assertRaisesRegex(ValueError, "ClosedSourceQualifiedContractRequired"):
                    analysis.canonical_records(candidate)

    def test_false_boolean_cannot_replace_zero_runtime_counts(self):
        for field in ("actualIrqDeliveries", "cpuExecutions", "romExecutions",
                      "rtiExecutions", "retiredInstructions"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    analysis.validate_contract(changed(("authority", field), False))

    def test_unknown_entry_owners_and_runtime_claims_cannot_be_promoted(self):
        for path, value in (
            (("authority", "actualMaskRevision"), "InventedMask"),
            (("authority", "actualPending"), 2),
            (("authority", "actualMie"), 1),
            (("authority", "actualMachineId"), "InventedNativeMachine"),
            (("authority", "actualEventOrdinal"), 1),
            (("authority", "actualWriteOrdinal"), 1),
            (("authority", "actualSrbufPacketObserved"), True),
            (("authority", "fourNativeInvocationsObserved"), True),
            (("authority", "runtimeAdmission"), "Allowed"),
            (("authority", "firmwareReady"), True),
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    analysis.validate_contract(changed(path, value))

    def test_source_integrity_scope_and_historical_claims_remain_closed(self):
        for path, value in (
            (("documents", 1, "date"), "January 1998"),
            (("documents", 1, "pageImageSha256"), "0" * 64),
            (("documents", 1, "integrity", "wholeArchive"), "PASS"),
            (("documents", 1, "integrity", "crcFailedMembers"), 0),
            (("documents", 1, "integrity", "repaired"), True),
            (("documents", 2, "allocationEvidence"), True),
            (("documents", 3, "newManufacturerDocument"), True),
            (("correction", "newPrimaryConflict"), True),
            (("correction", "newManufacturerErratum"), True),
            (("correction", "revisionSuccessionEstablished"), True),
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    analysis.validate_contract(changed(path, value))


if __name__ == "__main__":
    unittest.main()
