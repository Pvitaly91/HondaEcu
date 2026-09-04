# Crome oracle workflow

Crome is an independent observation tool, not an absolute source of truth. Keep all baseline, no-op, case, and re-save ROMs under ignored `private/oracle/` paths. Do not commit an installer or any ROM. Do not flash files made by this workflow; they are for PC analysis only.

Record the exact Crome version, optional plugin list, and whether plugins were disabled. The [official Crome page](https://crome.io/) describes P28 support and currently publishes its stable version; the manifest must record the version actually used, not a version assumed from the website.

## Exact 15-step procedure

1. Take one unchanged local copy of the P28-304 baseline and place it at `private/oracle/p28-304/base.bin`.
2. Record the baseline SHA-256 before opening it. Preserve that value in your notes and manifest.
3. Open that exact copy in Crome.
4. Disable every optional plugin, extra feature, RTP option, and datalogging patch. Record the resulting configuration.
5. Without changing a parameter, save to a new file named `crome-noop.bin`.
6. Reopen `crome-noop.bin` in Crome and confirm that the displayed calibration parameters did not change. Record any warning or normalization Crome reports.
7. For one parameter, create at least three separate case files from the same baseline/no-op-controlled starting point.
8. In each case file, change only that one parameter to one recorded engineering value.
9. Never use Save over `base.bin`; every no-op, case, and re-save uses a new filename.
10. Reopen every case file in Crome and record the value Crome displays after reloading it.
11. Create/update the manifest and run `hondaecu oracle analyze`; inspect every candidate and no-op-normalized range, not only the highest-confidence result.
12. After HondaEcu creates an output for the reviewed candidate, open that output in Crome.
13. Verify and record the value Crome displays, including any rounding difference or warning.
14. Save the HondaEcu output again from Crome to a new re-save file.
15. Compare the HondaEcu output with the Crome re-save and account separately for parameter bytes, checksum bytes, and no-op/plugin normalization.

## Initial control series

Use separate files for each value:

| Parameter | Values |
|---|---|
| `rev_limit_rpm` | 6500, 7000, 7500 RPM |
| `vtec_crossover_rpm` | 4000, 5000, 5500 RPM |

The published P28 map does not establish a P28-304 rev-limiter offset. The series above is therefore an oracle experiment, not a pre-approved definition.

## Example commands

```text
hondaecu oracle create-manifest --tool Crome --tool-version VERSION --profile p28-304 --baseline private/oracle/p28-304/base.bin --noop private/oracle/p28-304/crome-noop.bin --output private/reports/crome-oracle.json --plugins-disabled

hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 6500 --rom private/oracle/p28-304/crome-rev-6500.bin
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 7000 --rom private/oracle/p28-304/crome-rev-7000.bin
hondaecu oracle add-case --manifest private/reports/crome-oracle.json --parameter rev_limit_rpm --value 7500 --rom private/oracle/p28-304/crome-rev-7500.bin

hondaecu oracle analyze --manifest private/reports/crome-oracle.json --output private/reports/crome-analysis.json
```

Append `--displayed-value VALUE_AFTER_REOPEN` to each `add-case` command when the reopened display differs or when you want the manifest to preserve explicit rounding evidence. `--value` remains the value originally requested.

Repeat the manifest/case discipline for VTEC crossover. A candidate may be exported only by an explicit `export-candidate` action and human review; analysis never edits the checked-in profile.

For cross-editor work, use the exact same baseline SHA-256 in the HTS workflow, then run:

```text
hondaecu oracle compare --crome private/reports/crome-oracle.json --hts private/reports/hts-oracle.json --output private/reports/cross-editor.json
```

Do not label a result `cross-editor-confirmed` if the baseline hashes differ, either editor changed more than the isolated parameter plus explained normalization, or conversion/rounding remains ambiguous.
