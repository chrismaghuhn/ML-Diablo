param([int]$Episodes = 3)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$env:PYTHONPATH = "src"
python -m dxai smoke --episodes $Episodes --agent heuristic
