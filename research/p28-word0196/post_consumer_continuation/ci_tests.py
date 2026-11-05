"""Source routing and publication controls; no CPU or historical suite runs."""
from copy import deepcopy
from pathlib import Path
import re
import stat
from tempfile import TemporaryDirectory, gettempdir
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from original_rom_boundary.source_guard import Blob, contents, tree
from post_consumer_continuation import ci
import validate_post_consumer_continuation as publication


class SourceRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inventory = tree(ci.ROOT, ci.BASE)
        data = contents(ci.ROOT, (inventory,))
        cls.base = {n: Blob(mode, data[oid]) for n, (mode, oid) in inventory.items()}
        cls.current = dict(cls.base)
        for name in ci.NEW_PATHS:
            cls.current[name] = Blob('100644', (ci.ROOT / name).read_bytes())
        cls.pin = ci.new_fingerprint(cls.current)
        cls.current[ci.WORKFLOW] = Blob('100644', ci.make_workflow(cls.base[ci.WORKFLOW].data, cls.pin))

    def assert_full_qa(self, changed, pin=None):
        result = ci.classify(self.base, changed, self.pin if pin is None else pin)
        self.assertIs(result['full_qa'], True)
        self.assertIs(result['research_only'], False)
        self.assertEqual(result['historicalRequiredJobCount'], 17)

    def reviewed_mutation(self, name, blob):
        changed = {**self.current, name: blob}
        pin = ci.new_fingerprint(changed)
        changed[ci.WORKFLOW] = Blob('100644', ci.make_workflow(self.base[ci.WORKFLOW].data, pin))
        return changed, pin

    def test_exact_approved_refinement_selects_only_static_lane(self):
        result = ci.classify(self.base, self.current, self.pin)
        self.assertIs(result['full_qa'], False)
        self.assertIs(result['research_only'], True)
        projected = ci.projection(self.base, self.current, self.pin)
        self.assertEqual(projected['unchangedBaseFiles'], 1333)
        self.assertEqual(len(projected['sourceBindings']), 1349)
        self.assertEqual(len(projected['newPublicPaths']), 15)
        self.assertEqual(projected['targetCpuExecutions'], 0)
        self.assertIs(projected['firmwareReady'], False)

    def test_mutation_of_each_new_source_requires_new_approval(self):
        for name in sorted(ci.NEW_PATHS):
            with self.subTest(path=name):
                self.assert_full_qa({**self.current, name: Blob('100644', self.current[name].data + b'\n')})

    def test_all_frozen_m2cq_m2cp_m2co_m2cn_paths_remain_byte_exact(self):
        for name in sorted(ci.inherited.NEW_PATHS | ci.inherited.inherited.NEW_PATHS
                           | ci.inherited.inherited.inherited.NEW_PATHS
                           | ci.inherited.inherited.inherited.inherited.NEW_PATHS):
            with self.subTest(path=name):
                self.assert_full_qa({**self.current, name: Blob('100644', self.current[name].data + b'\n')})

    def test_runtime_old_or_unknown_source_cannot_bypass_full_qa(self):
        for name in ('rust/p28-slice-runner/src/exec.rs',
                     'research/p28-word0196/native_irq0213_four_invocations/reference_oracle.py',
                     'research/p28-word0196/post_consumer_continuation/unreviewed.py'):
            with self.subTest(path=name):
                self.assert_full_qa({**self.current, name: Blob('100644', b'changed')})

    def test_missing_source_wrong_base_or_wrong_approval_falls_back(self):
        changed = dict(self.current)
        del changed[next(iter(ci.NEW_PATHS))]
        self.assert_full_qa(changed)
        self.assertIs(ci.classify({}, self.current, self.pin)['full_qa'], True)
        self.assert_full_qa(self.current, '0' * 64)
        self.assert_full_qa(self.current, 'unreviewed')

    def test_approved_nonregular_empty_binary_or_invalid_text_is_refused(self):
        name = ci.PACKAGE + 'continuation.py'
        self.assertIn(name, ci.NEW_PATHS)
        for blob in (Blob('100755', b'pass\n'), Blob('120000', b'other.py'),
                     Blob('100644', b''), Blob('100644', b'\0'),
                     Blob('100644', b'\xff'), Blob('100644', b'not valid python !!!'),
                     Blob('100644', b'x' * (1024 * 1024))):
            with self.subTest(mode=blob.mode, size=len(blob.data)):
                changed, pin = self.reviewed_mutation(name, blob)
                self.assert_full_qa(changed, pin)

    def test_approved_contract_must_still_be_json_object(self):
        for raw in (b'[]', b'null', b'{invalid}'):
            with self.subTest(raw=raw):
                changed, pin = self.reviewed_mutation(ci.PACKAGE + 'contract.json', Blob('100644', raw))
                self.assert_full_qa(changed, pin)

    def test_historical_tail_is_byte_exact_and_old_approval_is_frozen(self):
        old = self.base[ci.WORKFLOW].data
        active = self.current[ci.WORKFLOW].data
        marker = b'  historical-pinned-qa:'
        self.assertEqual(old[old.index(marker):], active[active.index(marker):])
        self.assertEqual(len(old[old.index(marker):]), 74904)
        self.assertEqual(ci.inherited.approval(old), ci.BASE_APPROVAL)
        self.assertEqual(ci.approval(active), self.pin)

    def test_unreviewed_workflow_conditions_timeout_extra_job_or_mode_rejected(self):
        raw = self.current[ci.WORKFLOW].data
        variants = (Blob('100644', raw + b'\n# unreviewed\n'),
                    Blob('100644', raw + b'\n  extra-job: {}\n'),
                    Blob('100644', raw.replace(b"needs.ci-routing.outputs.full_qa == 'false'",
                                               b"needs.ci-routing.outputs.full_qa == 'true'", 1)),
                    Blob('100644', raw.replace(b'    runs-on: ${{ matrix.os }}\n',
                                               b'    runs-on: ${{ matrix.os }}\n    timeout-minutes: 1\n', 1)),
                    Blob('100755', raw))
        for blob in variants:
            with self.subTest(mode=blob.mode, size=len(blob.data)):
                self.assert_full_qa({**self.current, ci.WORKFLOW: blob})

    def test_workflow_projection_requires_exact_base_bytes_and_literal_pin(self):
        for pin in ('', '0' * 63, 'G' * 64, None):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                ci.make_workflow(self.base[ci.WORKFLOW].data, pin)
        with self.assertRaises(ValueError):
            ci.make_workflow(self.base[ci.WORKFLOW].data + b'\n', self.pin)
        for raw in (b'', self.current[ci.WORKFLOW].data + self.current[ci.WORKFLOW].data):
            with self.assertRaises(ValueError):
                ci.approval(raw)

    def test_workflow_canonical_step_invokes_actual_allowed_entry(self):
        entry = 'research/p28-word0196/validate_post_consumer_continuation.py'
        commands = re.findall(rb'python -B (research/\S+\.py) --output ',
                              self.current[ci.WORKFLOW].data)
        self.assertEqual(commands, [entry.encode()])
        self.assertIn(entry, ci.NEW_PATHS)
        self.assertTrue((ci.ROOT / entry).is_file())
        self.assertIn(b'name: M2cr-conditional-software-${{ matrix.os }}', self.current[ci.WORKFLOW].data)

    def test_output_cannot_overwrite_source_or_existing_evidence(self):
        for value in (ci.ROOT, ci.ROOT / 'private/reports/m2cr',
                      ci.ROOT / 'research/p28-word0196/post_consumer_continuation'):
            with self.subTest(path=value), self.assertRaises(ValueError):
                ci.validate_output(value)
        with TemporaryDirectory(prefix='m2cr-output-guard-') as temporary:
            isolated = Path(temporary).resolve()
            self.assertEqual(isolated.parent, Path(gettempdir()).resolve())
            with patch.object(ci, 'ROOT', isolated):
                target = isolated / 'private/reports/m2cr/controlled-owned-output'
                self.assertFalse(target.exists())
                self.assertEqual(ci.validate_output(target), target)
                target.mkdir(parents=True)
                with self.assertRaisesRegex(ValueError, '^FreshOutputRequired$'):
                    ci.validate_output(target)

    def test_wrong_head_rejected_without_runtime(self):
        with self.assertRaises(ValueError):
            ci.git_maps(expected_head='0' * 40)

    def test_output_parent_traversal_cannot_leave_owned_directory(self):
        with self.assertRaises(ValueError):
            ci.validate_output(ci.ROOT / 'private/reports/m2cr/../../escape')

    def test_report_control_root_reserved_in_clean_ci_without_private_data(self):
        with patch.object(ci.Path, 'exists', return_value=False), self.assertRaisesRegex(
                ValueError, 'ReportControlRootReservedEvenWhenAbsent'):
            ci.validate_output(ci.ROOT / 'private/reports/m2cr')

    def test_symbolic_and_windows_reparse_paths_are_rejected(self):
        for observed in (SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_file_attributes=0),
                         SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x400)):
            with self.subTest(attributes=observed.st_file_attributes), patch.object(
                    ci.os.path, 'lexists', return_value=True), patch.object(
                    ci.Path, 'lstat', return_value=observed), self.assertRaisesRegex(
                    ValueError, 'ReparsePathRefused'):
                ci.regular(ci.ROOT / '.tmp/m2cr-static-evidence/new')


class PublicationTests(unittest.TestCase):
    def safe_output(self, **extra):
        return {'status': 'CompleteConditional', 'actualHardwareObservation': None,
                'cpuInstructionRetirements': 0, 'executionStatus': 'EXECUTION_BLOCKED',
                'firmwareReady': False, **extra}

    def test_heterogeneous_outputs_are_preserved_without_read_kind_conflation(self):
        continuation = self.safe_output(reads=[{'pc': 0x298E, 'address': 0x3F1,
            'space': 'DATA', 'generations': [None], 'knownBits': {'03F1.0': 1}}],
            journal=[{'pc': 0x2994, 'address': 0x3F6, 'widthBits': 8,
                'before': None, 'after': None, 'sameValue': None}],
            intermediateStates=[{'state': {'registerKnownBits': {'AL.7': 0}}}],
            sourceScope=[0x2980, 0x2994])
        obligation = self.safe_output(reads=[], journal=[], steps=[],
            state={'prospectiveAL': {'value': None, 'knownBits': {'7': 0}, 'generation': None},
                   'actualBufferWrite': None, 'actualAcceptance': None,
                   'actualTransmission': None, 'actualCompletion': None, 'actualTxIrq': None},
            unresolvedConstraints=['StbufLifecycleAndOwnershipNotEstablished'], sourceScope=[0x2995])
        lineage = self.safe_output(reads=[], journal=[],
            state={'relations': [{'address': 0x3F2, 'sourceWindowRead': False,
                                 'relation': 'GenerationNotEstablished'}],
                   'endpointEqualityIsNotAnObservation': True}, sourceScope=[0x2980, 0x2994])
        records = [{'caseId': 'continuation', 'operation': 'post_consumer_continuation',
                    'input': {}, 'output': continuation},
                   {'caseId': 'stbuf', 'operation': 'stbuf_boundary_obligations', 'input': {}, 'output': obligation},
                   {'caseId': 'lineage', 'operation': 'continuation_lineage', 'input': {}, 'output': lineage}]
        before = deepcopy(records)
        operations, statuses = {}, {}
        for record in records:
            publication.observe_record(record, operations, statuses)
            self.assertEqual(publication.json.loads(publication.canonical(record)), record)
        self.assertEqual(records, before)
        self.assertEqual(operations, {'post_consumer_continuation': 1,
            'stbuf_boundary_obligations': 1, 'continuation_lineage': 1})
        self.assertEqual(statuses, {'CompleteConditional': 3})
        self.assertEqual(records[1]['output']['reads'], [])
        self.assertIsNone(records[1]['output']['state']['actualTransmission'])
        self.assertEqual(records[2]['output']['sourceScope'], [0x2980, 0x2994])

    def test_publication_cannot_certify_unsafe_execution_metadata(self):
        variants = ({'cpuInstructionRetirements': 1}, {'cpuInstructionRetirements': False},
                    {'actualHardwareObservation': {}}, {'executionStatus': 'EXECUTION_ALLOWED'},
                    {'firmwareReady': True},
                    *({'state': {name: {'invented': True}}} for name in (
                        'actualBufferWrite', 'actualAcceptance', 'actualTransmission',
                        'actualCompletion', 'actualTxIrq')))
        for change in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                publication.observe_record({'caseId': 'unsafe', 'operation': 'stbuf_boundary_obligations',
                    'input': {}, 'output': self.safe_output(**change)}, {}, {})

    def test_canonical_unknown_unicode_and_key_order_are_exact(self):
        expected = b'{"a":"' + bytes((92,)) + b'u0416","z":null}' + bytes((10,))
        self.assertEqual(publication.canonical({'z': None, 'a': chr(0x416)}), expected)
        self.assertEqual(publication.canonical({'b': 1, 'a': 0}), publication.canonical({'a': 0, 'b': 1}))
        with self.assertRaises(ValueError):
            publication.canonical({'value': float('nan')})


if __name__ == '__main__':
    unittest.main()
