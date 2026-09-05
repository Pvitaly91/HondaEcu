using System.Text.Json;

// Transport fault fixture only. This process does not execute CPU instructions.
_ = await Console.In.ReadToEndAsync();
switch (args[0])
{
    case "valid":
        Console.WriteLine("{\"protocolVersion\":1}");
        break;
    case "version":
        Console.WriteLine("{\"protocolVersion\":2}");
        break;
    case "duplicate":
        Console.WriteLine("{\"protocolVersion\":1,\"protocolVersion\":1}");
        break;
    case "malformed":
        Console.WriteLine("{}{}");
        break;
    case "empty":
        break;
    case "crash":
        Environment.ExitCode = 17;
        break;
    case "timeout":
        await Task.Delay(TimeSpan.FromMinutes(1));
        break;
    case "stdout-limit":
        Console.Write(new string('x', 8192));
        await Task.Delay(TimeSpan.FromMinutes(1));
        break;
    case "stderr-limit":
        Console.Error.Write(new string('x', 8192));
        await Task.Delay(TimeSpan.FromMinutes(1));
        break;
    case "arguments":
        Console.WriteLine(JsonSerializer.Serialize(new { protocolVersion = 1, arguments = args[1..] }));
        break;
    default:
        throw new ArgumentException("Unknown transport fixture scenario.");
}
