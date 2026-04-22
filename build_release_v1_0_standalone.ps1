$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PortableReleaseScript = Join-Path $ProjectRoot "prepare_release_v1_0_portable.ps1"
$PortableReleaseDir = Join-Path $ProjectRoot "release_candidates\Mr6_Auto_OCR_Pipeline_v1.0"
$StandaloneRoot = Join-Path $ProjectRoot "release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_standalone"
$RuntimeArchive = Join-Path $ProjectRoot "release_candidates\ocr_runtime_condapack.zip"
$CondaExe = "E:\Anaconda3\Scripts\conda.exe"
$CondaPackExe = "E:\Anaconda3\Scripts\conda-pack.exe"
$RuntimePrefix = "E:\Anaconda3\envs\ocr_runtime"

if (-not (Test-Path $CondaExe)) {
    throw "conda.exe was not found at $CondaExe"
}

if (-not (Test-Path $CondaPackExe)) {
    throw "conda-pack.exe was not found at $CondaPackExe"
}

if (-not (Test-Path $PortableReleaseScript)) {
    throw "Portable release script was not found: $PortableReleaseScript"
}

Write-Host "Step 1/5: Rebuilding portable release..."
powershell -ExecutionPolicy Bypass -File $PortableReleaseScript

if (-not (Test-Path $PortableReleaseDir)) {
    throw "Portable release directory was not created: $PortableReleaseDir"
}

Write-Host "Step 2/5: Packing ocr_runtime with conda-pack..."
if (Test-Path $RuntimeArchive) {
    Remove-Item -Path $RuntimeArchive -Force
}

& $CondaPackExe -p $RuntimePrefix -o $RuntimeArchive --format zip

if (-not (Test-Path $RuntimeArchive)) {
    throw "conda-pack archive was not created: $RuntimeArchive"
}

Write-Host "Step 3/5: Refreshing standalone directory..."
if (Test-Path $StandaloneRoot) {
    Remove-Item -Path $StandaloneRoot -Recurse -Force
}
Copy-Item -Path $PortableReleaseDir -Destination $StandaloneRoot -Recurse -Force

$RuntimeDir = Join-Path $StandaloneRoot "runtime_env"
if (Test-Path $RuntimeDir) {
    Remove-Item -Path $RuntimeDir -Recurse -Force
}

Write-Host "Step 4/5: Expanding bundled runtime..."
Expand-Archive -Path $RuntimeArchive -DestinationPath $RuntimeDir -Force

$CondaUnpackCandidates = @(
    (Join-Path $RuntimeDir "Scripts\conda-unpack.exe"),
    (Join-Path $RuntimeDir "conda-unpack.exe")
)

$CondaUnpack = $CondaUnpackCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($CondaUnpack) {
    Write-Host "Step 5/5: Running conda-unpack..."
    Push-Location $RuntimeDir
    try {
        & $CondaUnpack
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Warning "conda-unpack was not found in the packed runtime. The standalone folder was created, but you should verify runtime relocation before distributing it."
}

Write-Host ""
Write-Host "Standalone release directory created:" -ForegroundColor Green
Write-Host $StandaloneRoot -ForegroundColor Green
Write-Host ""
Write-Host "Next step:" -ForegroundColor Cyan
Write-Host "Use installer_assets\\Mr6_Auto_OCR_Pipeline_v1.0.iss with Inno Setup to create an installer."
