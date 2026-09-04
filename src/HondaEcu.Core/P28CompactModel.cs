namespace HondaEcu.Core;

/// <summary>Branches of the scoped integer contract, not physical engine operating states.</summary>
public enum P28CompactBranch
{
    LowRaw255,
    LowRaw254,
    Normal,
    UpperClamp,
    ZeroClamp,
    HighRaw,
    Unresolved,
}

public readonly record struct P28CompactHypothesisResult(byte Code, bool ExtraBit, P28CompactBranch Branch);

public readonly record struct P28CompactResult(byte? Code, bool? ExtraBit, P28CompactBranch Branch, bool Resolved);

/// <summary>Inclusive integer endpoints. Separate ranges preserve branch boundaries.</summary>
public sealed record P28RawRange(int StartInclusive, int EndInclusive, P28CompactBranch Branch);

public sealed record P28CodeDomain(
    byte Code,
    bool Data0217Bit4,
    bool? Reachable,
    IReadOnlyList<P28RawRange> ExactInputs,
    IReadOnlyList<P28RawRange> PredicateInputs,
    IReadOnlyList<P28RawRange> UnresolvedInputs,
    bool HypothesisReachable,
    IReadOnlyList<P28RawRange> HypothesisExactInputs,
    IReadOnlyList<P28RawRange> HypothesisPredicateInputs);

/// <summary>
/// Mathematical research model for one analyzed computation slice. Input is an unsigned raw
/// DATA word, NOT RPM. This is neither an OKI emulator nor a general Honda encoding codec.
/// See docs/M1B_RPM_CODEC_AND_VTEC_INSPECTOR.md for the entry contract and evidence limits.
/// </summary>
public static class P28CompactModel
{
    public const string ModelId = "p28-compact-v1";

    public static P28CompactResult Evaluate(ushort rawInput, bool data0217Bit4)
    {
        if (rawInput is >= 234 and < 3750)
        {
            // The available manufacturer manual does not establish the decoded word
            // ADD er3,A form. Do not expose a hypothesized result as an established value.
            return new(null, null, P28CompactBranch.Unresolved, false);
        }

        var established = EvaluateHypothesis(rawInput, data0217Bit4);
        return new(established.Code, established.ExtraBit, established.Branch, true);
    }

    /// <summary>
    /// Conditional mathematical contract assuming the pinned decoder's word ADD interpretation.
    /// Results in raw 234..3749 are hypotheses, even if a second translated model agrees.
    /// </summary>
    public static P28CompactHypothesisResult EvaluateHypothesis(ushort rawInput, bool data0217Bit4)
    {
        if (rawInput < 187)
        {
            return new(255, true, P28CompactBranch.LowRaw255);
        }

        if (rawInput < 234)
        {
            return new(254, true, P28CompactBranch.LowRaw254);
        }

        if (rawInput >= 3750)
        {
            return new(data0217Bit4 ? (byte)0 : (byte)1, false, P28CompactBranch.HighRaw);
        }

        // These comparisons preserve the repeated *integer* halving of 1875.
        var segment = rawInput >= 1875 ? 0 : rawInput >= 937 ? 1 : rawInput >= 468 ? 2 : 3;
        uint quotient = (480000U >> segment) / rawInput;
        var compact = (int)(quotient >> 1) + (64 * segment) - 64;

        // In the bounded normal domain the quotient fits 16 bits and compact is 0..256.
        // The signed -64 here is algebraically equivalent to the slice's modular word add;
        // this implementation does not simulate registers or inherit their incoming values.
        if (compact >= 255)
        {
            return new(254, true, P28CompactBranch.UpperClamp);
        }

        if (compact == 0)
        {
            return new(1, false, P28CompactBranch.ZeroClamp);
        }

        return new(checked((byte)compact), (quotient & 1) != 0, P28CompactBranch.Normal);
    }

    /// <summary>
    /// Exact code preimage and the distinct preimage of compactCode &gt; threshold.
    /// All ushort bit patterns are evaluated; this does not assert producer reachability.
    /// No nearest-value inverse encoding or physical RPM conversion is performed.
    /// </summary>
    public static P28CodeDomain GetDomain(byte threshold, bool data0217Bit4)
    {
        var exact = CollectRanges(threshold, data0217Bit4, equality: true, hypothesis: false);
        var hypothesisExact = CollectRanges(threshold, data0217Bit4, equality: true, hypothesis: true);
        return new(threshold, data0217Bit4, exact.Count != 0 ? true : null, exact,
            CollectRanges(threshold, data0217Bit4, equality: false, hypothesis: false),
            Array.AsReadOnly(new[] { new P28RawRange(234, 3749, P28CompactBranch.Unresolved) }),
            hypothesisExact.Count != 0, hypothesisExact,
            CollectRanges(threshold, data0217Bit4, equality: false, hypothesis: true));
    }

    public static IReadOnlyList<P28CodeDomain> GetAllDomains(bool data0217Bit4) =>
        Array.AsReadOnly(Enumerable.Range(0, 256).Select(code => GetDomain((byte)code, data0217Bit4)).ToArray());

    private static IReadOnlyList<P28RawRange> CollectRanges(byte threshold, bool context, bool equality, bool hypothesis)
    {
        var ranges = new List<P28RawRange>();
        int? start = null;
        var branch = P28CompactBranch.Normal;
        for (var raw = 0; raw <= ushort.MaxValue; raw++)
        {
            var result = EvaluateHypothesis((ushort)raw, context);
            var matches = (hypothesis || raw is < 234 or >= 3750) &&
                (equality ? result.Code == threshold : result.Code > threshold);
            if (start.HasValue && (!matches || result.Branch != branch))
            {
                ranges.Add(new(start.Value, raw - 1, branch));
                start = null;
            }

            if (matches && !start.HasValue)
            {
                start = raw;
                branch = result.Branch;
            }
        }

        if (start.HasValue)
        {
            ranges.Add(new(start.Value, ushort.MaxValue, branch));
        }

        return ranges.AsReadOnly();
    }
}
