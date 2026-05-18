$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "generate_env_secrets.py"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    if (-not $env:UV_CACHE_DIR) {
        $env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
    }
    & $uv.Source run python $script
    exit $LASTEXITCODE
}

if (Test-Path $venvPython) {
    & $venvPython $script
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source $script
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source $script
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python or run project dependency sync first."
