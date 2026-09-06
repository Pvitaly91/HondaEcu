namespace HondaEcu.Core;

public static partial class P28ChainValidator
{
    private static P28ChainArchitecture InitialArchitecture(int pattern)
    {
        var pointing = Enumerable.Repeat((byte)pattern, 16).ToArray(); pointing[14] = 0x80; pointing[15] = 2;
        return new(0x56BE, (ushort)(pattern * 257), 0x21, 0x1DCA, 0x7FE, Enumerable.Repeat((byte)pattern, 24).ToArray(), pointing, (ushort)(pattern * 257));
    }
    private static void CheckArchitecture(P28ChainObservedStage s, P28ChainEvent input, Action<bool, string> check)
    {
        if (s.Execution is null) return;
        var before = s.ArchitectureBefore; var entry = s.ArchitectureAtEntry; var after = s.ArchitectureAfter;
        var (pc, lrb, psw, usp, pointingBase) = s.Id switch
        {
            "Acquisition" => (0x56BE, 0x21, 0x1102, 0x280, 8),
            "G" => (0x0772, 0x40, 0x1101, 0x180, 0),
            "F" => (0x07C7, 0x40, 0x1101, 0x180, 0),
            "Decision" => (0x122C, 0x20, 0x0101, 0x280, 0),
            _ => (0x5BD0, 0x20, 0x0101, 0x280, 0),
        };
        check(entry.Pc == pc && entry.Lrb == lrb && entry.Psw == (psw | 0x0CC8), "Declared PC/LRB/PSW/SCB entry context");
        check(entry.Accumulator == before.Accumulator && entry.Ssp == before.Ssp && entry.StackWord == before.StackWord && entry.Banks.SequenceEqual(before.Banks),
            "No accumulator/SSP/stack/local-bank reseeding");
        var expectedPointing = before.Pointing.ToArray(); expectedPointing[pointingBase + 6] = (byte)usp; expectedPointing[pointingBase + 7] = (byte)(usp >> 8);
        if (s.Id == "NativeCounterBodies") { var target = input.FastTicks > 0 ? 0x1D8 : 0x1DF; expectedPointing[0] = (byte)target; expectedPointing[1] = (byte)(target >> 8); }
        check(entry.Pointing.SequenceEqual(expectedPointing), "Only active USP and explicit tick X1 entry changes");
        check(after.Lrb == lrb && (after.Psw & 7) == (psw & 7) && after.Pc == s.Execution.StopPc, "Native stage bank/SCB/exit preservation");
        if (s.Status == 0 || s.Execution.StopPc == 0x12B4)
            check(after.Ssp == entry.Ssp, "Native helper stack balanced; no host repair");
        var nativeBank = s.Id switch { "Acquisition" => (8, 16), "G" or "F" => (16, 24), "Decision" => (0, 8), _ => (0, 0) };
        check(Enumerable.Range(0, 24).Where(i => i < nativeBank.Item1 || i >= nativeBank.Item2).All(i => after.Banks[i] == entry.Banks[i]),
            "Inactive local-register banks preserved");
        var nativePointing = s.Id switch { "Acquisition" => new[] { 8, 9 }, "F" => new[] { 0, 1 }, _ => new[] { 0, 1, 4, 5 } };
        check(Enumerable.Range(0, 16).Where(i => !nativePointing.Contains(i)).All(i => after.Pointing[i] == entry.Pointing[i]),
            "Inactive SCB/X2/USP aliases preserved");
        if (s.Id != "Decision") check(after.StackWord == entry.StackWord, "Non-helper stage preserved stack memory");
        else if (s.Execution.ExecutedInstructionBytes.Contains(0x126F)) check(after.StackWord == 0x1272, "Native CAL return address retained in helper stack");
        else check(after.StackWord == entry.StackWord, "Skipped helper preserved stack memory");
    }
    internal static IReadOnlyList<P28ChainImageComparison> CompareImages(IReadOnlyList<P28ChainSequence> sequences, int imageCount)
    {
        var result = new List<P28ChainImageComparison>(); if (imageCount != 3) return result.AsReadOnly();
        foreach (var (left, right, label) in new[] { (0, 1, "A/B"), (0, 2, "A/C"), (1, 2, "B/C") })
            foreach (var pattern in Patterns)
            {
                var a = sequences.Single(s => s.ImageIndex == left && s.ScratchPattern == pattern);
                var b = sequences.Single(s => s.ImageIndex == right && s.ScratchPattern == pattern);
                var pairs = new List<P28ChainPairedCheckpoint>(); var comparable = 0; var decisions = 0; var boundaries = 0;
                var stateDifferences = 0; var requestDifferences = 0; int? first = null, rejoin = null; var prefixesEqual = true;
                for (var i = 0; i < a.Checkpoints.Count; i++)
                {
                    var x = a.Checkpoints[i]; var y = b.Checkpoints[i];
                    for (var j = 0; j < 5; j++)
                    {
                        var u = x.Stages[j].Actual; var v = y.Stages[j].Actual;
                        if (u.Status == 4 && v.Status == 4) continue;
                        if (u.Status == 0 && v.Status == 0) boundaries++;
                        prefixesEqual &= Equal(u, v);
                    }
                    bool Complete(P28ChainCheckpoint c) => c.Stages[0].Actual.Status == 0 && c.Stages.All(s => s.Actual.Status is 0 or 4) && (!c.Input.RunDecision || c.Stages[4].Actual.Status == 0);
                    if (!Complete(x) || !Complete(y)) { pairs.Add(new(i, "NotComparable", null, null, null)); continue; }
                    comparable++; var stateEqual = Equal(x.StateAfter, y.StateAfter);
                    var sideEffectsEqual = x.Stages.Zip(y.Stages).All(p => Equal(p.First.Actual.NativeWrites, p.Second.Actual.NativeWrites) &&
                        Equal(p.First.Actual.GateEvents, p.Second.Actual.GateEvents) && Equal(p.First.Actual.ArchitectureAfter, p.Second.Actual.ArchitectureAfter));
                    bool? requestEqual = null;
                    if (x.Stages[4].Actual.Status == 0 && y.Stages[4].Actual.Status == 0)
                    { decisions++; requestEqual = x.SoftwareRequest == y.SoftwareRequest; if (requestEqual == false) requestDifferences++; }
                    if (!stateEqual) { first ??= i; stateDifferences++; } else if (first is not null) rejoin ??= i;
                    pairs.Add(new(i, "Comparable", stateEqual, sideEffectsEqual, requestEqual));
                }
                result.Add(new(label, pattern, comparable, decisions, first, stateDifferences, requestDifferences, rejoin, boundaries, prefixesEqual, pairs.AsReadOnly()));
            }
        return result.AsReadOnly();
    }
}
