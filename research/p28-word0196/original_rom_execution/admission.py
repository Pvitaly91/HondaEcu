"""Host source admission; never manufactures native state or executes code.

Only private callers can pass an explicit local M2bs-verified image. Public
invented PROGRAM fixtures take a separate admission path in the Rust adapter.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path

from original_rom_boundary.verify import (
    ReadOnlyImage, file_binding, local_path, load_profile, preflight_outputs,
    verify_original_rom,
)

ROOT = Path(__file__).resolve().parents[3]
BASE = "4196153c6bcda3da5b164db752a8be4011c4e598"
M2BS_CONTRACT = ROOT / "research/p28-word0196/original_rom_boundary/contract.json"
M2BS_CONTRACT_SHA256 = "b8a1a482dfa8f48f310db89d291014d1f4ebf83f51022cf7f70fb1dea0c1da30"
MODE = "OriginalRomBytes_TechnicalSeededExecution"


class AdmissionError(ValueError):
    pass


def require(condition, code):
    if condition is not True:
        raise AdmissionError(code)


def validate_output_directory(directory, rom=None):
    """Resolve only selected output paths, reject reparse/ROM aliases upfront."""
    directory = local_path(directory).absolute()
    if rom is not None:
        source = local_path(rom).resolve(strict=True)
        require(directory != source, "OutputWouldOverwriteRom")
        require(not directory.exists() or not os.path.samefile(directory, source), "OutputWouldOverwriteRom")
        require(not directory.exists() or directory.is_dir(), "OutputDirectoryRequired")
        for name in ("summary.json", "canonical.jsonl.gz", "pre-runtime-freeze.json", "sourcejoin.json"):
            path = directory / name
            if path.exists():
                info = path.lstat()
                require(not path.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                        "OutputReparseAncestor")
                require(path.resolve() != source and not os.path.samefile(path, source),
                        "OutputWouldOverwriteRom")
        # The unchanged M2bs helper admits only new JSON outputs. A completed
        # M2bt resume instead validates its immutable summary/cache in the host;
        # it must not be mistaken for permission to rewrite an existing output.
        if not (directory / "summary.json").exists():
            preflight_outputs(source, [directory / "summary.json"])
    else:
        require(not directory.exists() or directory.is_dir(), "OutputDirectoryRequired")
    current = directory
    while current != current.parent:
        if current.exists():
            info = current.lstat()
            require(not current.is_symlink()
                    and not getattr(info, "st_file_attributes", 0) & 0x400,
                    "OutputReparseAncestor")
        current = current.parent
    return directory.resolve(strict=False)


class AdmittedOriginal:
    """One private immutable whole image and an original-PC execution segment."""
    def __init__(self, rom, profile, output_directory):
        validate_output_directory(output_directory, rom)
        contract = file_binding(M2BS_CONTRACT)
        require(contract["sha256"] == M2BS_CONTRACT_SHA256,
                "WrongM2bsSourceIdentity")
        self.report = verify_original_rom(rom, profile)
        require(self.report["passed"] is True
                and self.report["inputBeforeAfterEqual"] is True,
                "M2bsOriginalSourceVerificationFailed")
        _, historical = load_profile(profile)
        self.image = ReadOnlyImage(rom, historical["expectedSize"],
                                   historical["romHash"]["sha256"].lower())
        require(self.image.identity == {key: self.report["rom"][key]
                                       for key in ("bytes", "sha256")},
                "RomChangedBetweenVerificationAndAdmission")
        self.profile_binding = file_binding(profile)
        self.contract_binding = contract
        self.segment = self.image.data[0x556F:0x55C5]
        require(type(self.segment) is bytes and len(self.segment) == 86,
                "ClosedOriginalSegmentRequired")

    def program_request(self):
        self.assert_unchanged()
        return {"kind": "program", "schemaVersion": 1,
                "sourceBinding": {"baseCommit": BASE,
                                  "contractSha256": M2BS_CONTRACT_SHA256,
                                  "wholeRomSha256": self.image.identity["sha256"],
                                  "sourceAdmission": "M2bsHostVerifiedOriginalRom"},
                "segmentBase": 0x556F, "segmentBytes": list(self.segment),
                "segmentSha256": sha256(self.segment).hexdigest()}

    def assert_unchanged(self):
        self.image.assert_unchanged()
        require(file_binding(M2BS_CONTRACT) == self.contract_binding,
                "M2bsContractChanged")
        require(file_binding(self.profile_binding["path"]) == self.profile_binding,
                "M2bsProfileChanged")
        return True

    def private_identity(self):
        return {"classification": MODE, "rom": self.report["rom"],
                "profile": self.profile_binding, "m2bsContract": self.contract_binding,
                "segmentBase": 0x556F, "segmentEndExclusive": 0x55C5,
                "segmentBytes": len(self.segment),
                "segmentSha256": sha256(self.segment).hexdigest(),
                "relocated": False, "nativeSchedulerOwnershipClaimed": False,
                "strictEvidenceBoundCaseCount": 0,
                "factoryAuthenticity": "Unknown", "firmwareReady": False}
