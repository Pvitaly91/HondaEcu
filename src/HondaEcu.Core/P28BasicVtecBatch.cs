using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28BasicVtecWitness(string SlotId, int ScratchPattern, int Code, int Context, int PriorBits,
    int OldBits, int NewBits, string Meaning);
public sealed record P28BasicVtecEvidence(string Operation, string CorpusId, IReadOnlyList<RomHash> ImageHashes,
    IReadOnlyList<IReadOnlyList<int>> Rows, int ComparedCasesPerImage, int ChangedResultCases, IReadOnlyList<P28BasicVtecWitness> Witnesses);
internal static class P28BasicVtecBatch
{
    internal const string FullId = "basic-vtec-raw-prefix-all-codes-contexts-priors-enable-scratch-v1";
    internal const string ControlId = "basic-vtec-unchanged-0-127-255-contexts-priors-enable-scratch-v1";
    internal static string Operation(bool changed) => changed ? "vtecThresholdPrefix" : "vtecThresholdControl";
    internal static int[] Codes(bool changed) => changed ? Enumerable.Range(0, 256).ToArray() : [0, 127, 255];
    internal static object Request(P28BasicCalibrationPreview p) => new
    {
        protocolVersion = 1,
        operation = Operation(p.Plan.Groups[0].EffectivelyChanged),
        images = p.Images.Select(i => new { id = i.Id, rom = i.Image.ToArray().Select(b => (int)b).ToArray() }).ToArray(),
        allowAssumptions = Array.Empty<string>(),
        scratchPatterns = new[] { 0, 85, 170 }
    };
    internal static P28BasicVtecEvidence Analyze(P28BasicCalibrationPreview p, SliceProcessResponse response)
    {
        var changed = p.Plan.Groups[0].EffectivelyChanged; var operation = Operation(changed); var r = response.Response;
        _ = SliceRunnerIdentity.Validate(r, operation);
        if (r.GetProperty("entryContracts").GetArrayLength() != 1 || r.GetProperty("compactRows").GetArrayLength() != 0 ||
            r.GetProperty("syntheticResult").ValueKind != JsonValueKind.Null || r.GetProperty("diagnostics").GetArrayLength() > 128)
            throw new InvalidDataException("Prefix-only task/contract required.");
        P28ByteExecutionValidator.ValidateContract(r.GetProperty("entryContracts")[0], false);
        var rows = r.GetProperty("thresholdRows").EnumerateArray().Select(row => (IReadOnlyList<int>)row.EnumerateArray().Select(v => v.GetInt32()).ToArray()).ToArray();
        var (count, witnesses) = Check(p, rows);
        return new(operation, changed ? FullId : ControlId, p.Images.Select(i => i.Image.Hash).ToArray(), rows, Codes(changed).Length * 48, count, witnesses);
    }
    internal static void Require(P28BasicCalibrationPreview p, P28BasicVtecEvidence e)
    {
        var changed = p.Plan.Groups[0].EffectivelyChanged;
        if (e.Operation != Operation(changed) || e.CorpusId != (changed ? FullId : ControlId) ||
            !e.ImageHashes.SequenceEqual(p.Images.Select(i => i.Image.Hash)) || e.ComparedCasesPerImage != Codes(changed).Length * 48)
            throw new InvalidDataException("Stale/foreign VTEC prefix evidence.");
        var (count, witnesses) = Check(p, e.Rows);
        if (e.ChangedResultCases != count || !e.Witnesses.SequenceEqual(witnesses)) throw new InvalidDataException("Forged VTEC changed set or witness.");
    }
    private static (int Count, IReadOnlyList<P28BasicVtecWitness> Witnesses) Check(P28BasicCalibrationPreview p, IReadOnlyList<IReadOnlyList<int>> rows)
    {
        var plan = p.Plan; var codes = Codes(plan.Groups[0].EffectivelyChanged); var perImage = codes.Length * 48;
        if (rows.Count != perImage * 3) throw new InvalidDataException("Missing/extra threshold cases.");
        var index = new Dictionary<(int Image, int Scratch, int Code, int Context, int Prior, int Enabled), IReadOnlyList<int>>();
        foreach (var row in rows)
        {
            if (row.Count != 12 || row[0] is < 0 or > 2 || row[1] is not (0 or 85 or 170) || !codes.Contains(row[2]) ||
                row[3] is < 0 or > 1 || row[4] is < 0 or > 3 || row[5] is < 0 or > 1 || row[6] != 0 ||
                !index.TryAdd((row[0], row[1], row[2], row[3], row[4], row[5]), row)) throw new InvalidDataException("Invalid, non-strict or duplicate threshold case.");
            var image = p.Images[row[0]].Image;
            if (row[7] != P28ByteExecutionValidator.ThresholdBits(image.Span.Slice(P28ThresholdLogic.BlockOffset, 8), row[2], row[3], row[4], row[5]) ||
                !P28ByteExecutionValidator.ThresholdReadsMatch(row)) throw new InvalidDataException("Threshold predicate/actual-read mismatch.");
        }
        var changed = 0; var witnesses = new List<P28BasicVtecWitness>(); var slot = plan.Groups[0].Vtec!.Slot;
        foreach (var a in rows.Where(r => r[0] == 0))
        {
            var b = index[(1, a[1], a[2], a[3], a[4], a[5])]; var c = index[(2, a[1], a[2], a[3], a[4], a[5])];
            if (!b.Skip(1).SequenceEqual(c.Skip(1))) throw new InvalidDataException("B/C prefix observations differ.");
            if (a[7] == c[7]) continue;
            changed++;
            if (slot is null || a[5] != 1 || a[3] != slot.Context || ((a[4] & (1 << slot.Pair)) != 0) != slot.PriorState ||
                (a[7] ^ c[7]) != (1 << slot.Pair)) throw new InvalidDataException("Changed result outside selected slot dependency.");
            if (witnesses.Count == 0) witnesses.Add(new(slot.Id, a[1], a[2], a[3], a[4], a[7], c[7],
                "Actual selected threshold read -> strict native predicate change; other pair preserved; not P1/physical output"));
        }
        if (plan.Groups[0].EffectivelyChanged != (changed > 0)) throw new InvalidDataException("Missing changed VTEC witness or changed unedited family.");
        return (changed, witnesses.AsReadOnly());
    }
}
