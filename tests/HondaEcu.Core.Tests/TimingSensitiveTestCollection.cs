namespace HondaEcu.Core.Tests;

// Timer cancellation and child-start deadlines must not race CPU-heavy model tests.
// Assertions and deadlines remain unchanged; only these existing checks are isolated.
[CollectionDefinition(Name, DisableParallelization = true)]
public sealed class TimingSensitiveTestCollection
{
    public const string Name = "Timing-sensitive process and cancellation checks";
}
