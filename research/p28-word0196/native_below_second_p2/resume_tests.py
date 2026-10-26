"""Invented file/process seams only: these tests never spawn a CPU runner."""
from collections import Counter
from copy import deepcopy
import gzip
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_below_second_p2 import resume as r
from native_below_second_p2.checkpoint import atomic_json, canonical, read_checkpoint


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.runner = self.root / 'invented-nonexecutable-runner'
        self.runner.write_bytes(b'InventedOnly_NoCpuInvocation')
        self.rows = [{'path': 'invented.py', 'mode': '100644', 'bytes': 1, 'sha256': '1' * 64}]
        self.join = {'passed': True, 'milestone': 'M2bx', 'exactBase': r.BASE, 'sourceBindings': self.rows,
                     'sourceFingerprintSha256': sha256(canonical(self.rows)[:-1]).hexdigest(), 'firmwareReady': False}
        self.calls = []

    def cases(self, kind):
        paths = ['A'] * 16 if kind == 'positive' else []
        return [{'case_id': f'invented-{index:02d}', 'path': path, 'budget': r.BUDGETS[path],
                 'p2_snapshot': {'value': 0 if index % 2 == 0 else 255, 'p2io': 255, 'p2sf': 7,
                                 'provenance': 'TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration'},
                 'control_snapshot': {'tcon0': 131, 'trnsit_implemented_flags': 0,
                    'provenance': 'TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration'}}
                for index, path in enumerate(paths)]

    def make(self, *, public=True, kind='positive', output=None, global_checkpoint=None, executor=None, cases=None):
        cases = self.cases(kind) if cases is None else cases
        expected = [{'case_id': case['case_id'], 'path': case['path'], 'authority': 'InventedTestExpectation_NoCpu',
                     'initial_p2': case['p2_snapshot']['value'], 'final_p2': case['p2_snapshot']['value'],
                     'same_value_p2_write': True, 'final_p2_zf': case['p2_snapshot']['value'] == 0,
                     'control_initial': [131, 0], 'control_instruction_retirements': 4 if case['path'] == 'A' else 1} for case in cases]
        by_id = {row['case_id']: row for row in expected}
        wires = [{**case, 'kind': 'case', 'family': 'invented-file-transport', 'entry': {}, 'data': {}, 'internal_sf': False} for case in cases]
        identity = {'program_base': 0x6400 if public else 0x54F5, 'program_end_exclusive': 0x6593 if public else 0x5688,
                    'program_sha256': '2' * 64, 'source_binding': None, 'selected_extent_sha256': {str(i): '3' * 64 for i in range(49)}}
        def compare(case, actual, *, program_identity):
            if actual.get('invented_test_value') != 'InventedOnly_NotActualCpuEvidence':
                raise ValueError('InventedIndependentValueMismatch')
            return {'passed': True, 'expected': by_id[case['case_id']], 'comparison': {'inventedComparatorOnly': True}}
        def fake(runner, program, wire, attempt, callback):
            self.calls.append(wire['case_id'])
            attempt.mkdir(parents=True, exist_ok=False)
            callback(None)
            ack = {'kind': 'program_admitted', 'schemaVersion': 1,
                   'classification': 'ExplicitInventedPublicBelowSecondP2Fixture' if public else r.PRIVATE_MODE,
                   'program_sha256': identity['program_sha256'], 'entry_pc': identity['program_base'],
                   'program_node_count': 49, 'native_generation_ownership': False,
                   'physical_sf_known': False, 'hardware_validated': False}
            path, budget = wire['path'], wire['budget']
            terminal = 0x5688 if path == 'A' else 0x559D
            if public:
                terminal += 0x6400 - 0x54F5
            p2_pc = (0x55C5 if path == 'A' else 0x5596) + (0x6400 - 0x54F5 if public else 0)
            latch = wire['p2_snapshot']['value']
            actual = {'kind': 'below_second_p2_observation', 'accepted': True,
                'actual_successful_step_returns': budget, 'invented_test_value': 'InventedOnly_NotActualCpuEvidence',
                'report': {'positive_completed': True, 'boundary_only': False,
                    'actual_handoff_observed': True, 'stop_before_pc': terminal,
                    'native_predecessor_retirements': 6, 'algorithm_retirements': 10,
                    'p2_instruction_retirements': 2, 'control_instruction_retirements': 4,
                    'below_instruction_retirements': 18,
                    'peripheral_control_journal': [{'pc': terminal - 1,
                        'address': 64, 'width': 8, 'operation': operation,
                        'space': 'PeripheralControl', 'value': 131, 'same_value': False}
                        for operation in ['Read','Read','Write'] * 2],
                    'p2_initial': latch, 'p2_final': latch,
                    'p2_generation': {'inventedGeneration': 1}, 'second_p2_generation': {'inventedGeneration': 2},
                    'control_generation': {'inventedGeneration': 1}, 'second_control_generation': {'inventedGeneration': 2},
                    'p2_generations': [{'inventedGeneration': 1},{'inventedGeneration': 2}],
                    'control_generations': [{'inventedGeneration': 1},{'inventedGeneration': 2}],
                    'peripheral_p2_journal': [
                        {'pc': p2_pc, 'address': 36, 'width': 8, 'operation': operation,
                         'space': 'PeripheralP2', 'value': latch,
                         'same_value': True if operation == 'Write' else None}
                        for operation in ['Read', 'Write'] * 2]}}
            stdout, stderr = attempt / 'stdout.partial', attempt / 'stderr.partial'
            stdout.write_bytes(canonical(ack) + canonical(actual))
            stderr.write_bytes(b'')
            transport = {'schemaVersion': 1, 'runnerExitCode': 0, 'timedOut': False,
                         'stdout': r.file_binding(stdout), 'stderr': r.file_binding(stderr),
                         'caseId': wire['case_id'], 'oneRunnerProcessOneCase': True}
            atomic_json(attempt / 'transport.json', transport)
            return ack, actual, transport
        return r.VerificationRun(output=output or self.root / 'results', runner=self.runner,
            source_join=self.join, source_supplier=lambda: deepcopy(self.join), cases=cases, wire_cases=wires,
            expected=expected, program={'kind': 'public_fixture' if public else 'program', 'schemaVersion': 1},
            program_identity=identity, compare=compare, public=public, corpus_kind=kind,
            global_checkpoint=global_checkpoint, executor=executor or fake)

    def test_complete16_and_repeat_invocation_does_not_repeat_observations(self):
        run = self.make()
        summary = run.run()
        raw = gzip.decompress((run.output / 'canonical.jsonl.gz').read_bytes())
        self.assertEqual(summary['cases'], 16)
        self.assertEqual(summary['retiredInstructions'], 624)
        self.assertEqual(summary['p2Retirements'], 32)
        self.assertEqual(summary['functionalPeripheralP2Reads'], 32)
        self.assertEqual(summary['functionalPeripheralP2Writes'], 32)
        self.assertEqual(summary['sameValueP2Writes'], 32)
        self.assertEqual(summary['zeroResultP2Writes'], 8)
        self.assertEqual(summary['cycleAccounting'], r.CYCLE_ACCOUNTING)
        self.assertIn('DiagnosticCycleTimingEquivalenceNotEstablished', summary['unresolvedStatuses'])
        self.assertEqual(summary['canonicalFieldExclusions'], [])
        self.assertEqual(summary['paths'], {'A': 16})
        self.assertEqual(len(self.calls), 16)
        self.assertEqual(run.run(), summary)
        self.assertEqual(len(self.calls), 16)
        self.assertEqual(gzip.decompress((run.output / 'canonical.jsonl.gz').read_bytes()), raw)
        self.assertEqual(len(raw.splitlines()), 16)

    def test_completed_orphan_transport_is_recovered_not_reexecuted(self):
        run = self.make()
        run.prepare()
        atomic_json(run.intent_path(0), run.intent(0))
        run.executor(run.runner, run.program, run.wires[0], run.attempt_path(0), lambda _: None)
        self.assertFalse(run.cache_path(0).exists())
        resumed = self.make()
        self.assertEqual(resumed.run()['cases'], 16)
        self.assertEqual(resumed.recovered_orphan_cases, 1)
        self.assertEqual(len(self.calls), 16)
        self.assertEqual(Counter(self.calls), Counter(case['case_id'] for case in resumed.cases))

    def test_cache_one_ahead_of_checkpoint_is_recovered(self):
        run = self.make()
        run.prepare()
        atomic_json(run.intent_path(0), run.intent(0))
        ack, actual, transport = run.executor(run.runner, run.program, run.wires[0], run.attempt_path(0), lambda _: None)
        run.publish_case(0, run.make_record(0, ack, actual), transport)
        self.assertEqual(len(read_checkpoint(run.local_checkpoint)['canonicalRecordHashes']), 0)
        self.assertEqual(self.make().run()['cases'], 16)
        self.assertEqual(len(self.calls), 16)

    def test_partial_orphan_is_preserved_and_never_reexecuted(self):
        run = self.make()
        run.prepare()
        atomic_json(run.intent_path(0), run.intent(0))
        run.attempt_path(0).mkdir(parents=True)
        partial = run.attempt_path(0) / 'stdout.partial'
        partial.write_bytes(b'{"partial":')
        with self.assertRaisesRegex(r.ResumeError, 'OrphanOutcomeUnknown'):
            self.make().run()
        self.assertEqual(partial.read_bytes(), b'{"partial":')
        self.assertEqual(self.calls, [])
        self.assertEqual(read_checkpoint(run.local_checkpoint)['status'], 'BLOCKED')

    def test_two_global_modes_do_not_clobber_completed_private_or_public(self):
        state = self.root / 'GLOBAL.json'
        atomic_json(state, {'milestone': 'M2bx', 'schemaVersion': 1,
                           'sourceFingerprint': self.join['sourceFingerprintSha256'], 'completedSteps': [],
                           'branch': r.BRANCH, 'baseSha': r.BASE})
        for public in (False, True):
            output = self.root / ('public-positive' if public else 'private-positive')
            summary = self.make(public=public, output=output, global_checkpoint=state).run()
            self.assertEqual(summary['positiveCases'], 16)
            self.assertEqual(summary['OriginalRomP2HandoffObserved'], not public)
            self.assertFalse(summary['initialNativeP2OwnerEstablished'])
        modes = read_checkpoint(state)['runtimeModes']
        self.assertEqual(set(modes), {'private:positive', 'public:positive'})
        self.assertEqual({key: len(value['canonicalRecordHashes']) for key, value in modes.items()},
                         {'private:positive': 16, 'public:positive': 16})

    def test_corrupted_cached_actual_is_rejected_even_with_updated_record_hash(self):
        run = self.make()
        run.run()
        saved = r.read_json(run.cache_path(0))
        saved['record']['actual']['invented_test_value'] = 'forged'
        saved['recordSha256'] = r.digest(saved['record'])
        atomic_json(run.cache_path(0), saved, replace=True)
        old_hashes = read_checkpoint(run.local_checkpoint)['canonicalRecordHashes']
        with self.assertRaises(ValueError):
            self.make().run()
        self.assertEqual(len(self.calls), 16)
        self.assertEqual(read_checkpoint(run.local_checkpoint)['canonicalRecordHashes'], old_hashes)

    def test_unknown_duplicate_cache_and_nonprefix_observations_refused(self):
        run = self.make()
        run.run()
        extra = run.state / 'cases/0000-duplicate.json'
        extra.write_bytes(run.cache_path(0).read_bytes())
        with self.assertRaisesRegex(r.ResumeError, 'UnknownOrDuplicateCaseCache'):
            self.make().run()
        self.assertEqual(len(self.calls), 16)

    def test_changed_source_corpus_or_frozen_expected_cannot_resume(self):
        run = self.make()
        run.run()
        changed = self.make()
        changed.expected[0]['authority'] = 'changed-before-new-call'
        changed.freeze['independentExpected'] = changed.expected
        changed.freeze['expectedSha256'] = r.digest(changed.expected)
        with self.assertRaisesRegex(r.ResumeError, 'FrozenM2bxInputChanged'):
            changed.run()
        changed = self.make()
        changed.source_supplier = lambda: {**self.join, 'sourceFingerprintSha256': '0' * 64}
        with self.assertRaises(ValueError):
            changed.run()
        self.assertEqual(len(self.calls), 16)

    def test_live_or_uncertain_controller_lock_does_not_start_duplicate(self):
        run = self.make()
        run.state.mkdir(parents=True)
        identity = {'pid': 777777, 'identityKnown': True, 'startIdentity': 'invented', 'image': 'invented-only'}
        lock = run.state / 'runtime.lock.json'
        atomic_json(lock, {'milestone': 'M2bx', 'schemaVersion': 1, 'sourceFingerprint': run.fingerprint,
                          'corpusSha256': run.corpus_digest, 'controller': identity})
        for observed in (identity, {'pid': 777777, 'identityKnown': False}):
            with self.subTest(observed=observed), patch.object(r.transport_api, 'process_identity', return_value=observed):
                with self.assertRaises(ValueError):
                    run.run()
        self.assertEqual(self.calls, [])
        self.assertTrue(lock.exists())

    def test_unclosed_corpus_budget_or_duplicate_id_is_refused_before_files(self):
        for mutate in (lambda cases: cases.pop(), lambda cases: cases[0].update(budget=22),
                       lambda cases: cases[0].update(budget=True),
                       lambda cases: cases[1].update(case_id=cases[0]['case_id'])):
            cases = self.cases('positive')
            mutate(cases)
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                self.make(cases=cases)
        self.assertFalse((self.root / 'results').exists())
        self.assertEqual(self.calls, [])

    def test_global_completed_counter_without_actual_cache_cannot_trigger_rerun(self):
        state = self.root / 'GLOBAL.json'
        run = self.make(global_checkpoint=state)
        saved_mode = {'corpusSha256': run.corpus_digest, 'corpusKind': 'positive',
            'outputDirectory': str(run.output), 'stateDirectory': str(run.state),
            'lastCompletedCaseId': run.cases[0]['case_id'], 'canonicalRecordHashes': ['0' * 64],
            'pendingCases': [case['case_id'] for case in run.cases[1:]]}
        atomic_json(state, {'milestone': 'M2bx', 'schemaVersion': 1, 'branch': r.BRANCH, 'baseSha': r.BASE,
            'sourceFingerprint': run.fingerprint, 'runtimeModes': {'public:positive': saved_mode}, 'completedSteps': []})
        with self.assertRaisesRegex(r.ResumeError, 'CheckpointCompletedRecordMismatch'):
            run.run()
        self.assertEqual(self.calls, [])
        self.assertEqual(read_checkpoint(state)['runtimeModes']['public:positive'], saved_mode)

    def test_different_modes_share_global_mutex_before_any_runtime_or_checkpoint_update(self):
        state = self.root / 'GLOBAL.json'
        first = self.make(global_checkpoint=state)
        atomic_json(state, {'milestone': 'M2bx', 'schemaVersion': 1, 'branch': r.BRANCH, 'baseSha': r.BASE,
            'sourceFingerprint': first.fingerprint, 'completedSteps': []})
        owner = {'pid': 777777, 'identityKnown': True, 'startIdentity': 'invented', 'image': 'invented-only'}
        lock = state.parent / '.m2bx-runtime.lock.json'
        atomic_json(lock, {'milestone': 'M2bx', 'schemaVersion': 1, 'sourceFingerprint': first.fingerprint,
            'corpusSha256': first.corpus_digest, 'controller': owner, 'modeKey': first.mode_key})
        checkpoint_before, lock_before = state.read_bytes(), lock.read_bytes()
        other = self.make(public=False, output=self.root / 'other-mode', global_checkpoint=state)
        with patch.object(r.transport_api, 'process_identity', return_value=owner), self.assertRaises(ValueError):
            other.run()
        self.assertEqual(self.calls, [])
        self.assertEqual(state.read_bytes(), checkpoint_before)
        self.assertEqual(lock.read_bytes(), lock_before)

    def test_boolean_record_cache_and_transport_versions_are_not_integer_one_or_zero(self):
        run = self.make()
        run.run()
        original = r.read_json(run.cache_path(0))
        variants = []
        for where in ('wrapper', 'record', 'transport'):
            changed = deepcopy(original)
            if where == 'wrapper':
                changed['schemaVersion'] = True
            elif where == 'record':
                changed['record']['schemaVersion'] = True
                changed['recordSha256'] = r.digest(changed['record'])
            else:
                changed['transport']['runnerExitCode'] = False
            variants.append(changed)
        for changed in variants:
            atomic_json(run.cache_path(0), changed, replace=True)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.make().run()
        self.assertEqual(len(self.calls), 16)

    def test_global_checkpoint_uri_refused_at_constructor_before_checkpoint_read(self):
        with patch.object(r, 'read_checkpoint', side_effect=AssertionError('checkpoint read forbidden')):
            with self.assertRaises(ValueError):
                self.make(global_checkpoint='smb://invented.invalid/share/state.json')

    def test_explicit_pause_stops_before_next_case_and_resume_does_not_repeat_completed_case(self):
        for number, flags in enumerate(({'phase': 'PAUSED'}, {'pauseRequested': True})):
            state = self.root / f'paused-before-{number}.json'
            run = self.make(output=self.root / f'paused-output-{number}', global_checkpoint=state)
            atomic_json(state, {'milestone': 'M2bx', 'schemaVersion': 1, 'branch': r.BRANCH, 'baseSha': r.BASE,
                'sourceFingerprint': run.fingerprint, **flags})
            before = state.read_bytes()
            with self.subTest(flags=flags), self.assertRaises(r.PauseRequested):
                run.run()
            self.assertEqual(state.read_bytes(), before)
            self.assertFalse(run.output.exists())
        self.assertEqual(self.calls, [])
        state = self.root / 'PAUSE_GLOBAL.json'
        run = self.make(global_checkpoint=state)
        atomic_json(state, {'milestone': 'M2bx', 'schemaVersion': 1, 'branch': r.BRANCH, 'baseSha': r.BASE,
            'sourceFingerprint': run.fingerprint, 'completedSteps': []})
        original_executor = run.executor
        def pause_after_first(*args):
            result = original_executor(*args)
            saved = read_checkpoint(state)
            saved.update(phase='PAUSED', currentPhase='PAUSED')
            atomic_json(state, saved, replace=True)
            return result
        run.executor = pause_after_first
        with self.assertRaises(r.PauseRequested):
            run.run()
        self.assertEqual(self.calls, [run.cases[0]['case_id']])
        self.assertTrue(run.cache_path(0).exists())
        self.assertFalse(run.cache_path(1).exists())
        self.assertFalse((run.state / 'first-mismatch.json').exists())
        self.assertEqual(read_checkpoint(state)['phase'], 'PAUSED')
        first_cache = run.cache_path(0).read_bytes()
        # This fixture explicitly represents a later human RESUME, never an
        # automatic clearing of pause by the runtime controller itself.
        saved = read_checkpoint(state)
        saved.update(phase='ROM_EXECUTION', currentPhase='ROM_EXECUTION', status='RUNTIME_IN_PROGRESS', pauseRequested=False)
        atomic_json(state, saved, replace=True)
        self.assertEqual(self.make(global_checkpoint=state).run()['cases'], 16)
        self.assertEqual(len(self.calls), 16)
        self.assertEqual(run.cache_path(0).read_bytes(), first_cache)

    def test_stale_pending_case_list_is_refused_not_silently_rewritten(self):
        run = self.make()
        run.prepare()
        saved = read_checkpoint(run.local_checkpoint)
        saved['pendingCases'] = saved['pendingCases'][1:]
        atomic_json(run.local_checkpoint, saved, replace=True)
        with self.assertRaisesRegex(r.ResumeError, 'CheckpointLastOrPendingCaseMismatch'):
            self.make().run()
        self.assertEqual(self.calls, [])

    def test_program_ack_requires_closed49_node_schema_and_no_native_claim(self):
        run = self.make()
        run.run()
        ack = r.read_json(run.cache_path(0))['record']['programAdmission']
        for changes in ({'program_node_count': 23}, {'native_generation_ownership': True}, {'entry_pc': 0x556F}):
            with self.subTest(changes=changes), self.assertRaises(r.ResumeError):
                r.verify_ack({**ack, **changes}, run.program_identity, True)

    def test_branch_controls_are_not_an_admitted_m2bx_runtime(self):
        with self.assertRaisesRegex(r.ResumeError, 'ClosedM2bxPositiveCorpusKindRequired'):
            self.make(kind='branch_controls')
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / 'results').exists())

    def test_exactly_two_p2_read_write_pairs_and_retirements_is_required_for_record(self):
        run = self.make()
        run.run()
        original = r.read_json(run.cache_path(0))['record']
        for mutate in (lambda record: record['actual']['report'].update(p2_instruction_retirements=0),
                       lambda record: record['actual']['report'].update(p2_instruction_retirements=True),
                       lambda record: record['actual']['report'].update(p2_instruction_retirements=3),
                       lambda record: record['actual']['report']['peripheral_p2_journal'].pop(),
                       lambda record: record['actual']['report']['peripheral_p2_journal'].reverse(),
                       lambda record: record['actual']['report']['peripheral_p2_journal'][0].update(address=37)):
            altered = deepcopy(original)
            mutate(altered)
            with self.subTest(altered=altered), self.assertRaises(r.ResumeError):
                run.check_record(0, altered)
        self.assertEqual(len(self.calls), 16)


if __name__ == '__main__':
    unittest.main()
