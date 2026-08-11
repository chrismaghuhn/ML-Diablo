param(
    [Parameter(Mandatory = $true)]
    [string]$DiabloDataPath,
    [Parameter(Mandatory = $true)]
    [string]$DevilutionXCheckout,
    [Parameter(Mandatory = $true)]
    [string]$DevilutionXBuild,
    [string]$CoreAssetsPath = "",
    [string]$EngineRuntimePath = "",
    [string]$ProbeBuild = "",
    [UInt64]$Seed = 123,
    [string]$Task = "combat.single_melee.v0",
    [string]$RuntimeRoot = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-Directory([string]$PathValue, [string]$Label) {
    if (-not (Test-Path -LiteralPath $PathValue -PathType Container)) {
        throw "$Label does not exist: $PathValue"
    }
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Quote-WindowsArgument([string]$Value) {
    return '"' + $Value.Replace('"', '\"') + '"'
}

$lockText = Get-Content -LiteralPath (Join-Path $RepoRoot "upstream.lock.toml") -Raw
$commitMatch = [regex]::Match($lockText, '(?ms)^\[devilutionx\].*?^\s*commit\s*=\s*"([0-9a-f]{40})"')
if (-not $commitMatch.Success) {
    throw "unable to read the pinned DevilutionX commit from upstream.lock.toml"
}
$PinnedCommit = $commitMatch.Groups[1].Value

$DiabloDataPath = Resolve-Directory $DiabloDataPath "Diablo data path"
$DevilutionXCheckout = Resolve-Directory $DevilutionXCheckout "DevilutionX checkout"
$DevilutionXBuild = Resolve-Directory $DevilutionXBuild "DevilutionX build"

$actualCommit = (git -C $DevilutionXCheckout rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $PinnedCommit) {
    throw "DevilutionX commit mismatch: expected $PinnedCommit, found $actualCommit"
}
$checkoutStatus = (git -C $DevilutionXCheckout status --porcelain | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "unable to inspect the DevilutionX checkout"
}
if ($checkoutStatus) {
    throw "DevilutionX checkout must be clean for a reproducible probe run"
}

if (-not (Get-ChildItem -LiteralPath $DiabloDataPath -Filter "DIABDAT.MPQ" -File -ErrorAction SilentlyContinue)) {
    throw "DIABDAT.MPQ was not found below the supplied Diablo data path"
}

if (-not $CoreAssetsPath) {
    $CoreAssetsPath = Join-Path $DevilutionXBuild "assets"
}
$CoreAssetsPath = Resolve-Directory $CoreAssetsPath "DevilutionX core assets"
if (-not (Test-Path -LiteralPath (Join-Path $CoreAssetsPath "txtdata\text\textdat.tsv") -PathType Leaf)) {
    throw "DevilutionX core assets are missing txtdata\text\textdat.tsv"
}

if (-not $EngineRuntimePath) {
    $EngineRuntimePath = Join-Path $DevilutionXBuild "Release"
}
$EngineRuntimePath = Resolve-Directory $EngineRuntimePath "DevilutionX runtime"
$sharedLibrary = Join-Path $EngineRuntimePath "libdevilutionx_so.lib"
$runtimeLibrary = Join-Path $EngineRuntimePath "libdevilutionx_so.dll"
if (-not (Test-Path -LiteralPath $sharedLibrary -PathType Leaf)) {
    throw "DevilutionX import library is missing: $sharedLibrary"
}
if (-not (Test-Path -LiteralPath $runtimeLibrary -PathType Leaf)) {
    throw "DevilutionX runtime DLL is missing: $runtimeLibrary"
}

if (-not $ProbeBuild) {
    $ProbeBuild = Join-Path $RepoRoot "build\observation_probe-vs"
}
if (-not $RuntimeRoot) {
    $RuntimeRoot = Join-Path ([IO.Path]::GetTempPath()) "dxai-m02-probe-$Seed"
}
$RuntimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)

if (-not $SkipBuild) {
    $configureArguments = @(
        "-S", (Join-Path $RepoRoot "engine_adapter\observation_probe"),
        "-B", $ProbeBuild,
        "-G", "Visual Studio 17 2022",
        "-A", "x64",
        "-DDEVILUTIONX_SOURCE_DIR=$DevilutionXCheckout",
        "-DDEVILUTIONX_BINARY_DIR=$DevilutionXBuild",
        "-DDEVILUTIONX_SHARED_LIBRARY=$sharedLibrary",
        "-DDEVILUTIONX_CONFIG=Release"
    )
    & cmake @configureArguments
    if ($LASTEXITCODE -ne 0) {
        throw "observation probe CMake configuration failed"
    }
    & cmake --build $ProbeBuild --config Release --parallel 4
    if ($LASTEXITCODE -ne 0) {
        throw "observation probe build failed"
    }
}

$probeExecutable = Join-Path $ProbeBuild "bin\Release\dxai_observation_probe.exe"
if (-not (Test-Path -LiteralPath $probeExecutable -PathType Leaf)) {
    throw "observation probe executable is missing: $probeExecutable"
}

$processInfo = [Diagnostics.ProcessStartInfo]::new()
$processInfo.FileName = (Resolve-Path -LiteralPath $probeExecutable).Path
$processArguments = @(
    "--assets", $DiabloDataPath,
    "--core-assets", $CoreAssetsPath,
    "--runtime-root", $RuntimeRoot,
    "--seed", ([string]$Seed),
    "--task", $Task
) | ForEach-Object { Quote-WindowsArgument $_ }
$processInfo.Arguments = $processArguments -join " "
$processInfo.WorkingDirectory = $RepoRoot
$processInfo.UseShellExecute = $false
$processInfo.CreateNoWindow = $true
$processInfo.RedirectStandardOutput = $true
$processInfo.RedirectStandardError = $true
$processInfo.Environment["PATH"] = $EngineRuntimePath + [IO.Path]::PathSeparator + $env:PATH

$process = [Diagnostics.Process]::new()
$process.StartInfo = $processInfo
[void]$process.Start()
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()

if ($process.ExitCode -ne 0) {
    if ($stderr) {
        Write-Error $stderr.Trim()
    }
    throw "observation probe failed with exit code $($process.ExitCode)"
}

$observation = $stdout | ConvertFrom-Json
if ($observation.schema_version -ne "dxai.observation.v1") {
    throw "probe returned an unexpected observation schema"
}

Write-Host "Observation probe OK"
Write-Host "  upstream commit: $PinnedCommit"
Write-Host "  task: $($observation.task_id)"
Write-Host "  seed: $($observation.seed)"
Write-Host "  player: $($observation.player.position.x),$($observation.player.position.y)"
Write-Host "  local tiles: $($observation.local_tiles.Count)"
Write-Host "  visible entities: $($observation.entities.Count)"
Write-Host "  inventory entries: $($observation.player.inventory.Count)"
Write-Output $stdout.Trim()
