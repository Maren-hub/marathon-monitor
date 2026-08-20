$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$LocalPython = Join-Path $ProjectRoot ".runtime\python\python.exe"
$LocalNodeRoot = Join-Path $ProjectRoot ".runtime\node\node-v22.18.0-win-x64"
$LocalNpm = Join-Path $LocalNodeRoot "npm.cmd"

if (Test-Path $LocalPython) {
    $PythonCommand = $LocalPython
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
}
else {
    throw "Python was not found. Install Python 3.11 or newer and add it to PATH."
}

if (Test-Path $LocalNpm) {
    $NpmCommand = $LocalNpm
    $env:Path = "$LocalNodeRoot;$env:Path"
}
elseif (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
    $NpmCommand = "npm.cmd"
}
elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    $NpmCommand = "npm"
}
else {
    throw "Node.js/npm was not found. Install the current Node.js LTS."
}

if (-not (Test-Path $VirtualEnvironment)) {
    & $PythonCommand -m venv $VirtualEnvironment
}

$PythonExecutable = Join-Path $VirtualEnvironment "Scripts\python.exe"
& $PythonExecutable -m pip install --upgrade pip
& $PythonExecutable -m pip install -r (Join-Path $ProjectRoot "backend\requirements-dev.txt")

Push-Location (Join-Path $ProjectRoot "frontend")
try {
    & $NpmCommand install
}
finally {
    Pop-Location
}

Write-Host "Setup complete. Run scripts\start-backend.ps1 and scripts\start-frontend.ps1 in separate terminals." -ForegroundColor Green
