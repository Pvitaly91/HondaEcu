"""Invented output-routing fixtures; no Cargo/build/CPU is ever invoked."""
from hashlib import sha256
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from native_entry_continuity import build_guard as g


class BuildGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manifest = self.root / "rust/p28-slice-runner/Cargo.toml"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text('[package]\nname="invented"\nversion="0.1.0"\n', encoding="utf-8")
        self.lock = self.manifest.with_name("Cargo.lock")
        self.lock.write_text('version=3\n', encoding="utf-8")
        for index, path in enumerate(g.protected_paths(self.root)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'invented-protected-' + str(index).encode())
        self.bindings = [g.identity(path) for path in g.protected_paths(self.root)]
        self.target = self.root / g.TARGET_RELATIVE
        self.target.parent.mkdir(parents=True)
        self.owner = g.prepare_target(self.root, self.manifest, self.bindings)

    def command(self, *, feature=g.FEATURE, build=False):
        result = ['cargo', '+1.85.1', 'build' if build else 'test', '--release', '--locked', '--offline',
                  '--jobs', '1', '--manifest-path', str(self.manifest), '--target-dir', str(self.target), '--no-default-features']
        if feature:
            result += ['--features', feature]
        if build:
            result += ['--bin', 'm2bu-entry-continuity']
        return result

    def test_new_target_and_external_ownership_are_closed(self):
        self.assertEqual(len(self.bindings), 26)
        self.assertEqual(self.owner['scope'], 'M2buIsolatedCargoTarget')
        with self.assertRaises(g.BuildGuardError):
            g.prepare_target(self.root, self.manifest, self.bindings)
        g.check_owner(self.root, self.target, self.owner, g.protected_paths(self.root))

    def test_all_four_full_suites_and_only_new_binary(self):
        for feature in (None, 'p28-word0196-audit', 'p28-word0196-original-rom', g.FEATURE):
            with self.subTest(feature=feature):
                g.check_command(self.command(feature=feature), self.manifest, self.target)
        g.check_command(self.command(build=True), self.manifest, self.target)

    def test_missing_protected_input_or_changed_runner_refused(self):
        with self.assertRaises(g.BuildGuardError):
            g.prepare_target(self.root, self.manifest, self.bindings[:-1])
        g.protected_paths(self.root)[-1].write_bytes(b'changed')
        with self.assertRaises(g.BuildGuardError):
            g._protected(g.protected_paths(self.root), self.bindings)

    def test_command_mutations_fail_closed(self):
        original = self.command()
        variants = []
        for option in ('--target-dir', '--manifest-path', '--jobs', '--features'):
            index = original.index(option)
            changed = list(original)
            changed[index + 1] = ('2' if option == '--jobs' else 'unreviewed')
            variants.append(changed)
        variants.extend((original + ['--lib'], original + ['--target-dir', str(self.target)],
                         original + ['--config', 'build.target-dir="elsewhere"'],
                         [item for item in original if item != '--offline']))
        for command in variants:
            with self.subTest(command=command), self.assertRaises(g.BuildGuardError):
                g.check_command(command, self.manifest, self.target)

    def test_only_closed_initial_library_filter_allowed(self):
        g.check_command(self.command() + ['--lib', g.TEST_FILTER], self.manifest, self.target)
        for command in (self.command() + [g.TEST_FILTER],
                        self.command(feature='p28-word0196-original-rom') + ['--lib', g.TEST_FILTER],
                        self.command() + ['other-filter']):
            with self.subTest(command=command), self.assertRaises(g.BuildGuardError):
                g.check_command(command, self.manifest, self.target)

    def test_m2bt_guard_constants_and_old_feature_admission_unchanged(self):
        self.assertEqual(g.prior.TARGET_RELATIVE, Path('.tmp/m2bt-owned/cargo-target'))
        self.assertEqual(g.prior.OWNER_NAME, '.m2bt-target-owner.json')
        command = self.command()
        command[command.index('--target-dir') + 1] = str(self.root / g.prior.TARGET_RELATIVE)
        with self.assertRaises(g.BuildGuardError):
            g.prior.check_command(command, self.manifest, self.root / g.prior.TARGET_RELATIVE)

    def test_ci_routing_is_separate_and_never_private_preservation_pass(self):
        # A separate invented repository models an initially empty hosted job.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            env = {'GITHUB_ACTIONS': 'true', 'GITHUB_SHA': 'a' * 40,
                   'CARGO_TARGET_DIR': str(root / g.TARGET_RELATIVE)}
            first = g.ci_cargo_preflight(root, env)
            self.assertFalse(first['privateProtectedComparisonClaimed'])
            self.assertEqual(g.ci_cargo_preflight(root, env), first)
            for changes in ({'GITHUB_SHA': 'b' * 40}, {'CARGO_TARGET_DIR': str(root / 'rust/p28-slice-runner/target')},
                            {'GITHUB_ACTIONS': 'false'}):
                with self.subTest(changes=changes), self.assertRaises(g.BuildGuardError):
                    g.ci_cargo_preflight(root, {**env, **changes})

    def test_ci_cannot_adopt_local_or_unowned_nonempty_target(self):
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_SHA': 'a' * 40, 'CARGO_TARGET_DIR': str(self.target)}
        with self.assertRaises(g.BuildGuardError):
            g.ci_cargo_preflight(self.root, env)

    def test_same_target_hardlink_to_protected_inode_refused(self):
        invented = self.target / 'invented-alias'
        invented.write_bytes(b'not-a-real-link')
        original = Path.stat
        protected = g.protected_paths(self.root)
        first = original(protected[0])
        def altered(path, *args, **kwargs):
            if path == invented:
                info = original(path, *args, **kwargs)
                return SimpleNamespace(st_dev=first.st_dev, st_ino=first.st_ino,
                    st_mode=info.st_mode, st_file_attributes=getattr(info, 'st_file_attributes', 0))
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', altered), self.assertRaises(g.BuildGuardError):
            g.check_owner(self.root, self.target, self.owner, protected)

    def test_reparse_ancestor_refused_without_actual_symlink_privilege(self):
        original = Path.lstat
        def altered(path, *args, **kwargs):
            if path == self.target:
                info = original(path, *args, **kwargs)
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'lstat', altered), self.assertRaises(g.BuildGuardError):
            g.no_reparse(self.target / 'any-child')

    def test_guarded_execute_passes_exact_cwd_and_copied_environment(self):
        env = {'CARGO_TARGET_DIR': str(self.target), 'CARGO_HOME': str(self.root / 'invented-cargo-home')}
        arguments = dict(repository=self.root, manifest=self.manifest, ownership=self.owner, command=self.command(),
                         cargo_home=self.root / 'invented-cargo-home', protected_bindings=self.bindings,
                         expected_manifest_sha256=sha256(self.manifest.read_bytes()).hexdigest(),
                         expected_lock_sha256=sha256(self.lock.read_bytes()).hexdigest(), environment=env)
        calls = []
        with patch.object(g.prior, 'review_toolchain', return_value={'proxy': {'path': 'invented-cargo.exe'}}), \
             patch.object(g.prior, 'review_build_surface', return_value={'invented': True}):
            result = g.guarded_execute(spawn=lambda command, **kwargs: calls.append((command, kwargs)) or 'spy', **arguments)
        self.assertEqual(result, 'spy')
        self.assertEqual(calls[0][0][0], 'invented-cargo.exe')
        self.assertEqual(calls[0][1]['cwd'], str(self.root))
        self.assertEqual(calls[0][1]['env'], env)
        self.assertIsNot(calls[0][1]['env'], env)


if __name__ == '__main__':
    unittest.main()
