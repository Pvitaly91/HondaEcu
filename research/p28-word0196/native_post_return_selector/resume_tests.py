"""New49-policy resume, actual-file corruption and orphan tests with fabricated transport only."""
from copy import deepcopy
import unittest
from . import resume,oracle


class PostReturnResumeTests(unittest.TestCase):
    """New49-policy ledger tests; fabricated transport never invokes a CPU."""
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
        join={'passed':True,'milestone':'M2bz','exactBase':resume.BASE,'sourceBindings':rows,
            'sourceFingerprintSha256':sha256(canonical(rows)[:-1]).hexdigest(),'firmwareReady':False}
        cases=list(corpus.iter_cases());wires=[corpus.wire_case(c,'public_fixture') for c in cases]
        expected=[oracle.expected_case(c,'public_fixture') for c in cases];identity=oracle.public_program_identity()
        by_id={c['case_id']:c for c in cases}
        def compare(case,actual,*,program_identity):
            return oracle.compare_observation(case,actual,'public_fixture',program_identity)
        def fake(runner,program,wire,attempt,callback):
            self.calls.append(wire['case_id']);attempt.mkdir(parents=True,exist_ok=False);callback(None)
            ack={'kind':'program_admitted','schemaVersion':1,'classification':'ExplicitInventedPublicPostReturnSelectorFixture',
                'program_sha256':identity['program_sha256'],'entry_pc':0x2000,'body_pc':0x6400,'return_pc':0x2003,'stop_before_pc':0x2011,'selector_address':0x0140,
                'program_node_count':59,'program_windows':identity['program_windows'],'native_generation_ownership':False,
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

    def test_m2bz49_full16_resume_retains_exact16_transport_calls(self):
        run=self.make();summary=run.run()
        from .checkpoint import read_checkpoint
        self.assertEqual((summary['cases'],summary['retiredInstructions'],summary['calRetirements'],summary['rtRetirements']),
            (16,784,16,16))
        self.assertEqual(len(self.calls),16);self.assertEqual(len(set(self.calls)),16)
        self.assertEqual(len(read_checkpoint(run.local_checkpoint)['canonicalRecordHashes']),16)
        retained=(run.output/'canonical.jsonl.gz').read_bytes()
        resumed=self.make();self.assertEqual(resumed.run(),summary)
        self.assertEqual(len(self.calls),16)
        self.assertEqual((run.output/'canonical.jsonl.gz').read_bytes(),retained)

    def test_m2bz49_corrupt_completed_cache_rejected_after_hash_recalculation(self):
        run=self.prefix_one();cached=resume.read_json(run.cache_path(0))
        cached['record']['actual']['report']['prefix']['stack_frame']['generation_ordinal']+=1
        cached['recordSha256']=resume.digest(cached['record'])
        from .checkpoint import atomic_json
        atomic_json(run.cache_path(0),cached,replace=True)
        with self.assertRaises(ValueError):self.make().run()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(resume.read_json(run.cache_path(0)),cached)

    def test_m2bz49_duplicate_completed_case_id_rejected_before_transport(self):
        run=self.prefix_one();duplicate=resume.read_json(run.cache_path(0))
        duplicate['record']['caseIndex']=1
        duplicate['recordSha256']=resume.digest(duplicate['record'])
        from .checkpoint import atomic_json
        atomic_json(run.cache_path(1),duplicate)
        with self.assertRaises(ValueError):self.make().run()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(resume.read_json(run.cache_path(1)),duplicate)


    def test_complete_orphan_transport_is_recovered_without_second_observation(self):
        from .checkpoint import atomic_json
        run=self.make();run.prepare();atomic_json(run.intent_path(0),run.intent(0))
        run.executor(run.runner,run.program,run.wires[0],run.attempt_path(0),lambda _:None)
        self.assertFalse(run.cache_path(0).exists())
        resumed=self.make();summary=resumed.run()
        self.assertEqual((summary['cases'],summary['retiredInstructions']),(16,784))
        self.assertEqual(resumed.recovered_orphan_cases,1);self.assertEqual(len(self.calls),16)
        self.assertEqual(len(set(self.calls)),16)

    def test_ambiguous_partial_orphan_is_preserved_and_never_reexecuted(self):
        from .checkpoint import atomic_json
        run=self.make();run.prepare();atomic_json(run.intent_path(0),run.intent(0));run.attempt_path(0).mkdir(parents=True)
        path=run.attempt_path(0)/'stdout.partial';path.write_bytes(b'{"partial":')
        with self.assertRaisesRegex(ValueError,'OrphanOutcomeUnknown'):self.make().run()
        self.assertEqual(path.read_bytes(),b'{"partial":');self.assertEqual(self.calls,[])

    def test_duplicate_completed_hashes_and_explicit_pause_do_not_start_transport(self):
        from .checkpoint import atomic_json,read_checkpoint
        run=self.prefix_one();state=read_checkpoint(run.local_checkpoint)
        duplicate=deepcopy(state);duplicate['canonicalRecordHashes']*=2
        atomic_json(run.local_checkpoint,duplicate,replace=True)
        with self.assertRaises(ValueError):self.make().run()
        self.assertEqual(len(self.calls),1)
        paused=deepcopy(state);paused.update(phase='PAUSED',currentPhase='PAUSED',status='PAUSED',pauseRequested=True)
        atomic_json(run.local_checkpoint,paused,replace=True)
        with self.assertRaises(resume.PauseRequested):self.make().run()
        self.assertEqual(len(self.calls),1)

    def test_parent41_policy_defaults_remain_unchanged(self):
        from native_cal_rt_continuity.resume import VerificationRun as Parent
        self.assertEqual((Parent.MILESTONE,Parent.BUDGETS),('M2by',{'A':41}))
        self.assertEqual(Parent.BASE,'832b7c382076a8a441e48d2d19917aa43118eb37')
        self.assertEqual((resume.VerificationRun.MILESTONE,resume.VerificationRun.BUDGETS),('M2bz',{'A':49}))
