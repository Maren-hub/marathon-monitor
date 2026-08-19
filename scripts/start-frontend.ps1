$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$LocalNodeRoot = Join-Path $ProjectRoot ".runtime\node\node-v22.18.0-win-x64"
$LocalNpm = Join-Path $LocalNodeRoot "npm.cmd"

if (Test-Path $LocalNpm) {
    $NpmCommand = $LocalNpm
    $env:Path = "$LocalNodeRoot;$env:Path"
}
elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    $NpmCommand = "npm"
}
else {
    throw "npm was not found. Install Node.js LTS and run scripts\setup.ps1."
}

if (-not (Test-Path (Join-Path $FrontendRoot "node_modules"))) {
    throw "Frontend dependencies are missing. Run scripts\setup.ps1 first."
}

Set-Location $FrontendRoot
& $NpmCommand run dev
