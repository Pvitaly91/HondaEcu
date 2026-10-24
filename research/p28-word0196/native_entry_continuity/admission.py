"""Explicit original-byte source admission; never an execution-state handoff."""
from hashlib import sha256
from pathlib import Path

from original_rom_execution.admission import AdmittedOriginal, validate_output_directory
from original_rom_execution.verify import canonical
from original_rom_boundary.verify import load_contract

MODE = 'OriginalRomBytes_TechnicalCallerToExitExecution'
PREDECESSORS = (0x54F5, 0x54F8, 0x54FA, 0x54FC, 0x54FD, 0x5501)


class AdmittedEntryOriginal:
    """Reuse immutable whole-image verification, not the old 86-byte executor."""
    def __init__(self, rom, profile, output):
        self.original = AdmittedOriginal(rom, profile, output)
        self.segment = self.original.image.data[0x54F5:0x55C5]
        if type(self.segment) is not bytes or len(self.segment) != 208:
            raise ValueError('ExactUnrelocated208ByteOriginalSegmentRequired')
        contract = load_contract()
        self.selected_pcs = set(PREDECESSORS) | set(contract['algorithmPcs'])
        if len(self.selected_pcs) != 24:
            raise ValueError('ClosedSixPlusEighteenOriginalSitesRequired')
        self.selected_extents = {
            str(row['pc']): sha256(self.original.image.data[row['pc']:row['pc'] + row['length']]).hexdigest()
            for row in contract['instructionExtents'] if row['pc'] in self.selected_pcs
        }
        if len(self.selected_extents) != 24:
            raise ValueError('AllSelectedOriginalExtentsRequired')

    def assert_unchanged(self):
        self.original.assert_unchanged()
        if self.original.image.data[0x54F5:0x55C5] != self.segment:
            raise ValueError('OriginalEntrySegmentChanged')
        return True

    def program_request(self):
        self.assert_unchanged()
        # The old method supplies only its established source-binding domain.
        # No CPU is constructed and none of its execution results are imported.
        binding = self.original.program_request()['sourceBinding']
        return {'kind': 'program', 'schemaVersion': 1, 'sourceBinding': binding,
                'segmentBase': 0x54F5, 'segmentBytes': list(self.segment),
                'segmentSha256': sha256(self.segment).hexdigest()}

    def program_identity(self):
        request = self.program_request()
        return {'program_base': 0x54F5, 'program_end_exclusive': 0x55C5,
                'program_sha256': request['segmentSha256'], 'source_binding': request['sourceBinding'],
                'selected_extent_sha256': dict(self.selected_extents)}

    def private_identity(self):
        report = self.original.report
        return {'classification': MODE, 'rom': report['rom'],
                'profile': self.original.profile_binding,
                'm2bsContract': self.original.contract_binding,
                'sourceVerificationSummary': report['publicSummary'],
                'sourceVerificationDigest': sha256(canonical(report)).hexdigest(),
                'selectedSourceFences': report['selectedSourceFinalFences'],
                'historicalSourceRelationships': report['historical']['publicSummary'],
                'historicalRelationshipClassification': 'QualifiedPreviousSourceCpuScope_NotNewCpuOwnership',
                'newSessionExecutedProducer05EB': False,
                'newSessionDATA0196Owner': 'TechnicalSeeded_NoNativeGenerationOwner',
                'segmentBase': 0x54F5, 'segmentEndExclusive': 0x55C5, 'segmentBytes': 208,
                'segmentSha256': sha256(self.segment).hexdigest(), 'relocated': False,
                'nativeSchedulerOwnershipClaimed': False, 'strictEvidenceBoundCaseCount': 0,
                'factoryAuthenticity': 'Unknown', 'firmwareReady': False}
