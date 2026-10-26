"""Unchanged historical TestCase exercises current shared M2bx defaults.
Fixtures are fabricated transports, never CPU execution evidence.
"""
from copy import deepcopy
import unittest
from native_below_second_p2.resume_tests import ResumeTests as HistoricalM2bxResumeCompatibilityTests
from native_below_second_p2 import resume as historical
from . import resume,oracle
class CalRtPolicyTests(unittest.TestCase):
    def test_historical_defaults_not_rebound_by_subclass(self):
        self.assertEqual(historical.VerificationRun.MILESTONE,'M2bx')
        self.assertEqual(historical.VerificationRun.BUDGETS,{'A':39})
        self.assertEqual(historical.VerificationRun.BASE,'4d99ebcf02016df3dfa0a6d035bb01def4b170cd')
        self.assertEqual((resume.VerificationRun.MILESTONE,resume.VerificationRun.BUDGETS),('M2by',{'A':41}))
        self.assertIsNot(resume.VerificationRun.read_checkpoint,historical.VerificationRun.read_checkpoint)
    def test_two_window_domain_rejects_padding_mapping_and_wrong_return(self):
        r=object.__new__(resume.VerificationRun);i=oracle.public_program_identity();r.validate_program_domain(i,True);edits=[]
        v=deepcopy(i);v['program_windows'][0]['end_exclusive']+=1;edits.append(v)
        v=deepcopy(i);v['program_windows'].reverse();edits.append(v)
        v=deepcopy(i);v['program_windows'][1]['byte_count']+=4096;edits.append(v)
        v=deepcopy(i);v['program_base']=0x2000;edits.append(v)
        for v in edits:
            with self.assertRaises(ValueError):r.validate_program_domain(v,True)
    def test_no_unqualified_inherited_negative_execution_claim(self):
        self.assertNotIn('RT5688NotExecuted',resume.UNRESOLVED);self.assertNotIn('ReturnFrameNotEstablished',resume.UNRESOLVED)
        for v in ('FullNativeCallerSchedulerNotEstablished','EnclosingIRQFrameNotEstablished','PhysicalNativeStackSafetyNotEstablished'):
            self.assertIn(v,resume.UNRESOLVED)


class CalRtResumeTests(unittest.TestCase):
    """New41-policy ledger tests; fabricated transport never invokes a CPU."""
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve();self.calls=[]
        self.runner=self.root/'invented-nonexecutable-runner';self.runner.write_bytes(b'InventedOnly_NoCpuInvocation')

    def make(self):
        from . import corpus
        from .oracle_tests import invented_observation
        from .checkpoint import canonical,atomic_json
        from hashlib import sha256
        rows=[{'path':'invented-fixture.py','mode':'100644','bytes':1,'sha256':'1'*64}]
        join={'passed':True,'milestone':'M2by','exactBase':resume.BASE,'sourceBindings':rows,
            'sourceFingerprintSha256':sha256(canonical(rows)[:-1]).hexdigest(),'firmwareReady':False}
        cases=list(corpus.iter_cases());wires=[corpus.wire_case(c,'public_fixture') for c in cases]
        expected=[oracle.expected_case(c,'public_fixture') for c in cases];identity=oracle.public_program_identity()
        by_id={c['case_id']:c for c in cases}
        def compare(case,actual,*,program_identity):
            return oracle.compare_observation(case,actual,'public_fixture',program_identity)
        def fake(runner,program,wire,attempt,callback):
            self.calls.append(wire['case_id']);attempt.mkdir(parents=True,exist_ok=False);callback(None)
            ack={'kind':'program_admitted','schemaVersion':1,'classification':'ExplicitInventedPublicCalRtFrameContinuityFixture',
                'program_sha256':identity['program_sha256'],'entry_pc':0x2000,'body_pc':0x6400,'return_pc':0x2003,
                'program_node_count':51,'program_windows':identity['program_windows'],'native_generation_ownership':False,
                'physical_sf_known':False,'hardware_validated':False}
            actual=invented_observation(by_id[wire['case_id']])
            stdout,stderr=attempt/'stdout.partial',attempt/'stderr.partial'
            stdout.write_bytes(canonical(ack)+canonical(actual));stderr.write_bytes(b'')
            transport={'schemaVersion':1,'runnerExitCode':0,'timedOut':False,'stdout':resume.file_binding(stdout),
                'stderr':resume.file_binding(stderr),'caseId':wire['case_id'],'oneRunnerProcessOneCase':True}
            atomic_json(attempt/'transport.json',transport)
            return ack,actual,transport
        return resume.VerificationRun(output=self.root/'evidence',runner=self.runner,source_join=join,
            source_supplier=lambda:deepcopy(join),cases=cases,wire_cases=wires,expected=expected,
            program={'kind':'public_fixture','schemaVersion':1},program_identity=identity,
            compare=compare,public=True,executor=fake)

    def prefix_one(self):
        run=self.make();run.prepare()
        from .checkpoint import atomic_json
        atomic_json(run.intent_path(0),run.intent(0))
        ack,actual,transport=run.executor(run.runner,run.program,run.wires[0],run.attempt_path(0),lambda _:None)
        run.publish_case(0,run.make_record(0,ack,actual),transport);run.checkpoint('ROM_EXECUTION')
        return run

    def test_m2by41_full16_resume_retains_exact16_transport_calls(self):
        run=self.make();summary=run.run()
        from .checkpoint import read_checkpoint
        self.assertEqual((summary['cases'],summary['retiredInstructions'],summary['calRetirements'],summary['rtRetirements']),
            (16,656,16,16))
        self.assertEqual(len(self.calls),16);self.assertEqual(len(set(self.calls)),16)
        self.assertEqual(len(read_checkpoint(run.local_checkpoint)['canonicalRecordHashes']),16)
        retained=(run.output/'canonical.jsonl.gz').read_bytes()
        resumed=self.make();self.assertEqual(resumed.run(),summary)
        self.assertEqual(len(self.calls),16)
        self.assertEqual((run.output/'canonical.jsonl.gz').read_bytes(),retained)

    def test_m2by41_corrupt_completed_cache_rejected_after_hash_recalculation(self):
        run=self.prefix_one();cached=resume.read_json(run.cache_path(0))
        cached['record']['actual']['report']['stack_frame']['generation_ordinal']+=1
        cached['recordSha256']=resume.digest(cached['record'])
        from .checkpoint import atomic_json
        atomic_json(run.cache_path(0),cached,replace=True)
        with self.assertRaises(ValueError):self.make().run()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(resume.read_json(run.cache_path(0)),cached)

    def test_m2by41_duplicate_completed_case_id_rejected_before_transport(self):
        run=self.prefix_one();duplicate=resume.read_json(run.cache_path(0))
        duplicate['record']['caseIndex']=1
        duplicate['recordSha256']=resume.digest(duplicate['record'])
        from .checkpoint import atomic_json
        atomic_json(run.cache_path(1),duplicate)
        with self.assertRaises(ValueError):self.make().run()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(resume.read_json(run.cache_path(1)),duplicate)
