# Mr.6 Auto OCR Pipeline v1.0 Release Guide

## 1. Overview

`Mr6_Auto_OCR_Pipeline_v1.0` is the portable release package of the local automatic label-recognition system developed in this project.

This release focuses on turning the latest detector-integrated GUI version into a cleaner and more portable package. It includes:

- the main GUI application
- the runtime configuration file
- launch scripts for normal and debug startup
- the exported 45-epoch label detection model
- the PaddleDetection deploy helpers required by inference
- default input/output folders
- bundled sample images and a truth CSV for validation

For installer-oriented packaging notes, see `PACKAGING_NOTES.en.md`.

## 2. Package Structure

The package root is intended to be the working directory of the application:

```text
Mr6_Auto_OCR_Pipeline_v1.0/
+-- auto_ocr_pipeline_v1.0.py
+-- app_config_v1.0.json
+-- start_release_v1_0.bat
+-- start_release_v1_0.ps1
+-- start_release_v1_0_debug.bat
+-- start_release_v1_0_debug.ps1
+-- README.md
+-- README.zh-CN.md
+-- README.en.md
+-- README.txt
+-- logs/
+-- watch_directory/
+-- processed_directory/
+-- error_directory/
+-- json_directory/
+-- output_directory/
+-- visual_outputs/
+-- multiple_labels_test/
+-- PaddleDetection-release-2.8.1/
    +-- deploy/python/
    +-- output_inference/label_det_m_45e/
```

## 3. What Each Part Is For

| File or Folder | Purpose |
| --- | --- |
| `auto_ocr_pipeline_v1.0.py` | Main application with GUI, OCR workflow, detector integration, logging, and save logic |
| `app_config_v1.0.json` | Runtime configuration file |
| `start_release_v1_0.bat` | Recommended launcher for double-click startup |
| `start_release_v1_0.ps1` | PowerShell launcher |
| `start_release_v1_0_debug.bat` | Debug launcher for troubleshooting |
| `logs/` | Startup logs and debug information |
| `watch_directory/` | Input folder for watch mode |
| `processed_directory/` | Archive folder for successfully processed original images |
| `error_directory/` | Archive folder for failed or poor-result images |
| `json_directory/` | Default JSON output folder |
| `output_directory/` | Default TXT output folder |
| `visual_outputs/` | Default visualization output folder |
| `multiple_labels_test/` | Bundled sample images and ground truth CSV |
| `PaddleDetection-release-2.8.1/` | Detector deploy helpers and exported model |

## 4. Runtime Requirements

This release package is portable, but it is not yet a fully standalone executable build. It still requires an available Python runtime environment.

Recommended setup:

- Windows
- A working Python environment
- Preferably the `ocr_runtime` environment used in this project

Required core libraries include:

- `paddleocr`
- `paddlepaddle`
- `opencv-python`
- `PyQt5`
- `watchdog`
- `pyzbar`
- `numpy`

## 5. How to Start the Program

### 5.1 Recommended Method

Double-click:

```text
start_release_v1_0.bat
```

This is the preferred entry point for normal users.

### 5.2 Start from PowerShell

If you already opened PowerShell in the release folder:

```powershell
.\start_release_v1_0.ps1
```

### 5.3 Debug Startup

If the program does not launch correctly, run:

```text
start_release_v1_0_debug.bat
```

Then inspect:

```text
logs/startup_debug.log
```

This log is useful for diagnosing:

- wrong Python interpreter selection
- missing `paddleocr`
- broken relative paths
- missing model files

## 6. Main Working Modes

### 6.1 Single-Image Mode

Use this mode when you want to manually select and recognize one image at a time.

Typical workflow:

1. Start the application
2. Keep the mode as single-image mode
3. Select an image manually
4. Let the program run label detection, OCR, barcode/QR decoding, and result formatting
5. View logs and results on the right panel
6. Save results automatically or manually depending on the current output mode

### 6.2 Watch Mode

Use this mode for continuous processing or batch-style testing.

Typical workflow:

1. Switch to watch mode
2. Confirm the `watch_directory` path
3. Start monitoring
4. Copy images into `watch_directory`
5. The program processes them and moves originals to either the processed or error folder

## 7. Output Types

The program can generate several kinds of outputs:

| Output Type | Default Folder | Description |
| --- | --- | --- |
| JSON results | `json_directory/` | Structured results including label boxes, recognized text, and code data |
| TXT results | `output_directory/` | Human-readable plain-text summaries |
| Visual outputs | `visual_outputs/` | Visualization images |
| Debug logs | `logs/` | Startup and troubleshooting logs |

The application also supports two output behaviors:

- automatic output
- manual output

## 8. Configuration File

The default configuration file is:

```text
app_config_v1.0.json
```

It stores:

- input and output directories
- detector model directory
- ground truth CSV path
- result record CSV path
- detection thresholds and NMS settings
- adaptive strategy options
- automatic/manual output preference

One key engineering improvement of this release is that most paths are stored as relative paths, so the whole folder can be moved as one package.

## 9. Bundled Test Materials

The package includes:

- sample multi-label images in `multiple_labels_test/`
- the corresponding truth table in `multiple_labels_test/truth.csv`

These files are useful for:

- quick functional verification
- label-detection demonstrations
- result-record comparisons

## 10. Common Issues

### 10.1 The window does not appear

Run:

```text
start_release_v1_0_debug.bat
```

Then check:

```text
logs/startup_debug.log
```

### 10.2 `paddleocr` is missing

This means the selected Python environment does not contain `paddleocr`.  
Use the correct runtime environment and launch again.

### 10.3 Watch mode cannot read newly added images

This usually happens when the image file is still being written.  
The current release includes a file-readiness wait mechanism, but it is still better to avoid copying partially written files from unstable network or sync folders.

### 10.4 Detector model fails to load

Make sure the following folders exist:

```text
PaddleDetection-release-2.8.1/output_inference/label_det_m_45e
PaddleDetection-release-2.8.1/deploy/python
```

## 11. Recommended Distribution Method

When sharing this program with teachers, classmates, or testers, distribute the entire:

```text
Mr6_Auto_OCR_Pipeline_v1.0
```

folder instead of sending only the Python script. This keeps the relative paths, model files, launchers, and default directories intact.

## 12. Future Packaging Direction

This `v1.0` release already works as a portable release folder, but future engineering steps may include:

- packaging into a standalone installer
- building a real executable release
- adding dependency checks
- exporting more complete logs and diagnostic reports
