"""Invented temporary files only. No Cargo, compiler, CPU, ROM or network runs."""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import tempfile
import sys
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

if __package__:
    from . import build_guard as g
else:  # Preserve direct-script invocation as well as package discovery.
    import build_guard as g


class CargoBuildGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m2bt-build-guard-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve() / "repo"
        self.repo.mkdir()
        self.manifest = self.repo / "rust/p28-slice-runner/Cargo.toml"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text('[package]\nname="invented"\nversion="0.40.0"\n', encoding="utf-8")
        self.lock = self.manifest.with_name("Cargo.lock")
        self.lock.write_text('version=4\n[[package]]\nname="invented"\nversion="0.40.0"\n', encoding="utf-8")
        self.protected = [self.repo / p for p in g.PROTECTED_RELATIVE]
        for index, path in enumerate(self.protected):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"invented historical executable " + bytes([index]))
        self.target = self.repo / g.TARGET_RELATIVE
        self.target.parent.mkdir(parents=True)
        self.cargo_home = self.repo / ".tmp/dependency-cache"
        self.cargo_home.mkdir()
        suffix = ".exe" if sys.platform == "win32" else ""
        triple = "x86_64-pc-windows-msvc" if sys.platform == "win32" else "x86_64-unknown-linux-gnu"
        self.rustup_home = self.repo / ".tmp/rustup"
        self.toolchain = self.rustup_home / ("toolchains/1.85.1-" + triple)
        for path in (self.cargo_home / ("bin/cargo" + suffix), self.toolchain / ("bin/cargo" + suffix),
                     self.toolchain / ("bin/rustc" + suffix)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"invented toolchain identity; never executed")
            path.chmod(0o700)
        distribution = self.toolchain / "lib/rustlib/multirust-channel-manifest.toml"
        distribution.parent.mkdir(parents=True)
        distribution.write_text('[pkg.rustc]\nversion="1.85.1 (4eb161250 2025-03-15)"\n', encoding="utf-8")
        self.env = {"CARGO_HOME": str(self.cargo_home), "RUSTUP_HOME": str(self.rustup_home),
                    "PATH": str(self.cargo_home / "bin")}
        self.owner = g.prepare_target(self.repo, self.manifest)
        self.command = ["cargo", "+1.85.1", "test", "--release", "--locked", "--offline", "--lib",
                        "--manifest-path", str(self.manifest), "--target-dir", str(self.target), "--jobs", "1"]

    def arguments(self, **changes):
        values = {"repository": self.repo, "manifest": self.manifest, "ownership": self.owner,
                  "command": self.command, "cargo_home": self.cargo_home,
                  "expected_manifest_sha256": sha256(self.manifest.read_bytes()).hexdigest(),
                  "expected_lock_sha256": sha256(self.lock.read_bytes()).hexdigest(), "environment": self.env}
        values.update(changes)
        return values

    def test_fresh_owner_and_explicit_test_target_pass_without_cargo(self):
        before = [p.read_bytes() for p in self.protected]
        receipt = g.preflight(**self.arguments())
        self.assertEqual(receipt["target"], str(self.target))
        self.assertIn("NotHistoricalPreservationPass", receipt["classification"])
        self.assertEqual(before, [p.read_bytes() for p in self.protected])

    def test_default_target_regression_refuses_before_any_spawn_or_overwrite(self):
        calls = []
        def fake_cargo(command, **_):
            calls.append(command)
            self.protected[0].write_bytes(b"would overwrite without preflight")
        for replacement in (None, str(self.manifest.parent / "target")):
            command = list(self.command)
            index = command.index("--target-dir")
            if replacement is None:
                del command[index:index + 2]
            else:
                command[index + 1] = replacement
            before = [p.read_bytes() for p in self.protected]
            with self.assertRaises(g.BuildGuardError):
                g.guarded_execute(spawn=fake_cargo, **self.arguments(command=command))
            self.assertEqual(calls, [])
            self.assertEqual(before, [p.read_bytes() for p in self.protected])

    def test_preflight_and_postflight_surround_only_explicit_spawn(self):
        calls = []
        value = g.guarded_execute(spawn=lambda command, **_: calls.append(command) or 17, **self.arguments())
        self.assertEqual(value, 17)
        self.assertEqual(calls[0][1:], self.command[1:])
        self.assertEqual(Path(calls[0][0]).parent, self.cargo_home / "bin")

    def test_spawn_gets_exact_reviewed_environment_and_working_directory(self):
        observed = []
        def fake_cargo(command, *, cwd, env):
            observed.append((cwd, dict(env)))
            self.env["LINK"] = "/OUT:late-external-mutation.exe"
        original = dict(self.env)
        g.guarded_execute(spawn=fake_cargo, **self.arguments())
        self.assertEqual(observed, [(str(self.repo), original)])

    def test_postflight_reports_protected_change_instead_of_claiming_success(self):
        def invalid_executor(_, **__):
            self.protected[0].write_bytes(b"invented damage")
        with self.assertRaisesRegex(g.BuildGuardError, "BuildInputsOrProtectedIdentityChanged"):
            g.guarded_execute(spawn=invalid_executor, **self.arguments())

    def test_resume_requires_external_matching_ownership_receipt(self):
        altered = dict(self.owner, nonce="f" * 64)
        with self.assertRaisesRegex(g.BuildGuardError, "OwnershipMarkerMismatch"):
            g.preflight(**self.arguments(ownership=altered))
        self.assertEqual(g.preflight(**self.arguments())["ownershipSha256"], sha256(g.canonical(self.owner)).hexdigest())

    def test_existing_directory_never_adopted_or_cleaned(self):
        before = (self.target / g.OWNER_NAME).read_bytes()
        with self.assertRaisesRegex(g.BuildGuardError, "ExistingUnownedTargetRejected"):
            g.prepare_target(self.repo, self.manifest)
        self.assertEqual(before, (self.target / g.OWNER_NAME).read_bytes())

    def test_source_target_and_protected_overlaps_fail(self):
        with self.assertRaisesRegex(g.BuildGuardError, "ProtectedTargetOverlap"):
            g.preflight(**self.arguments(extra_protected=[self.target.parent]))
        inside = self.target / "source/Cargo.toml"
        inside.parent.mkdir()
        inside.write_text(self.manifest.read_text(), encoding="utf-8")
        with self.assertRaisesRegex(g.BuildGuardError, "SourceTargetOverlap"):
            g.paths(self.repo, self.target, inside)

    def test_symlink_lstat_inside_target_is_rejected_without_os_link_privilege(self):
        link = self.target / "release"
        link.mkdir()
        original = Path.lstat
        def symlink_lstat(item):
            info = original(item)
            if item == link:
                return SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
            return info
        with patch.object(Path, "lstat", symlink_lstat):
            with self.assertRaisesRegex(g.BuildGuardError, "SymlinkPathRejected"):
                g.preflight(**self.arguments())

    def test_windows_junction_attribute_is_rejected_even_without_symlink_privilege(self):
        original = Path.lstat
        def reparse(item):
            info = original(item)
            if item == self.target.parent:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        with patch.object(Path, "lstat", reparse):
            with self.assertRaisesRegex(g.BuildGuardError, "ReparsePointRejected"):
                g.preflight(**self.arguments())

    def test_shared_inode_in_target_is_rejected_without_os_hardlink_privilege(self):
        alias = self.target / "aliased.exe"
        alias.write_bytes(b"invented inode alias")
        original = Path.stat
        protected_info = original(self.protected[0])
        def shared_inode(item, **kwargs):
            if item == alias:
                return protected_info
            return original(item, **kwargs)
        with patch.object(Path, "stat", shared_inode):
            with self.assertRaisesRegex(g.BuildGuardError, "ProtectedHardlinkInTarget"):
                g.preflight(**self.arguments())

    def test_actual_hardlink_to_protected_fixture_is_rejected(self):
        os.link(self.protected[0], self.target / "actual-alias.exe")
        with self.assertRaisesRegex(g.BuildGuardError, "ProtectedHardlinkInTarget"):
            g.preflight(**self.arguments())

    def test_output_environment_and_wrapper_overrides_are_rejected(self):
        for name, value in {"CARGO_TARGET_DIR": str(self.manifest.parent / "target"),
                            "CARGO_BUILD_TARGET_DIR": str(self.protected[0].parent),
                            "RUSTFLAGS": "--out-dir=elsewhere", "RUSTC_WRAPPER": "arbitrary.exe",
                            "CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER": "arbitrary.exe",
                            "OUT_DIR": str(self.protected[0].parent),
                            "LINK": "/OUT:protected.exe", "_LINK_": "/PDB:protected.pdb",
                            "CL": "/Feprotected.exe", "_CL_": "/Fooutside.obj",
                            "CARGO_PROFILE_RELEASE_BUILD_OVERRIDE_DEBUG": "1"}.items():
            with self.subTest(name=name), self.assertRaises(g.BuildGuardError):
                g.preflight(**self.arguments(environment={**self.env, name: value}))
        g.preflight(**self.arguments(environment={**self.env, "CARGO_TARGET_DIR": str(self.target)}))

    def test_effective_dependency_cache_cannot_differ_from_reviewed_cache(self):
        with self.assertRaisesRegex(g.BuildGuardError, "ExplicitReviewedCargoHomeRequired"):
            g.preflight(**self.arguments(environment={}))
        with self.assertRaisesRegex(g.BuildGuardError, "ExplicitReviewedCargoHomeRequired"):
            g.preflight(**self.arguments(environment={"CARGO_HOME": str(self.repo)}))

    def test_missing_or_wrong_pinned_toolchain_and_proxy_are_rejected(self):
        env = dict(self.env)
        del env["RUSTUP_HOME"]
        with self.assertRaisesRegex(g.BuildGuardError, "ExplicitRustupHomeRequired"):
            g.preflight(**self.arguments(environment=env))
        with self.assertRaisesRegex(g.BuildGuardError, "ConflictingRustupToolchain"):
            g.preflight(**self.arguments(environment={**self.env, "RUSTUP_TOOLCHAIN": "nightly"}))
        with self.assertRaisesRegex(g.BuildGuardError, "UnreviewedCargoExecutable"):
            g.preflight(**self.arguments(command=[str(self.repo / "cargo.exe"), *self.command[1:]]))
        distribution = self.toolchain / "lib/rustlib/multirust-channel-manifest.toml"
        distribution.write_text('[pkg.rustc]\nversion="unreviewed"\n', encoding="utf-8")
        with self.assertRaisesRegex(g.BuildGuardError, "PinnedToolchainVersionMismatch"):
            g.preflight(**self.arguments())

    def test_closed_filters_config_and_output_arguments_are_rejected(self):
        cases = [self.command + ["arbitrary_filter"],
                 self.command + ["--all-targets"], self.command + ["--config", 'build.target-dir="old"'],
                 self.command + ["--out-dir", str(self.protected[0].parent)],
                 self.command + ["--target-dir", str(self.target)], self.command + ["--", "--logfile=old"],
                 self.command + [g.ORIGINAL_TEST_FILTER],
                 self.command + ["--features", "p28-word0196-original-rom", g.ORIGINAL_TEST_FILTER, g.ORIGINAL_TEST_FILTER],
                 [v for v in self.command if v != "--lib"] + ["--features", "p28-word0196-original-rom", g.ORIGINAL_TEST_FILTER]]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(g.BuildGuardError):
                g.preflight(**self.arguments(command=command))

    def test_full_suites_and_exact_original_filter_only_in_owned_target(self):
        full = [v for v in self.command if v != "--lib"]
        for feature in (None, "p28-word0196-audit", "p28-word0196-original-rom"):
            command = full if feature is None else full + ["--features", feature]
            with self.subTest(feature=feature):
                g.preflight(**self.arguments(command=command))
                for replacement in (None, str(self.manifest.parent / "target")):
                    bad = list(command)
                    index = bad.index("--target-dir")
                    if replacement is None:
                        del bad[index:index + 2]
                    else:
                        bad[index + 1] = replacement
                    with self.assertRaises(g.BuildGuardError):
                        g.guarded_execute(spawn=lambda *_a, **_k: self.fail("Unsafe target reached spawn"),
                                          **self.arguments(command=bad))
        targeted = self.command + ["--features", "p28-word0196-original-rom", g.ORIGINAL_TEST_FILTER]
        g.preflight(**self.arguments(command=targeted))

    def test_cargo_config_in_cwd_manifest_or_cache_is_not_silently_accepted(self):
        for config in (self.repo / ".cargo/config.toml", self.manifest.parent / ".cargo/config", self.cargo_home / "config.toml"):
            config.parent.mkdir(exist_ok=True)
            config.write_text('[build]\ntarget-dir="old"\n', encoding="utf-8")
            with self.assertRaisesRegex(g.BuildGuardError, "UnreviewedCargoConfiguration"):
                g.preflight(**self.arguments())
            config.unlink()

    def test_ancestor_workspace_cannot_redirect_manifest_discovery(self):
        (self.repo / "Cargo.toml").write_text('[workspace]\nmembers=[]\n', encoding="utf-8")
        with self.assertRaisesRegex(g.BuildGuardError, "UnreviewedAncestorCargoManifest"):
            g.preflight(**self.arguments())

    def test_new_project_build_script_cannot_write_custom_outputs(self):
        (self.manifest.parent / "build.rs").write_text('fn main() {}', encoding="utf-8")
        with self.assertRaisesRegex(g.BuildGuardError, "ProjectBuildScriptRejected"):
            g.preflight(**self.arguments())

    def test_manifest_and_lock_digests_remain_exact(self):
        with self.assertRaisesRegex(g.BuildGuardError, "ManifestIdentityMismatch"):
            g.preflight(**self.arguments(expected_manifest_sha256="0" * 64))
        with self.assertRaisesRegex(g.BuildGuardError, "LockIdentityMismatch"):
            g.preflight(**self.arguments(expected_lock_sha256="0" * 64))

    def test_historical_build_is_allowed_only_with_explicit_owned_target(self):
        command = [v for v in self.command if v != "--lib"]
        command[2] = "build"
        g.preflight(**self.arguments(command=command))

    def test_unknown_dependency_build_script_and_custom_path_are_rejected(self):
        self.lock.write_text('version=4\n[[package]]\nname="invented"\nversion="0.40.0"\n'
                             '[[package]]\nname="fixture"\nversion="1.0.0"\n'
                             'source="registry+https://github.com/rust-lang/crates.io-index"\nchecksum="00"\n', encoding="utf-8")
        root = self.cargo_home / "registry/src/test/fixture-1.0.0"
        root.mkdir(parents=True)
        (root / "Cargo.toml").write_text('[package]\nname="fixture"\nversion="1.0.0"\nbuild="build.rs"\n', encoding="utf-8")
        (root / "build.rs").write_text('fn main() { panic!("unreviewed"); }', encoding="utf-8")
        with self.assertRaisesRegex(g.BuildGuardError, "UnreviewedDependencyBuildScript"):
            g.preflight(**self.arguments())
        (root / "Cargo.toml").write_text('[package]\nname="fixture"\nversion="1.0.0"\nbuild="../escape.rs"\n', encoding="utf-8")
        with self.assertRaisesRegex(g.BuildGuardError, "CustomDependencyBuildPathRejected"):
            g.preflight(**self.arguments())


if __name__ == "__main__":
    unittest.main()
