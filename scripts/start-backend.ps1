$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExecutable = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExecutable)) {
    throw "Python environment not found. Run scripts\setup.ps1 first."
}

Set-Location $ProjectRoot
& $PythonExecutable -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
