namespace HondaEcu.Core;

/// <summary>Finite deterministic raw-word stimuli, not an exhaustive six-word domain or measured engine history.</summary>
public static class P28ProducerCases
{
    public const string Version = "p28-producer-cases-v1";
    public const uint RandomSeed = 0x028304E1;
    public static IReadOnlyList<P28ProducerInput> Create()
    {
        var cases = new List<P28ProducerInput>(140000);
        void Add(string group, ushort[] samples, bool alternative = false, bool previousS = true,
            ushort previousT = 0x1234, bool previousFallback = true, int? pattern = null)
        {
            var id = cases.Count;
            var scratch = pattern ?? new[] { 0, 85, 170 }[id % 3];
            // Other bits are preserved outputs too; they are not assigned undocumented physical meaning.
            var flags217 = (byte)((scratch & 0x6F) | (previousS ? 0x10 : 0) | (alternative ? 0x80 : 0));
            var flags231 = (byte)((scratch & 0xDF) | (previousFallback ? 0x20 : 0));
            cases.Add(new P28ProducerInput(id, group, scratch, Array.AsReadOnly(samples.ToArray()), previousT,
                flags217, flags231, (id >> 1) & 1, (id >> 2) & 3, (id & 1) != 0));
        }

        foreach (var alternative in new[] { false, true })
        {
            for (var raw = 0; raw <= ushort.MaxValue; raw++)
            {
                Add(alternative ? "UniformIntervalWordsAlternative" : "UniformIntervalWordsNormal",
                    Enumerable.Repeat((ushort)raw, 6).ToArray(), alternative);
            }
        }

        foreach (var alternative in new[] { false, true })
        {
            foreach (var previousS in new[] { false, true })
            {
                foreach (var previousFallback in new[] { false, true })
                {
                    foreach (var previousT in new ushort[] { 0, 1, 0x1234, ushort.MaxValue })
                    {
                        foreach (var pattern in new[] { 0, 85, 170 })
                        {
                            for (var zero = 0; zero < 6; zero++)
                            {
                                var samples = Enumerable.Repeat((ushort)1000, 6).ToArray();
                                samples[zero] = 0;
                                Add("ZeroPositionAndPreviousState", samples, alternative, previousS, previousT, previousFallback, pattern);
                            }
                            Add("InitializationLikeSeedNotResetExecution", new ushort[6], alternative, previousS, previousT, previousFallback, pattern);
                        }
                    }
                }
            }

            for (var position = 0; position < 6; position++)
            {
                foreach (var value in new ushort[] { 0, 1, 186, 187, 233, 234, 32767, 65534, 65535 })
                {
                    var samples = Enumerable.Repeat((ushort)1000, 6).ToArray();
                    samples[position] = value;
                    Add("SingleSampleChange", samples, alternative);
                }
            }
            for (ushort tail = 0; tail < 16; tail++)
            {
                Add("CarryAndDivisionBoundary", [65535, 1, 1, 1, 1, tail], alternative);
                Add("QuotientWidthBoundary", [65535, 65535, 65535, 65535, 65535, tail], alternative);
            }
            foreach (var samples in new ushort[][]
            {
                [1, 65535, 1, 65535, 1, 65535], [65535, 1, 65535, 1, 65535, 1],
                [20, 20, 20, 5000, 5000, 5000], [5000, 5000, 5000, 20, 20, 20],
                [1000, 2000, 3000, 4000, 5000, 6000], [6000, 5000, 4000, 3000, 2000, 1000],
                [65535, 65535, 65535, 65535, 65535, 65535],
            })
            {
                Add("AlternatingStepAndRamp", samples, alternative);
            }
        }

        var random = RandomSeed;
        uint Next()
        {
            random ^= random << 13;
            random ^= random >> 17;
            random ^= random << 5;
            return random;
        }
        for (var index = 0; index < 2048; index++)
        {
            var samples = Enumerable.Range(0, 6).Select(_ => (ushort)Next()).ToArray();
            Add("DeterministicRawRandom", samples, (index & 1) != 0, (index & 2) != 0, (ushort)Next(), (index & 4) != 0);
        }
        return cases.AsReadOnly();
    }

    public static int[] Pack(P28ProducerInput input) =>
        [input.CaseId, input.ScratchPattern, .. input.Samples.Select(value => (int)value), input.PreviousT,
         input.PreviousFlags0217, input.PreviousFlags0231, input.ThresholdContext, input.ThresholdPriorBits, input.ThresholdEnabled ? 1 : 0];
}
