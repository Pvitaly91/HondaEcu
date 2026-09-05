using HondaEcu.Core;

namespace HondaEcu.Desktop.Models;

/// <summary>Immutable scenario and query snapshots; no file path is authoritative.</summary>
public sealed record DesktopRpmJob(long SessionId, long JobId, DesktopDocument Document,
    P28RpmQuery Query, string? ScenarioPath, string? ScenarioFileDigest);
