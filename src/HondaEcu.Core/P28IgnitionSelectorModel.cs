namespace HondaEcu.Core;

public sealed record P28IgnitionSelectorModelStep(P28IgnitionMapState Before, byte SourceBefore,
    byte SourceAfterInputs, byte SelectorAfterProducer, IReadOnlyList<int> ProducerProgramReads,
    IReadOnlyList<int> ProducerPath, P28IgnitionMapModelStep Ignition);

/// <summary>Independent ROM and persistent history; Rust observations never seed this model.</summary>
public sealed class P28IgnitionSelectorModel
{
    private readonly byte[] _rom;
    private readonly P28IgnitionMapModel _ignition;
    private P28IgnitionMapState _state;
    private byte _source;

    public P28IgnitionSelectorModel(RomImage image, P28IgnitionSelectorInitial initial)
    {
        _rom = image.ToArray(); _ignition = new(image, initial.Ignition);
        _state = initial.Ignition; _source = initial.Source03c7;
    }

    public P28IgnitionSelectorModelStep Step(P28IgnitionSelectorCall call)
    {
        var previous = _state;
        var sourceBefore = _source;
        _source = call.Source03c7;
        // The bound original's 60FB=0 first chooses 5FA0; 60EA=0 then
        // bypasses the two source shifts. RC at 5F98 owns carry=0 at 5FAC.
        // No source bit or seed selector is promoted to an invented map input.
        if (_rom[0x60FB] != 0 || _rom[0x60EA] != 0 || _rom[0x7E02] != 0)
            throw new InvalidDataException("M2g model requires the bound original producer configuration.");
        var selector = (byte)(previous.Selector0227 & ~P28IgnitionMapContract.SelectorMask);
        var ignition = _ignition.StepWithSelector(selector, call.RawLoad, call.RawMap0Rpm, call.RawMap1Rpm);
        _state = ignition.After;
        return new(previous, sourceBefore, _source, selector, [0x60FB, 0x60EA],
            [0x5F93, 0x5F96, 0x5F97, 0x5F98, 0x5F99, 0x5F9D, 0x7DF4, 0x7DF5, 0x7DF7,
                0x5FA0, 0x5FA4, 0x5FAC], ignition);
    }
}
