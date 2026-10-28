"""Actual source/workflow relations; no CPU, Cargo or private ROM access."""
from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from original_rom_boundary.source_guard import Blob, contents, tree
from . import ci_contract as contract
from . import ci_projection as projection
from . import ci_routing as routing


class CiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        inventory = tree(cls.root, contract.BASE)
        data = contents(cls.root, (inventory,))
        cls.base = {name: Blob(mode, data[oid]) for name, (mode, oid) in inventory.items()}
        cls.old_workflow = cls.base[contract.WORKFLOW].data
        cls.current = dict(cls.base)
        cls.current[contract.WORKFLOW] = Blob('100644', (cls.root / contract.WORKFLOW).read_bytes())
        for name in projection.NEW_PATHS:
            cls.current[name] = Blob('100644', (cls.root / name).read_bytes())
        cls.approved = contract.workflow_approved_fingerprint(cls.current[contract.WORKFLOW].data)

    def assert_full(self, current, base=None):
        result = projection.classify_changes(self.base if base is None else base, current, self.approved)
        self.assertIs(result['full_qa'], True)
        self.assertIs(result['research_only'], False)
        self.assertEqual(result['targetCpuExecutions'], 0)
        self.assertEqual(result['historicalJobsPerformedByRouter'], 0)
        return result

    def test_exact_fourteen_static_additions_and_only_projected_workflow_route_research(self):
        result = projection.research_projection(self.base, self.current, self.approved)
        self.assertEqual(len(self.base), 1119)
        self.assertEqual(len(projection.NEW_PATHS), 14)
        self.assertEqual(len(result['sourceBindings']), 1133)
        self.assertEqual(result['unchangedBaseFiles'], 1118)
        self.assertEqual(result['onlyChangedBasePath'], contract.WORKFLOW)
        routed = projection.classify_changes(self.base, self.current, self.approved)
        self.assertIs(routed['research_only'], True)
        self.assertIs(routed['full_qa'], False)
        self.assertEqual(routed['sourceFingerprintSha256'], result['sourceFingerprintSha256'])
        self.assertEqual(result['targetCpuExecutions'], 0)
        self.assertIs(result['firmwareReady'], False)

    def test_exact_workflow_preserves_all_seventeen_gates_and_bounded_three_new_jobs(self):
        workflow = self.current[contract.WORKFLOW].data
        self.assertEqual(workflow, contract.make_workflow(self.old_workflow, self.approved))
        value = contract.workflow_projection(self.old_workflow, workflow, self.approved)
        self.assertEqual(value['historicalRequiredJobCount'], 17)
        self.assertEqual(value['researchOnlyRequiredActualJobCount'], 3)
        self.assertEqual(value['researchOnlyHistoricalJobsNotRun'], 17)
        self.assertEqual(value['duplicateHeavyHistoricalJobsAdded'], 0)
        self.assertIs(value['researchOnlyLaneIsProductionQaPass'], False)
        self.assertIs(value['researchOnlyArtifactsAreCpuObservations'], False)

    def test_router_failure_missing_output_and_prior_matrix_success_are_explicit(self):
        text = self.current[contract.WORKFLOW].data.decode('utf-8')
        for job, predecessor in contract.HISTORICAL_JOBS:
            with self.subTest(job=job):
                expected = contract.historical_condition(predecessor)
                dependencies = 'ci-routing' if predecessor is None else '[ci-routing, ' + predecessor + ']'
                self.assertIn('\n  ' + job + ':\n    needs: ' + dependencies + '\n' + expected, text)
                self.assertIn("always() && (needs.ci-routing.result != 'success' ||", expected)
                self.assertIn("needs.ci-routing.outputs.full_qa != 'false'", expected)
                if predecessor is not None:
                    self.assertIn("&& needs." + predecessor + ".result == 'success'", expected)

    def test_all_old_source_runtime_dependencies_contracts_and_tests_force_full(self):
        names = (
            'rust/p28-slice-runner/src/exec.rs',
            'rust/p28-slice-runner/src/bus.rs',
            'rust/p28-slice-runner/Cargo.toml',
            'rust/p28-slice-runner/Cargo.lock',
            'HondaEcu.Windows.sln',
            'AGENTS.md',
            'research/p28-word0196/native_post_return_selector/contract.json',
            'research/p28-word0196/native_post_return_selector/ci_contract_tests.py',
            'research/p28-word0196/native_post_return_selector/source_guard.py',
        )
        for name in names:
            with self.subTest(path=name):
                self.assertIn(name, self.base)
                altered = dict(self.current)
                altered[name] = Blob(self.base[name].mode, self.base[name].data + b'\n# changed input\n')
                self.assert_full(altered)

    def test_unknown_added_deleted_renamed_or_missing_paths_cannot_select_static_lane(self):
        variants = []
        value = dict(self.current); value['docs/unreviewed.txt'] = Blob('100644', b'new'); variants.append(value)
        value = dict(self.current); value.pop('AGENTS.md'); variants.append(value)
        value = dict(self.current)
        value['docs/renamed-agents.md'] = value.pop('AGENTS.md')
        variants.append(value)
        value = dict(self.current); value.pop(projection.PACKAGE + 'contract.json'); variants.append(value)
        value = dict(self.current)
        value[projection.PACKAGE + 'extra_runtime.py'] = Blob('100644', b'pass\n')
        variants.append(value)
        for index, current in enumerate(variants):
            with self.subTest(mutation=index):
                self.assert_full(current)

    def test_unreviewed_workflow_steps_pins_conditions_and_artifacts_force_full(self):
        valid = contract.make_workflow(self.old_workflow, self.approved)
        changes = (
            (b'needs: [ci-routing, native-p2-handoff]', b'needs: [ci-routing, build-and-test]'),
            (b'ref: ' + contract.BASE.encode(), b'ref: main'),
            (b"needs.ci-routing.result != 'success' || ", b''),
            (b"needs.historical-pinned-qa.result == 'success'", b'true'),
            (b'cargo +1.85.1 test --release', b'echo skipped-test --release'),
            (b'if-no-files-found: error', b'if-no-files-found: ignore'),
            (b'      - name: Test desktop contracts', b'      - if: false\n        name: Test desktop contracts'),
            (b'static-canonical.jsonl.gz', b'runtime-canonical.jsonl.gz'),
            (b'--expected-head "', b'--unchecked-head "'),
        )
        for old, new in changes:
            with self.subTest(relation=old):
                changed = valid.replace(old, new, 1)
                self.assertNotEqual(changed, valid)
                with self.assertRaises(ValueError):
                    contract.workflow_projection(self.old_workflow, changed, self.approved)
                current = dict(self.current)
                current[contract.WORKFLOW] = Blob('100644', changed)
                self.assert_full(current)
        with self.assertRaises(ValueError):
            contract.workflow_projection(self.old_workflow, valid + b'\n# unreviewed policy\n', self.approved)

    def test_wrong_accepted_base_membership_and_fingerprint_force_full(self):
        old = dict(self.base)
        old['AGENTS.md'] = Blob('100644', old['AGENTS.md'].data + b'\n')
        self.assert_full(self.current, old)
        old = dict(self.base); old.pop('AGENTS.md')
        self.assert_full(self.current, old)
        with self.assertRaises(ValueError):
            contract.make_workflow(self.old_workflow + b'\n', self.approved)
        self.assertNotEqual(sha256(self.old_workflow + b'\n').hexdigest(), contract.BASE_WORKFLOW_SHA)

    def test_new_sources_must_remain_small_regular_utf8_parseable_text(self):
        name = projection.PACKAGE + 'ci_routing.py'
        variants = (
            Blob('100755', b'pass\n'),
            Blob('120000', b'target'),
            Blob('100644', b''),
            Blob('100644', b'\xff'),
            Blob('100644', b'\0pass'),
            Blob('100644', b'def broken(:\n'),
            Blob('100644', b'#' * (2 * 1024 * 1024 + 1)),
        )
        for index, value in enumerate(variants):
            with self.subTest(mutation=index):
                current = dict(self.current); current[name] = value
                self.assert_full(current)
        for raw in (b'{"bad":NaN}', b'[]', b'{'):
            current = dict(self.current)
            current[projection.PACKAGE + 'contract.json'] = Blob('100644', raw)
            self.assert_full(current)

    def test_router_git_errors_fail_toward_full_without_executing_fallback_work(self):
        with patch.object(routing, 'git', side_effect=OSError('InventedReadFailure')) as reader:
            result = routing.classify_git(self.root, '1' * 40, self.approved)
        self.assertIs(result['full_qa'], True)
        self.assertIs(result['research_only'], False)
        self.assertEqual(result['reason'], 'RoutingError_FullHistoricalQaRequired')
        self.assertEqual(result['targetCpuExecutions'], 0)
        self.assertEqual(reader.call_count, 1)

    def test_invalid_inputs_and_ambiguous_output_cannot_claim_bounded_success(self):
        self.assert_full(None)
        self.assert_full(self.current, {})
        for decision in ({}, {'full_qa': True, 'research_only': True},
                         {'full_qa': False, 'research_only': False},
                         {'full_qa': 0, 'research_only': 1}):
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                routing.output_text(decision)
        full = projection.full_qa_decision('InventedControl')
        self.assertEqual(routing.output_text(full), 'full_qa=true\nresearch_only=false\n')
        static = deepcopy(full); static.update(full_qa=False, research_only=True)
        self.assertEqual(routing.output_text(static), 'full_qa=false\nresearch_only=true\n')

    def test_router_may_append_only_to_exact_github_owned_output(self):
        decision = projection.full_qa_decision('InventedMetadataControl')
        with tempfile.TemporaryDirectory() as directory:
            owner = Path(directory).resolve() / 'github-output'
            owner.write_bytes(b'')
            other = Path(directory).resolve() / 'source.py'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(owner)}):
                with self.assertRaises(ValueError):
                    routing.write_github_output(other, decision)
                self.assertFalse(other.exists())
                routing.write_github_output(owner, decision)
                self.assertEqual(owner.read_text('utf-8'), 'full_qa=true\nresearch_only=false\n')
            self.assertFalse(other.exists())

    def test_missing_nonlocal_traversal_directory_and_checkout_outputs_are_refused(self):
        decision = projection.full_qa_decision('InventedOutputPolicyControl')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            missing = root / 'missing'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(missing)}):
                with self.assertRaises(FileNotFoundError):
                    routing.write_github_output(missing, decision)
            self.assertFalse(missing.exists())
            for raw in ('relative-output', '//server/share/output', str(root) + '/child/../output'):
                with self.subTest(path=raw), patch.dict(os.environ, {'GITHUB_OUTPUT': raw}):
                    with self.assertRaises(ValueError):
                        routing.write_github_output(raw, decision)
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(root)}):
                with self.assertRaises(ValueError):
                    routing.write_github_output(root, decision)
            project = root / 'checkout'
            project.mkdir()
            source = project / 'source.py'
            source.write_bytes(b'UnchangedInventedSource')
            with patch.object(routing, 'ROOT', project), patch.dict(os.environ, {'GITHUB_OUTPUT': str(source)}):
                with self.assertRaises(ValueError):
                    routing.write_github_output(source, decision)
            self.assertEqual(source.read_bytes(), b'UnchangedInventedSource')

    def test_mocked_symlink_reparse_parent_and_hardlink_metadata_refuse_before_append(self):
        decision = projection.full_qa_decision('InventedMetadataRefusal')
        original = Path.lstat
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            owner = root / 'github-output'
            owner.write_bytes(b'UnchangedPrefix\n')
            for mutation in ('file-symlink', 'parent-reparse', 'file-hardlink'):
                def metadata(node):
                    info = original(node)
                    result = SimpleNamespace(st_mode=info.st_mode, st_dev=info.st_dev,
                        st_ino=info.st_ino, st_nlink=info.st_nlink,
                        st_file_attributes=getattr(info, 'st_file_attributes', 0))
                    if mutation == 'file-symlink' and node == owner:
                        result.st_mode = stat.S_IFLNK | stat.S_IMODE(info.st_mode)
                    elif mutation == 'parent-reparse' and node == root:
                        result.st_file_attributes |= 0x400
                    elif mutation == 'file-hardlink' and node == owner:
                        result.st_nlink = 2
                    return result
                with self.subTest(mutation=mutation), patch.dict(os.environ, {'GITHUB_OUTPUT': str(owner)}):
                    with patch.object(Path, 'lstat', metadata), patch.object(routing.os, 'open') as opener:
                        with self.assertRaises(ValueError):
                            routing.write_github_output(owner, decision)
                        opener.assert_not_called()
                self.assertEqual(owner.read_bytes(), b'UnchangedPrefix\n')

    def test_open_descriptor_identity_change_refuses_without_writing(self):
        decision = projection.full_qa_decision('InventedDescriptorRace')
        actual_fstat = os.fstat
        with tempfile.TemporaryDirectory() as directory:
            owner = Path(directory).resolve() / 'github-output'
            owner.write_bytes(b'UnchangedPrefix\n')
            def different_identity(descriptor):
                info = actual_fstat(descriptor)
                return SimpleNamespace(st_mode=info.st_mode, st_dev=info.st_dev,
                    st_ino=info.st_ino + 1, st_nlink=info.st_nlink)
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(owner)}):
                with patch.object(routing.os, 'fstat', different_identity), patch.object(routing.os, 'write') as writer:
                    with self.assertRaises(ValueError):
                        routing.write_github_output(owner, decision)
                    writer.assert_not_called()
            self.assertEqual(owner.read_bytes(), b'UnchangedPrefix\n')

    def test_runtime_code_inside_an_allowed_new_file_cannot_use_unchanged_approval(self):
        for name in (projection.PACKAGE + 'gate_model.py',
                     'research/p28-word0196/validate_native_branch064c.py'):
            with self.subTest(path=name):
                current = dict(self.current)
                current[name] = Blob('100644', current[name].data
                    + b'\nimport subprocess\nsubprocess.run([\"invented-cpu-command\"])\n')
                self.assert_full(current)
                changed_fingerprint = projection.new_source_fingerprint(current)
                self.assertNotEqual(changed_fingerprint, self.approved)
                # Freshly hashing altered input must not silently approve its old workflow.
                result = projection.classify_changes(self.base, current, changed_fingerprint)
                self.assertIs(result['full_qa'], True)
                self.assertIs(result['research_only'], False)

    def test_missing_wrong_or_duplicate_new_source_review_pin_cannot_select_research(self):
        for approved in (None, '', '0' * 64, self.approved.upper()):
            with self.subTest(approved=approved):
                result = projection.classify_changes(self.base, self.current, approved)
                self.assertIs(result['full_qa'], True)
                self.assertIs(result['research_only'], False)
        valid = contract.make_workflow(self.old_workflow, self.approved)
        pin = ('--approved-new-source-fingerprint \"' + self.approved + '\"').encode('ascii')
        for mutation in (valid.replace(pin, b'', 1), valid + b'\n# ' + pin + b'\n'):
            with self.assertRaises(ValueError):
                contract.workflow_approved_fingerprint(mutation)
            current = dict(self.current)
            current[contract.WORKFLOW] = Blob('100644', mutation)
            self.assert_full(current)
