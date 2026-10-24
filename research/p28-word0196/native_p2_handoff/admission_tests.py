"""Opaque invented source controls, not original-image acceptance or execution."""
from hashlib import sha256
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from . import admission


def opaque_entry(image):
    from native_entry_continuity.corpus import PREFIX
    from original_rom_boundary.verify import load_contract
    algorithm = set(load_contract()['algorithmPcs'])
    return SimpleNamespace(original=SimpleNamespace(image=SimpleNamespace(data=image)),
        selected_pcs=set(PREFIX) | algorithm, assert_unchanged=lambda: True,
        program_request=lambda: {'sourceBinding': {'fixture': 'InventedOnly_NotRomAdmission'}},
        private_identity=lambda: {'firmwareReady': False})


class AdmissionTests(unittest.TestCase):
    def test_exact_unrelocated211_byte_segment_and26_extents(self):
        image = bytes((index * 13 + 3) & 255 for index in range(32768))
        with patch.object(admission, 'AdmittedEntryOriginal', return_value=opaque_entry(image)):
            selected = admission.AdmittedP2Original('invented', 'invented', 'invented')
        identity, request = selected.program_identity(), selected.program_request()
        self.assertEqual(request['segmentBytes'], list(image[0x54F5:0x55C8]))
        self.assertEqual(identity['program_base'], 0x54F5)
        self.assertEqual(identity['program_end_exclusive'], 0x55C8)
        self.assertEqual(len(identity['selected_extent_sha256']), 26)
        self.assertTrue({str(0x5596), str(0x55C5)} <= set(identity['selected_extent_sha256']))
        self.assertEqual(identity['program_sha256'], sha256(image[0x54F5:0x55C8]).hexdigest())
        self.assertEqual(selected.private_identity()['initialP2NativeOwner'], 'NotEstablished')

    def test_truncation_and_mutation_are_not_repaired(self):
        entry = opaque_entry(bytes([0xA5] * 0x55C7))
        with patch.object(admission, 'AdmittedEntryOriginal', return_value=entry), self.assertRaises(ValueError):
            admission.AdmittedP2Original('invented', 'invented', 'invented')
        entry = opaque_entry(bytes([0xA5] * 32768))
        with patch.object(admission, 'AdmittedEntryOriginal', return_value=entry):
            selected = admission.AdmittedP2Original('invented', 'invented', 'invented')
        changed = bytearray(entry.original.image.data); changed[0x55C7] ^= 1
        entry.original.image.data = bytes(changed)
        with self.assertRaisesRegex(ValueError, 'OriginalP2EntrySegmentChanged'):
            selected.assert_unchanged()

    def test_old_source_refusal_has_no_synthetic_fallback(self):
        for cause in ('WrongRomSha', 'WrongM2bsSourceIdentity', 'OriginalInstructionByteChanged'):
            with patch.object(admission, 'AdmittedEntryOriginal', side_effect=ValueError(cause)):
                with self.assertRaisesRegex(ValueError, cause):
                    admission.AdmittedP2Original('invented', 'invented', 'invented')


if __name__ == '__main__':
    unittest.main()
