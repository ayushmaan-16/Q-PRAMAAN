param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$runtimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
    & '.\.venv\Scripts\python.exe' -m qpramaan.server --port $Port
} elseif (Test-Path -LiteralPath $runtimePython) {
    & $runtimePython -m qpramaan.server --port $Port
} else {
    python -m qpramaan.server --port $Port
}
