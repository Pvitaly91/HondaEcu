"""Read-only M2bs admission plus five independently reviewed control extents."""
from hashlib import sha256

from native_p2_handoff.admission import AdmittedP2Original, validate_output_directory
from . import corpus
from .oracle import CONTROL_FORM, control_extent


class AdmittedPostP2Original:
    def __init__(self, rom, profile, output):
        self.p2 = AdmittedP2Original(rom, profile, output)
        self.segment = self.p2.entry.original.image.data[0x54F5:0x55D2]
        if type(self.segment) is not bytes or len(self.segment) != 221:
            raise ValueError('ExactUnrelocated221ByteOriginalSegmentRequired')
        self.selected_extents = dict(self.p2.selected_extents)
        for pc, row in CONTROL_FORM.items():
            raw = self.p2.entry.original.image.data[pc:pc + row[3]]
            if raw != control_extent(pc, 'private'):
                raise ValueError('OriginalControlExtentDoesNotMatchReviewedManufacturerForm')
            self.selected_extents[str(pc)] = sha256(raw).hexdigest()
        if len(self.selected_extents) != 31:
            raise ValueError('ClosedThirtyOneOriginalExtentsRequired')

    def assert_unchanged(self):
        self.p2.assert_unchanged()
        if self.p2.entry.original.image.data[0x54F5:0x55D2] != self.segment:
            raise ValueError('OriginalPostP2SegmentChanged')
        return True

    def program_request(self):
        self.assert_unchanged()
        return {'kind': 'program', 'schemaVersion': 1,
            'sourceBinding': self.p2.program_request()['sourceBinding'],
            'segmentBase': 0x54F5, 'segmentBytes': list(self.segment),
            'segmentSha256': sha256(self.segment).hexdigest()}

    def program_identity(self):
        request = self.program_request()
        return {'program_base': 0x54F5, 'program_end_exclusive': 0x55D2,
            'program_sha256': request['segmentSha256'], 'source_binding': request['sourceBinding'],
            'selected_extent_sha256': dict(self.selected_extents)}

    def private_identity(self):
        self.assert_unchanged()
        return {**self.p2.private_identity(), 'classification': corpus.MODE,
            'segmentBase': 0x54F5, 'segmentEndExclusive': 0x55D2, 'segmentBytes': 221,
            'segmentSha256': sha256(self.segment).hexdigest(), 'selectedInstructionCount': 31,
            'initialControlNativeOwner': 'NotEstablished', 'controlConfigurationSource': corpus.CONTROL_PROVENANCE,
            'timerEvolutionModeled': False, 'irqDeliveryInjected': False, 'firmwareReady': False}
