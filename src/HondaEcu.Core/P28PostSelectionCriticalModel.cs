namespace HondaEcu.Core;

public sealed record P28PostSelectionCriticalProjection(int Word0190, int Word0192, int Word0194,
    int CommonPathWord, int IeBefore, int IeMasked, int IeAfter);
public static class P28PostSelectionCriticalModel
{
    // Storage-domain software projection. Inputs here are never ready-value scenario setters.
    public static P28PostSelectionCriticalProjection Project(ushort selectedX1, ushort retainedA,
        ushort current03b4, ushort ie, ushort restoreIe) =>
        new(retainedA, retainedA, selectedX1, Math.Min(current03b4 * 5 / 4, 65535), ie, ie & 0x02A0, restoreIe);
}

internal sealed record P28PostSelectionCriticalState(ushort Ie, ushort RestoreIe, IReadOnlyList<int> Words019x,
    ushort Word03b4, IReadOnlyList<int> CommonWords03b6, byte Mode012c, ushort Word0150);
internal sealed record P28PostSelectionCriticalOwn(P28PostStoreConsumerOwn Prefix, P28PostStoreConsumerOracle Consumer,
    P28PostSelectionCriticalProjection Projection, P28PostSelectionCriticalOracle Oracle,
    P28PostSelectionCriticalState Before, P28PostSelectionCriticalState Entry, P28PostSelectionCriticalState After);

// ROM, native mode/0150/03B4, IE and new RAM generations are owned independently for each image.
internal sealed class P28PostSelectionCriticalHistory
{
    private readonly P28PostStoreConsumerHistory _prefix;
    private readonly byte _configuration;
    private P28PostSelectionCriticalState _state;
    internal P28PostSelectionCriticalHistory(RomImage image, P28PostSelectionCriticalScenario scenario, int scratchPattern)
    {
        _prefix = new(image, scenario.PrefixScenario); _configuration = image.Span[0x60F8];
        if (_configuration != 0) throw new InvalidDataException("M2r original configuration must remain zero.");
        var initial = scenario.InitialState.Adaptive;
        _state = new(initial.Ie, initial.RestoreIe, Enumerable.Repeat(scratchPattern * 257, 3).ToArray(),
            scenario.InitialState.Previous03b4, Enumerable.Repeat(scratchPattern * 257, 4).ToArray(),
            initial.Joint.ProducerMode012c, 0);
    }
    internal P28PostSelectionCriticalOwn Step(P28PostStoreCall call)
    {
        var before = _state; var prefix = _prefix.Step(call, before.Ie); var sources = call.Adaptive.Fuel.Sources;
        // X1's entry canary is irrelevant after mandatory native2254; arithmetic is own model only.
        var consumer = P28PostStoreConsumerEvidence.Build(prefix.PostStoreExit, (ushort)prefix.PostStore.Result,
            sources.Source014c, sources.Source0144, (byte)prefix.Consumer.ModeBefore, 0);
        var entry = before with
        {
            Ie = prefix.PrefixIe,
            Word03b4 = (ushort)prefix.PostStore.Current,
            Mode012c = (byte)prefix.Consumer.ModeAfter,
            Word0150 = (ushort)prefix.PostStore.Result
        };
        var projection = P28PostSelectionCriticalModel.Project((ushort)consumer.X1, (ushort)consumer.Machine.Accumulator,
            entry.Word03b4, entry.Ie, entry.RestoreIe);
        var oracle = P28PostSelectionCriticalEvidence.Build(consumer, entry.Word03b4, entry.Ie, entry.RestoreIe,
            _configuration, entry.Words019x.Concat(entry.CommonWords03b6).ToArray());
        _state = entry with
        {
            Ie = entry.RestoreIe,
            Words019x = new[] { projection.Word0190, projection.Word0192, projection.Word0194 },
            CommonWords03b6 = Enumerable.Repeat(projection.CommonPathWord, 4).ToArray()
        };
        return new(prefix, consumer, projection, oracle, before, entry, _state);
    }
}
