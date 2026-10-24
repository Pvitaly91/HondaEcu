"""Small invented host/source-admission controls, never CPU observations."""
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from native_entry_continuity import admission, verify


class VerifyTests(unittest.TestCase):
    def test_exact_acknowledgement_and_no_native_or_hardware_promotion(self):
        identity = {'program_base': 0x6200, 'program_sha256': 'a' * 64}
        ack = {'kind': 'program_admitted', 'schemaVersion': 1,
               'classification': 'ExplicitInventedPublicEntryFixture',
               'program_sha256': 'a' * 64, 'entry_pc': 0x6200, 'program_node_count': 24,
               'native_generation_ownership': False, 'physical_sf_known': False, 'hardware_validated': False}
        verify.verify_ack(ack, identity, True)
        for field, value in (('program_node_count', 18), ('program_node_count', True),
                             ('entry_pc', 0x627A), ('program_sha256', 'b' * 64),
                             ('native_generation_ownership', True), ('physical_sf_known', True),
                             ('hardware_validated', True), ('schemaVersion', True),
                             ('classification', admission.MODE)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                verify.verify_ack({**ack, field: value}, identity, True)
        with self.assertRaises(ValueError):
            verify.verify_ack({**ack, 'native_scheduler_verified': True}, identity, True)

    def test_new_source_segment_is_unmodified208_bytes_and24_closed_extents(self):
        # Explicitly invented opaque bytes. This mock tests slicing/identity,
        # not the old source verifier's acceptance or instruction execution.
        image = bytes((i * 11 + 7) & 255 for i in range(32768))
        binding = {'baseCommit': 'synthetic-only'}
        original = SimpleNamespace(image=SimpleNamespace(data=image),
            assert_unchanged=lambda: True, program_request=lambda: {'sourceBinding': binding})
        with patch.object(admission, 'AdmittedOriginal', return_value=original):
            obj = admission.AdmittedEntryOriginal('invented', 'invented', 'invented')
        request, identity = obj.program_request(), obj.program_identity()
        self.assertEqual(request['segmentBytes'], list(image[0x54F5:0x55C5]))
        self.assertEqual(len(request['segmentBytes']), 208)
        self.assertEqual(identity['program_base'], 0x54F5)
        self.assertEqual(identity['program_end_exclusive'], 0x55C5)
        self.assertEqual(len(identity['selected_extent_sha256']), 24)
        self.assertNotIn(str(0x5596), identity['selected_extent_sha256'])
        self.assertNotIn(str(0x55C5), identity['selected_extent_sha256'])
        self.assertEqual(identity['program_sha256'], sha256(image[0x54F5:0x55C5]).hexdigest())

    def test_truncated_or_mutated_original_input_is_not_repaired(self):
        original = SimpleNamespace(image=SimpleNamespace(data=b'\xA5' * 0x5500),
            assert_unchanged=lambda: True, program_request=lambda: {})
        with patch.object(admission, 'AdmittedOriginal', return_value=original), self.assertRaises(ValueError):
            admission.AdmittedEntryOriginal('invented', 'invented', 'invented')
        image = bytearray([0xA5] * 32768)
        original.image.data = bytes(image)
        with patch.object(admission, 'AdmittedOriginal', return_value=original):
            obj = admission.AdmittedEntryOriginal('invented', 'invented', 'invented')
        image[0x54F5] ^= 1
        original.image.data = bytes(image)
        with self.assertRaises(ValueError):
            obj.assert_unchanged()

    def test_source_verification_failure_is_propagated_without_synthetic_fallback(self):
        with (patch.object(admission, 'AdmittedOriginal', side_effect=ValueError('WrongRomSha')),
              self.assertRaisesRegex(ValueError, 'WrongRomSha')):
            admission.AdmittedEntryOriginal('invented', 'invented', 'invented')


if __name__ == '__main__':
    unittest.main()
