using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>One original-parent composition verified by the shared engine, never deserialized from a report.</summary>
public sealed class P28VerifiedChecksumComposition
{
    internal P28VerifiedChecksumComposition(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        RomImage image, P28ChecksumPreservingPlan plan, P28ChecksumPreservingReport report, VerifiedCompensationLocation location)
    {
        Baseline = baseline; Profile = profile; Binding = binding; Image = image;
        Plan = P28ChecksumPreservingPlan.Parse(plan.ToJson(false));
        Report = P28ChecksumPreservingReport.Parse(report.ToJson(false));
        Location = location;
    }
    internal RomImage Baseline { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Image { get; }
    public P28ChecksumPreservingPlan Plan { get; }
    public P28ChecksumPreservingReport Report { get; }
}

/// <summary>Produced only after this process observed complete strict native baseline/output matches.</summary>
public sealed class P28VerifiedChecksumExport
{
    private readonly string _checksumJson;
    internal P28VerifiedChecksumExport(P28VerifiedChecksumComposition composition, P28NativeChecksumReport report)
    {
        Composition = composition;
        _checksumJson = report.ToJson(false);
    }
    public P28VerifiedChecksumComposition Composition { get; }
    // Defensive deserialization prevents a caller from changing an observed proof
    // through collection aliases before the publication recheck.
    public P28NativeChecksumReport ChecksumReport =>
        JsonSerializer.Deserialize<P28NativeChecksumReport>(_checksumJson, JsonDefaults.Create())!;
}

public sealed record P28ChecksumPreservingInspectionReport(
    P28ChecksumPreservingVerification Verification, P28VtecInspectionReport OutputInspection,
    IReadOnlyList<P28ThresholdContextReport> DerivedContexts, bool PhysicalRpmAvailable,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety);

public static class P28ChecksumPreservingExecution
{
    public static async Task<P28VerifiedChecksumExport> ValidateForExportAsync(
        P28VerifiedChecksumComposition composition, string runner, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(composition);
        cancellationToken.ThrowIfCancellationRequested();
        P28ChecksumPreservingEditor.ValidateAdmittedChild(composition, composition.Baseline, composition.Profile,
            composition.Binding, composition.Image);
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner))
            throw new InvalidDataException("A selected existing Rust runner is required for verified checksum-preserving export; preview is not execution.");
        var report = await P28NativeChecksumVerifier.CheckAsync(composition.Baseline, composition.Profile,
            composition.Binding, true, runner, derived: composition.Image, options: options,
            cancellationToken: cancellationToken, composition: composition).ConfigureAwait(false);
        cancellationToken.ThrowIfCancellationRequested();
        RequireStrictSuccess(composition, report);
        return new(composition, report);
    }

    public static void ValidateForPublication(P28VerifiedChecksumExport export)
    {
        ArgumentNullException.ThrowIfNull(export);
        var composition = export.Composition;
        P28ChecksumPreservingEditor.ValidateAdmittedChild(composition, composition.Baseline, composition.Profile,
            composition.Binding, composition.Image);
        RequireStrictSuccess(composition, export.ChecksumReport);
    }

    private static void RequireStrictSuccess(P28VerifiedChecksumComposition composition, P28NativeChecksumReport report)
    {
        if (report.BaselineHash != composition.Baseline.Hash || report.DerivedHash != composition.Image.Hash ||
            report.PlanDigest != P28ChecksumPreservingEditor.ComputePlanDigest(composition.Plan) ||
            report.Mode != "strict" || report.PermittedAssumptions.Count != 0 || report.UsedAssumptions.Count != 0 ||
            report.HasFailure || report.Cases.Count != 2 || report.Counts.Total != 6 || report.Counts.MatchesWithoutAssumptions != 6 ||
            report.Cases.Any(item => item.ChecksumStatus != ChecksumStatus.Valid || item.Arithmetic.ComputedResult != 0 ||
                !item.CodeAssessment.ContractRecognized || !item.CodeAssessment.GateEnabled || item.Execution.Count != 3 ||
                item.Execution.Any(run => run.Status != NativeChecksumExecutionStatus.Match || !run.Complete ||
                    run.ComputedResult != 0 || run.Decision != "ResidueZero" || run.Invocations != 512 ||
                    !run.CoverageMatches || !run.IntermediateStateMatches || run.UsedAssumptions.Count != 0)) ||
            report.FlashReadiness != FlashReadinessStatus.PcInspectionOnly || report.FlashSafety != FlashSafetyStatus.NotFlashReady)
            throw new InvalidDataException("Verified export requires actual strict zero-residue ordinary-pass execution and complete ordered coverage for all baseline/output scratch cases. Not-run, canceled, unresolved or conditional results cannot authorize publication.");
    }
}
