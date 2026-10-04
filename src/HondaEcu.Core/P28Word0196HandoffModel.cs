namespace HondaEcu.Core;

internal sealed record P28Word0196Oracle(IReadOnlyList<int[]> Events, IReadOnlyList<int[]> Accesses, IReadOnlyList<int> AccessEnds, IReadOnlyList<int> Lengths, int Stop, int A, int Psw);
internal static class P28Word0196HandoffModel
{
    // Independent primary-ISA software observations; no Rust0196 expected operand.
    internal static P28Word0196Oracle Build(int value, int entryPsw, byte control0128, byte source0117)
    {
        var a = value; var psw = entryPsw; var pc = 0x54F5;
        var events = new List<int[]>(); var accesses = new List<int[]>(); var ends = new List<int>(); var lengths = new List<int>();
        void Flag(int mask, bool yes) => psw = yes ? psw | mask : psw & ~mask;
        void Access(int address, int width, int write, int v) => accesses.Add([pc, address, width, write, v]);
        while (pc is not (0x5503 or 0x5533 or 0x556F))
        {
            var oldA = a; var oldPsw = psw; int next, length; var lhs = 65536; var rhs = 65536;
            switch (pc)
            {
                case 0x54F5: length = 3; next = (control0128 & 4) == 0 ? 0x5533 : 0x54F8; Access(0x128, 8, 0, control0128); break;
                case 0x54F8: length = 2; next = 0x54FA; Access(0x108, 8, 1, 255); break;
                case 0x54FA: length = 2; next = 0x54FC; Access(0x196, 16, 0, value); a = value; Flag(0x1000, true); Flag(0x4000, a == 0); break;
                case 0x54FC: length = 1; next = 0x54FD; Access(0x10A, 16, 1, a); break;
                case 0x54FD: length = 4; next = 0x5501; Access(0x117, 8, 0, source0117); lhs = source0117; rhs = 15; Flag(0x8000, source0117 < 15); Flag(0x4000, source0117 == 15); break;
                case 0x5501: length = 2; next = (psw & 0x4000) == 0 ? 0x556F : 0x5503; break;
                default: throw new InvalidOperationException("Unadmitted software consumer PC.");
            }
            events.Add([pc, next, oldA, a, oldPsw, psw, lhs, rhs]); ends.Add(accesses.Count); lengths.Add(length); pc = next;
        }
        return new(events, accesses, ends, lengths, pc, a, psw);
    }
}
