$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

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

try {
    $PythonExe = Get-AvailablePython
    if (-not $PythonExe) {
        throw "No usable Python interpreter was found. Please activate the ocr_runtime environment first, or edit start_release_v1_0.ps1 to point to your python.exe."
    }

    Write-Host "Project root: $ProjectRoot"
    Write-Host "Python exe:   $PythonExe"
    Write-Host "Starting v1.0 GUI..."

    & $PythonExe ".\auto_ocr_pipeline_v1.0.py"
}
catch {
    Write-Host ""
    Write-Host "Startup failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Press Enter to close..."
    Read-Host | Out-Null
    exit 1
}
