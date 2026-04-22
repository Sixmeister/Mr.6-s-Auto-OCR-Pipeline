# v1.0 Packaging Notes

The project is now ready for a self-contained installer workflow.

## Recommended Approach

Instead of forcing `PaddleOCR + PaddlePaddle + PyQt5 + pyzbar` into a single frozen executable immediately, the more reliable route is:

1. build a standalone release folder that bundles the validated `ocr_runtime` environment
2. wrap that folder with an installer

This approach is more stable for the current project because it stays closer to the runtime environment that has already been tested successfully.

## Files Already Prepared

- `build_release_v1_0_standalone.ps1`
  - builds a standalone release folder with the bundled runtime environment
- `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0.iss`
  - Inno Setup script for generating a Windows installer

## Build Steps

### 1. Build the standalone folder

Run from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release_v1_0_standalone.ps1
```

This should generate:

```text
release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_standalone
```

### 2. Install Inno Setup

If Inno Setup is not installed yet, install it first.

### 3. Compile the installer

Open this file in Inno Setup:

```text
installer_assets\Mr6_Auto_OCR_Pipeline_v1.0.iss
```

Compile it to produce a Windows installer.

## Notes

- The `ocr_runtime` environment is currently large, around 3 GB
- The final installer will therefore also be fairly large
- If you later want a smaller package, we can evaluate PyInstaller or Nuitka after the self-contained installer path is stable
