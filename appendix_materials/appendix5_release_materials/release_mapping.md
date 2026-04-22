# Release Material Mapping

## Purpose

This note maps the release-related files in the repository to the engineering
work described in Chapter 5.

## Main files

- `auto_ocr_pipeline_v1.0.py`
  - Final release-oriented main program.
  - Integrates the tuned adaptive-threshold logic into the publishable GUI
    version.

- `app_config_v1.0.json`
  - Default release configuration.
  - Uses relative paths so the packaged directory can be relocated.

- `prepare_release_v1_0_portable.ps1`
  - Builds the portable release directory.
  - Copies required models, test samples, startup scripts, and documentation.

- `build_release_v1_0_standalone.ps1`
  - Packs the `ocr_runtime` Conda environment.
  - Rebuilds the standalone release directory and expands the bundled runtime.

- `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0.iss`
  - Inno Setup script for producing the Windows installer.
  - Uses the standalone directory under `release_candidates`.

- `release_assets/Mr6_Auto_OCR_Pipeline_v1.0/`
  - End-user documentation copied into the packaged release.

## Suggested use in the thesis

If the thesis needs a repository pointer for the release phase, Chapter 5 can
refer to:

- `appendix_materials/appendix5_release_materials/README.md`
- `appendix_materials/appendix5_release_materials/release_mapping.md`

This keeps the release-engineering evidence separate from dataset, training, and
test-record appendices.
