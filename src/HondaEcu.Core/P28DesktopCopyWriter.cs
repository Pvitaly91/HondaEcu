namespace HondaEcu.Core;

/// <summary>
/// Publishes an existing, validated M1c result and its plan to three new paths.
/// Uses the existing staged document/pair writers with best-effort rollback;
/// this is not a filesystem transaction across three files.
/// </summary>
public static class P28DesktopCopyWriter
{
    public static P28RawThresholdVerificationReport Save(
        P28RawThresholdPatchResult result, string outputPath, string planPath, string reportPath,
        IEnumerable<string>? protectedPaths = null)
    {
        ArgumentNullException.ThrowIfNull(result);
        var destinations = new[] { outputPath, planPath, reportPath }.Select(Path.GetFullPath).ToArray();
        var sources = (protectedPaths ?? []).Concat(new[]
        {
            result.Baseline.SourcePath, result.Profile.SourcePath,
        }.OfType<string>()).ToArray();
        for (var index = 0; index < destinations.Length; index++)
        {
            foreach (var other in destinations.Skip(index + 1).Concat(sources))
            {
                AtomicFile.EnsureDifferentPath(destinations[index], other);
            }

            if (File.Exists(destinations[index]) || Directory.Exists(destinations[index]))
            {
                throw new IOException("Each BIN, plan and patch report destination must be a new file.");
            }
        }

        var check = P28RawThresholdEditor.Verify(result.Image, result.Baseline, result.Profile,
            result.Binding, result.Plan, result.Report);
        if (!check.IsValid)
        {
            throw new InvalidDataException("Raw patch result failed pre-write verification.");
        }

        var planJson = result.Plan.ToJson();
        AtomicFile.WriteAllText(destinations[1], planJson);
        try
        {
            P28RawThresholdEditor.WriteAtomic(result, destinations[0], destinations[2], sources.Append(destinations[1]));
        }
        catch (Exception publicationError)
        {
            try
            {
                // Only roll back the new plan this invocation published. Never remove a
                // different document another actor may have substituted at this path.
                if (File.Exists(destinations[1]) && File.ReadAllText(destinations[1]) == planJson)
                {
                    File.Delete(destinations[1]);
                }
            }
            catch (Exception rollbackError) when (rollbackError is IOException or UnauthorizedAccessException)
            {
                throw new AggregateException("Publication failed and the new plan could not be rolled back.",
                    publicationError, rollbackError);
            }

            throw;
        }

        // A failed readback is reported, not silently repaired or erased. Retain the
        // new artifacts for inspection; never claim their existence proves success.
        return VerifySavedCopy(result, destinations[0], destinations[1], destinations[2]);
    }

    public static P28RawThresholdVerificationReport VerifySavedCopy(
        P28RawThresholdPatchResult result, string outputPath, string planPath, string reportPath)
    {
        ArgumentNullException.ThrowIfNull(result);
        var parent = result.Baseline.SourcePath is { } source ? RomImage.Load(source) : result.Baseline;
        var plan = P28RawThresholdPlan.Load(planPath);
        var report = P28RawThresholdPatchReport.Load(reportPath);
        if (P28RawThresholdEditor.ComputePlanDigest(plan) != P28RawThresholdEditor.ComputePlanDigest(result.Plan) ||
            report.ToJson() != result.Report.ToJson())
        {
            throw new InvalidDataException("Saved plan or patch report differs from the confirmed in-memory result.");
        }

        return P28RawThresholdEditor.Verify(RomImage.Load(outputPath), parent, result.Profile, result.Binding,
            plan, report);
    }
}
