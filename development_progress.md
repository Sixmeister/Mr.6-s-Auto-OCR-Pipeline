# Development Progress

This document summarizes the public development path of `Mr.6's Auto OCR Pipeline` and highlights the milestones that are most relevant for readers of the repository and the thesis-support materials.

## 1. Project Goal

The project aims to build a local automatic label-recognition workflow for label-image scenarios. The core tasks include:

- label-region detection and separation,
- OCR text recognition,
- barcode and QR decoding,
- multi-label grouping,
- structured result output,
- Windows GUI integration and release engineering.

## 2. Main Public Development Stages

### Stage 1. Early OCR and code-recognition prototype

The early prototype verified the basic local OCR and code-recognition chain and established the first automatic processing workflow.

Representative file:

- `auto_ocr_pipeline_v0.1.py`

### Stage 2. GUI introduction

After the basic recognition chain was verified, a desktop GUI was introduced to support manual testing, path selection, and result inspection.

Representative file:

- `auto_ocr_pipeline_v0.2gui.py`

### Stage 3. OCR clustering for multi-label grouping

As multi-label images became more important, the project introduced grouping based on OCR text-box spatial relations, together with rule-based correction for over-splitting and over-merging.

Representative files:

- `auto_ocr_pipeline_v0.4.py`
- `auto_ocr_pipeline_v0.5.py`

Historical 10-image result:

- `v0.5`: exact-match `2/10`, MAE not used in the original summary table, average time `1.3482 s`

Expanded 50-image result:

- `v0.5`: exact-match `14/50`, MAE `1.2000`, average time `1.4352 s`

### Stage 4. Detector-first system integration

The project then moved from “recognize first, group later” to “detect label regions first, then recognize within each region”.

This stage introduced:

- detector-first processing,
- detector-box filtering,
- clustering fallback when detection is unavailable or insufficient.

Representative file:

- `auto_ocr_pipeline_v0.63.py`

Historical 10-image result:

- `v0.63`: exact-match `7/10`, MAE `0.3000`

Expanded 50-image result:

- `v0.63`: exact-match `36/50`, MAE `0.2800`, average time `2.5564 s`

### Stage 5. Historical adaptive candidate-selection branch

A later branch explored adaptive candidate selection and tuned filtering rules on the original 10-image multi-label set.

Representative files:

- `auto_ocr_pipeline_v0.71.py`
- `auto_ocr_pipeline_v0.71_tuned.py`

Historical 10-image result:

- `v0.71_tuned`: exact-match `8/10`, MAE `0.3000`

However, the expanded 50-image validation showed that the earlier small-sample-tuned rules did not generalize stably:

- `v0.71_tuned` on the 50-image set: exact-match `9/50`, MAE `1.4800`

This made it inappropriate to present the old tuned branch as the final thesis conclusion for the expanded validation set.

### Stage 6. `v0.7_retuned` candidate-selection optimization branch

To preserve the historical `v0.71_tuned` branch while still improving the expanded-set result, a new branch named `v0.7_retuned` was created.

This branch focused on:

- correcting detector integration into the local project root,
- reducing system-level loss between detector output and final system output,
- retuning candidate-box filtering and selection for the 50-image expanded set.

Representative file:

- `auto_ocr_pipeline_v0.7_retuned.py`

Expanded 50-image result:

- `v0.7_retuned`: exact-match `47/50`, MAE `0.0600`, average time `3.4147 s`

Compared with `v0.63` on the same 50-image set:

- `v0.63`: exact-match `36/50`, MAE `0.2800`
- `v0.7_retuned`: exact-match `47/50`, MAE `0.0600`

The main interpretation is not that the system surpassed the detector itself, but that the system-level pipeline was improved until it could preserve the strong counting ability of the 45-epoch detector much more faithfully.

### Stage 7. Detector-model comparison and model selection

The project also compared multiple exported label-detection models under the same truth table and evaluation logic.

Historical 10-image detector comparison:

- early model: exact-match `0/10`
- `80e` model: exact-match `0/10`
- `45e` model: exact-match `7/10`

Expanded 50-image detector comparison:

- early model: exact-match `0/50`, MAE `2.8800`
- `80e` model: exact-match `0/50`, MAE `2.8200`
- `45e` model: exact-match `47/50`, MAE `0.0600`

This is why the later system branches continue to use the 45-epoch detector as the core model.

### Stage 8. Release engineering and `v1.0`

After the main functional path stabilized, the project moved into release preparation and Windows delivery work.

Representative file:

- `auto_ocr_pipeline_v1.0.py`

Public release-related work includes:

- release directory cleanup,
- standalone environment preparation,
- Windows installer generation with Inno Setup,
- GUI and path cleanup for delivery.

A key successful packaging route was:

- cleanup with `build_release_v1_0_standalone.ps1`,
- path shortening via `subst R:`,
- Inno Setup compilation from `R:`.

## 3. Public Appendix Materials

The repository keeps thesis-support materials under `appendix_materials/`.

Important folders include:

- `appendix1_code_overview/`
- `appendix2_dataset_overview/`
- `appendix3_training_and_model_compare/`
- `appendix4_test_records/`
- `appendix5_release_materials/`

For the thesis revision, the most important new public folders are:

- `appendix3_training_and_model_compare/model_compare_45e_vs_80e_enhanced50/`
- `appendix3_training_and_model_compare/model_compare_three_models_enhanced50/`
- `appendix3_training_and_model_compare/truth_table_enhanced50/`
- `appendix4_test_records/4_3_multi_label_grouping_tests_enhanced50/`
- `appendix4_test_records/4_4_label_detector_integration_tests_enhanced50/`
- `appendix4_test_records/4_5_candidate_selection_optimization_tests_enhanced50/`

The original 10-image historical materials are still retained alongside the new 50-image materials for traceability.

## 4. Current Public Repository State

The repository is currently organized as a public archive of:

- representative source versions,
- thesis appendix materials,
- detector-comparison records,
- release and installer support files.

The internal local handoff log is not part of the public repository. Public-facing readers should use:

- `README.md`
- `development_progress.md`
- `appendix_materials/`

## 5. Suggested Reading Entry Points

Readers who want the shortest route through the repository can start with:

1. `README.md`
2. `development_progress.md`
3. `auto_ocr_pipeline_v0.63.py`
4. `auto_ocr_pipeline_v0.7_retuned.py`
5. `auto_ocr_pipeline_v1.0.py`
6. `appendix_materials/`
