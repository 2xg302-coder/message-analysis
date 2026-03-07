param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

Write-Host "Starting Smart News Analysis system (Python backend)..."

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python not found. Please install Python 3.8+ and add it to PATH."
}

$venvPath = Join-Path $scriptDir "server_py\venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating Python virtual environment..."
    & python -m venv $venvPath
}

if (-not $SkipInstall) {
    Write-Host "Installing Python dependencies..."
    try {
        & $venvPython -m pip install -r (Join-Path $scriptDir "server_py\requirements.txt")
    }
    catch {
        throw "Python dependency install failed. Try: Remove-Item -Recurse -Force .\server_py\venv ; python -m venv .\server_py\venv ; .\server_py\venv\Scripts\python -m pip install -r .\server_py\requirements.txt"
    }
}
else {
    Write-Host "SkipInstall enabled, skipping dependency installation."
}

$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpm) {
    Write-Host "pnpm not found, installing via npm..."
    & npm install -g pnpm --registry=https://registry.npmmirror.com/
    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if (-not $pnpm) {
        throw "pnpm install failed. Please run: npm install -g pnpm --registry=https://registry.npmmirror.com/"
    }
}

if (-not $SkipInstall) {
    if (-not (Test-Path -LiteralPath (Join-Path $scriptDir "node_modules"))) {
        Write-Host "Installing root dependencies..."
        & pnpm install --registry https://registry.npmmirror.com/
    }
}

if (-not $SkipInstall) {
    if (-not (Test-Path -LiteralPath (Join-Path $scriptDir "client\node_modules"))) {
        Write-Host "Installing frontend dependencies..."
        Push-Location (Join-Path $scriptDir "client")
        try {
            & pnpm install --registry https://registry.npmmirror.com/
        }
        finally {
            Pop-Location
        }
    }
}

Write-Host "Environment ready, starting services..."
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend: http://localhost:8000"
Write-Host "Tip: Press Ctrl+C to stop all services"

$backendCmd = 'cd server_py && venv\Scripts\python main.py'
$frontendCmd = 'cd client && pnpm dev'
& pnpm exec concurrently --kill-others --prefix "[{name}]" --names "BACKEND,FRONTEND" --prefix-colors "blue,magenta" $backendCmd $frontendCmd
