$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogPath = Join-Path $LogDir "startup_debug.log"

function Get-AvailablePython {
    $candidates = @()

    $candidates += @(
        (Join-Path $ProjectRoot "runtime_env\python.exe"),
        (Join-Path $ProjectRoot "runtime_env\Scripts\python.exe")
    )

    if ($env:CONDA_PREFIX) {
        $candidates += (Join-Path $env:CONDA_PREFIX "python.exe")
    }

    $candidates += @(
        "E:\Anaconda3\envs\ocr_runtime\python.exe",
        "C:\Users\26310\anaconda3\envs\ocr_runtime\python.exe",
        "E:\Anaconda3\python.exe",
        "C:\Users\26310\anaconda3\python.exe"
    )

    $commandPython = Get-Command python -ErrorAction SilentlyContinue
    if ($commandPython) {
        $candidates += $commandPython.Source
    }

    $commandPy = Get-Command py -ErrorAction SilentlyContinue
    if ($commandPy) {
        $candidates += $commandPy.Source
    }

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

"" | Set-Content -Path $LogPath -Encoding UTF8
"=== Startup Debug Log ===" | Add-Content -Path $LogPath -Encoding UTF8
"Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content -Path $LogPath -Encoding UTF8
"Project root: $ProjectRoot" | Add-Content -Path $LogPath -Encoding UTF8

try {
    $PythonExe = Get-AvailablePython
    "Python exe: $PythonExe" | Add-Content -Path $LogPath -Encoding UTF8

    if (-not $PythonExe) {
        throw "No usable Python interpreter was found."
    }

    Write-Host "Project root: $ProjectRoot"
    Write-Host "Python exe:   $PythonExe"
    Write-Host "Writing log to: $LogPath"
    Write-Host "Starting v1.0 GUI in debug mode..."

    & $PythonExe ".\auto_ocr_pipeline_v1.0.py" *>> $LogPath
}
catch {
    "Startup failed: $($_.Exception.Message)" | Add-Content -Path $LogPath -Encoding UTF8
    Write-Host ""
    Write-Host "Startup failed. See log:" -ForegroundColor Red
    Write-Host $LogPath -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "Debug log saved to:" -ForegroundColor Cyan
Write-Host $LogPath -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Enter to close..."
Read-Host | Out-Null
