using System.Globalization;
using System.Numerics;
using HondaEcu.Core;
using HondaEcu.Desktop.Controls;

namespace HondaEcu.Desktop.ViewModels;

public sealed record RpmCandidateView(P28RpmCandidate Candidate, string DomainText)
{
    public byte RawValue => Candidate.RawValue;
    public bool IsBest => Candidate.IsBest;
    public bool SimpleSelectable => Candidate.SimpleSelectable;
    public string IntervalText => Candidate.TransitionBand is { } interval ? MainViewModel.RpmIntervalText(interval) : "Немає finite transition band";
    public string ErrorText => Candidate.MinimaxError ?? "Недоступно";
    public string ReasonText => Candidate.SimpleSelectable ? DomainText : string.Join("; ", Candidate.IneligibilityReasons);
}

public sealed record RpmForwardView(string Samples, string Producer, string Compact, string Predicates, string Evidence);

public sealed partial class MainViewModel
{
    private RpmCandidateView? _selectedRpmCandidate;
    public IReadOnlyList<RpmCandidateView> RpmCandidates { get; private set; } = [];
    public IReadOnlyList<RpmForwardView> RpmForwardRows { get; private set; } = [];
    public IReadOnlyList<RpmPlotRegion> RpmPlotRows { get; private set; } = [];
    public bool HasRpmPlot => RpmPlotRows.Count != 0;
    public string RpmPlotCaption { get; private set; } = "";
    public string RpmCandidateSummary { get; private set; } = "Оберіть кандидата явно. Ties не мають прихованого переможця.";
    public RpmCandidateView? SelectedRpmCandidate
    {
        get => _selectedRpmCandidate;
        set
        {
            if (_selectedRpmCandidate?.RawValue == value?.RawValue) return;
            if (value is not null && !RpmCandidates.Contains(value)) return;
            // Candidate selection is not a new physical query, but invalidates the old plan/export.
            if (IsBusy) { InvalidateSession(); NotifyAll(); return; }
            ClearChecksumPreview();
            ClearRpmSelection();
            _selectedRpmCandidate = value;
            UpdateRpmCandidateDisplay();
            NotifyAll();
        }
    }

    internal static string RpmIntervalText(P28RpmInterval interval) =>
        $"{(interval.LowerInclusive ? "[" : "(")}{interval.Lower}, {interval.Upper ?? "+∞"}{(interval.UpperInclusive ? "]" : ")")}";

    private void UpdateRpmDisplays()
    {
        var report = _rpmReport!;
        var forward = report.Forward;
        var domain = report.SupportedNormalDomain is { } normal ? RpmIntervalText(normal) : "Недоступно";
        RpmCandidates = report.Inverse.Select(candidate => new RpmCandidateView(candidate, "Normal domain: " + domain)).ToArray();
        _selectedRpmCandidate = null;
        RpmPreviewSummary = $"{report.Status}\nMonotonicity: {report.MonotonicityStatus}; normal domain RPM: {domain}.\n" +
            $"Policy: {report.PolicyId}. Exact best raw: {string.Join(", ", report.BestCandidates.Select(item => item.RawValue))}.\n" +
            $"Дозволено: {string.Join(", ", report.Query.PermittedAssumptions.DefaultIfEmpty("немає — strict"))}; використано: {string.Join(", ", report.UsedAssumptions.DefaultIfEmpty("немає"))}.\n" +
            string.Join("\n", report.UnavailableReasons) + (forward is null ? "" :
                $"\nRequested RPM: {forward.RequestedRpm}; timerHz: {forward.TimerHz}; ideal ticks: {forward.IdealTicksPerSample}; floor/ceiling: {forward.FloorTicks}/{forward.CeilingTicks}; integer={forward.IntegralTicks}; all variants normal={forward.AllVariantsNormal}.\n" +
                string.Join("; ", forward.Reasons)) +
            "\nMathematics only; byte execution/checksum/hardware: NotRun. PhysicalRpmAvailable=false. PcInspectionOnly / NotFlashReady.";
        UpdateRpmCandidateDisplay();
    }

    private void UpdateRpmCandidateDisplay()
    {
        var candidate = _selectedRpmCandidate?.Candidate;
        var report = _rpmReport;
        RpmPlotRows = [];
        RpmPlotCaption = "";
        RpmCandidateSummary = candidate is null ? "Оберіть raw явно. Жоден best/tie не обрано автоматично." :
            $"raw {candidate.RawValue}; best={candidate.IsBest}; eligible={candidate.SimpleSelectable}.\n" +
            $"Transition hull: {(candidate.TransitionBand is { } band ? RpmIntervalText(band) : "недоступно")}; minimax error={candidate.MinimaxError ?? "недоступно"}.\n" +
            $"{candidate.BandQualification}\n" + string.Join("\n", candidate.Regions.Select(region =>
                $"{region.State}: {RpmIntervalText(region.Interval)} — {region.Reason}"));
        if (report?.Forward is not null)
        {
            var forward = candidate is null ? report.Forward : P28RpmPlanner.EvaluateForward(report.Query, candidate.RawValue);
            RpmForwardRows = forward!.Variants.Select(variant => new RpmForwardView(
                string.Join(",", variant.Samples),
                variant.Producer is { } producer ? $"{producer.Disposition}; T={producer.T}; S={producer.S}; written={producer.TWritten}; flags0217={producer.Flags0217:X2}; flags0231={producer.Flags0231:X2}" : "NotRun / capture invalid",
                variant.Compact is { } compact ? $"{compact.Code?.ToString(CultureInfo.InvariantCulture) ?? "?"} / {compact.ExtraBit?.ToString() ?? "?"}; {compact.Branch}" : "NotRun",
                $"{PredicateText(variant.OldPredicate)} → {PredicateText(variant.NewPredicate)}",
                $"{variant.Status}; normal={variant.NormalEligible}; used={string.Join(",", variant.UsedAssumptions)}; {string.Join("; ", variant.Reasons)}")).ToArray();
            if (candidate is not null) UpdateRpmPlot(candidate, report.Forward.RequestedRpm);
        }
        else RpmForwardRows = [];
    }

    private void UpdateRpmPlot(P28RpmCandidate candidate, string requested)
    {
        // Approximate coordinates ONLY. Core's rational comparisons and original endpoint flags decide everything.
        var target = DisplayNumber(requested);
        var points = candidate.TransitionBand is { Upper: not null } band
            ? new[] { target, DisplayNumber(band.Lower), DisplayNumber(band.Upper) }
            : new[] { target };
        var lower = Math.Max(0, points.Min() * 0.75);
        var upper = points.Max() * 1.25;
        var rows = new List<RpmPlotRegion>();
        foreach (var region in candidate.Regions)
        {
            var start = DisplayNumber(region.Interval.Lower);
            var end = region.Interval.Upper is null ? double.PositiveInfinity : DisplayNumber(region.Interval.Upper);
            if (end < lower || start > upper) continue;
            rows.Add(new(Math.Max(lower, start), Math.Min(upper, end), start < lower || region.Interval.LowerInclusive,
                end > upper || region.Interval.UpperInclusive, region.State.ToString()));
        }
        RpmPlotRows = rows.AsReadOnly();
        RpmPlotCaption = $"raw {candidate.RawValue}; zoom біля запиту/переходу; scenario {_rpmScenario!.Digest[..12]}. Повні області — вище та в JSON.";
    }

    private static double DisplayNumber(string rational)
    {
        var parts = rational.Split('/');
        return (double)BigInteger.Parse(parts[0], CultureInfo.InvariantCulture) / (double)BigInteger.Parse(parts[1], CultureInfo.InvariantCulture);
    }
    private static string PredicateText(bool? value) => value?.ToString() ?? "Unknown / NotSelected";
    private void ClearRpmDisplays()
    {
        _selectedRpmCandidate = null; RpmCandidates = []; RpmForwardRows = []; RpmPlotRows = []; RpmPlotCaption = "";
        RpmCandidateSummary = "Старий вибір не застосовується. Обчисліть preview для поточного сценарію.";
    }
}
