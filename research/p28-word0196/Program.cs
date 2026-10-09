using System.Globalization;
using System.Reflection;
using System.Text.Json;

// Calls the unchanged production C# oracle AFTER the independent C/IR seal.
// No native execution, copied oracle implementation, or ROM input exists here.
if (args.Length != 1) throw new ArgumentException("Supply the existing Core DLL path.");
var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
var model = assembly.GetType("HondaEcu.Core.P28Word0196AlternateModel", true)!;
var build = model.GetMethod("Build", BindingFlags.Static | BindingFlags.NonPublic)
    ?? throw new InvalidOperationException("Original oracle Build method unavailable.");
var options = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
string? line;
while ((line = Console.ReadLine()) is not null)
{
    var tokens = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
    if (tokens.Length != 30 || !tokens[0].All(c => char.IsAsciiLetterOrDigit(c) || c is '_' or '-'))
        throw new ArgumentException("Expected a closed ID plus29 unsigned fields.");
    var values = tokens.Skip(1).Select(v => uint.Parse(v, NumberStyles.None, CultureInfo.InvariantCulture)).ToArray();
    if (values.Take(9).Any(v => v > ushort.MaxValue) || values.Skip(13).Any(v => v > byte.MaxValue)
        || values[9] > 1 || values[10] > 1 || values[2] != 0x556F || values[3] != 0x0021
        || values[10] != 0 || values[11] > uint.MaxValue - 5)
        throw new ArgumentException("Unsupported offline state/context.");
    var local = values.Skip(13).Take(8).Select(v => (int)v).ToArray();
    int[] addresses = [0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197];
    var ram = addresses.Select((address, i) => (address, value: (int)values[21 + i]))
        .ToDictionary(pair => pair.address, pair => pair.value);
    for (var i = 0; i < 8; ++i) ram[0x108 + i] = local[i];
    var entryRam = new Dictionary<int, int>(ram);
    var left = ram[0x196] | (ram[0x197] << 8);
    var oracle = build.Invoke(null, [left, (int)values[0], (int)values[1], ram])
        ?? throw new InvalidOperationException("Original oracle returned null.");
    var result = JsonSerializer.SerializeToElement(oracle, oracle.GetType(), options);
    var events = result.GetProperty("events").EnumerateArray()
        .Select(row => row.EnumerateArray().Select(v => v.GetInt32()).ToArray()).ToArray();
    var accesses = result.GetProperty("accesses").EnumerateArray()
        .Select(row => row.EnumerateArray().Select(v => v.GetInt32()).ToArray()).ToArray();
    var writes = new List<object>();
    foreach (var access in accesses)
    {
        if (access[3] == 0) continue;
        var oldValue = ram[access[1]];
        var ordinal = checked(values[11] + (uint)writes.Count);
        writes.Add(new
        {
            pc = access[0],
            address = access[1],
            width = access[2],
            oldValue,
            newValue = access[4],
            eventIndex = values[12],
            writeOrdinal = ordinal
        });
        ram[access[1]] = access[4];
    }
    object State(int a, int psw, int pc, Dictionary<int, int> memory) => new
    {
        a,
        psw,
        pc,
        lrb = (int)values[3],
        x1 = (int)values[4],
        x2 = (int)values[5],
        dp = (int)values[6],
        usp = (int)values[7],
        ssp = (int)values[8],
        sf = values[9] != 0,
        halted = values[10] != 0,
        registers = Enumerable.Range(0, 8).Select(i => memory[0x108 + i]).ToArray(),
        ram0117 = memory[0x117],
        ram0124 = memory[0x124],
        ram0128 = memory[0x128],
        ram012A = memory[0x12A],
        ram018E = memory[0x18E],
        ram018F = memory[0x18F],
        ram0196Lo = memory[0x196],
        ram0196Hi = memory[0x197]
    };
    var compare = events.Single(e => e[0] == 0x5578);
    var branch = events.Single(e => e[0] == 0x557D);
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        id = tokens[0],
        status = "Complete",
        entry = State((int)values[0], (int)values[1], (int)values[2], entryRam),
        final = State(result.GetProperty("a").GetInt32(), result.GetProperty("psw").GetInt32(), result.GetProperty("stop").GetInt32(), ram),
        compare = new { left = compare[6], right = compare[7], cf = (compare[5] & 0x8000) != 0, zf = (compare[5] & 0x4000) != 0 },
        branchTaken = branch[1] == 0x55BF,
        stopPc = result.GetProperty("stop").GetInt32(),
        steps = events.Select(e => new { pc = e[0], nextPc = e[1], a = e[3], psw = e[5] }).ToArray(),
        accesses = accesses.Select(e => new { pc = e[0], address = e[1], width = e[2], write = e[3] != 0, value = e[4] }).ToArray(),
        writes
    }));
}
