# Mr.6 Auto OCR Pipeline v1.0

This folder is the portable release package for the local label OCR system developed in this project.

## Documentation

- Chinese guide: `README.zh-CN.md`
- English guide: `README.en.md`
- Quick text note for Windows users: `README.txt`
- Packaging notes: `PACKAGING_NOTES.zh-CN.md` and `PACKAGING_NOTES.en.md`

## Quick Start

1. Double-click `start_release_v1_0.bat`
2. If startup fails, run `start_release_v1_0_debug.bat`
3. Check `logs/startup_debug.log` for startup diagnostics

## Package Highlights

- GUI application based on `auto_ocr_pipeline_v1.0.py`
- Exported 45-epoch label detection model
- PaddleDetection deploy helpers required by the detector
- Default input/output folders for single-image mode and watch mode
- Bundled multi-label sample images and truth CSV for validation

## Notes

- All default paths in `app_config_v1.0.json` are stored as relative paths.
- You can move the entire folder to another location without changing the default configuration.
- This release package currently depends on an available Python runtime environment with the required OCR and GUI libraries installed.
