namespace HondaEcu.Core.Tests;

// Pure static mathematics and invented evidence guards. No Cpu/Bus, executor,
// journal-to-expected adaptation, scenario input or actual-ROM operation.
internal enum JgtHypothesis { HypotheticalPrintedOR, HypotheticalExecutorAND }
internal sealed record ResearchFlags(bool Cf, bool Zf, bool Hc, bool Dd);
internal sealed record LoopResearchContext(int? Lrb = 0x10, int? Scb = 0, bool? Dd = true,
    bool NativeUspSource = true, bool NativeMarkerSource = true, bool StableContext = true,
    bool UnknownAlias = false, bool ValidWordStorage = true);
internal sealed record AbstractLoopStore(int Number, int Address, int Usp, ResearchFlags Compare, bool Taken);
internal sealed record AbstractLoopResult(JgtHypothesis Hypothesis, IReadOnlyList<AbstractLoopStore> Stores,
    IReadOnlyList<int> PassExitStoreNumbers, bool ExitReached, string Boundary)
{
    internal int ActualRomExecutions => 0;
    internal string Evidence => "ConditionalStaticProof";
    internal void RequireActualExecution() => throw new InvalidDataException("A predicate hypothesis is not primary validation or actual execution.");
}
internal sealed record DocumentaryWitness(string Identity, string VisualIdentity, string Core,
    bool VendorPrimary, bool ExactC8Predicate, bool BasicAssemblyCompatibility = false);

internal static class JgtStaticResearchFixture
{
    internal static ResearchFlags Compare16(ushort left, ushort right, ResearchFlags incoming) =>
        incoming with { Cf = left < right, Zf = left == right };

    internal static bool Predicate(JgtHypothesis hypothesis, ResearchFlags flags) => hypothesis switch
    {
        JgtHypothesis.HypotheticalPrintedOR => !flags.Cf || !flags.Zf,
        JgtHypothesis.HypotheticalExecutorAND => !flags.Cf && !flags.Zf,
        _ => throw new InvalidDataException("No validated primary predicate supplied by a caller.")
    };

    internal static ushort TwoDecrements(ushort pointer) => unchecked((ushort)(pointer - 2));

    internal static void RequireContext(LoopResearchContext context)
    {
        if (context.Lrb != 0x10 || context.Scb != 0 || context.Dd != true || !context.NativeUspSource ||
            !context.NativeMarkerSource || !context.StableContext || context.UnknownAlias || !context.ValidWordStorage)
            throw new InvalidDataException("Unknown or unowned initialization/alias/address context.");
    }

    internal static bool Off86IsActiveUsp(int lrb, int scb) =>
        (((lrb & 0x1FE0) << 3) | 0x86) == 0x80 + 8 * scb + 6;

    internal static AbstractLoopResult Analyze(JgtHypothesis hypothesis, byte retainedMarker, LoopResearchContext context)
    {
        RequireContext(context);
        ushort dp = 0x480, usp = 0x356;
        var stores = new List<AbstractLoopStore>(); var exits = new List<int>();
        for (var number = 1; number <= 520; number++)
        {
            dp = TwoDecrements(dp);
            if (dp == 0x86) return new(hypothesis, stores, exits, false, "BeforeActiveUspAlias");
            var compare = Compare16(dp, usp, new(false, false, false, true));
            var taken = Predicate(hypothesis, compare);
            stores.Add(new(number, dp, usp, compare, taken));
            if (taken) continue;
            exits.Add(number);
            if (dp <= 0x98) return new(hypothesis, stores, exits, true, "ConditionalExit");
            usp = 0x98;
            if (retainedMarker == 0x47) dp = 0x300;
        }
        throw new InvalidDataException("Unproved abstract loop bound.");
    }

    // Both edges are propagated at each opaque JGT. This is a universal finite
    // prefix proof, not host branch selection or adoption of OR/AND as truth.
    internal static IReadOnlyList<int> TargetPrefixForOpaqueJgt(byte retainedMarker, LoopResearchContext context)
    {
        RequireContext(context);
        if (retainedMarker == 0x47) throw new InvalidDataException("Warm path can reset DP to0300 and cycle at02FE.");
        var heads = new HashSet<(int Dp, int Usp)> { (0x480, 0x356) };
        var stores = new List<int>();
        for (var number = 1; number <= 371; number++)
        {
            var next = new HashSet<(int Dp, int Usp)>(); var address = 0x480 - 2 * number;
            foreach (var head in heads)
            {
                var after = head.Dp - 2;
                if (after != address || after < 0x19A || after <= 0x98)
                    throw new InvalidDataException("Lost pointer/rank invariant.");
                next.Add((after, head.Usp)); // Taken: direct loop.
                next.Add((after, 0x98)); // Not taken: JLE false, non47 JNE true.
            }
            stores.Add(address); heads = next;
        }
        return stores;
    }

    internal static bool CanResolvePrimary(DocumentaryWitness source, DocumentaryWitness original) =>
        source.VendorPrimary && source.Core == "nX-8/200" && source.ExactC8Predicate &&
        source.Identity != original.Identity && source.VisualIdentity != original.VisualIdentity;
}
