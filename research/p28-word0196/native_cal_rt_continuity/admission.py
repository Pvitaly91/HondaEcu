"""Two immutable source-verified windows, with no gap, relocation or return decode."""
from hashlib import sha256
from native_below_second_p2.admission import AdmittedBelowSecondP2Original, validate_output_directory
from . import corpus


class AdmittedCalRtOriginal:
    def __init__(self, rom, profile, output):
        self.below = AdmittedBelowSecondP2Original(rom, profile, output)
        image = self.below.post.p2.entry.original.image.data
        self.caller, self.body = image[0x063B:0x063E], image[0x54F5:0x5689]
        # Reviewed CAL addr16 and RT forms, independent of production decoder.
        if (len(self.caller) != 3 or self.caller[0] != 0x32
                or int.from_bytes(self.caller[1:], 'little') != corpus.BODY_BASE or self.body[-1:] != bytes((0x01,))):
            raise ValueError('ReviewedOriginalCalAndRtFormsRequired')
        if len(self.caller) != 3 or len(self.body) != 404 or self.body[:-1] != self.below.segment:
            raise ValueError('TwoExactOriginalWindowsRequired')
        self.selected_extents = {**self.below.selected_extents,
            str(0x063B): sha256(self.caller).hexdigest(), str(0x5688): sha256(self.body[-1:]).hexdigest()}
        if len(self.selected_extents) != 51:
            raise ValueError('ClosedFiftyOneOriginalSitesRequired')

    def assert_unchanged(self):
        self.below.assert_unchanged()
        image = self.below.post.p2.entry.original.image.data
        if image[0x063B:0x063E] != self.caller or image[0x54F5:0x5689] != self.body:
            raise ValueError('OriginalCallOrBodyWindowChanged')
        return True

    def program_request(self):
        self.assert_unchanged()
        return {'kind': 'program', 'schemaVersion': 1,
            'sourceBinding': self.below.program_request()['sourceBinding'],
            'callerBase': 0x063B, 'callerBytes': list(self.caller), 'callerSha256': sha256(self.caller).hexdigest(),
            'bodyBase': 0x54F5, 'bodyBytes': list(self.body), 'bodySha256': sha256(self.body).hexdigest()}

    def program_identity(self):
        request = self.program_request()
        return {'program_base': 0x54F5, 'program_end_exclusive': 0x5689,
            'program_sha256': sha256(self.caller + self.body).hexdigest(),
            'source_binding': request['sourceBinding'], 'selected_extent_sha256': dict(self.selected_extents),
            'program_windows': [{'base': base, 'end_exclusive': base + len(raw), 'sha256': sha256(raw).hexdigest(),
                'byte_count': len(raw), 'role': role} for base,raw,role in (
                    (0x063B,self.caller,'CallerCAL'), (0x54F5,self.body,'CalleeBodyAndRT'))]}

    def private_identity(self):
        self.assert_unchanged()
        return {**{k:v for k,v in self.below.private_identity().items() if k not in ('rt5688Executed','returnFrame')}, 'classification': corpus.MODE,
            'programWindows': self.program_identity()['program_windows'], 'selectedInstructionCount': 51,
            'segmentBase':0x54F5,'segmentEndExclusive':0x5689,'segmentBytes':404,'segmentSha256':sha256(self.body).hexdigest(),
            'returnFrameRequirement':'MustBeFreshCurrentExecutionCALWriter','rt5688ExecutionRequired':True,
            'initialDATA0196Owner': corpus.DATA0196_OWNER,
            'nativeCallerScheduler': 'NotEstablished', 'physicalNativeStackSafety': 'NotEstablished',
            'returnPcDecodedOrExecuted': False, 'firmwareReady': False}
