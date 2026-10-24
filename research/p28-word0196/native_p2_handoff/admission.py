"""Read-only original-image admission for exactly one post-algorithm P2 RMW."""
from hashlib import sha256

from native_entry_continuity.admission import AdmittedEntryOriginal, validate_output_directory
from original_rom_boundary.verify import load_contract

MODE = 'OriginalRomBytes_TechnicalP2HandoffExecution'
P2_PCS = frozenset({0x5596, 0x55C5})


class AdmittedP2Original:
    def __init__(self, rom, profile, output):
        self.entry = AdmittedEntryOriginal(rom, profile, output)
        self.segment = self.entry.original.image.data[0x54F5:0x55C8]
        if type(self.segment) is not bytes or len(self.segment) != 211:
            raise ValueError('ExactUnrelocated211ByteOriginalSegmentRequired')
        self.selected_pcs = self.entry.selected_pcs | P2_PCS
        contract = load_contract()
        self.selected_extents = {
            str(row['pc']): sha256(self.entry.original.image.data[row['pc']:row['pc'] + row['length']]).hexdigest()
            for row in contract['instructionExtents'] if row['pc'] in self.selected_pcs}
        if len(self.selected_pcs) != 26 or len(self.selected_extents) != 26:
            raise ValueError('ClosedTwentySixOriginalExtentsRequired')

    def assert_unchanged(self):
        self.entry.assert_unchanged()
        if self.entry.original.image.data[0x54F5:0x55C8] != self.segment:
            raise ValueError('OriginalP2EntrySegmentChanged')
        return True

    def program_request(self):
        self.assert_unchanged()
        binding = self.entry.program_request()['sourceBinding']
        return {'kind': 'program', 'schemaVersion': 1, 'sourceBinding': binding,
            'segmentBase': 0x54F5, 'segmentBytes': list(self.segment),
            'segmentSha256': sha256(self.segment).hexdigest()}

    def program_identity(self):
        request = self.program_request()
        return {'program_base': 0x54F5, 'program_end_exclusive': 0x55C8,
            'program_sha256': request['segmentSha256'], 'source_binding': request['sourceBinding'],
            'selected_extent_sha256': dict(self.selected_extents)}

    def private_identity(self):
        self.assert_unchanged()
        return {**self.entry.private_identity(), 'classification': MODE,
            'segmentBase': 0x54F5, 'segmentEndExclusive': 0x55C8, 'segmentBytes': 211,
            'segmentSha256': sha256(self.segment).hexdigest(), 'selectedInstructionCount': 26,
            'initialP2NativeOwner': 'NotEstablished', 'p2ConfigurationSource': 'TechnicalPrimaryOutputPrecondition',
            'startupInstructionsExecuted': False, 'physicalP2Owner': 'NotEstablished',
            'physicalP2ElectricalEffect': 'NotObserved', 'firmwareReady': False}
