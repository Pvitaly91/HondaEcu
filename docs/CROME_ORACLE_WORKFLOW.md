# Crome oracle workflow

Crome is an independent observation tool, not an absolute source of truth. Keep all baseline, no-op, case, and re-save ROMs under ignored `private/oracle/` paths. Do not commit an installer, ROM, or generated oracle report. Do not flash files made by this workflow; they are for PC analysis only.

Record the exact Crome version, edition/variant, optional plugin list, and whether plugins were disabled. Also record OS/environment and every relevant editor option. The [official Crome page](https://crome.io/) describes P28 support and currently publishes its stable version; the manifest must record the version actually used, not a version assumed from the website. These fields are provenance declared by the collector. A tool name in JSON does not prove that Crome produced the bytes.

Use the [M0.1 collection checklist](M0_1_ORACLE_COLLECTION_CHECKLIST.md) while collecting files. The checked-in [manifest template](templates/oracle-manifest.m0-1.json.template) is an intentionally unpopulated field reference; generate real hashes and ranges locally with the CLI.

## Controlled collection procedure

1. Take one unchanged local copy of the P28-304 baseline and place it at `private/oracle/p28-304/base.bin`.
2. Record its SHA-256 before opening it, keep it read-only where practical, and use byte-identical copies for both Crome and HTS. Cross-editor comparison is invalid if their baseline hashes differ.
3. Record Crome's exact version and edition/variant, plugins and features, disabled state, OS/environment, and collection notes. Do not infer these from the website.
4. Disable every optional plugin, extra feature, RTP option, and datalogging patch. Record the resulting configuration. `plugins-disabled=true` does not prove Crome has no built-in save transformation.
5. In a fresh editor session, open a copy of the baseline and save without a parameter change to `crome-noop-a.bin`.
6. Reopen `crome-noop-a.bin`, record the values Crome displays and any warnings, and save again to a new `crome-noop-a-resave.bin`.
7. Independently start again from a byte-identical baseline copy, preferably in a fresh session, and save a second no-op as `crome-noop-b.bin`.
8. Record hashes and exact byte ranges for `base → noop-a`, `base → noop-b`, and `noop-a → noop-a-resave`.
9. Determine whether the two independent no-op outputs are byte-identical and whether the re-save stabilizes. Keep every differing hash and range visible; do not average or silently normalize them.
10. Treat an unknown no-op difference as an unknown transformation—not automatically a checksum, error, or allowed change. If Crome changes runtime code or layout, document a separate transformation profile for that exact provenance. Do not treat the native baseline and Crome-modified code base as the same compatibility scope.
11. Designate and hash the exact no-op-controlled parent used to make cases. Every case in the series must start from that same parent; do not mix native and transformed parents in one analysis.
12. For one parameter, create at least three independent discovery/training files. Change only that requested parameter, once per new file.
13. For every case record the requested value, then reopen it and separately record the displayed value. Raw bytes are measured from the file and remain a third, separate observation.
14. Collect at least one independent repeat in a new file/session. Identical repeats measure repeatability but do not add an independent fitting value. The same requested value producing different raw bytes is a conflict and must retain both provenances.
15. Expect quantization: different requested values may map to the same displayed value and raw bytes. Retain those observations; do not reject them as non-monotonic or pretend they are independent formula points.
16. Declare separate holdout cases before analysis. Do not use holdouts to fit coefficients or widen tolerance. Use their independent values and exact bytes to rule out contradicted training-compatible candidates/policies while preserving both the original and holdout-compatible policy sets in the report.
17. After freezing a candidate, choose boundary and midpoint cases from its raw/engineering domain and values Crome actually permits. Do not apply a universal RPM step.
18. Never save over `base.bin`, a no-op, or a case. Every artifact and re-save uses a new filename.
19. Run `hondaecu oracle preflight` and resolve missing files, stale hashes/digests, provenance gaps, repeat conflicts, no-op instability, and insufficient train/holdout data.
20. Run `hondaecu oracle analyze`; inspect all alternative offsets, widths, endianness, conversions, and rounding policies—not only the best fit score.
21. Review actual changed bytes, bytes covered by hypotheses, bytes explained by a selected and verified definition, checksum storage, no-op transformations, and unexplained bytes as separate sets.
22. A candidate may be exported only by an explicit action and human review. Selecting it adds no evidence, never makes it writable, and never edits the checked-in profile automatically.
23. In a later reviewed validation step, reopen any HondaEcu output in the same Crome provenance, record the displayed value, and save to a new re-save file.
24. Compare the HondaEcu output with that Crome re-save. Exact parameter bytes and all residual changes must be accounted for before any cross-editor claim.

## Initial control series

Use separate files for each value:

| Parameter | Values |
|---|---|
| `rev_limit_rpm` | 6500, 7000, 7500 RPM |
| `vtec_crossover_rpm` | 4000, 5000, 5500 RPM |

The published P28 map does not establish a P28-304 rev-limiter offset. Both series are discovery inputs for fitting only, not holdouts, boundary tests, pre-approved definitions, or writable parameters. Holdouts must be collected separately. Boundary and rounding-discrimination values depend on the candidate formula and the values Crome accepts.

## Example commands

```text
hondaecu oracle create-manifest --tool Crome --tool-version VERSION --tool-edition EDITION_OR_VARIANT --profile p28-304 --baseline private/oracle/p28-304/base.bin --noop private/oracle/p28-304/crome-noop-a.bin --independent-noop private/oracle/p28-304/crome-noop-b.bin --resaved-noop private/oracle/p28-304/crome-noop-a-resave.bin --output private/reports/crome-oracle.json --plugins-disabled

hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 6500 --displayed-value VALUE_AFTER_REOPEN --role training --observation-id crome-rev-6500-training-1 --rom private/oracle/p28-304/crome-rev-6500-training-1.bin
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 7000 --displayed-value VALUE_AFTER_REOPEN --role training --observation-id crome-rev-7000-training-1 --rom private/oracle/p28-304/crome-rev-7000-training-1.bin
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 7500 --displayed-value VALUE_AFTER_REOPEN --role training --observation-id crome-rev-7500-training-1 --rom private/oracle/p28-304/crome-rev-7500-training-1.bin
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 6500 --displayed-value VALUE_AFTER_REOPEN --role training --observation-id crome-rev-6500-repeat-2 --rom private/oracle/p28-304/crome-rev-6500-repeat-2.bin
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value HOLDOUT_VALUE --displayed-value VALUE_AFTER_REOPEN --role holdout --observation-id crome-rev-holdout-1 --rom private/oracle/p28-304/crome-rev-holdout-1.bin

hondaecu oracle preflight --manifest private/reports/crome-oracle.json --output private/reports/crome-preflight.json
hondaecu oracle analyze --manifest private/reports/crome-oracle.json --output private/reports/crome-analysis.json
hondaecu oracle export-candidate --analysis private/reports/crome-analysis.json --candidate-id CANDIDATE_ID --output private/reports/crome-candidate.json
```

Replace every placeholder with a value recorded from the local collection. `--displayed-value` keeps the reopened display distinct from the requested value; raw bytes come from the case file. `--role training` is the default, but specify it for audit clarity. Repeats are inferred from retained observations; do not reuse an observation id. Integer-only observations do not establish a rounding rule; midpoint cases distinguish `Nearest` from `ToEven`, while negative fractional inputs are required before extending `Floor`/`Truncate` equivalence beyond a non-negative domain.

When there is independent evidence for a continuous unrounded raw-input interval, add repeatable `--rounding-domain PARAMETER=MINIMUM:MAXIMUM --domain-evidence "EVIDENCE AND SCOPE"` options to `create-manifest`. Do not substitute training-sample extrema. Optional `--transformation-profile ID` records a claimed, separately documented transformation profile; it authorizes nothing and does not raise compatibility.

Repeat the manifest/case discipline for VTEC crossover. A candidate may be exported only by an explicit `export-candidate` action and human review; analysis never edits the checked-in profile.

For cross-editor work, use the exact same baseline SHA-256 in the HTS workflow, then run:

```text
hondaecu oracle compare --crome private/reports/crome-oracle.json --hts private/reports/hts-oracle.json --output private/reports/cross-editor.json
```

After reviewing both analyses, an explicit comparison selection uses repeatable `--crome-candidate PARAMETER=CANDIDATE_ID` and `--hts-candidate PARAMETER=CANDIDATE_ID` plus `--selection-reason "REVIEWED REASON"`. Analyzer selection similarly uses repeatable `--select-candidate PARAMETER=CANDIDATE_ID` with a reason. Selection preserves every alternative and adds no evidence; exact independent holdout bytes must still distinguish the definition.

Do not label a result `cross-editor-confirmed` if the baseline hashes differ, the two manifests name the same normalized editor, either provenance/digest is stale, holdouts were used for fitting, candidate alternatives remain unresolved, exact holdout bytes disagree, or any actual change lacks a verified explanation. `HasCommonCandidate` is not `UniqueValidatedDefinition`.

Until real private Crome files following this procedure exist, Crome M1 data status is `AwaitingUserFiles`. Synthetic fixtures validate analyzer behavior only and must never be represented as Crome output.
