"""Invented public acknowledgement negatives, without a subprocess or CPU."""
from copy import deepcopy
import unittest

from . import verify


class VerifyTests(unittest.TestCase):
    def test_exact49_node_ack_and_no_native_or_hardware_promotion(self):
        identity = {'program_base': 0x6400, 'program_sha256': 'a' * 64}
        ack = {'kind': 'program_admitted', 'schemaVersion': 1, 'classification': 'ExplicitInventedPublicBelowSecondP2Fixture',
            'program_sha256': 'a' * 64, 'entry_pc': 0x6400, 'program_node_count': 49,
            'native_generation_ownership': False, 'physical_sf_known': False, 'hardware_validated': False}
        verify.verify_ack(ack, identity, True)
        for field, value in [('program_node_count', 24), ('program_node_count', True), ('entry_pc', 0x64A1),
            ('entry_pc', 0x64D0), ('classification', 'OriginalRomBytes_TechnicalBelowSecondP2Execution'),
            ('schemaVersion', True), ('native_generation_ownership', True), ('physical_sf_known', True),
            ('hardware_validated', True), ('program_sha256', 'b' * 64)]:
            altered = deepcopy(ack); altered[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify.verify_ack(altered, identity, True)
        with self.assertRaises(ValueError):
            verify.verify_ack({**ack, 'startup_execution_observed': True}, identity, True)

    def test_private_public_source_paths_cannot_be_combined(self):
        for arguments in ({'public': True, 'rom': 'invented', 'profile': 'invented'},
                          {'public': False, 'rom': None, 'profile': None}, {'public': 1}):
            # Imported controller/contract modules do no work at import; the
            # explicit mode admission must refuse before any source/runtime.
            with self.assertRaises(ValueError):
                verify.verify_execution(output='invented', runner='invented', **arguments)


if __name__ == '__main__':
    unittest.main()
