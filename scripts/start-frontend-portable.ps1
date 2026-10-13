$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "prepare-portable.ps1")

$NodeContainer = Join-Path $ProjectRoot ".runtime\node"
$NodeRoot = Get-ChildItem -LiteralPath $NodeContainer -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "npm.cmd") } |
    Select-Object -First 1 -ExpandProperty FullName
$NpmExecutable = Join-Path $NodeRoot "npm.cmd"
$env:Path = "$NodeRoot;$env:Path"

Set-Location (Join-Path $ProjectRoot "frontend")
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Cyan
& $NpmExecutable run dev -- --host 127.0.0.1
