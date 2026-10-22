"""Invented single-extent regressions, never an original-ROM fixture or run."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from original_rom_boundary.decode import DecodeFailure, decode_extent


# Independently specified, differently located single instructions. These are
# manufacturer-form grammar examples, not a recovered OEM instruction window.
INVENTED = (
    ("lb-a-page", bytes((0xF4, 0x66)), 2, False),
    ("sllb-a", bytes((0x53,)), 1, True),
    ("rolb-page", bytes((0xC4, 0x66, 0xB7)), 3, False),
    ("lb-a-r0", bytes((0x78,)), 1, False),
    ("andb-a-page", bytes((0xD7, 0x66)), 2, True),
    ("cmp-page-imm16", bytes((0xB4, 0x66, 0xC0, 0x68, 0x24)), 5, False),
    ("jlt-rel8", bytes((0xCA, 0xF0)), 2, False),
    ("movb-r1-page", bytes((0xC4, 0x66, 0x49)), 3, False),
    ("andb-page-a", bytes((0xC4, 0x66, 0xD1)), 3, False),
    ("jbs-page-bit7", bytes((0xEF, 0x66, 0xF0)), 3, False),
    ("jbs-page-bit5", bytes((0xED, 0x66, 0xF0)), 3, False),
    ("orb-page-imm8", bytes((0xC4, 0x66, 0xE0, 0x35)), 4, False),
    ("orb-a-imm8", bytes((0xE6, 0x35)), 2, True),
    ("lb-a-imm8", bytes((0x77, 0x35)), 2, False),
    ("stb-a-page", bytes((0xD4, 0x66)), 2, True),
)


class ExtentTests(unittest.TestCase):
    def refused(self, code, *args, **kwargs):
        with self.assertRaises(DecodeFailure) as caught:
            decode_extent(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_all_fifteen_forms_and_dd(self):
        accepted = 0
        for name, payload, length, dd0 in INVENTED:
            for dd in (0, 1):
                with self.subTest(form=name, dd=dd):
                    if dd0 and dd == 1:
                        if name == "stb-a-page":
                            # The extended profile recognizes the documented
                            # word form here; it must not call this STB.
                            self.assertEqual("st-a-page", decode_extent(payload, 0x2000, dd)["formId"])
                        else:
                            self.refused("WrongDD", payload, 0x2000, dd)
                        continue
                    result = decode_extent(payload, 0x2000, dd)
                    self.assertEqual(name, result["formId"])
                    self.assertEqual(length, result["length"])
                    self.assertEqual(0x2000 + length, result["nextPc"])
                    self.assertEqual(dd, result["incomingDd"])
                    self.assertFalse(result["actualExecutionObserved"])
                    self.assertFalse(result["programFetchIsDataOperandRead"])
                    self.assertNotIn("encodedBytes", result)
                    self.assertNotIn("payload", result)
                    self.assertEqual("Preserved", result["registerEffects"]["AH"])
                    accepted += 1
        self.assertEqual(26, accepted)

    def test_entry_load_kills_incoming_dd_but_retains_ah_cf_hc(self):
        for dd in (0, 1):
            value = decode_extent(bytes((0xF4, 0x66)), 0x2000, dd)
            self.assertEqual(0, value["resultingDd"])
            self.assertEqual(["ZF", "DD"], value["flagEffects"]["written"])
            self.assertEqual(["CF", "HC", "OtherPSW"], value["flagEffects"]["preserved"])
            self.assertEqual(0x166, value["dataReads"][0]["address"])
            self.assertEqual([], value["dataWrites"])

    def test_rmw_flags_and_same_value_event_not_deduplicated(self):
        value = decode_extent(bytes((0xC4, 0x66, 0xB7)), 0x2000, 1)
        self.assertEqual(["CF"], value["flagEffects"]["read"])
        self.assertEqual(["CF"], value["flagEffects"]["written"])
        self.assertEqual("ReadModifyWriteRotateThroughCarry", value["dataWrites"][0]["operation"])
        self.assertEqual("RetainFreshOrdinal", value["dataWrites"][0]["sameValueWrite"])
        self.assertTrue(value["dataWrites"][0]["ordered"])
        self.assertEqual(1, value["resultingDd"])

    def test_compare_unsigned_word_immediate_is_not_data_read(self):
        value = decode_extent(bytes((0xB4, 0x66, 0xC0, 0x68, 0x24)), 0x2000, 1)
        self.assertEqual({"kind": "Immediate16", "value": 0x2468}, value["typedOperands"][1])
        self.assertEqual(1, len(value["dataReads"]))
        self.assertEqual(0x166, value["dataReads"][0]["address"])
        self.assertEqual(16, value["dataReads"][0]["widthBits"])
        self.assertEqual("LittleEndian", value["dataReads"][0]["byteOrder"])
        self.assertEqual(["CF", "ZF"], value["flagEffects"]["written"])
        self.assertEqual("Preserved", value["registerEffects"]["AL"])
        self.refused("OddWordOffsetOutsideProfile", bytes((0xB4, 0x67, 0xC0, 0x68, 0x24)), 0x2000, 1)

    def test_local_register_alias(self):
        source = decode_extent(bytes((0x78,)), 0x2000, 0)
        target = decode_extent(bytes((0xC4, 0x66, 0x49)), 0x2000, 1)
        self.assertEqual(0x108, source["dataReads"][0]["address"])
        self.assertEqual(0x109, target["dataWrites"][0]["address"])
        self.assertEqual("LocalRegister", target["dataWrites"][0]["mode"])
        self.assertEqual(8, target["dataWrites"][0]["widthBits"])
        self.assertEqual([], target["flagEffects"]["written"])

    def test_branches_use_ordered_targets_and_correct_predicate(self):
        jlt = decode_extent(bytes((0xCA, 0xF0)), 0x2000, 0)
        self.assertEqual([0x1FF2, 0x2002], jlt["successors"])
        self.assertEqual({"kind": "FlagEquals", "flag": "CF", "value": 1}, jlt["branch"]["predicate"])
        self.assertEqual(-16, jlt["branch"]["signedDelta"])
        self.assertEqual([], jlt["dataReads"])
        for opcode, bit in ((0xEF, 7), (0xED, 5)):
            gate = decode_extent(bytes((opcode, 0x66, 0xF0)), 0x2000, 1)
            self.assertEqual([0x1FF3, 0x2003], gate["successors"])
            self.assertEqual(bit, gate["branch"]["predicate"]["bit"])
            self.assertEqual([], gate["flagEffects"]["written"])
            self.assertEqual([], gate["dataWrites"])

    def test_all_byte_offsets_are_parameters_not_hidden_native_constants(self):
        for offset in range(256):
            value = decode_extent(bytes((0xF4, offset)), 0x2000, 0)
            self.assertEqual(0x100 + offset, value["dataReads"][0]["address"])
        for offset in range(0, 256, 2):
            value = decode_extent(bytes((0xB4, offset, 0xC0, 0x68, 0x24)), 0x2000, 1)
            self.assertEqual(0x100 + offset, value["dataReads"][0]["address"])

    def test_malformed_and_extra_bytes_fail_closed(self):
        for value in (None, bytearray((0x78,)), [], b"", bytes(6)):
            self.refused("ExtentBytesInvalid", value, 0x2000, 0)
        for pc in (True, -1, 0x10000, "8192"):
            self.refused("PcInvalid", bytes((0x78,)), pc, 0)
        for dd in (True, -1, 2, "0", None):
            self.refused("IncomingDdInvalid", bytes((0x78,)), 0x2000, dd)
        for lrb in (0, 0x20, 0x41, True, None):
            self.refused("UnsupportedLrbContext", bytes((0x78,)), 0x2000, 0, lrb=lrb)
        self.refused("TruncatedEncoding", bytes((0xF4,)), 0x2000, 0)
        self.refused("TrailingBytes", bytes((0xF4, 0x66, 0)), 0x2000, 0)
        self.refused("UnsupportedEncoding", bytes((0xFF,)), 0x2000, 0)
        self.refused("OriginSpanOutsideProfile", bytes((0xF4, 0x66)), 0xFFFF, 0)
        self.refused("RelativeTargetOutsideProfile", bytes((0xCA, 0x80)), 0, 0)
        self.refused("RelativeTargetOutsideProfile", bytes((0xCA, 0x7F)), 0xFF80, 0)

    def test_outputs_do_not_share_mutable_effect_objects(self):
        payload = bytes((0xC4, 0x66, 0xD1))
        first = decode_extent(payload, 0x2000, 0)
        expected = copy.deepcopy(first)
        first["flagEffects"]["written"].append("HC")
        first["dataWrites"][0]["address"] = 0
        self.assertEqual(expected, decode_extent(payload, 0x2000, 0))

    def test_word_load_and_store_have_distinct_dd_effects(self):
        for dd in (0, 1):
            loaded = decode_extent(bytes((0xE4, 0x66)), 0x2000, dd)
            self.assertEqual("l-a-page", loaded["formId"])
            self.assertEqual(1, loaded["resultingDd"])
            self.assertEqual("LoadWord", loaded["registerEffects"]["A"])
            self.assertEqual("LoadedWordHighByte_NotPreserved", loaded["registerEffects"]["AH"])
            self.assertEqual(["ZF", "DD"], loaded["flagEffects"]["written"])
            self.assertEqual(16, loaded["dataReads"][0]["widthBits"])
        stored = decode_extent(bytes((0xD4, 0x66)), 0x2000, 1)
        self.assertEqual("st-a-page", stored["formId"])
        self.assertEqual("RequiresDD1", stored["ddApplicability"])
        self.assertEqual(["DD"], stored["flagEffects"]["selectionRead"])
        self.assertEqual(16, stored["dataWrites"][0]["widthBits"])
        self.assertEqual([], stored["flagEffects"]["written"])
        # The same bytes in DD0 are STB, not a claim that DD is irrelevant.
        self.assertEqual("stb-a-page", decode_extent(bytes((0xD4, 0x66)), 0x2000, 0)["formId"])
        self.refused("OddWordOffsetOutsideProfile", bytes((0xE4, 0x67)), 0x2000, 0)
        self.refused("OddWordOffsetOutsideProfile", bytes((0xD4, 0x67)), 0x2000, 1)

    def test_jne_uses_zero_flag_not_carry(self):
        for dd in (0, 1):
            branch = decode_extent(bytes((0xCE, 0xF0)), 0x2000, dd)
            self.assertEqual("jne-rel8", branch["formId"])
            self.assertEqual([0x1FF2, 0x2002], branch["successors"])
            self.assertEqual({"kind": "FlagEquals", "flag": "ZF", "value": 0}, branch["branch"]["predicate"])
            self.assertEqual(["ZF"], branch["flagEffects"]["read"])
            self.assertEqual([], branch["flagEffects"]["written"])
            self.assertEqual([], branch["dataReads"])
        self.refused("RelativeTargetOutsideProfile", bytes((0xCE, 0x80)), 0, 1)
        self.refused("OriginSpanOutsideProfile", bytes((0xCE, 0)), 0xFFFE, 1)

    def test_zero_page_rmw_never_assumes_peripheral_state(self):
        for suffix, form, operation in ((0xD1, "andb-zero-a", "ReadModifyWriteAnd"),
                                        (0xE1, "orb-zero-a", "ReadModifyWriteOr")):
            for dd in (0, 1):
                value = decode_extent(bytes((0xC5, 0x66, suffix)), 0x2000, dd)
                self.assertEqual(form, value["formId"])
                self.assertEqual(0x66, value["dataReads"][0]["address"])
                self.assertEqual("ZeroPage", value["dataReads"][0]["mode"])
                self.assertEqual(operation, value["dataWrites"][0]["operation"])
                self.assertEqual("RetainFreshOrdinal", value["dataWrites"][0]["sameValueWrite"])
                self.assertEqual(["ZF"], value["flagEffects"]["written"])
                self.assertEqual("Preserved", value["registerEffects"]["A"])
                self.assertEqual(dd, value["resultingDd"])
                self.assertEqual("NotEstablishedByInstructionDecoding", value["sfrOrPeripheralStateOwnership"])
        self.refused("UnsupportedEncoding", bytes((0xC5, 0x66, 0)), 0x2000, 0)
        self.refused("TruncatedEncoding", bytes((0xC5, 0x66)), 0x2000, 0)
        self.refused("TrailingBytes", bytes((0xC5, 0x66, 0xE1, 0)), 0x2000, 0)

    def test_context_local_register_writers(self):
        for dd in (0, 1):
            value = decode_extent(bytes((0x98, 0x35)), 0x2000, dd)
            self.assertEqual("movb-r0-imm8", value["formId"])
            self.assertEqual({"kind": "Immediate8", "value": 0x35}, value["typedOperands"][1])
            self.assertEqual(0x108, value["dataWrites"][0]["address"])
            self.assertEqual(8, value["dataWrites"][0]["widthBits"])
            self.assertEqual([], value["flagEffects"]["written"])
            self.assertEqual("Preserved", value["registerEffects"]["A"])
        value = decode_extent(bytes((0x89,)), 0x2000, 1)
        self.assertEqual("st-a-er1", value["formId"])
        self.assertEqual(0x10A, value["dataWrites"][0]["address"])
        self.assertEqual(16, value["dataWrites"][0]["widthBits"])
        self.assertEqual("LittleEndian", value["dataWrites"][0]["byteOrder"])
        self.assertEqual("RequiresDD1", value["ddApplicability"])
        self.assertEqual([], value["flagEffects"]["written"])
        self.refused("WrongDD", bytes((0x89,)), 0x2000, 0)
        self.refused("TrailingBytes", bytes((0x89, 0)), 0x2000, 1)

    def test_prefix_bit_reset_branch_and_byte_compare(self):
        for dd in (0, 1):
            gate = decode_extent(bytes((0xDA, 0x66, 0xF0)), 0x2000, dd)
            self.assertEqual("jbr-page-bit2", gate["formId"])
            self.assertEqual([0x1FF3, 0x2003], gate["successors"])
            self.assertEqual({"kind": "MemoryBitEquals", "address": 0x166,
                              "bit": 2, "value": 0}, gate["branch"]["predicate"])
            self.assertEqual([], gate["flagEffects"]["written"])
            self.assertEqual(dd, gate["resultingDd"])
            comparison = decode_extent(bytes((0xC4, 0x66, 0xC0, 0x35)), 0x2000, dd)
            self.assertEqual("cmpb-page-imm8", comparison["formId"])
            self.assertEqual(4, comparison["length"])
            self.assertEqual({"kind": "Immediate8", "value": 0x35}, comparison["typedOperands"][1])
            self.assertEqual(8, comparison["dataReads"][0]["widthBits"])
            self.assertEqual(0x166, comparison["dataReads"][0]["address"])
            self.assertEqual([], comparison["dataWrites"])
            self.assertEqual(["CF", "ZF"], comparison["flagEffects"]["written"])
            self.assertEqual("UnsignedDataByteLessThanImmediate8", comparison["flagEffects"]["rules"]["CF"])
            self.assertEqual("Preserved", comparison["registerEffects"]["A"])
            self.assertEqual(dd, comparison["resultingDd"])
        self.refused("TruncatedEncoding", bytes((0xC4, 0x66, 0xC0)), 0x2000, 0)
        self.refused("TrailingBytes", bytes((0xC4, 0x66, 0xC0, 0x35, 0)), 0x2000, 0)
        self.refused("RelativeTargetOutsideProfile", bytes((0xDA, 0x66, 0x80)), 0, 0)
        self.refused("RelativeTargetOutsideProfile", bytes((0xDA, 0x66, 0x7F)), 0xFF80, 0)


if __name__ == "__main__":
    unittest.main()
