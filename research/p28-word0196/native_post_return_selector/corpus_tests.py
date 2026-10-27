"""Once-only source, strict0..3 and preserved entry-context admission."""
from copy import deepcopy
import unittest
from . import corpus
class CorpusTests(unittest.TestCase):
    def test_sixteen_cases_784_retirements_four_each_and_reachable_sbr_history(self):
        cases=list(corpus.iter_cases());c=corpus.coverage(cases)
        self.assertEqual((c['cases'],c['retirements']),(16,784));self.assertEqual(c['selectorCounts'],{0:4,1:4,2:4,3:4})
        self.assertEqual(c['ssps'],[0x0702,0x0720,0x07FC,0x07FE]);self.assertEqual(c['hostSfVariants'],[False,True])
        self.assertEqual(c['sbrTargetBitOldStateCounts'],{'0:1':8,'1:0':8})
        for case in cases:
            for kind,address in (('private',0x013C),('public_fixture',0x0140)):
                w=corpus.wire_case(case,kind);self.assertNotIn(str(address),w['data']);self.assertEqual(len(w['data']),25)
                self.assertEqual(w['selector_snapshot'],case['selector_snapshot']);self.assertEqual(w['budget'],49)
    def test_outside_missing_repeated_ready_per_event_selector_and_wrong_context_refused(self):
        case=next(corpus.iter_cases());variants=[]
        for value in (-1,4,255,True,None):
            c=deepcopy(case);c['selector_snapshot']['value']=value;variants.append(c)
        c=deepcopy(case);c.pop('selector_snapshot');variants.append(c)
        for field in ('finalSelector','expectedSelector','per_event_selector','repeated_selector_initialization'):
            c=deepcopy(case);c[field]=1;variants.append(c)
        for key,value in (('pc',0x063E),('pc',0x064A),('lrb',0x20),('scb',7)):
            c=deepcopy(case);c['entry'][key]=value;variants.append(c)
        c=deepcopy(case);c['budget']=48;variants.append(c)
        c=deepcopy(case);c['data'][str(0x013C)]=1;variants.append(c)
        for c in variants:
            with self.subTest(c=c),self.assertRaises(ValueError):corpus.validate_case(c)
