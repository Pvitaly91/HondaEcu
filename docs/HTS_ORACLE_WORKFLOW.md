# Honda Tuning Suite oracle workflow

Honda Tuning Suite (HTS) is an independent observation tool, not an absolute source of truth. Keep all baseline, no-op, case, and re-save ROMs under ignored `private/oracle/` paths. Do not commit an installer or any ROM. Do not flash files made by this workflow; they are for PC analysis only.

Record the exact HTS version, optional plugin/feature list, and whether those additions were disabled. The [official HTS page](https://hondatuningsuite.com/) describes OBD1 fuel, timing, cut-off/calibration, and VTEC functionality, but the manifest must record the version actually used.

## Exact 15-step procedure

1. Take one unchanged local copy of the P28-304 baseline and place it at `private/oracle/p28-304/base.bin`—the same bytes used for Crome comparison.
2. Record the baseline SHA-256 before opening it. Preserve that value in your notes and manifest.
3. Open that exact copy in Honda Tuning Suite.
4. Disable every optional plugin, extra feature, RTP option, and datalogging patch. Record the resulting configuration.
5. Without changing a parameter, save to a new file named `hts-noop.bin`.
6. Reopen `hts-noop.bin` in HTS and confirm that the displayed calibration parameters did not change. Record any warning or normalization HTS reports.
7. For one parameter, create at least three separate case files from the same baseline/no-op-controlled starting point.
8. In each case file, change only that one parameter to one recorded engineering value.
9. Never use Save over `base.bin`; every no-op, case, and re-save uses a new filename.
10. Reopen every case file in HTS and record the value HTS displays after reloading it.
11. Create/update the manifest and run `hondaecu oracle analyze`; inspect every candidate and no-op-normalized range, not only the highest-confidence result.
12. After HondaEcu creates an output for the reviewed candidate, open that output in HTS.
13. Verify and record the value HTS displays, including any rounding difference or warning.
14. Save the HondaEcu output again from HTS to a new re-save file.
15. Compare the HondaEcu output with the HTS re-save and account separately for parameter bytes, checksum bytes, and no-op/plugin normalization.

## Initial control series

Use separate files for each value:

| Parameter | Values |
|---|---|
| `rev_limit_rpm` | 6500, 7000, 7500 RPM |
| `vtec_crossover_rpm` | 4000, 5000, 5500 RPM |

The series are experiments. They do not make the inferred offsets writable or flash-ready.

## Example commands

```text
hondaecu oracle create-manifest --tool "Honda Tuning Suite" --tool-version VERSION --profile p28-304 --baseline private/oracle/p28-304/base.bin --noop private/oracle/p28-304/hts-noop.bin --output private/reports/hts-oracle.json --plugins-disabled

hondaecu oracle add-case --manifest private/reports/hts-oracle.json --parameter vtec_crossover_rpm --value 4000 --rom private/oracle/p28-304/hts-vtec-4000.bin
hondaecu oracle add-case --manifest private/reports/hts-oracle.json --parameter vtec_crossover_rpm --value 5000 --rom private/oracle/p28-304/hts-vtec-5000.bin
hondaecu oracle add-case --manifest private/reports/hts-oracle.json --parameter vtec_crossover_rpm --value 5500 --rom private/oracle/p28-304/hts-vtec-5500.bin

hondaecu oracle analyze --manifest private/reports/hts-oracle.json --output private/reports/hts-analysis.json
```

Append `--displayed-value VALUE_AFTER_REOPEN` to each `add-case` command when the reopened display differs or when you want the manifest to preserve explicit rounding evidence. `--value` remains the value originally requested.

For cross-editor comparison, use the same baseline SHA-256 as Crome and run:

```text
hondaecu oracle compare --crome private/reports/crome-oracle.json --hts private/reports/hts-oracle.json --output private/reports/cross-editor.json
```

Do not label a result `cross-editor-confirmed` when baseline hashes differ, no-op changes are unexplained, the editors disagree on width/endian/conversion/rounding, or extra changed bytes cannot be isolated.
