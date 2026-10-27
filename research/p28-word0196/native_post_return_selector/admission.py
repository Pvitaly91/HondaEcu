"""Verified original caller/post-return and callee windows, without relocation."""
from hashlib import sha256
from native_cal_rt_continuity.admission import AdmittedCalRtOriginal,validate_output_directory
from . import corpus


class AdmittedPostReturnOriginal:
    def __init__(self,rom,profile,output):
        from .oracle import post_return_extent
        self.cal=AdmittedCalRtOriginal(rom,profile,output)
        image=self.cal.below.post.p2.entry.original.image.data
        self.caller,self.body=image[0x063B:0x064C],image[0x54F5:0x5689]
        if len(self.caller)!=17 or len(self.body)!=404 or self.caller[:3]!=self.cal.caller or self.body!=self.cal.body:
            raise ValueError('ExactUnrelocatedSeventeenAnd404ByteOriginalWindowsRequired')
        self.selected_extents=dict(self.cal.selected_extents)
        for pc in corpus.POST_PCS:
            reviewed=post_return_extent(pc,'private');actual=image[pc:pc+len(reviewed)]
            if actual!=reviewed:raise ValueError('OriginalPostReturnExtentDoesNotMatchIndependentlyReviewedForm')
            self.selected_extents[str(pc)]=sha256(actual).hexdigest()
        if len(self.selected_extents)!=59:raise ValueError('ClosedFiftyNineOriginalSitesRequired')

    def assert_unchanged(self):
        self.cal.assert_unchanged();image=self.cal.below.post.p2.entry.original.image.data
        if image[0x063B:0x064C]!=self.caller or image[0x54F5:0x5689]!=self.body:
            raise ValueError('OriginalCallerPostReturnOrBodyWindowChanged')
        return True

    def program_request(self):
        self.assert_unchanged()
        return {'kind':'program','schemaVersion':1,'sourceBinding':self.cal.program_request()['sourceBinding'],
            'callerBase':0x063B,'callerBytes':list(self.caller),'callerSha256':sha256(self.caller).hexdigest(),
            'bodyBase':0x54F5,'bodyBytes':list(self.body),'bodySha256':sha256(self.body).hexdigest()}

    def program_identity(self):
        request=self.program_request()
        return {'program_base':0x54F5,'program_end_exclusive':0x5689,'program_sha256':sha256(self.caller+self.body).hexdigest(),
            'source_binding':request['sourceBinding'],'selected_extent_sha256':dict(self.selected_extents),
            'program_windows':[{'base':base,'end_exclusive':base+len(raw),'sha256':sha256(raw).hexdigest(),
                'byte_count':len(raw),'role':role} for base,raw,role in (
                    (0x063B,self.caller,'CallerCALAndPostReturn'),(0x54F5,self.body,'CalleeBodyAndRT'))]}

    def private_identity(self):
        self.assert_unchanged()
        return {**{k:v for k,v in self.cal.private_identity().items() if k!='returnPcDecodedOrExecuted'},'classification':corpus.MODE,'programWindows':self.program_identity()['program_windows'],
            'selectedInstructionCount':59,'callerWindowBytes':17,'callerWindowEndExclusive':0x064C,
            'postReturnExecutionRequired':True,'postReturnInstructionsRequired':8,'postReturnTerminalPc':0x064C,'branch064CExecuted':False,
            'initialSelectorSource':corpus.SELECTOR_CLASSIFICATION,'initialSelectorNativeGeneration':None,
            'selectorWriterRequirement':'CurrentExecutionNativeSelectorWriter064A','nextEventSelectorHandoff':'NotEstablished',
            'nativeCallerScheduler':'NotEstablished','physicalNativeStackSafety':'NotEstablished','firmwareReady':False}
