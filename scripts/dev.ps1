[CmdletBinding()]
param(
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [string]$FrontendHost = "127.0.0.1",
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $backendPython)) {
    throw "Backend virtualenv Python was not found at $backendPython."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required to start the frontend dev server."
}

Push-Location $backendDir
try {
    & $backendPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed."
    }
}
finally {
    Pop-Location
}

$backendCommand = "Set-Location '$backendDir'; & '$backendPython' -m uvicorn app.main:app --reload --host $BackendHost --port $BackendPort"
$frontendCommand = "Set-Location '$frontendDir'; npm run dev -- --host $FrontendHost --port $FrontendPort"

$backendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $backendCommand -PassThru
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendCommand -PassThru

Write-Host "Backend dev server launched in a new PowerShell window (PID $($backendProcess.Id))."
Write-Host "Frontend dev server launched in a new PowerShell window (PID $($frontendProcess.Id))."
Write-Host "Run .\scripts\smoke-test.ps1 after both servers finish booting."
