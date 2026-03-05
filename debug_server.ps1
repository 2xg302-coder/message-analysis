$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

$venvPython = Join-Path $scriptDir "server_py\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Error "Python virtual environment not found at $venvPython"
    exit 1
}

Write-Host "Starting Backend in debug mode..."
Write-Host "Python path: $venvPython"
Write-Host "Working directory: $scriptDir"

try {
    cd server_py
    & $venvPython main.py
}
catch {
    Write-Error $_
}

Read-Host "Press Enter to exit"
