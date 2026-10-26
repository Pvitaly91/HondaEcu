"""M2bs/M2bw read-only source admission plus eighteen reviewed Below forms."""
from hashlib import sha256
from native_post_p2_control.admission import AdmittedPostP2Original, validate_output_directory
from . import corpus
from .oracle import TAIL_FORM, downstream_extent

class AdmittedBelowSecondP2Original:
    def __init__(self, rom, profile, output):
        self.post = AdmittedPostP2Original(rom, profile, output)
        self.segment = self.post.p2.entry.original.image.data[0x54F5:0x5688]
        if type(self.segment) is not bytes or len(self.segment) != 403:
            raise ValueError('ExactUnrelocated403ByteOriginalSegmentRequired')
        self.selected_extents = dict(self.post.selected_extents)
        for pc, row in TAIL_FORM.items():
            raw = self.post.p2.entry.original.image.data[pc:pc + row[3]]
            if raw != downstream_extent(pc, 'private'):
                raise ValueError('OriginalBelowExtentDoesNotMatchReviewedManufacturerForm')
            self.selected_extents[str(pc)] = sha256(raw).hexdigest()
        if len(self.selected_extents) != 49:
            raise ValueError('ClosedFortyNineOriginalExtentsRequired')

    def assert_unchanged(self):
        self.post.assert_unchanged()
        if self.post.p2.entry.original.image.data[0x54F5:0x5688] != self.segment:
            raise ValueError('OriginalBelowSegmentChanged')
        return True

    def program_request(self):
        self.assert_unchanged()
        return {'kind': 'program', 'schemaVersion': 1,
            'sourceBinding': self.post.program_request()['sourceBinding'], 'segmentBase': 0x54F5,
            'segmentBytes': list(self.segment), 'segmentSha256': sha256(self.segment).hexdigest()}

    def program_identity(self):
        request = self.program_request()
        return {'program_base': 0x54F5, 'program_end_exclusive': 0x5688,
            'program_sha256': request['segmentSha256'], 'source_binding': request['sourceBinding'],
            'selected_extent_sha256': dict(self.selected_extents)}

    def private_identity(self):
        self.assert_unchanged()
        return {**self.post.private_identity(), 'classification': corpus.MODE,
            'segmentBase': 0x54F5, 'segmentEndExclusive': 0x5688, 'segmentBytes': 403,
            'segmentSha256': sha256(self.segment).hexdigest(), 'selectedInstructionCount': 49,
            'returnFrame': 'NotEstablished', 'rt5688Executed': False,
            'initialControlNativeOwner': 'NotEstablished', 'controlConfigurationSource': corpus.CONTROL_PROVENANCE,
            'timerEvolutionModeled': False, 'irqDeliveryInjected': False, 'firmwareReady': False}
