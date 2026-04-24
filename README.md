# Mr.6's Auto OCR Pipeline

`Mr.6's Auto OCR Pipeline` is a local automatic recognition system for label-image scenarios. The project focuses on label-region handling, OCR text extraction, barcode/QR decoding, multi-label separation, structured result output, and the final Windows GUI and release engineering workflow.

This public repository is organized as a presentation-oriented archive of the project. It keeps representative source versions, appendix materials, experiment records, model-comparison outputs, and release-related assets so that readers can understand the implementation path and verify the main thesis results.

## What Is In This Repository

The repository currently keeps four kinds of public materials:

- Representative source versions from early prototypes to the `v1.0` release branch.
- Appendix-oriented experiment materials used to support the thesis.
- Label-detection training and model-comparison outputs.
- Windows release, packaging, and installer assets.

## Main Version Path

The most important script versions are:

- `auto_ocr_pipeline_v0.5.py`
  - OCR clustering and rule-correction stage.
- `auto_ocr_pipeline_v0.63.py`
  - Detector-first system with clustering fallback.
- `auto_ocr_pipeline_v0.71.py`
  - Early adaptive candidate-selection stage.
- `auto_ocr_pipeline_v0.71_tuned.py`
  - Historically tuned small-sample branch used on the original 10-image set.
- `auto_ocr_pipeline_v0.7_retuned.py`
  - Retuned branch created after the expanded 50-image validation, used to reduce system-level loss between detector output and final system output.
- `auto_ocr_pipeline_v1.0.py`
  - Public release branch prepared for standalone packaging and installer delivery.

If you only want to inspect the final delivery-oriented code path, start with:

- `auto_ocr_pipeline_v1.0.py`
- `app_config_v1.0.json`

## Public Experiment Highlights

### 1. Expanded Multi-Label Validation (`enhanced50`)

The original multi-label experiments were based on a 10-image set. For the thesis revision, the validation set was expanded to 50 enhanced multi-label images while keeping the original evaluation logic unchanged.

Key results on the 50-image set are:

- `v0.5` system result:
  - exact-match `14/50`
  - MAE `1.2000`
- `v0.63` system result:
  - exact-match `36/50`
  - MAE `0.2800`
- `v0.71_tuned` historical tuned branch on the same 50-image set:
  - exact-match `9/50`
  - MAE `1.4800`
  - shows that the earlier small-sample-tuned rules did not generalize stably
- `v0.7_retuned` system result:
  - exact-match `47/50`
  - MAE `0.0600`
  - restores the system-level result to the strong counting ability of the 45-epoch detector

### 2. Label-Detector Comparison on the Expanded Set

The detector-only count comparison on the same 50-image set shows:

- `20`-epoch / early detector:
  - exact-match `0/50`
  - MAE `2.8800`
- `80`-epoch detector:
  - exact-match `0/50`
  - MAE `2.8200`
- `45`-epoch detector:
  - exact-match `47/50`
  - MAE `0.0600`

This is why the later system branches continue to use the 45-epoch detector as the core label-detection model.

## Appendix Navigation

Public thesis-support materials are organized under `appendix_materials/`.

### `appendix_materials/appendix1_code_overview/`

Index of representative source files and their thesis mapping.

### `appendix_materials/appendix2_dataset_overview/`

Dataset description, structure notes, and examples related to label-detection data preparation.

### `appendix_materials/appendix3_training_and_model_compare/`

Training and detector-comparison materials.

Important folders include:

- `model_compare_45e_vs_80e/`
  - historical 10-image comparison between the 45-epoch and 80-epoch models.
- `model_compare_three_models/`
  - historical 10-image three-model comparison.
- `model_compare_45e_vs_80e_enhanced50/`
  - updated 50-image comparison between the 45-epoch and 80-epoch models.
- `model_compare_three_models_enhanced50/`
  - updated 50-image comparison among the early detector, 80-epoch detector, and 45-epoch detector.
- `truth_table/`
  - historical 10-image truth table.
- `truth_table_enhanced50/`
  - 50-image truth table used for the expanded validation.

### `appendix_materials/appendix4_test_records/`

System-level test records and comparison files.

Historical 10-image folders are kept intact:

- `4_3_multi_label_grouping_tests/`
- `4_4_label_detector_integration_tests/`
- `4_5_adaptive_threshold_tests/`

Expanded 50-image folders added for the thesis revision are:

- `4_3_multi_label_grouping_tests_enhanced50/`
  - `v0.5` result on the 50-image set.
- `4_4_label_detector_integration_tests_enhanced50/`
  - `v0.63` result and `v0.5 vs v0.63` comparison on the 50-image set.
- `4_5_candidate_selection_optimization_tests_enhanced50/`
  - `v0.71_tuned` failure case on the expanded set,
  - `v0.7_retuned` result,
  - `v0.63 vs v0.7_retuned` comparison,
  - truth table and sample list for the expanded set.

### `appendix_materials/appendix5_release_materials/`

Release mapping, release-asset notes, and packaging references.

## Additional Utility Scripts

Several experiment-support scripts are also kept in the repository root for traceability, including:

- `run_v05_grouping_test_enhanced50.py`
- `run_v063_grouping_test_enhanced50.py`
- `run_v07_retuned_grouping_test_enhanced50.py`
- `build_v05_vs_v063_compare_enhanced50.py`
- `build_v063_vs_v07_retuned_compare_enhanced50.py`
- `compare_exported_label_models.py`
- `compare_three_label_models.py`

## Release Materials

The release-oriented branch and packaging resources are still retained in the repository, including:

- `release_assets/`
- `installer_assets/`
- `build_release_v1_0_standalone.ps1`
- `prepare_release_v1_0_portable.ps1`

The final successful packaging route used:

- standalone-environment cleanup before packaging,
- shortened build path via `subst R:`,
- Inno Setup compilation from the shortened path.

## Reading Order

For a quick high-level tour, the recommended reading order is:

1. `development_progress.md`
2. `auto_ocr_pipeline_v0.5.py`
3. `auto_ocr_pipeline_v0.63.py`
4. `auto_ocr_pipeline_v0.7_retuned.py`
5. `auto_ocr_pipeline_v1.0.py`
6. `appendix_materials/`

## Repository Owner

Repository owner: [Sixmeister](https://github.com/Sixmeister)
