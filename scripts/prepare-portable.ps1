$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimePythonRoot = Join-Path $ProjectRoot ".runtime\python"
$RuntimePython = Join-Path $RuntimePythonRoot "python.exe"
$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$VirtualPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
$VenvConfig = Join-Path $VirtualEnvironment "pyvenv.cfg"
$NodeContainer = Join-Path $ProjectRoot ".runtime\node"

if (-not (Test-Path -LiteralPath $RuntimePython)) {
    throw "Portable Python is missing: .runtime\python\python.exe"
}

if (-not (Test-Path -LiteralPath $VirtualPython)) {
    throw "Backend environment is missing: .venv\Scripts\python.exe"
}

$NodeRoot = Get-ChildItem -LiteralPath $NodeContainer -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "node.exe") } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $NodeRoot) {
    throw "Portable Node.js is missing under .runtime\node"
}

$NodeExecutable = Join-Path $NodeRoot "node.exe"
$NpmExecutable = Join-Path $NodeRoot "npm.cmd"
$ViteCommand = Join-Path $ProjectRoot "frontend\node_modules\.bin\vite.cmd"

if (-not (Test-Path -LiteralPath $NpmExecutable)) {
    throw "Portable npm is missing."
}

if (-not (Test-Path -LiteralPath $ViteCommand)) {
    throw "Frontend dependencies are missing: frontend\node_modules"
}

# The copied virtual environment remembers the creator's absolute path.
# Rewrite it to the current extracted directory so the package can be moved.
$ConfigText = @"
home = $RuntimePythonRoot
include-system-site-packages = false
version = 3.13.15
executable = $RuntimePython
command = $RuntimePython -m venv $VirtualEnvironment
"@
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($VenvConfig, $ConfigText, $Utf8NoBom)

& $VirtualPython -c "import fastapi, uvicorn, openpyxl"
if ($LASTEXITCODE -ne 0) {
    throw "Backend dependencies could not be loaded."
}

& $NodeExecutable --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Portable Node.js could not be started."
}

$Tileset = Join-Path $ProjectRoot "frontend\public\3dtiles\nanlin\tileset.json"
if (-not (Test-Path -LiteralPath $Tileset)) {
    Write-Warning "Campus 3D model is missing. The platform can run, but the campus buildings will not appear."
}

Write-Host "Portable package check passed." -ForegroundColor Green
