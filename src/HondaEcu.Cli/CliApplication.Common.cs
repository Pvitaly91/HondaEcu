using System.Globalization;
using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private static readonly JsonSerializerOptions JsonOptions = JsonDefaults.Create(writeIndented: true);

    private string ResolvePath(string path) =>
        Path.GetFullPath(path, _workingDirectory);

    private ProfileCatalog LoadProfileCatalog()
    {
        var definitionsDirectory = _definitionsDirectory ?? FindDefinitionsDirectory();
        if (definitionsDirectory is null || !Directory.Exists(definitionsDirectory))
        {
            throw new InvalidOperationException(
                "ROM profile definitions were not found. Run from the repository or provide a definitions directory.");
        }

        return ProfileCatalog.LoadDirectory(definitionsDirectory);
    }

    private string? FindDefinitionsDirectory()
    {
        foreach (var startingDirectory in new[] { _workingDirectory, AppContext.BaseDirectory })
        {
            var current = new DirectoryInfo(startingDirectory);
            while (current is not null)
            {
                var candidate = Path.Combine(current.FullName, "definitions");
                if (Directory.Exists(candidate))
                {
                    return candidate;
                }

                current = current.Parent;
            }
        }

        return null;
    }

    private static int ParsePositiveInt(string value, string optionName)
    {
        if (!int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var result) || result <= 0)
        {
            throw new CliUsageException($"Option '--{optionName}' must be a positive integer.");
        }

        return result;
    }

    private static double ParseNumber(string value, string description)
    {
        if (!double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var result) ||
            !double.IsFinite(result))
        {
            throw new CliUsageException($"{description} must be a finite number using '.' as the decimal separator.");
        }

        return result;
    }

    private static (string Id, double Value) ParseAssignment(string assignment)
    {
        var separator = assignment.IndexOf('=');
        if (separator <= 0 || separator == assignment.Length - 1)
        {
            throw new CliUsageException($"Invalid assignment '{assignment}'; expected parameter=value.");
        }

        var id = assignment[..separator];
        var value = ParseNumber(assignment[(separator + 1)..], $"Value for '{id}'");
        return (id, value);
    }

    private static string Hex(ReadOnlySpan<byte> bytes) =>
        Convert.ToHexString(bytes).ToLowerInvariant();

    private static string Kebab(Enum value)
    {
        var text = value.ToString();
        var result = new System.Text.StringBuilder(text.Length + 4);
        for (var index = 0; index < text.Length; index++)
        {
            if (index > 0 && char.IsUpper(text[index]))
            {
                result.Append('-');
            }

            result.Append(char.ToLowerInvariant(text[index]));
        }

        return result.ToString();
    }

    private static async Task WriteJsonFileAsync(string path, object value, CancellationToken cancellationToken)
    {
        var json = JsonSerializer.Serialize(value, value.GetType(), JsonOptions);
        await Task.Run(() => AtomicFile.WriteAllText(path, json), cancellationToken).ConfigureAwait(false);
    }

    private async Task WriteJsonAsync(object value)
    {
        var json = JsonSerializer.Serialize(value, value.GetType(), JsonOptions);
        await _output.WriteLineAsync(json).ConfigureAwait(false);
    }
}
