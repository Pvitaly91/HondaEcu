namespace HondaEcu.Cli;

internal sealed class CommandLine
{
    private readonly Dictionary<string, List<string?>> _options;

    private CommandLine(IReadOnlyList<string> positionals, Dictionary<string, List<string?>> options)
    {
        Positionals = positionals;
        _options = options;
    }

    public IReadOnlyList<string> Positionals { get; }

    public static CommandLine Parse(
        IEnumerable<string> arguments,
        IReadOnlySet<string>? flagOptions = null)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        flagOptions ??= new HashSet<string>(StringComparer.Ordinal);

        var tokens = arguments.ToArray();
        var positionals = new List<string>();
        var options = new Dictionary<string, List<string?>>(StringComparer.Ordinal);

        for (var index = 0; index < tokens.Length; index++)
        {
            var token = tokens[index];
            if (token == "--")
            {
                positionals.AddRange(tokens[(index + 1)..]);
                break;
            }

            if (!token.StartsWith("--", StringComparison.Ordinal))
            {
                positionals.Add(token);
                continue;
            }

            var equals = token.IndexOf('=');
            var name = equals < 0 ? token[2..] : token[2..equals];
            if (string.IsNullOrWhiteSpace(name))
            {
                throw new CliUsageException("Invalid empty option name.");
            }

            string? value;
            if (equals >= 0)
            {
                if (flagOptions.Contains(name))
                {
                    throw new CliUsageException($"Flag '--{name}' does not accept a value.");
                }

                value = token[(equals + 1)..];
            }
            else if (flagOptions.Contains(name))
            {
                value = null;
            }
            else
            {
                if (++index >= tokens.Length || tokens[index].StartsWith("--", StringComparison.Ordinal))
                {
                    throw new CliUsageException($"Option '--{name}' requires a value.");
                }

                value = tokens[index];
            }

            if (!options.TryGetValue(name, out var values))
            {
                values = [];
                options.Add(name, values);
            }

            values.Add(value);
        }

        return new CommandLine(positionals, options);
    }

    public bool HasFlag(string name)
    {
        if (!_options.TryGetValue(name, out var values))
        {
            return false;
        }

        if (values.Count != 1 || values[0] is not null)
        {
            throw new CliUsageException($"Flag '--{name}' must not be repeated or given a value.");
        }

        return true;
    }

    public string? Optional(string name)
    {
        if (!_options.TryGetValue(name, out var values))
        {
            return null;
        }

        if (values.Count != 1 || values[0] is null)
        {
            throw new CliUsageException($"Option '--{name}' must be specified exactly once with a value.");
        }

        return values[0];
    }

    public string Required(string name) =>
        Optional(name) ?? throw new CliUsageException($"Missing required option '--{name}'.");

    public IReadOnlyList<string> Many(string name)
    {
        if (!_options.TryGetValue(name, out var values))
        {
            return [];
        }

        if (values.Any(value => value is null))
        {
            throw new CliUsageException($"Option '--{name}' requires a value.");
        }

        return values.Select(value => value!).ToArray();
    }

    public void EnsureOnly(params string[] names)
    {
        var allowed = names.ToHashSet(StringComparer.Ordinal);
        var unknown = _options.Keys.FirstOrDefault(name => !allowed.Contains(name));
        if (unknown is not null)
        {
            throw new CliUsageException($"Unknown option '--{unknown}'.");
        }
    }

    public void RequirePositionals(int count, string usage)
    {
        if (Positionals.Count != count)
        {
            throw new CliUsageException($"Usage: {usage}");
        }
    }
}

public sealed class CliUsageException : Exception
{
    public CliUsageException(string message)
        : base(message)
    {
    }
}
