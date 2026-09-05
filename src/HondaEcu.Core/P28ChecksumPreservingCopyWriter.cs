namespace HondaEcu.Core;

/// <summary>Historical observation, never a capability to publish another file.</summary>
public sealed record P28ChecksumExportObservation(string ImageKind, RomHash Hash, int ScratchPattern,
    NativeChecksumExecutionStatus Status, bool Complete, int ComputedResult, string Decision,
    int Invocations, int Steps, int ProgramReadCount, bool CoverageMatches,
    bool IntermediateStateMatches, IReadOnlyList<string> UsedAssumptions);

public sealed record P28ChecksumPreservingExportReport(string FormatVersion, string Purpose,
    P28ChecksumPreservingReport CompositionReport, string RunnerVersion, string UpstreamCommit,
    IReadOnlyList<string> LocalSemanticFixes, IReadOnlyList<P28ChecksumExportObservation> Observations,
    string ExecutionEvidenceScope)
{
    public const string Version = "1.0";
    public const string ReportPurpose = "checksum-preserving-pc-only-export-receipt";
    public const string HistoricalScope = "Historical strict M1f observations for these exact bytes; reopening verifies composition, not a new execution. No publication authority, full ECU boot or hardware safety claim.";
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public static P28ChecksumPreservingExportReport Load(string path) => Parse(File.ReadAllText(path));
    public static P28ChecksumPreservingExportReport Parse(string json)
    {
        var receipt = P28RawEditJson.Parse<P28ChecksumPreservingExportReport>(json);
        P28ChecksumPreservingEditor.ValidateReportShape(receipt.CompositionReport);
        if (receipt.FormatVersion != Version || receipt.Purpose != ReportPurpose ||
            receipt.ExecutionEvidenceScope != HistoricalScope || receipt.CompositionReport.SyntheticOnly ||
            string.IsNullOrWhiteSpace(receipt.RunnerVersion) || string.IsNullOrWhiteSpace(receipt.UpstreamCommit) ||
            receipt.Observations.Count != 6)
            throw new InvalidDataException("Unsupported or incomplete checksum export receipt.");
        _ = SliceRunnerIdentity.Validate(System.Text.Json.JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = "checksumBatch",
            runnerVersion = receipt.RunnerVersion,
            upstreamCommit = receipt.UpstreamCommit,
            localSemanticFixes = receipt.LocalSemanticFixes,
        }), "checksumBatch");
        foreach (var kind in new[] { "baseline", "derived" })
        {
            var rows = receipt.Observations.Where(row => row.ImageKind == kind).ToArray();
            var expectedHash = kind == "baseline" ? receipt.CompositionReport.BaselineHash : receipt.CompositionReport.OutputHash;
            // 511 * 205 + 208 instructions is the reviewed zero-residue path.
            // Checking this receipt contract is not authenticating its history
            // or granting authority to publish another file.
            if (rows.Length != 3 || !rows.Select(row => row.ScratchPattern).Order().SequenceEqual(new[] { 0, 85, 170 }) ||
                rows.Any(row => row.Hash != expectedHash || row.Status != NativeChecksumExecutionStatus.Match ||
                    !row.Complete || row.ComputedResult != 0 || row.Decision != "ResidueZero" ||
                    row.Invocations != 512 || row.Steps != 104963 || row.ProgramReadCount != 32768 ||
                    !row.CoverageMatches || !row.IntermediateStateMatches || row.UsedAssumptions.Count != 0))
                throw new InvalidDataException("Receipt does not describe complete strict zero-residue observations for the exact parent and output.");
        }
        return receipt;
    }

    internal static P28ChecksumPreservingExportReport From(P28VerifiedChecksumExport validated)
    {
        var native = validated.ChecksumReport;
        var receipt = new P28ChecksumPreservingExportReport(Version, ReportPurpose, validated.Composition.Report,
            native.RunnerVersion ?? "", native.UpstreamCommit ?? "", native.LocalSemanticFixes,
            native.Cases.SelectMany(item => item.Execution.Select(run => new P28ChecksumExportObservation(
                item.Id, item.Hash, run.ScratchPattern, run.Status, run.Complete, run.ComputedResult ?? -1,
                run.Decision ?? "", run.Invocations, run.Steps, run.ProgramReadCount, run.CoverageMatches,
                run.IntermediateStateMatches, run.UsedAssumptions))).ToArray(), HistoricalScope);
        return Parse(receipt.ToJson(false));
    }
}

/// <summary>Three new paths using existing staged writers and best-effort rollback, not a group power-loss transaction.</summary>
public static class P28ChecksumPreservingCopyWriter
{
    public static P28ChecksumPreservingVerification Save(P28VerifiedChecksumExport validated,
        string outputPath, string planPath, string reportPath, IEnumerable<string>? protectedPaths = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(validated);
        cancellationToken.ThrowIfCancellationRequested();
        P28ChecksumPreservingExecution.ValidateForPublication(validated);
        var composition = validated.Composition;
        var destinations = new[] { outputPath, planPath, reportPath }.Select(Path.GetFullPath).ToArray();
        var sources = (protectedPaths ?? []).Concat(new[] { composition.Baseline.SourcePath, composition.Profile.SourcePath }.OfType<string>()).ToArray();
        for (var index = 0; index < destinations.Length; index++)
        {
            foreach (var other in destinations.Skip(index + 1).Concat(sources)) AtomicFile.EnsureDifferentPath(destinations[index], other);
            if (File.Exists(destinations[index]) || Directory.Exists(destinations[index]))
                throw new IOException("Each BIN, composed plan and export receipt destination must be a new file.");
        }
        RequireCurrentParent(composition);
        var planJson = composition.Plan.ToJson();
        var reportJson = P28ChecksumPreservingExportReport.From(validated).ToJson();
        cancellationToken.ThrowIfCancellationRequested();
        AtomicFile.WriteAllText(destinations[1], planJson);
        try
        {
            // Once publication begins, finish rollback/readback rather than interrupting the file group.
            AtomicOutputPair.Write(destinations[0], composition.Image.Span, destinations[2], reportJson, overwrite: false);
        }
        catch (Exception publicationError)
        {
            try
            {
                if (File.Exists(destinations[1]) && File.ReadAllText(destinations[1]) == planJson) File.Delete(destinations[1]);
            }
            catch (Exception rollbackError) when (rollbackError is IOException or UnauthorizedAccessException)
            {
                throw new AggregateException("Publication failed; the newly published plan could not be rolled back.", publicationError, rollbackError);
            }
            throw;
        }
        return VerifySavedCopy(validated, destinations[0], destinations[1], destinations[2]);
    }

    public static P28ChecksumPreservingVerification VerifySavedCopy(P28VerifiedChecksumExport validated,
        string outputPath, string planPath, string reportPath)
    {
        ArgumentNullException.ThrowIfNull(validated);
        P28ChecksumPreservingExecution.ValidateForPublication(validated);
        var composition = validated.Composition;
        var parent = RequireCurrentParent(composition);
        var plan = P28ChecksumPreservingPlan.Load(planPath);
        var receipt = P28ChecksumPreservingExportReport.Load(reportPath);
        if (plan.ToJson(false) != composition.Plan.ToJson(false) || receipt.ToJson(false) != P28ChecksumPreservingExportReport.From(validated).ToJson(false))
            throw new InvalidDataException("Saved plan or receipt differs from the confirmed, actually executed composition. New artifacts are retained for inspection.");
        return P28ChecksumPreservingEditor.Verify(RomImage.Load(outputPath), parent, composition.Profile,
            composition.Binding, plan, receipt.CompositionReport, composition.Location);
    }

    private static RomImage RequireCurrentParent(P28VerifiedChecksumComposition composition)
    {
        var parent = composition.Baseline.SourcePath is { } source ? RomImage.Load(source) : composition.Baseline;
        if (parent.Hash != composition.Baseline.Hash) throw new InvalidDataException("Original parent changed after validation.");
        if (composition.Profile.SourcePath is { } profilePath &&
            P28VtecInspector.ComputeProfileDigest(RomProfile.Load(profilePath)) != P28VtecInspector.ComputeProfileDigest(composition.Profile))
            throw new InvalidDataException("Profile changed after validation.");
        return parent;
    }
}
