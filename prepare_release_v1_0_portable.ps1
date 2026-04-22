$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleaseRoot = Join-Path $ProjectRoot "release_candidates"
$ReleaseName = "Mr6_Auto_OCR_Pipeline_v1.0"
$TargetDir = Join-Path $ReleaseRoot $ReleaseName
$ReleaseAssetDir = Join-Path $ProjectRoot "release_assets\Mr6_Auto_OCR_Pipeline_v1.0"

$foldersToCopy = @(
    "PaddleDetection-release-2.8.1\deploy\python",
    "PaddleDetection-release-2.8.1\output_inference\label_det_m_45e",
    "multiple_labels_test"
)

$foldersToCreate = @(
    "watch_directory",
    "processed_directory",
    "error_directory",
    "json_directory",
    "output_directory",
    "visual_outputs",
    "logs"
)

$filesToCopy = @(
    "auto_ocr_pipeline_v1.0.py",
    "app_config_v1.0.json",
    "start_release_v1_0.ps1",
    "start_release_v1_0.bat",
    "start_release_v1_0_debug.ps1",
    "start_release_v1_0_debug.bat"
)

if (Test-Path $TargetDir) {
    try {
        Remove-Item -Path $TargetDir -Recurse -Force
    }
    catch {
        Write-Host "Target directory is in use. Refreshing releasable files and keeping locked items if necessary..."
        Get-ChildItem -Path $TargetDir -Force | Where-Object { $_.Name -ne "logs" } | Remove-Item -Recurse -Force
    }
}

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

foreach ($file in $filesToCopy) {
    $source = Join-Path $ProjectRoot $file
    $destination = Join-Path $TargetDir $file
    $destinationDir = Split-Path -Parent $destination
    if (-not (Test-Path $destinationDir)) {
        New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
    }
    Copy-Item -Path $source -Destination $destination -Force
}

foreach ($folder in $foldersToCopy) {
    $source = Join-Path $ProjectRoot $folder
    if (-not (Test-Path $source)) {
        continue
    }
    $destination = Join-Path $TargetDir $folder
    $destinationParent = Split-Path -Parent $destination
    if (-not (Test-Path $destinationParent)) {
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    }
    Copy-Item -Path $source -Destination $destination -Recurse -Force
}

foreach ($folder in $foldersToCreate) {
    $destination = Join-Path $TargetDir $folder
    if (-not (Test-Path $destination)) {
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
    }
}

if (Test-Path $ReleaseAssetDir) {
    Get-ChildItem -Path $ReleaseAssetDir -File | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination (Join-Path $TargetDir $_.Name) -Force
    }
}
else {
    $readme = @"
Mr.6 Auto OCR Pipeline v1.0

Quick start:
1. Double-click start_release_v1_0.bat
2. If startup fails, run start_release_v1_0_debug.bat
3. Check logs\startup_debug.log for details

Detailed documentation:
- README.md
- README.zh-CN.md
- README.en.md
"@
    Set-Content -Path (Join-Path $TargetDir "README.txt") -Value $readme -Encoding UTF8
}

Write-Host "Portable release directory created:"
Write-Host $TargetDir
