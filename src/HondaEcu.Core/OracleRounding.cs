namespace HondaEcu.Core;

/// <summary>A documented continuous interval of the unrounded raw input to rounding, not sample extrema.</summary>
public sealed record OracleRoundingDomain(double Minimum, double Maximum, string Documentation);

public enum OracleRoundingStatus
{
    Ambiguous,
    Unambiguous,
    EquivalentOnDomain,
}

public sealed record OracleRoundingAssessment(
    OracleRoundingStatus Status,
    IReadOnlyList<RoundingPolicy> Policies,
    OracleRoundingDomain? Domain,
    string Explanation)
{
    public bool IsEstablished => Status is OracleRoundingStatus.Unambiguous or OracleRoundingStatus.EquivalentOnDomain;
}

public static class OracleRoundingBehavior
{
    public static OracleRoundingAssessment Assess(IReadOnlyList<RoundingPolicy> policies, OracleRoundingDomain? domain)
    {
        ArgumentNullException.ThrowIfNull(policies);
        if (policies.Any(policy => !Enum.IsDefined(policy)))
        {
            throw new ArgumentOutOfRangeException(nameof(policies));
        }

        ValidateDomain(domain);
        var distinct = policies.Distinct().Order().ToArray();
        if (distinct.Length == 1)
        {
            return new(OracleRoundingStatus.Unambiguous, distinct, domain, "One rounding rule is compatible with the observations; this is not proof of extrapolation.");
        }

        if (distinct.Length > 1 && domain is not null &&
            distinct.All(left => distinct.All(right => Equivalent(left, right, domain))))
        {
            return new(OracleRoundingStatus.EquivalentOnDomain, distinct, domain,
                "The rounding functions are mathematically equivalent throughout the documented unrounded-raw interval. No policy name has been selected.");
        }

        return new(OracleRoundingStatus.Ambiguous, distinct, domain,
            "Observational agreement does not establish rounding behavior over fractional requests; provide discriminating boundary observations or a documented domain proof.");
    }

    public static void ValidateDomain(OracleRoundingDomain? domain)
    {
        if (domain is not null && (!double.IsFinite(domain.Minimum) || !double.IsFinite(domain.Maximum) ||
            domain.Minimum > domain.Maximum || string.IsNullOrWhiteSpace(domain.Documentation)))
        {
            throw new InvalidDataException("A rounding domain requires finite ordered bounds and an explicit justification of admissibility.");
        }
    }

    public static bool Equivalent(RoundingPolicy left, RoundingPolicy right, OracleRoundingDomain domain)
    {
        ValidateDomain(domain);
        if (!Enum.IsDefined(left) || !Enum.IsDefined(right))
        {
            throw new ArgumentOutOfRangeException(nameof(left));
        }

        if (left == right)
        {
            return true;
        }

        if (domain.Minimum == domain.Maximum)
        {
            var leftValue = Round(domain.Minimum, left);
            return double.IsFinite(leftValue) && leftValue == Round(domain.Minimum, right);
        }

        var pair = new HashSet<RoundingPolicy> { left, right };
        if (pair.SetEquals(new[] { RoundingPolicy.Floor, RoundingPolicy.Truncate }))
        {
            return domain.Minimum >= 0;
        }

        if (pair.SetEquals(new[] { RoundingPolicy.Ceiling, RoundingPolicy.Truncate }))
        {
            return domain.Maximum <= 0;
        }

        if (pair.SetEquals(new[] { RoundingPolicy.Nearest, RoundingPolicy.ToEven }))
        {
            // These rules differ only at midpoints. Absence of EVERY midpoint is a sufficient
            // proof; intervals containing even an agreeing midpoint are conservatively ambiguous.
            var firstMidpoint = Math.Ceiling(domain.Minimum - 0.5) + 0.5;
            return firstMidpoint > domain.Maximum;
        }

        return false;
    }

    internal static double Round(double value, RoundingPolicy policy) => policy switch
    {
        RoundingPolicy.Exact when Math.Abs(value - Math.Round(value)) <= 1e-9 => Math.Round(value),
        RoundingPolicy.Exact => double.NaN,
        RoundingPolicy.Nearest => Math.Round(value, MidpointRounding.AwayFromZero),
        RoundingPolicy.ToEven => Math.Round(value, MidpointRounding.ToEven),
        RoundingPolicy.Floor => Math.Floor(value),
        RoundingPolicy.Ceiling => Math.Ceiling(value),
        RoundingPolicy.Truncate => Math.Truncate(value),
        _ => double.NaN,
    };
}
