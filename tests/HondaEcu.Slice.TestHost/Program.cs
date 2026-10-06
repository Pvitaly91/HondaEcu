using System.Diagnostics;
using System.Globalization;
using System.IO.Pipes;
using System.Text.Json;

// Transport fault fixture only. This process does not execute CPU instructions.
if (args[0] == "descendant-ready")
{
    using var descendantPipe = new NamedPipeClientStream(".", args[1], PipeDirection.Out, PipeOptions.Asynchronous);
    await descendantPipe.ConnectAsync(10000);
    using var writer = new StreamWriter(descendantPipe) { AutoFlush = true };
    await writer.WriteLineAsync(Environment.ProcessId.ToString(CultureInfo.InvariantCulture));
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return;
}
if (args[0] == "ready-wait")
{
    using var readyPipe = new NamedPipeClientStream(".", args[1], PipeDirection.InOut, PipeOptions.Asynchronous);
    await readyPipe.ConnectAsync(10000);
    using var writer = new StreamWriter(readyPipe) { AutoFlush = true };
    await writer.WriteLineAsync($"START {Environment.ProcessId.ToString(CultureInfo.InvariantCulture)}");
    _ = await Console.In.ReadToEndAsync(); // READY means the transport sent the entire request and EOF.
    var childPid = 0;
    if (args[2] == "tree")
    {
        var childName = "hondaecu-descendant-" + Guid.NewGuid().ToString("N");
        using var childPipe = new NamedPipeServerStream(childName, PipeDirection.In, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
        var start = new ProcessStartInfo(Environment.ProcessPath!) { UseShellExecute = false, CreateNoWindow = true };
        start.ArgumentList.Add(typeof(Program).Assembly.Location); start.ArgumentList.Add("descendant-ready"); start.ArgumentList.Add(childName);
        using var child = Process.Start(start) ?? throw new InvalidOperationException("Descendant failed to start.");
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await childPipe.WaitForConnectionAsync(deadline.Token);
        using var reader = new StreamReader(childPipe);
        childPid = int.Parse((await reader.ReadLineAsync(deadline.Token))!, CultureInfo.InvariantCulture);
        if (childPid != child.Id || child.HasExited) throw new InvalidOperationException("Invalid descendant readiness.");
    }
    await writer.WriteLineAsync($"READY {Environment.ProcessId.ToString(CultureInfo.InvariantCulture)} {childPid.ToString(CultureInfo.InvariantCulture)}");
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return;
}
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
    case "pid-sleep":
        await File.WriteAllTextAsync(args[1], Environment.ProcessId.ToString(System.Globalization.CultureInfo.InvariantCulture));
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
