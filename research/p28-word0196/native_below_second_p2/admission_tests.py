"""Opaque invented source seams; no original-image or CPU execution claim."""
from hashlib import sha256
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from . import admission, oracle


def opaque_post():
    image = bytearray((i * 13 + 3) & 255 for i in range(32768))
    for pc in oracle.TAIL_FORM:
        raw = oracle.downstream_extent(pc, 'private')
        image[pc:pc + len(raw)] = raw
    from native_post_p2_control.oracle import FORM
    return SimpleNamespace(p2=SimpleNamespace(entry=SimpleNamespace(original=SimpleNamespace(image=SimpleNamespace(data=bytes(image))))),
        selected_extents={str(pc): 'a' * 64 for pc in FORM}, assert_unchanged=lambda: True,
        program_request=lambda: {'sourceBinding': {'fixture': 'InventedOnly_NotRomAdmission'}},
        private_identity=lambda: {'firmwareReady': False})


class AdmissionTests(unittest.TestCase):
    def test_exact_unrelocated403_byte_segment_and49_extents(self):
        previous = opaque_post()
        with patch.object(admission, 'AdmittedPostP2Original', return_value=previous):
            admitted = admission.AdmittedBelowSecondP2Original('invented', 'invented', 'invented')
        image = previous.p2.entry.original.image.data
        request, identity = admitted.program_request(), admitted.program_identity()
        self.assertEqual(request['segmentBytes'], list(image[0x54F5:0x5688]))
        self.assertEqual(identity['program_base'], 0x54F5)
        self.assertEqual(identity['program_end_exclusive'], 0x5688)
        self.assertEqual(identity['program_sha256'], sha256(image[0x54F5:0x5688]).hexdigest())
        self.assertEqual(len(identity['selected_extent_sha256']), 49)
        self.assertEqual(admitted.private_identity()['initialControlNativeOwner'], 'NotEstablished')

    def test_truncation_modified_form_and_source_fence_refuse(self):
        previous = opaque_post()
        original = previous.p2.entry.original.image.data
        for changed in (original[:0x5687], original[:0x5680] + bytes([original[0x5680] ^ 1]) + original[0x5681:]):
            previous.p2.entry.original.image.data = changed
            with patch.object(admission, 'AdmittedPostP2Original', return_value=previous), self.assertRaises(ValueError):
                admission.AdmittedBelowSecondP2Original('invented', 'invented', 'invented')
        previous.p2.entry.original.image.data = original
        with patch.object(admission, 'AdmittedPostP2Original', return_value=previous):
            admitted = admission.AdmittedBelowSecondP2Original('invented', 'invented', 'invented')
        changed = bytearray(original)
        changed[0x5687] ^= 1
        previous.p2.entry.original.image.data = bytes(changed)
        with self.assertRaisesRegex(ValueError, 'OriginalBelowSegmentChanged'):
            admitted.assert_unchanged()

    def test_old_identity_refusal_has_no_synthetic_fallback(self):
        # Actual frozen low-level validators, not injected exceptions or mocked
        # admission functions. All bytes below are invented public fixtures.
        import tempfile
        from pathlib import Path
        from original_rom_boundary.verify import ReadOnlyImage, BoundaryError, read_bound
        from original_rom_execution.admission import M2BS_CONTRACT_SHA256
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / 'invented-image.data'
            raw = bytes((index * 13 + 3) & 255 for index in range(32768))
            candidate.write_bytes(raw)
            with self.assertRaisesRegex(BoundaryError, 'RomSourceIdentityMismatch'):
                ReadOnlyImage(candidate, 32768, '0' * 64)
            # Positive control proves wrong digest, not inaccessible-file refusal.
            selected = ReadOnlyImage(candidate, 32768, sha256(raw).hexdigest())
            self.assertEqual(selected.data, raw)
            self.assertTrue(selected.assert_unchanged())
            source = root / 'invented-source-contract.json'
            source_raw = b'{"inventedOnly":true}\n'
            source.write_bytes(source_raw)
            with self.assertRaisesRegex(BoundaryError, 'SelectedSourceIdentityMismatch'):
                read_bound({'path': str(source), 'bytes': len(source_raw), 'sha256': M2BS_CONTRACT_SHA256})
            self.assertEqual(read_bound({'path': str(source), 'bytes': len(source_raw),
                'sha256': sha256(source_raw).hexdigest()}), source_raw)
