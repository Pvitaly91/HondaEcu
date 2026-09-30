namespace HondaEcu.Core;

public sealed record P28PostStoreConsumerProjection(int Word0150, int Operand014c, int Selected, string Comparison,
    int ModeBefore, int ModeAfter, string HelperStatus, int? HelperInput, int SelectedScaledWordX1, int RetainedOrZeroA)
{
    public string SelectedSource => Operand014c < Word0150 ? "0150" : "014C";
    public bool NativeRelationReachable => (Word0150 == 0 || Word0150 is >= 250 and <= 2000) && (Operand014c == 0 || Word0150 == 0);
}
public static class P28PostStoreConsumerModel
{
    public static P28PostStoreConsumerProjection Project(ushort word0150, ushort source014c, ushort source0144, byte mode012c)
    {
        var borrow = source014c < word0150;
        var selected = borrow ? word0150 : source014c;
        var mode = (mode012c & ~32) | (borrow ? 32 : 0);
        int? helperInput = selected == 0 ? null : Math.Min(selected + source0144, 65535);
        var result = helperInput.HasValue ? Math.Min(helperInput.Value * 5 / 4, 65535) : 0;
        return new(word0150, source014c, selected, source014c == word0150 ? "014C==0150" : borrow ? "014C<0150" : "014C>0150",
            mode012c, mode, selected == 0 ? "NotRunZeroSelection" : "NativeCall", helperInput, result, borrow ? 0 : result);
    }
}
// Each image owns its upstream ROM/model histories, previous03B4 and native mode012C generation.
internal sealed class P28PostStoreConsumerHistory
{
    private readonly P28PostStorePrefixModel _prefix;
    private ushort _previous;
    private byte _mode;
    internal P28PostStoreConsumerHistory(RomImage image, P28PostStoreConsumerScenario scenario)
    {
        _prefix = new(image, scenario.PrefixScenario.PrefixScenario);
        _previous = scenario.InitialState.Previous03b4;
        _mode = scenario.InitialState.Adaptive.Joint.ProducerMode012c;
    }
    internal P28PostStoreConsumerOwn Step(P28PostStoreCall call)
    {
        var prefix = _prefix.Step(call.Adaptive, _previous, _mode);
        var sources = call.Adaptive.Fuel.Sources;
        var projection = P28PostStoreModel.Project(_previous, (ushort)prefix.Numeric.Corrected, call.Disable125,
            call.Disable12e, sources.Source0133, sources.Source014c);
        var postStore = P28PostStoreEvidence.Build(prefix.Exit, call.Disable125 ? (byte)16 : (byte)0,
            call.Disable12e ? (byte)16 : (byte)0, sources.Source0133, sources.Source014c);
        var consumer = P28PostStoreConsumerModel.Project((ushort)projection.Result, sources.Source014c, sources.Source0144, _mode);
        _previous = (ushort)prefix.Numeric.Store03b4; _mode = (byte)consumer.ModeAfter;
        return new(projection, postStore, consumer);
    }
}
internal sealed record P28PostStoreConsumerOwn(P28PostStoreProjection PostStore, P28FuelAdditiveOracle PostStoreExit,
    P28PostStoreConsumerProjection Consumer);
