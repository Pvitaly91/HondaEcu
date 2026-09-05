using System.Globalization;

namespace HondaEcu.Core;

/// <summary>
/// Exact finite partition of a conservative uniform-interval envelope. The only G/F
/// arithmetic comes from the existing models; permission never becomes evidence.
/// </summary>
public static class P28RpmPlanner
{
    public const string ModelId = "p28-rpm-planner-v1";
    public const string PolicyId = "finite-transition-band-minimax-v1";
    public const string AddEr3Assumption = "oki.add-er3-a";
    public const int MaximumNormalIdealTicks = 54613;
    private const string EnvelopeQualification = "For integral ideal ticks there is exactly one sample vector. Otherwise all 64 ordered floor/ceiling vectors form a conservative superset, not a proof of physically reachable sequential capture phases and not a probability distribution. Normal acquisition only; alternate acquisition/producer, startup, stale history, overflow and hardware timing are excluded.";

    public static P28RpmPlanningReport Analyze(P28RpmQuery query, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(query);
        cancellationToken.ThrowIfCancellationRequested();
        var unavailable = Missing(query);
        if (unavailable.Count != 0)
        {
            return new("Unavailable", unavailable, query, null, [], [], [], "NotEstablished", null);
        }
        var forward = EvaluateForward(query)!;
        var product = query.Scenario!.TicksRpmProduct;
        var target = P28ExactNumber.From(query.RequestedRpm!);
        var atoms = BuildNormalAtoms(query, cancellationToken);
        var fullyResolved = atoms.All(atom => atom.Resolved);
        var monotonic = fullyResolved && CheckMonotonicity(atoms);
        var used = Freeze(atoms.SelectMany(atom => atom.UsedAssumptions).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal));
        var domain = new P28RpmInterval((product / new P28ExactNumber(MaximumNormalIdealTicks, 1)).ToString(), product.ToString(), true, true);
        var candidates = new List<P28RpmCandidate>(256);
        P28ExactNumber? bestError = null;
        for (var raw = 0; raw <= byte.MaxValue; raw++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var normalRegions = CollectRegions(atoms, (byte)raw, product);
            var regions = ExcludedLowRegions(product).Concat(normalRegions)
                .Append(new(new(product.ToString(), null, false, false), P28RpmRegionState.Invalid,
                    "IdealTicksBelowOne: the conservative envelope contains zero samples; startup/zero fallback is not normal RPM."));
            var reasons = new List<string>();
            if (!forward.AllVariantsNormal)
            {
                reasons.Add("The requested RPM envelope is not completely resolved normal NewValue production; it is not admitted for automatic selection.");
            }
            if (!fullyResolved) { reasons.Add("The common full supported domain includes unresolved G/F results; no simple candidate is selected across unknown regions."); }
            if (fullyResolved && !monotonic) { reasons.Add("Monotonicity is not established over the complete supported domain."); }
            var mixed = normalRegions.Where(region => region.State == P28RpmRegionState.Mixed).ToArray();
            var hasFalse = normalRegions.Any(region => region.State == P28RpmRegionState.AllFalse);
            var hasTrue = normalRegions.Any(region => region.State == P28RpmRegionState.AllTrue);
            if (mixed.Length != 1 || !hasFalse || !hasTrue)
            {
                reasons.Add(!fullyResolved ? "NoSingleFiniteTransitionEstablished: unresolved regions prevent an absolute always-true or always-false classification." :
                    !hasFalse && hasTrue ? "AlwaysTrueInSupportedDomain: no finite transition." :
                    hasFalse && !hasTrue ? "AlwaysFalseInSupportedDomain: no finite transition." :
                    mixed.Length > 1 ? "MultipleDisconnectedTransitions: not a simple finite-band candidate." : "NoSingleFiniteTransitionEstablished.");
            }
            P28RpmInterval? band = null;
            string? error = null;
            var selectable = reasons.Count == 0;
            if (selectable)
            {
                band = mixed[0].Interval with { LowerInclusive = true, UpperInclusive = true };
                var lowError = (target - ParseExact(band.Lower)).Abs();
                var highError = (target - ParseExact(band.Upper!)).Abs();
                var value = lowError.CompareTo(highError) >= 0 ? lowError : highError;
                error = value.ToString();
                if (bestError is null || value.CompareTo(bestError.Value) < 0) { bestError = value; }
            }
            candidates.Add(new((byte)raw, Freeze(regions), selectable, Freeze(reasons), band, error, false, used));
        }
        var completed = Freeze(candidates.Select(candidate => candidate with
        {
            IsBest = candidate.SimpleSelectable && bestError.HasValue && ParseExact(candidate.MinimaxError!).CompareTo(bestError.Value) == 0,
        }));
        return new(!fullyResolved ? "Unresolved" : !forward.AllVariantsNormal ? "InvalidRequestedDomain" : "ConditionalPreview",
            !forward.AllVariantsNormal ? forward.Reasons : [], query, forward, completed,
            Freeze(completed.Where(candidate => candidate.IsBest)), used,
            monotonic ? "NondecreasingCodeWithRpmWithinSupportedDomain" : "NotEstablishedUnresolvedOrNonmonotone",
            domain);
    }

    public static P28RpmForwardPreview? EvaluateForward(P28RpmQuery query, byte? proposedRaw = null)
    {
        ArgumentNullException.ThrowIfNull(query);
        if (Missing(query).Count != 0) { return null; }
        var scenario = query.Scenario!;
        var rpm = P28ExactNumber.From(query.RequestedRpm!);
        var ticks = scenario.TicksRpmProduct / rpm;
        var integral = ticks.Floor == ticks.Ceiling;
        var variants = new List<P28RpmForwardVariant>(integral ? 1 : 64);
        for (var mask = 0; mask < (integral ? 1 : 64); mask++)
        {
            var samples = Enumerable.Range(0, 6).Select(index => (mask & (1 << index)) == 0 ? ticks.Floor : ticks.Ceiling).ToArray();
            var textSamples = Freeze(samples.Select(value => value.ToString(CultureInfo.InvariantCulture)));
            if (samples.Any(value => value >= ushort.MaxValue))
            {
                variants.Add(new(mask, textSamples, "InvalidCapture", false, null, null, null, null, [],
                    ["Sample reaches normal capture's TCERR FFFF-or-more boundary; no wrap/overflow sample is invented."]));
                continue;
            }
            var evaluation = EvaluateSamples(query, samples.Select(value => (ushort)value).ToArray());
            var reasons = new List<string>();
            if (!evaluation.Producer.Resolved) { reasons.Add("G reaches unresolved ADD er1,A; previous T is not a newly produced normal value."); }
            else if (evaluation.Producer.Disposition != P28ProducerDisposition.NewValue) { reasons.Add($"G disposition {evaluation.Producer.Disposition} is excluded from normal RPM selection."); }
            if (evaluation.Producer.Resolved && evaluation.Compact is { Resolved: false }) { reasons.Add("F reaches unresolved ADD er3,A."); }
            var eligible = evaluation.Producer.Resolved && evaluation.Producer.Disposition == P28ProducerDisposition.NewValue;
            var code = evaluation.Compact is { Resolved: true } compact ? compact.Code : null;
            var status = !evaluation.Producer.Resolved || evaluation.Compact is { Resolved: false } ? "Unresolved" :
                !eligible ? "InvalidProducerDisposition" : evaluation.UsedAssumptions.Count == 0 ? "ResolvedModel" : "ConditionalModel";
            variants.Add(new(mask, textSamples, status, eligible, evaluation.Producer, evaluation.Compact,
                code.HasValue ? P28ThresholdLogic.Evaluate(query.OriginalRaw, code.Value) : null,
                code.HasValue && proposedRaw.HasValue ? P28ThresholdLogic.Evaluate(proposedRaw.Value, code.Value) : null,
                evaluation.UsedAssumptions, Freeze(reasons)));
        }
        var allNormal = variants.All(value => value.NormalEligible);
        return new(rpm.ToString(), (scenario.Quantity("clockHz") / scenario.Quantity("timerClockDivisor")).ToString(),
            scenario.TicksRpmProduct.ToString(), ticks.ToString(), ticks.Floor.ToString(CultureInfo.InvariantCulture),
            ticks.Ceiling.ToString(CultureInfo.InvariantCulture), integral, allNormal, query.OriginalRaw, proposedRaw, Freeze(variants),
            Freeze(variants.SelectMany(value => value.UsedAssumptions).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal)),
            Freeze(variants.SelectMany(value => value.Reasons).Distinct(StringComparer.Ordinal)), EnvelopeQualification);
    }

    private static IReadOnlyList<string> Missing(P28RpmQuery query)
    {
        var missing = new List<string>();
        if (query.Scenario is null)
        {
            missing.AddRange(new[] { "Missing scenario quantity: clockHz", "Missing scenario quantity: timerClockDivisor", "Missing scenario quantity: eventsPerCrankRev", "Missing scenario quantity: eventsPerSample" });
        }
        if (query.RequestedRpm is null) { missing.Add("Missing requested RPM query and provenance."); }
        return Freeze(missing);
    }

    private sealed record Evaluation(P28ProducerModelResult Producer, P28CompactResult? Compact, IReadOnlyList<string> UsedAssumptions);

    private static Evaluation EvaluateSamples(P28RpmQuery query, ushort[] samples)
    {
        // Previous T/S/status are explicit technical zeros, never borrowed from the
        // threshold's prior state. Completed positive normal G overwrites T and clears S.
        var input = new P28ProducerInput(0, "rpm-conservative-normal-envelope", 0, samples, 0, 0, 0,
            query.Slot.Context, query.Slot.PriorState ? 1 << query.Slot.Pair : 0, true);
        var producer = P28ProducerModel.Evaluate(input, query.PermittedAssumptions.Contains(P28ProducerModel.AddEr1Assumption));
        producer = producer with { Samples = Freeze(producer.Samples), UsedAssumptions = Freeze(producer.UsedAssumptions) };
        P28CompactResult? compact = null;
        var used = producer.UsedAssumptions.ToList();
        if (producer.Resolved)
        {
            compact = P28CompactModel.Evaluate(producer.T, producer.S);
            if (!compact.Value.Resolved && query.PermittedAssumptions.Contains(AddEr3Assumption))
            {
                var hypothesis = P28CompactModel.EvaluateHypothesis(producer.T, producer.S);
                compact = new(hypothesis.Code, hypothesis.ExtraBit, hypothesis.Branch, true);
                used.Add(AddEr3Assumption);
            }
        }
        return new(producer, compact, Freeze(used.Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal)));
    }

    private sealed record Atom(int LowerTickDivisor, int UpperTickDivisor, bool Point, bool Resolved,
        byte MinimumCode, byte MaximumCode, IReadOnlyList<string> UsedAssumptions);

    private static IReadOnlyList<Atom> BuildNormalAtoms(P28RpmQuery query, CancellationToken cancellationToken)
    {
        var atoms = new List<Atom>((2 * MaximumNormalIdealTicks) - 1);
        for (var ticks = MaximumNormalIdealTicks; ticks >= 1; ticks--)
        {
            if ((ticks & 255) == 0) { cancellationToken.ThrowIfCancellationRequested(); }
            atoms.Add(Build(ticks, ticks, point: true));
            if (ticks > 1) { atoms.Add(Build(ticks - 1, ticks, point: false)); }
        }
        return atoms;

        Atom Build(int floor, int ceiling, bool point)
        {
            var minimum = byte.MaxValue;
            byte maximum = 0;
            var resolved = true;
            var used = new HashSet<string>(StringComparer.Ordinal);
            // On this positive, non-alternative domain every permutation has equal
            // unit coefficients and no early zero exit. Seven high-count representatives
            // therefore cover the 64 ordered vectors; this is not a phase probability.
            for (var high = 0; high <= (point ? 0 : 6); high++)
            {
                var values = Enumerable.Range(0, 6).Select(index => (ushort)(index < high ? ceiling : floor)).ToArray();
                var evaluation = EvaluateSamples(query, values);
                foreach (var assumption in evaluation.UsedAssumptions) { used.Add(assumption); }
                if (!evaluation.Producer.Resolved || evaluation.Producer.Disposition != P28ProducerDisposition.NewValue ||
                    evaluation.Compact is not { Resolved: true, Code: not null } compact)
                {
                    resolved = false;
                    continue;
                }
                minimum = Math.Min(minimum, compact.Code.Value);
                maximum = Math.Max(maximum, compact.Code.Value);
            }
            return new(ceiling, floor, point, resolved, minimum, maximum, Freeze(used.Order(StringComparer.Ordinal)));
        }
    }

    private static bool CheckMonotonicity(IReadOnlyList<Atom> atoms)
    {
        // Ordered in increasing RPM. Check every singleton and each envelope against
        // both neighboring exact points instead of assuming a globally monotone F.
        for (var index = 0; index < atoms.Count; index += 2)
        {
            if (atoms[index].MinimumCode != atoms[index].MaximumCode) { return false; }
            if (index + 2 >= atoms.Count) { continue; }
            var left = atoms[index].MinimumCode;
            var right = atoms[index + 2].MinimumCode;
            var gap = atoms[index + 1];
            if (left > right || gap.MinimumCode != left || gap.MaximumCode != right) { return false; }
        }
        return true;
    }

    private static IReadOnlyList<P28RpmRegion> CollectRegions(IReadOnlyList<Atom> atoms, byte raw, P28ExactNumber product)
    {
        var result = new List<P28RpmRegion>();
        var start = 0;
        var state = Classify(atoms[0], raw);
        for (var index = 1; index <= atoms.Count; index++)
        {
            if (index < atoms.Count && Classify(atoms[index], raw) == state) { continue; }
            var first = atoms[start];
            var last = atoms[index - 1];
            result.Add(new(new((product / new P28ExactNumber(first.LowerTickDivisor, 1)).ToString(),
                (product / new P28ExactNumber(last.UpperTickDivisor, 1)).ToString(), first.Point, last.Point), state,
                state == P28RpmRegionState.Unknown ? "At least one conservative sample vector has unresolved G/F arithmetic; it is not discarded." :
                state == P28RpmRegionState.Mixed ? "Both predicate values occur in the conservative envelope; not a probability." : "Exact enabled one-step compactCode > rawThreshold predicate."));
            if (index < atoms.Count) { start = index; state = Classify(atoms[index], raw); }
        }
        return Freeze(result);
    }

    private static P28RpmRegionState Classify(Atom atom, byte raw) => !atom.Resolved ? P28RpmRegionState.Unknown :
        atom.MinimumCode > raw ? P28RpmRegionState.AllTrue : atom.MaximumCode <= raw ? P28RpmRegionState.AllFalse : P28RpmRegionState.Mixed;

    private static IEnumerable<P28RpmRegion> ExcludedLowRegions(P28ExactNumber product)
    {
        var capture = (product / new P28ExactNumber(65534, 1)).ToString();
        var overflow = (product / new P28ExactNumber(54614, 1)).ToString();
        var normal = (product / new P28ExactNumber(MaximumNormalIdealTicks, 1)).ToString();
        yield return new(new("0/1", capture, false, false), P28RpmRegionState.Invalid,
            "CaptureInvalidEnvelope: ceiling ticks reaches FFFF or more; normal TCERR behavior is not a numerical RPM model.");
        yield return new(new(capture, overflow, true, true), P28RpmRegionState.Invalid,
            "OutsideSupportedNormalDomain: producer quotient overflow under the arithmetic hypothesis; not a normal transition.");
        yield return new(new(overflow, normal, false, false), P28RpmRegionState.Invalid,
            "MixedNormalAndOverflowDispositions: some envelope vectors are valid T=FFFF and others overflow; none are silently dropped.");
    }

    private static P28ExactNumber ParseExact(string text)
    {
        var parts = text.Split('/');
        return new(System.Numerics.BigInteger.Parse(parts[0], CultureInfo.InvariantCulture),
            System.Numerics.BigInteger.Parse(parts[1], CultureInfo.InvariantCulture));
    }

    private static IReadOnlyList<T> Freeze<T>(IEnumerable<T> values) => Array.AsReadOnly(values.ToArray());
}
