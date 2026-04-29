$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ScriptPath = Join-Path $ProjectRoot "tools\dev\graphify_wiki.py"
$Candidates = @()

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvConfig = Join-Path $ProjectRoot ".venv\pyvenv.cfg"
if ((Test-Path $VenvPython) -and (Test-Path $VenvConfig)) {
    $Candidates += $VenvPython
}

$Candidates += Join-Path $env:APPDATA "uv\tools\graphifyy\Scripts\python.exe"

foreach ($PythonPath in $Candidates) {
    if (-not (Test-Path $PythonPath)) {
        continue
    }

    try {
        & $PythonPath $ScriptPath $ProjectRoot @args
    }
    catch {
        Write-Warning "Python candidate failed: $PythonPath"
        Write-Warning $_
        continue
    }

    if ($LASTEXITCODE -eq 0) {
        exit 0
    }

    Write-Warning "Python candidate failed: $PythonPath"
}

throw "Python executable not found or failed. Tried:`n- $($Candidates -join "`n- ")"
