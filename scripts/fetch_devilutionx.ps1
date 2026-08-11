$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Values = python -c "import tomllib,pathlib; v=tomllib.loads(pathlib.Path(r'$Root/upstream.lock.toml').read_text(encoding='utf-8'))['devilutionx']; print(v['repository']); print(v['commit'])"
$Repository = $Values[0]
$Commit = $Values[1]
$Target = Join-Path $Root "third_party/DevilutionX"
if (-not (Test-Path (Join-Path $Target ".git"))) {
    git clone --filter=blob:none --no-checkout $Repository $Target
}
git -C $Target fetch --depth=1 origin $Commit
git -C $Target checkout --detach $Commit
$Actual = (git -C $Target rev-parse HEAD).Trim()
if ($Actual -ne $Commit) { throw "revision mismatch: $Actual" }
Write-Host "DevilutionX pinned at $Actual"
Write-Host "No Diablo MPQ/assets were downloaded by this script. Read upstream LICENSE.md before use."
