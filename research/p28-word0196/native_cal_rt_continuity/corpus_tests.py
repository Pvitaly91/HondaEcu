"""Closed invented callsite/SSP corpus, independent of CPU observations."""
from copy import deepcopy
import unittest
from . import corpus
class CorpusTests(unittest.TestCase):
    def test_exact_sixteen_four_slots_two_host_sf_states(self):
        cases=list(corpus.iter_cases());c=corpus.coverage(cases)
        self.assertEqual((c['cases'],c['retirements']),(16,656))
        self.assertEqual(c['ssps'],[0x0702,0x0720,0x07FC,0x07FE])
        self.assertEqual(c['hostSfVariants'],[False,True]);self.assertEqual(c['preexistingEqualReturnCanaries'],4)
        self.assertEqual(len({x['case_id'] for x in cases}),16)
    def test_private_public_callsite_not_ready_callee(self):
        for case in corpus.iter_cases():
            for kind,entry in (('private',0x063B),('public_fixture',0x2000)):
                w=corpus.wire_case(case,kind)
                self.assertEqual((w['entry']['pc'],w['entry']['ssp'],len(w['data']),w['budget']),
                    (entry,case['entry']['ssp'],25,41))
            b=corpus.body_case(case)
            self.assertEqual((b['entry']['ssp'],b['entry']['pc'],b['internal_sf']),(case['entry']['ssp']-2,0x54F5,False))
    def test_invalid_callsite_ssp_overlap_canary_budget_refused(self):
        case=next(corpus.iter_cases());variants=[]
        for ssp in (0x0703,0xFFFF,0,0x0108,0x0124,0x0080,0x0700):
            c=deepcopy(case);c['entry']['ssp']=ssp;variants.append(c)
        for pc in (0x54F5,0x5688,0x063E):
            c=deepcopy(case);c['entry']['pc']=pc;variants.append(c)
        c=deepcopy(case);c['budget']=40;variants.append(c)
        c=deepcopy(case);c['stack_canary']['provenance']='NativeFrame';variants.append(c)
        c=deepcopy(case);c['data'][str(case['entry']['ssp'])]^=1;variants.append(c)
        for c in variants:
            with self.subTest(c=c),self.assertRaises(ValueError):corpus.validate_case(c)
