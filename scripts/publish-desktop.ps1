#requires -Version 7.0
[CmdletBinding()]
param(
    [string] $OutputPath = 'artifacts/desktop/win-x64'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Desktop publishing requires Windows x64.' }

$repository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$artifactRoot = [IO.Path]::GetFullPath((Join-Path $repository 'artifacts/desktop'))
$buildRoot = [IO.Path]::GetFullPath((Join-Path $repository 'artifacts/desktop-build'))
$destination = [IO.Path]::GetFullPath($OutputPath, $repository)
if (-not $destination.StartsWith($artifactRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputPath must name a new directory below artifacts/desktop; existing publications are never overwritten.'
}
if (Test-Path -LiteralPath $destination) { throw "Output already exists: $destination. Choose a new -OutputPath." }

function Invoke-Checked([string] $Command, [string[]] $Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE." }
}

function Assert-NoReparseParents([string] $Path) {
    $ancestor = [IO.Path]::GetFullPath($Path)
    while ($ancestor) {
        if ((Test-Path -LiteralPath $ancestor) -and
            (Get-Item -LiteralPath $ancestor -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) {
            throw "Artifact paths must not traverse symbolic links or junctions: $ancestor"
        }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
}

function Copy-RequiredFile([string] $Source, [string] $Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Required package resource is missing: $Source" }
    if ((Get-Item -LiteralPath $Source -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) {
        throw "Package resources must not be symbolic links: $Source"
    }
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($Destination)) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination
}

Assert-NoReparseParents $buildRoot
Assert-NoReparseParents $destination
foreach ($command in @('dotnet', 'rustup', 'cargo', 'rustc')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Missing build tool: $command. See docs/D0_DESKTOP_PREVIEW.md." }
}

$desktopProject = Join-Path $repository 'src/HondaEcu.Desktop/HondaEcu.Desktop.csproj'
if (-not (Test-Path -LiteralPath $desktopProject -PathType Leaf)) { throw 'Desktop project is missing.' }

Push-Location -LiteralPath $repository
$originalRustFlags = $env:RUSTFLAGS
$originalEncodedRustFlags = $env:CARGO_ENCODED_RUSTFLAGS
try {
    $sdkVersion = (& dotnet --version).Trim()
    if ($LASTEXITCODE -ne 0 -or $sdkVersion -notmatch '^8\.0\.') { throw 'Install the .NET 8 SDK selected by global.json.' }
    $rustVersion = (& rustc +1.85.1 --version).Trim()
    if ($LASTEXITCODE -ne 0 -or $rustVersion -notmatch '^rustc 1\.85\.1 ') {
        throw 'Install Rust with: rustup toolchain install 1.85.1 --profile minimal --component rustfmt'
    }
    $installedTargets = @(& rustup target list --installed --toolchain 1.85.1)
    if ($LASTEXITCODE -ne 0 -or 'x86_64-pc-windows-msvc' -notin $installedTargets) {
        throw 'Install target with: rustup target add x86_64-pc-windows-msvc --toolchain 1.85.1'
    }
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $visualStudio = @(if (Test-Path -LiteralPath $vswhere) {
        & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    })
    if ($visualStudio.Count -eq 0 -and -not (Get-Command link.exe -ErrorAction SilentlyContinue)) {
        throw 'Install Visual Studio Build Tools with Desktop development with C++ and a Windows SDK (MSVC x64 linker required).'
    }

    $stage = Join-Path $buildRoot ('publish-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    # No existing output is deleted. A failed build leaves this ignored staging directory for diagnosis.
    Write-Host "Staging portable application in $stage"
    # Use the static Microsoft CRT so the Rust child needs no separately installed VC redistributable.
    # Ignore caller build flags deliberately; restore them before leaving this script.
    $env:CARGO_ENCODED_RUSTFLAGS = $null
    $env:RUSTFLAGS = '-C target-feature=+crt-static'
    $cargoTarget = Join-Path $buildRoot 'rust'
    $dotnetArtifacts = Join-Path $buildRoot 'dotnet'
    Invoke-Checked cargo @('+1.85.1', 'build', '--release', '--locked', '--target', 'x86_64-pc-windows-msvc',
        '--target-dir', $cargoTarget, '--manifest-path', 'rust/p28-slice-runner/Cargo.toml')
    Invoke-Checked cargo @('+1.85.1', 'test', '--release', '--locked', '--target', 'x86_64-pc-windows-msvc',
        '--target-dir', $cargoTarget, '--manifest-path', 'rust/p28-slice-runner/Cargo.toml')
    Invoke-Checked dotnet @('publish', $desktopProject, '--configuration', 'Release', '--runtime', 'win-x64',
        '--self-contained', 'true', '--output', $stage, '-p:PublishTrimmed=false', '-p:PublishAot=false',
        '-p:PublishSingleFile=false', '-p:DebugType=None', '-p:DebugSymbols=false',
        "-p:ArtifactsPath=$dotnetArtifacts", '-p:UseArtifactsOutput=true')

    Copy-RequiredFile (Join-Path $cargoTarget 'x86_64-pc-windows-msvc/release/p28-slice-runner.exe') (Join-Path $stage 'tools/p28-slice-runner.exe')
    foreach ($definition in Get-ChildItem -LiteralPath (Join-Path $repository 'definitions') -Filter '*.json' -File -Recurse) {
        $relative = [IO.Path]::GetRelativePath((Join-Path $repository 'definitions'), $definition.FullName)
        Copy-RequiredFile $definition.FullName (Join-Path $stage "definitions/$relative")
    }
    Copy-RequiredFile (Join-Path $repository 'THIRD_PARTY_NOTICES.md') (Join-Path $stage 'THIRD_PARTY_NOTICES.md')
    Copy-RequiredFile (Join-Path $repository 'docs/D0_DESKTOP_PREVIEW.md') (Join-Path $stage 'docs/D0_DESKTOP_PREVIEW.md')
    Copy-RequiredFile (Join-Path $repository 'docs/M1F_NATIVE_CHECKSUM_VALIDATION.md') (Join-Path $stage 'docs/M1F_NATIVE_CHECKSUM_VALIDATION.md')
    Copy-RequiredFile (Join-Path $repository 'rust/p28-slice-runner/LICENSE.upstream') (Join-Path $stage 'licenses/p28-slice-runner/LICENSE.upstream')
    foreach ($license in Get-ChildItem -LiteralPath (Join-Path $repository 'rust/p28-slice-runner/third_party') -File -Recurse) {
        $relative = [IO.Path]::GetRelativePath((Join-Path $repository 'rust/p28-slice-runner/third_party'), $license.FullName)
        Copy-RequiredFile $license.FullName (Join-Path $stage "licenses/p28-slice-runner/crates/$relative")
    }
    $rustSysroot = (& rustc +1.85.1 --print sysroot).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the pinned Rust standard-library notices.' }
    foreach ($name in @('LICENSE-MIT', 'LICENSE-APACHE', 'COPYRIGHT')) {
        Copy-RequiredFile (Join-Path $rustSysroot "share/doc/rust/$name") (Join-Path $stage "licenses/rust-1.85.1/$name")
    }

    # Resolve the exact restored runtime packs instead of guessing a NuGet cache or copying SDK licenses.
    $runtimeJson = & dotnet msbuild $desktopProject -nologo -verbosity:quiet -target:ResolveFrameworkReferences `
        -property:Configuration=Release -property:RuntimeIdentifier=win-x64 -property:SelfContained=true `
        "-property:ArtifactsPath=$dotnetArtifacts" -property:UseArtifactsOutput=true -getItem:ResolvedRuntimePack
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve .NET runtime package license locations.' }
    $includedFrameworks = @((Get-Content -LiteralPath (Join-Path $stage 'HondaEcu.Desktop.runtimeconfig.json') -Raw | ConvertFrom-Json).runtimeOptions.includedFrameworks)
    if ($includedFrameworks.Count -ne 2 -or @($includedFrameworks | Where-Object { $_.name -notin @('Microsoft.NETCore.App', 'Microsoft.WindowsDesktop.App') }).Count -ne 0) {
        throw 'Unexpected self-contained runtime frameworks; review new dependencies before packaging.'
    }
    # ResolveFrameworkReferences also lists downloadable but unused ASP.NET packs.
    # Inventory only frameworks actually included in this published application.
    $runtimePacks = @((($runtimeJson -join [Environment]::NewLine) | ConvertFrom-Json).Items.ResolvedRuntimePack |
        Where-Object { $_.FrameworkName -in $includedFrameworks.name })
    if ($runtimePacks.Count -ne 2) { throw 'Expected exactly .NETCore and WindowsDesktop runtime packs; review new dependencies before packaging.' }
    $runtimeInventory = foreach ($pack in $runtimePacks) {
        if ($pack.NuGetPackageId -notin @('Microsoft.NETCore.App.Runtime.win-x64', 'Microsoft.WindowsDesktop.App.Runtime.win-x64')) {
            throw "Unexpected runtime pack: $($pack.NuGetPackageId)"
        }
        if (@($includedFrameworks | Where-Object { $_.name -eq $pack.FrameworkName -and $_.version -eq $pack.NuGetPackageVersion }).Count -ne 1) {
            throw 'Runtime package version differs from the published runtime configuration.'
        }
        $packageName = "$($pack.NuGetPackageId)-$($pack.NuGetPackageVersion)"
        $names = if ($pack.NuGetPackageId -eq 'Microsoft.NETCore.App.Runtime.win-x64') {
            @('LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT')
        } else {
            # WindowsDesktop 8 runtime packages distribute their MIT LICENSE but no separate notice file.
            @('LICENSE')
        }
        foreach ($name in $names) {
            Copy-RequiredFile (Join-Path $pack.PackageDirectory $name) (Join-Path $stage "licenses/dotnet/$packageName/$name")
        }
        # Preserve any additional future package notices too; never synthesize a substitute license.
        foreach ($notice in Get-ChildItem -LiteralPath $pack.PackageDirectory -File | Where-Object { $_.Name -match '^(LICENSE|NOTICE|THIRD.?PARTY)' }) {
            Copy-RequiredFile $notice.FullName (Join-Path $stage "licenses/dotnet/$packageName/$($notice.Name)")
        }
        [ordered]@{ id = $pack.NuGetPackageId; version = $pack.NuGetPackageVersion; requiredNotices = @($names) }
    }

    foreach ($required in @('HondaEcu.Desktop.exe', 'HondaEcu.Desktop.runtimeconfig.json', 'coreclr.dll',
            'PresentationFramework.dll', 'tools/p28-slice-runner.exe', 'definitions/p28/p28-304.experimental.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $stage $required) -PathType Leaf)) { throw "Incomplete portable build: $required" }
    }
    $forbidden = @(Get-ChildItem -LiteralPath $stage -Recurse -Force | Where-Object {
        $_.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint) -or
        $_.Extension -match '^\.(bin|rom|hex|eep|dump|gzf|rep|gpr|bak|db|trace|pdb|zip|cs|rs|asm)$' -or
        $_.Name -in @('private', '.git', '.tmp')
    })
    if ($forbidden.Count -ne 0) { throw 'Portable build contains forbidden data, source/debug artifacts or links; it will not be published.' }
    $manifest = [ordered]@{
        formatVersion = 1; purpose = 'D0 + M1f Windows Desktop Research Preview'; safety = 'PcInspectionOnly / NotFlashReady'
        runtimeIdentifier = 'win-x64'; selfContained = $true; trimmed = $false; nativeAot = $false
        dotnetSdk = $sdkVersion; rustCompiler = $rustVersion; rustStaticCrt = $true; runtimePacks = @($runtimeInventory)
        files = @(Get-ChildItem -LiteralPath $stage -File -Recurse | Sort-Object FullName | ForEach-Object {
            [ordered]@{ path = [IO.Path]::GetRelativePath($stage, $_.FullName).Replace('\', '/'); sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
        })
    }
    [IO.File]::WriteAllText((Join-Path $stage 'PUBLISH-MANIFEST.json'), ($manifest | ConvertTo-Json -Depth 8) + [Environment]::NewLine)

    # Validate both absolute move targets immediately before publication. No source/user folder is moved.
    Assert-NoReparseParents $stage
    Assert-NoReparseParents $destination
    if (-not [IO.Path]::GetFullPath($stage).StartsWith($buildRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
        -not $destination.StartsWith($artifactRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
        (Test-Path -LiteralPath $destination)) { throw 'Publication paths changed or are outside the allowed artifact directories.' }
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destination)) -Force | Out-Null
    Move-Item -LiteralPath $stage -Destination $destination
    Write-Host "Portable preview: $(Join-Path $destination 'HondaEcu.Desktop.exe')"
    Write-Host 'Copy the complete folder, not only the EXE. No SDK, Cargo, Git or source repository is required to run it.'
} finally {
    $env:RUSTFLAGS = $originalRustFlags
    $env:CARGO_ENCODED_RUSTFLAGS = $originalEncodedRustFlags
    Pop-Location
}
