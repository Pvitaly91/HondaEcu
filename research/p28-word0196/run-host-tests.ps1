param(
    [string] $RunTag = 'ci',
    [string] $NativeInput = '',
    [string] $NativeRows = ''
)
$ErrorActionPreference = 'Stop'
if ($RunTag -notmatch '^[A-Za-z0-9-]+$') { throw 'Expected a safe output tag.' }
if ([bool]$NativeInput -ne [bool]$NativeRows) { throw 'Supply both sealed offline native paths or neither.' }
$taskRepo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$output = Join-Path $taskRepo ('.tmp/m2av-host/' + $RunTag)
if (Test-Path -LiteralPath $output) { throw 'Refuse host test output directory reuse.' }
New-Item -ItemType Directory -Path $output | Out-Null
$coreSource = Join-Path $taskRepo 'src/HondaEcu.Core/bin/Release/net8.0/HondaEcu.Core.dll'
if (-not (Test-Path -LiteralPath $coreSource)) { throw 'Build the existing Release Core before the oracle test.' }
# Preserve the exact loaded oracle artifact even if later standard QA rebuilds Core.
$coreHash = (Get-FileHash -LiteralPath $coreSource -Algorithm SHA256).Hash
$core = Join-Path $output 'HondaEcu.Core.oracle-snapshot.dll'
Copy-Item -LiteralPath $coreSource -Destination $core
if ((Get-FileHash -LiteralPath $core -Algorithm SHA256).Hash -ne $coreHash -or
    (Get-FileHash -LiteralPath $coreSource -Algorithm SHA256).Hash -ne $coreHash) {
    throw 'Core changed while preserving the oracle artifact.'
}
$python = if ($env:HONDAECU_RESEARCH_PYTHON) { $env:HONDAECU_RESEARCH_PYTHON } else { 'python' }
$compilerLog = Join-Path $output 'compiler.log'
$specification = Join-Path $output 'word0196-spec'
$driver = Join-Path $output 'word0196-driver'
if ($IsWindows) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswhere)) { throw 'Installed MSVC discovery tool unavailable.' }
    $installations = @(& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)
    $discoveryExit = $LASTEXITCODE
    $installation = $installations | Select-Object -First 1
    if ($discoveryExit -ne 0 -or -not $installation) { throw 'Installed host C compiler unavailable.' }
    $vcvars = Join-Path $installation 'VC/Auxiliary/Build/vcvars64.bat'
    $tools = @(Get-ChildItem -LiteralPath (Join-Path $installation 'VC/Tools/MSVC') -Directory | Sort-Object { [version]$_.Name } -Descending)
    if ($tools.Count -eq 0) { throw 'MSVC toolset unavailable.' }
    $toolset = ($tools[0].Name.Split('.')[0..1]) -join '.'
    $specification += '.exe'; $driver += '.exe'
    $helper = Join-Path $output 'build-msvc.cmd'
    $commands = @(
        '@echo off',
        ('call "' + $vcvars + '" -vcvars_ver=' + $toolset + ' >nul'),
        'if errorlevel 1 exit /b 1',
        ('cl /nologo /std:c11 /W4 /WX /O2 /TC /Fe"' + $specification + '" "' + (Join-Path $PSScriptRoot 'word0196_equivalent.c') + '" "' + (Join-Path $PSScriptRoot 'word0196_spec_tests.c') + '"'),
        'if errorlevel 1 exit /b 1',
        ('cl /nologo /std:c11 /W4 /WX /O2 /TC /Fe"' + $driver + '" "' + (Join-Path $PSScriptRoot 'word0196_equivalent.c') + '" "' + (Join-Path $PSScriptRoot 'word0196_host_driver.c') + '"'),
        'if errorlevel 1 exit /b 1',
        'exit /b 0'
    )
    [IO.File]::WriteAllLines($helper, $commands, [Text.Encoding]::ASCII)
    Push-Location -LiteralPath $output
    try { $compileText = & cmd.exe /d /c build-msvc.cmd 2>&1; $compileExit = $LASTEXITCODE }
    finally { Pop-Location }
    [IO.File]::WriteAllLines($compilerLog, @($compileText | ForEach-Object { "$_" }), [Text.UTF8Encoding]::new($false))
    if ($compileExit -ne 0) { throw ('Strict MSVC C11 failed: ' + ($compileText -join "`n")) }
    $compiler = 'MSVC ' + $tools[0].Name
} else {
    $compiler = (Get-Command cc -ErrorAction Stop).Source
    $compileText = @(& $compiler --version 2>&1)
    $flags = @('-std=c11', '-Wall', '-Wextra', '-Wpedantic', '-Werror', '-O2')
    foreach ($unit in @(@('word0196_spec_tests.c', $specification), @('word0196_host_driver.c', $driver))) {
        $text = & $compiler @flags (Join-Path $PSScriptRoot 'word0196_equivalent.c') (Join-Path $PSScriptRoot $unit[0]) -o $unit[1] 2>&1
        $compileExit = $LASTEXITCODE
        $compileText += @($text)
        if ($compileExit -ne 0) { throw ('Strict host C11 failed: ' + ($text -join "`n")) }
    }
    [IO.File]::WriteAllLines($compilerLog, @($compileText | ForEach-Object { "$_" }), [Text.UTF8Encoding]::new($false))
}
$specText = (& $specification 2>&1) -join "`n"
if ($LASTEXITCODE -ne 0) { throw ('Independent C specification failed: ' + $specText) }
$spec = $specText | ConvertFrom-Json
if ($spec.failures -ne 0 -or $spec.actualRomExecutions -ne 0) { throw 'C specification result failed.' }
$irText = (& $python (Join-Path $PSScriptRoot 'validate_ir.py') $PSScriptRoot 2>&1) -join "`n"
if ($LASTEXITCODE -ne 0) { throw ('IR validation failed: ' + $irText) }
$ir = $irText | ConvertFrom-Json
if (-not $ir.passed) { throw 'IR validation not passed.' }
$oracleDirectory = Join-Path $output 'oracle'
$oracleBuild = & dotnet build (Join-Path $PSScriptRoot 'OracleBridge.csproj') -c Release -o $oracleDirectory ('-p:BaseIntermediateOutputPath=' + (Join-Path $output 'oracle-obj/')) -m:1 -nr:false -p:UseSharedCompilation=false 2>&1
$oracleExit = $LASTEXITCODE
[IO.File]::WriteAllLines((Join-Path $output 'oracle-build.log'), @($oracleBuild | ForEach-Object { "$_" }), [Text.UTF8Encoding]::new($false))
if ($oracleExit -ne 0) { throw ('Original-oracle adapter build failed: ' + ($oracleBuild -join "`n")) }
$arguments = @((Join-Path $PSScriptRoot 'verify_equivalence.py'), '--driver', $driver,
    '--oracle', (Join-Path $oracleDirectory 'OracleBridge.dll'), '--core', $core,
    '--output', (Join-Path $output 'equivalence.json'))
if ($NativeInput) { $arguments += @('--native-input', $NativeInput, '--native-rows', $NativeRows) }
$diffText = & $python @arguments 2>&1
$diffExit = $LASTEXITCODE
[IO.File]::WriteAllLines((Join-Path $output 'differential.log'), @($diffText | ForEach-Object { "$_" }), [Text.UTF8Encoding]::new($false))
if ($diffExit -ne 0) { throw ('C differential failed: ' + ($diffText -join "`n")) }
$receipt = [ordered]@{milestone='M2av';compiler=$compiler;cStandard='C11';compileExitCode=0;
    specification=$spec;ir=$ir;oracleBuildExitCode=$oracleExit;differentialExitCode=$diffExit;
    actualRomExecutions=0;firmwareBin=0;nativePathsSupplied=[bool]$NativeInput;
    equivalenceReceipt=(Join-Path $output 'equivalence.json');passed=$true}
[IO.File]::WriteAllText((Join-Path $output 'host-qa.json'), ($receipt | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 8
