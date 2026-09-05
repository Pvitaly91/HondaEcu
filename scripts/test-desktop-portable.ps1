#requires -Version 7.0
[CmdletBinding()]
param([string] $PortablePath = 'artifacts/desktop/win-x64')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'The self-contained Windows application must be checked on Windows.' }
$repository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$source = [IO.Path]::GetFullPath($PortablePath, $repository)
if (-not (Test-Path -LiteralPath (Join-Path $source 'HondaEcu.Desktop.exe') -PathType Leaf)) {
    throw 'Publish the complete portable application before testing it.'
}
if (@(Get-ChildItem -LiteralPath $source -Recurse -Force | Where-Object {
    $_.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)
}).Count -ne 0) { throw 'Portable test input cannot contain links.' }

# A fresh copy outside the repository; retain it for diagnostics, never delete a
# computed user/temp directory recursively. Only the no-window diagnostic runs.
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('HondaEcu D0 ' + [Guid]::NewGuid().ToString('N'))
$copy = Join-Path $testRoot 'Портативна копія з пробілами'
$unrelated = Join-Path $testRoot 'Інша робоча папка'
New-Item -ItemType Directory -Path $testRoot, $unrelated | Out-Null
Copy-Item -LiteralPath $source -Destination $copy -Recurse
$start = [Diagnostics.ProcessStartInfo]::new((Join-Path $copy 'HondaEcu.Desktop.exe'))
$start.ArgumentList.Add('--check-portable-resources')
$start.WorkingDirectory = $unrelated
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardError = $true
# A self-contained host must not resolve a developer's installed SDK/runtime.
$start.Environment['DOTNET_ROOT'] = Join-Path $testRoot 'nonexistent-dotnet'
$start.Environment['DOTNET_ROOT_X64'] = Join-Path $testRoot 'nonexistent-dotnet'
$start.Environment['DOTNET_MULTILEVEL_LOOKUP'] = '0'
$start.Environment['PATH'] = Join-Path $env:SystemRoot 'System32'
$process = [Diagnostics.Process]::Start($start)
$diagnostics = $process.StandardError.ReadToEndAsync()
try {
    if (-not $process.WaitForExit(30000)) {
        $process.Kill($true)
        $process.WaitForExit()
        throw "Portable resource startup check timed out. $($diagnostics.GetAwaiter().GetResult())"
    }
    if ($process.ExitCode -ne 0) { throw "Portable resource startup check failed: exit $($process.ExitCode). $($diagnostics.GetAwaiter().GetResult())" }
    Write-Host 'PASS: self-contained host and bundled resources, outside repository, Ukrainian/spaces path, different CWD, no SDK/Cargo/Git PATH.'
    Write-Host 'This no-window startup diagnostic is not a GUI smoke test.'
    Write-Host "Diagnostic copy retained: $copy"
} finally {
    $process.Dispose()
}
