"""Own invented documentary/archive refusal tests, not fake release receipts."""
import copy
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
import zipfile

sys.dont_write_bytecode = True
import validate_asm662_original_release as policy

counts = dict(positive=0, negative=0, properties=0, propertyVectors=0)
named = []


def accept(name, action):
    result = action()
    counts["positive"] += 1
    named.append(name)
    return result


def refuse(name, action):
    try:
        action()
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        counts["negative"] += 1
        named.append(name)
        return
    raise AssertionError("Unsafe/forged metadata accepted: " + name)


def tar_fixture(rows):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, kind, data in rows:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.mtime = 0
            member.size = len(data) if kind == tarfile.REGTYPE else 0
            member.linkname = "../../invented-external" if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE} else ""
            archive.addfile(member, io.BytesIO(data) if member.size else None)
    return gzip.compress(stream.getvalue(), mtime=0)


def zip_fixture(name="owned-fixture.txt", data=b"owned synthetic text", mode=0o100644):
    stream = io.BytesIO()
    member = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
    member.create_system = 3
    member.external_attr = mode << 16
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(member, data)
    return stream.getvalue()


def model():
    return {"scope": "InventedDocumentaryPolicyModel", "gates": {name: True for name in policy.GATES},
            "claims": {name: False for name in ["actualAcquisition", "legalApproval", "buildVerified",
                       "runtimeVerified", "targetEncodingVerified", "nativeHistory", "firmwareReady",
                       "mitigationImplemented", "executionPermission"]}}


def leaves(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from leaves(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from leaves(value, path + (index,))
    else:
        yield path, node


def changed(node, path, value):
    result = copy.deepcopy(node)
    cursor = result
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return result


def blocked(name, gate):
    record = model()
    record["gates"][gate] = False
    result = policy.classify_model(record)
    policy.demand(result["classification"] == "ModelBlocked" and result["blockers"] == [gate]
                  and not result["executionPermission"], "Prerequisite waived")
    counts["negative"] += 1
    named.append(name)


def main():
    policy.demand(len(sys.argv) <= 2, "At most one research directory")
    directory = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).parent
    actual = policy.load_contract(directory / "asm662_original_release_contract.json")
    accept("reviewed_official_acquisition_not_build_permission", lambda: policy.validate(actual))
    result = accept("complete_mock_documentary_prerequisites_not_legal_approval", lambda: policy.classify_model(model()))
    policy.demand(not result["legalApproval"] and not result["actualAcquisition"], "Model promoted")
    accept("owned_tar_container_not_original_release", lambda: policy.inspect_invented_archive(
        tar_fixture([("owned-fixture.txt", tarfile.REGTYPE, b"own invented text")])) )
    accept("owned_zip_container_not_original_release", lambda: policy.inspect_invented_archive(zip_fixture()))
    accept("owned_directory_structure", lambda: policy.inspect_invented_archive(tar_fixture([
        ("fixture-dir", tarfile.DIRTYPE, b""), ("fixture-dir/owned.txt", tarfile.REGTYPE, b"x")])) )
    requested = [
        ("sourceforge_listing_without_bytes", "bytesObserved"),
        ("missing_license", "componentLicenseNotices"),
        ("project_license_applied_to_all_components", "rightsNotProjectInferred"),
        ("mirror_unlicense_automatic_original_relicensing", "rightsNotMirrorInferred"),
        ("original_bsd_applied_to_future_unknown_contributions", "originalRightsScope"),
        ("missing_doc_contribution_rights", "docRights"),
        ("same_hash_claimed_independent", "independentProvenance"),
        ("rcs_revision_mismatch", "rcsCorrespondence"),
        ("old_generated_artifact_mixed_new_inputs", "generatedInputsMatch"),
        ("incomplete_source_claimed_complete", "sourceComplete"),
    ]
    for name, gate in requested:
        blocked(name, gate)
    for claim, name in [("mitigationImplemented", "proposal_claimed_implemented"),
                        ("runtimeVerified", "source_completeness_claimed_safe_runtime"),
                        ("buildVerified", "compiler_build_claimed_run_without_logs"),
                        ("targetEncodingVerified", "target_bytes_verified_without_execution"),
                        ("actualAcquisition", "mock_package_claimed_real_acquisition"),
                        ("nativeHistory", "invented_native_history"),
                        ("legalApproval", "unverified_rights_claimed_legal_approval"),
                        ("firmwareReady", "firmware_ready_promotion"),
                        ("executionPermission", "manual_model_execution_permission")]:
        refuse(name, lambda: policy.classify_model(changed(model(), ("claims", claim), True)))
    refuse("html_download_page_not_tar", lambda: policy.inspect_invented_archive(b"<html>download</html>"))
    valid = tar_fixture([("owned-fixture.txt", tarfile.REGTYPE, b"x")])
    damaged = bytearray(valid)
    damaged[-8] ^= 1
    refuse("damaged_archive_gzip_crc", lambda: policy.inspect_invented_archive(bytes(damaged)))
    refuse("damaged_archive_truncation", lambda: policy.inspect_invented_archive(valid[:-2]))
    for name in ["../escape", "/absolute", "C:/drive", "\\\\server\\share", "dir/../../escape",
                 "file:stream", "CON.txt", "dir./name", "file ", "a\x01b", "a?b", "a*b", 'a"b', "a|b", "a<b"]:
        refuse("file_traversal_or_windows_ambiguity:" + repr(name), lambda: policy.inspect_invented_archive(
            tar_fixture([(name, tarfile.REGTYPE, b"x")])))
    for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE]:
        refuse("symlink_escape_or_special:" + repr(kind), lambda: policy.inspect_invented_archive(
            tar_fixture([("owned-fixture", kind, b"")])))
    refuse("duplicate_member_conflict", lambda: policy.inspect_invented_archive(tar_fixture([
        ("owned.txt", tarfile.REGTYPE, b"x"), ("owned.txt", tarfile.REGTYPE, b"y")])) )
    refuse("casefold_member_conflict", lambda: policy.inspect_invented_archive(tar_fixture([
        ("Owned.txt", tarfile.REGTYPE, b"x"), ("owned.txt", tarfile.REGTYPE, b"y")])) )
    for rows in [[("a", tarfile.REGTYPE, b"x"), ("a/b", tarfile.REGTYPE, b"x")],
                 [("a/b", tarfile.REGTYPE, b"x"), ("a", tarfile.REGTYPE, b"x")]]:
        refuse("file_parent_conflict", lambda: policy.inspect_invented_archive(tar_fixture(rows)))
    for payload in [b"MZfake", b"\x7fELFfake", b"PK\x03\x04fake", b"Rar!fake",
                    b"7z\xbc\xaf\x27\x1cfake", b"BZhfake", b"\xfd7zXZ\0fake",
                    b"\0" * 257 + b"ustar" + b"\0" * 250]:
        refuse("unexpected_binary_or_nested_payload", lambda: policy.inspect_invented_archive(
            tar_fixture([("owned.txt", tarfile.REGTYPE, payload)])))
    refuse("gzip_concatenation", lambda: policy.inspect_invented_archive(valid + valid))
    tar_data = gzip.decompress(valid)
    hidden = gzip.compress(tar_data + b"hidden" + b"\0" * 1018, mtime=0)
    refuse("hidden_tar_suffix", lambda: policy.inspect_invented_archive(hidden))
    for raw in [zip_fixture() + b"garbage", zip_fixture(mode=0o120777),
                zip_fixture(mode=0o040777), zip_fixture(name="owned/", mode=0o100644),
                zip_fixture(name="../escape") + zip_fixture()]:
        refuse("zip_suffix_link_or_directory_contradiction", lambda: policy.inspect_invented_archive(raw))
    zipped = bytearray(zip_fixture(data=b"distinct-fixture-payload"))
    zipped[zipped.index(b"distinct-fixture-payload")] ^= 1
    refuse("damaged_zip_crc", lambda: policy.inspect_invented_archive(bytes(zipped)))
    refuse("compressed_fixture_limit", lambda: policy.inspect_invented_archive(b"x" * 1048577))
    refuse("member_fixture_limit", lambda: policy.inspect_invented_archive(tar_fixture([
        ("owned.txt", tarfile.REGTYPE, b"x" * 1048577)])))
    refuse("member_count_limit", lambda: policy.inspect_invented_archive(tar_fixture([
        (f"owned-{i}.txt", tarfile.REGTYPE, b"x") for i in range(65)])))
    for section in actual:
        forged = copy.deepcopy(actual)
        del forged[section]
        refuse("missing_actual_section:" + section, lambda: policy.validate(forged))
    for path, value in leaves(actual):
        for replacement in [None, False, True, 0, 1, 1.0, "ForgedVerified", [], {}]:
            if not policy.equal(value, replacement):
                refuse("typed_actual_leaf_mutation", lambda: policy.validate(changed(actual, path, replacement)))
                counts["propertyVectors"] += 1
    counts["properties"] += 1
    for raw in [b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{}', b'{}\r\n', b'\xff', b' ' * 65537]:
        refuse("malformed_noncanonical_json", lambda: policy.parse_contract(raw))
    for mask in range(1 << len(policy.GATES)):
        record = model()
        for index, gate in enumerate(policy.GATES):
            record["gates"][gate] = bool(mask & (1 << index))
        result = policy.classify_model(record)
        policy.demand(len(result["blockers"]) == len(policy.GATES) - mask.bit_count()
                      and not result["executionPermission"] and not result["legalApproval"]
                      and not result["actualAcquisition"], "Gate algebra promoted mock facts")
        counts["propertyVectors"] += 1
    counts["properties"] += 1
    for gate in policy.GATES:
        for invalid in [None, 0, "Verified"]:
            refuse("model_gate_exact_boolean", lambda: policy.classify_model(changed(model(), ("gates", gate), invalid)))
    refuse("real_scope_not_model", lambda: policy.classify_model(changed(model(), ("scope",), "ActualRelease")))
    print(json.dumps(dict(milestone="M2az", passed=True, **counts, namedRequiredRefusals=22,
                         fixtureScope="InventedArchiveSafetyFixtureNotFakeReleaseReceipt",
                         actualAsm662Executions=0, actualBuilds=0, syntheticAssemblerOutputs=0,
                         targetBytes=0, firmwareBin=0), sort_keys=True))


if __name__ == "__main__":
    main()
