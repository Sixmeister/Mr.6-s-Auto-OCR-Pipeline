# Project Progress Summary

Last updated: 2026-04-02
Project root: E:\Mr.6_Auto_OCR_PipelineWithCodeX

## 1. Project overview
This project is a local automatic label recognition system for electronic material labels. The overall pipeline is:
- image input
- label region segmentation
- OCR text recognition
- barcode/QR code recognition
- result organization and output

The development path has been:
- early single-image prototype validation
- automatic folder watching and continuous processing
- GUI prototype
- OCR-text-box clustering for multi-label grouping
- label detection dataset creation and detector training
- detector integration and post-processing optimization
- adaptive threshold strategy

## 2. Environment history and current split
### Early environment
- `ml_project`
  - used in the earliest prototype validation stage
  - mainly for testing PaddleOCR + pyzbar + basic scripts

### Current stable environment split
- `ocr_runtime`
  - used for GUI system running, OCR, code recognition, and detector integration testing
- `label_train`
  - used for PaddleDetection training
- `label_export`
  - used for exporting the trained detector model

### Why the environments were split
The project originally tried to keep OCR running, detector training, and export in the same environment, but package/version conflicts appeared. Typical conflict points included:
- PaddleOCR version vs paddlepaddle version
- numpy ABI conflicts
- OpenCV compatibility issues
- export-only dependencies differing from runtime dependencies

The current three-environment split is intentional and should be kept.

## 3. Important problems encountered historically
### 3.1 OCR runtime and dependency issues
- Early PaddleOCR scripts defaulted to GPU mode and failed because of missing `cudnn64_8.dll`.
- Fix used in runtime scripts: force `use_gpu=False` for local CPU testing when needed.
- PaddleOCR 3.x was incompatible with the chosen Paddle 2.6.x runtime in `ocr_runtime`.
- The stable route became PaddleOCR 2.x compatible logic in the project scripts.

### 3.2 OCR result parsing issues
- Early prototype scripts could run OCR but failed to print usable results because PaddleOCR return formats were not parsed correctly.
- These scripts were later adapted to the current environment and now parse list-based OCR results correctly.

### 3.3 GUI and thread issues
- Earlier GUI stages had usability limitations because most output stayed in the terminal.
- There had also been thread-cleanup and runtime stability issues during detector integration.
- Later detector-integration versions added safer GUI log handling and thread cleanup.

### 3.4 Multi-label grouping issues
- The earliest multi-label idea was simple OCR text-box distance grouping.
- Main failure modes:
  - oversplitting one true label into several groups
  - overmerging several true labels into one group
- Even after clustering improvements, the route remained layout-sensitive and parameter-sensitive.

### 3.5 Detector training and inference issues
- Training config path issues once caused dataset file loading failures.
- There were periods where the detector integrated into the GUI but produced zero boxes; this was later traced to model/training/output issues rather than pure integration bugs.
- Detector integration then evolved through filtering, NMS, crop-OCR, and adaptive threshold logic.

### 3.6 Output path issues
- In `v0.5`-family scripts, JSON output previously fell back to the image parent directory in some modes.
- This has now been fixed so configured JSON output directories are respected.

## 4. Key code files and their current role
### Prototype and early automation
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\test\test_ocr_and_codes_final.py`
  - cleaned early prototype validation script
  - suitable for Chapter 4 prototype testing
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.1.py`
  - early watch-folder automation prototype
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.2gui.py`
  - early GUI prototype with single-image mode and watch mode
  - includes CSV test recording for continuous watch-mode testing

### Clustering-based multi-label stage
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.5.py`
  - mature clustering/grouping route representative
  - now supports:
    - timing
    - truth CSV input
    - grouping test CSV output
    - label-count correctness evaluation
    - oversplit / overmerge labeling

### Detector-integration stage
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.62.py`
  - detector integration with box filtering, NMS, crop OCR, and detailed stats
  - now also supports the same testing CSV features as `v0.5`
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.7.py`
  - adaptive threshold strategy version
  - now also supports the same testing CSV features as `v0.5`

## 5. Default directories now expected by the project
The current expected default directories are:
- watch folder: `watch_directory`
- processed original images: `processed_directory`
- error images: `error_directory`
- JSON output: `json_directory`
- visualization output: `visual_outputs`
- TXT output: `output_directory`

These defaults were synchronized into:
- `app_config_v05.json`
- `app_config_v062_stable.json`
- `app_config_v07.json`
- related script defaults in `v0.5`, `v0.62`, and `v0.7`

## 6. Test datasets and truth files
### Single-label testing
Used for prototype validation and early automation/GUI testing.

### Multi-label testing
- folder: `E:\Mr.6_Auto_OCR_PipelineWithCodeX\multiple_labels_test`
- contains 10 multi-label images
- truth file: `E:\Mr.6_Auto_OCR_PipelineWithCodeX\multiple_labels_test\truth.csv`
- truth CSV format:
  - `image_name,actual_label_count`

This dataset is currently used to evaluate grouping and detector-based label-count performance.

## 7. Real measured results already obtained
### 7.1 GUI-stage continuous watch-mode test (`v0.2gui`)
Source file:
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\v0_2gui_test_records.csv`

Measured on 10 single-label images in watch mode:
- test image count: 10
- OCR valid images: 10
- code valid images: 5
- successful auto-processing images: 10
- OCR valid rate: 100.0%
- code valid rate: 50.0%
- auto-processing success rate: 100.0%
- average processing time: 0.8012 s

These data were intended for the Chapter 4 GUI/automation table.

### 7.2 Clustering-stage multi-label test (`v0.5`)
Source file:
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\v0_5_grouping_test_records.csv`

Measured on 10 multi-label images:
- test image count: 10
- correct predicted label-count images: 2
- label-count correctness rate: 20.0%
- oversplit images: 3
- oversplit ratio: 30.0%
- overmerge images: 5
- overmerge ratio: 50.0%
- successful processing images: 10
- average processing time: 1.3482 s

Interpretation:
- the clustering route can run stably
- the main weakness is grouping accuracy, not pipeline execution
- this supports the thesis narrative that clustering was useful but insufficient

## 8. Thesis writing status
### Overall direction
Chapter 4 is being restructured to de-emphasize version numbers and emphasize staged system growth.

Agreed writing style:
- explain each stage goal first
- explain concrete implementation second
- use figures and metric tables as evidence
- point out limitations honestly
- transition naturally to the next stage

### Current Chapter 4 structure direction
- `4.1` prototype validation and early environment setup
- `4.2` automatic processing flow and GUI construction
- `4.3` initial multi-label implementation
- later sections on dataset/model training, detector integration, adaptive threshold strategy, and tests

### Terminology conventions already agreed
- overall task: `标签识别`
- neutral middle step: `标签区域划分`
- early rule route: `聚类分组`
- later model route: `标签检测` or `标签区域定位`

### Chapter 4 data tables already planned or partly supported
- prototype validation table using single-label images
- automation/GUI watch-mode test table using `v0_2gui_test_records.csv`
- clustering-stage multi-label table using `v0_5_grouping_test_records.csv`

## 9. Current code health
The following files were checked after the latest repairs and passed syntax compilation:
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.5.py`
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.62.py`
- `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.7.py`

## 10. Immediate next tasks
1. Re-test `v0.5` after the JSON-output path fix to confirm JSON files now go to `json_directory`.
2. Run the same multi-label truth-based tests for:
   - `v0.62`
   - `v0.7`
3. Collect:
   - `v0_62_grouping_test_records.csv`
   - `v0_7_grouping_test_records.csv`
4. Use those CSV files to create Chapter 4 comparison tables.
5. Continue rewriting Chapter 4 in the new process-based style.
6. After Chapter 4 is stable, continue polishing appendices and final thesis formatting.

## 11. Notes for the next thread
If a new thread is opened, the most useful starting actions are:
- read this file first
- inspect the latest CSV test outputs
- continue from Chapter 4 reconstruction and later detector-stage testing
- do not reintroduce heavy version-number narration in the thesis body unless necessary

## 12. Tonight's update (2026-04-02)
### 12.1 New label detector training completed
- A new training config was created:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\PaddleDetection-release-2.8.1\configs\label_det_m_45e.yml`
- This run used:
  - 45 epochs
  - a new output directory: `output/label_det_m_45e`
- Training finished successfully and produced:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\PaddleDetection-release-2.8.1\output\label_det_m_45e\model_final.pdparams`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\PaddleDetection-release-2.8.1\output\label_det_m_45e\best_model.pdparams`

### 12.2 Training log parsing and visualization
- A log parser / plotting script was added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\monitor_training_log.py`
- A one-click training launcher was also added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\start_label_det_45e_training.ps1`
- Parsed training artifacts were generated under:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\training_logs\label_det_m_45e`
- Key generated files:
  - `training_progress.csv`
  - `loss_curve.png`
  - `lr_curve.png`
  - `batch_cost_curve.png`
- Current parsed summary:
  - train rows: 45
  - eval rows parsed: 0
  - last loss: 1.024462
  - last learning rate: 1e-06

### 12.3 Problems encountered during training-log handling
- Problem 1:
  - the first real-time monitor run produced empty CSV files and no curves
- Cause:
  - `train.log` written by PowerShell `Tee-Object` was UTF-16, but the parser initially read it as UTF-8
- Fix:
  - `monitor_training_log.py` was updated to detect and decode UTF-16 / UTF-8 / UTF-8-SIG / GBK logs before parsing
- Result:
  - the same completed training log could be parsed correctly and the curves could be generated afterward

### 12.4 Model export status
- The new trained model was exported successfully to:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\PaddleDetection-release-2.8.1\output_inference\label_det_m_45e`
- Exported files confirmed:
  - `infer_cfg.yml`
  - `model.pdmodel`
  - `model.pdiparams`

### 12.5 Problems encountered during export
- Problem 2:
  - export failed at first with a Windows permission error under `C:\Users\26310\.cache\paddle\to_static_tmp`
- Cause:
  - Paddle tried to create temporary export files under a user cache directory that was not writable in the current run context
- Fix:
  - temporary/cache-related environment variables were redirected into the project workspace
- Problem 3:
  - export still failed in the training environment due to a Paddle static export compatibility issue
- Cause:
  - the training environment was usable for training, but not stable for export in this run
- Fix:
  - export was retried in the dedicated `label_export` environment, consistent with the project's multi-environment split
- Problem 4:
  - the `label_export` environment initially rejected the config because it uses CPU Paddle while config had `use_gpu: true`
- Fix:
  - export was rerun with `use_gpu=false`
- Result:
  - export completed successfully in `label_export`

### 12.6 New code versions using the new model
- Two new runtime versions were created to avoid overwriting previous detector-based versions:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.63.py`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.71.py`
- Their dedicated config files were also created:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\app_config_v063.json`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\app_config_v071.json`
- These new versions:
  - explicitly mention at the top of the file that they use the newly trained `label_det_m_45e` model
  - point to the new exported model directory by default
  - use separate test-record CSV names

### 12.7 New-model inference verification
- The exported `label_det_m_45e` model was used to run a direct detection visualization test on:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\multiple_labels_test\m001.jpg`
- A new visualization output folder was created:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\visual_outputs_new_model`
- Output image confirmed:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\visual_outputs_new_model\m001.jpg`
- Direct inference printed 3 boxes with high confidence, showing that the new exported model can detect label regions and produce box visualization
- A trailing PaddleDetection JSON-saving error appeared after the image had already been saved; this did not invalidate the box-visualization result itself

### 12.8 Thesis-writing guidance produced tonight
- Section `4.3.3` was reviewed and expanded conceptually
- Main recommendation:
  - keep the current data-making and environment-split narrative
  - strengthen it by adding:
    - dataset scale details
    - training parameter details
    - loss / learning-rate curve discussion
    - a natural transition toward later system integration with the trained detector

## 13. Follow-up update (2026-04-08 to 2026-04-09)
### 13.1 Thesis direction clarified further
- The immediate writing focus is still Chapter 4, especially:
  - `4.3.3 数据集制作与标签模型训练`
  - the subsection after it on how the newly trained detector is integrated into later pipeline versions
- Current agreed writing strategy:
  - use process-based narration instead of stacking version numbers
  - use training curves and model comparison evidence, not only console screenshots
  - explicitly explain why the final detector used in the system is the 45-epoch model

### 13.2 How training-log artifacts should be used in the thesis
- The folder
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\training_logs\label_det_m_45e`
  now has a stable role in thesis evidence
- Recommended usage:
  - `loss_curve.png`
    - main figure for showing convergence
  - `lr_curve.png`
    - supporting figure for showing the learning-rate schedule
  - `training_progress.csv`
    - source for quoted numeric values such as initial loss, final loss, and total epochs
  - `train.log`
    - raw record only, mainly for traceability, not the main thesis figure
  - `batch_cost_curve.png`
    - optional engineering-support figure; not necessary in the main body unless discussing runtime fluctuation
  - `evaluation_metrics.csv`
    - currently not useful for thesis evidence because no effective eval rows were parsed in this run

### 13.3 Final model-selection narrative now supported
- Current agreed thesis conclusion:
  - 20-epoch model:
    - used as an early-stage verification model
    - could not produce usable label boxes in later comparison
  - 80-epoch model:
    - used as a longer training reference model
    - exported model exists, but later comparison showed poor label-count matching on the 10-image multi-label test set
  - 45-epoch model:
    - chosen as the final detector used for later system integration
    - reason: it both converged clearly and performed much better in later practical inference comparison
- This should be written as a staged model-selection process, not as arbitrary trial-and-error

### 13.4 Exported-model comparison experiment completed
- A dedicated comparison script was added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\compare_exported_label_models.py`
- Comparison target:
  - `label_det_m_80e`
  - `label_det_m_45e`
- Shared test set:
  - images:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\multiple_labels_test`
  - truth file:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\multiple_labels_test\truth.csv`
- Output directory:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e`
- Key generated files:
  - `model_compare.csv`
  - `summary.txt`
  - per-image visualization folders for both models

### 13.5 Important comparison result already obtained
- The corrected comparison result (same 10 multi-label images, same threshold = 0.5) is:
  - `label_det_m_80e`
    - total images: 10
    - exact-match images: 0
    - exact-match rate: 0.0000
    - mean absolute error: 2.8
    - all 10 images were under-detected
  - `label_det_m_45e`
    - total images: 10
    - exact-match images: 7
    - exact-match rate: 0.7000
    - mean absolute error: 0.3
- This result is currently the strongest evidence supporting the thesis statement that the 45-epoch detector is better suited for the later system versions than the 80-epoch detector
- The summary file containing this conclusion is:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e\summary.txt`

### 13.6 Problem found and fixed during comparison
- Problem 5:
  - the first version of the comparison script counted all returned raw boxes instead of only threshold-valid boxes
- Cause:
  - direct detector output included many low-confidence candidate boxes, while thesis comparison should be based on the same threshold rule as visualization and actual use
- Fix:
  - `compare_exported_label_models.py` was updated so that counting only uses boxes whose confidence is greater than or equal to the chosen threshold
- Result:
  - the comparison summary became consistent with the saved visualization results

### 13.7 Visualization evidence currently available
- New-model visualization directory:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\visual_outputs_new_model`
- Confirmed files:
  - `m010.jpg`
    - 45-epoch model on `processed_directory\m010.jpg`
  - `m001.jpg`
    - currently stores the latest saved result in that folder
  - `m001-45.jpg`
    - intended as the 45-epoch model result for `processed_directory\m001.jpg`
  - `m001-80.jpg`
    - intended as the 80-epoch model result for `processed_directory\m001.jpg`
- Important note:
  - there was confusion caused by image overwriting / viewer caching when repeatedly saving `m001.jpg`
  - for later thesis use, it is safer to generate comparison images directly from the stable directory:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e`
  - in other words, the `model_compare_outputs` directory should be treated as the canonical evidence source for 80e vs 45e visualization

### 13.8 Current best thesis claim that can be defended
- The safest currently supportable statement is:
  - the 20-epoch detector failed to produce usable boxes
  - the 80-epoch detector under-detected on the 10-image multi-label comparison set
  - the 45-epoch detector achieved 7/10 correct label-count matches on the same test set
  - therefore the 45-epoch detector was selected as the formal detector integrated into later system versions
- Do not currently claim:
  - that the 80-epoch model produced better visual redundancy under the standard threshold
  - that 45e is better because of offline mAP, since no complete mAP evidence has yet been organized in the thesis materials

### 13.9 Recommended next tasks for the next thread
1. Rewrite `4.3.3` using the already agreed expanded structure:
   - dataset making
   - environment split
   - training setup
   - loss / learning-rate curve analysis
   - staged choice among 20e / 80e / 45e
2. Add a small comparison table in the thesis:
   - 20e / 80e / 45e
   - role, observed effect, whether chosen as final model
3. Add a detector-comparison table using:
   - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e\model_compare.csv`
   - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e\summary.txt`
4. If needed, regenerate final thesis-use images with stable names copied from:
   - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e\label_det_m_45e`
   - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e\label_det_m_80e`
5. Then continue to the next thesis subsection on detector integration and later multi-label system optimization

### 13.10 Thread handoff summary
- The next conversation thread should treat this section as the current handoff baseline
- The project is now in a mixed phase:
  - thesis Chapter 4 still needs focused writing and polishing
  - code-side detector training, export, and basic comparison have already advanced enough to support thesis claims
- The most important already-finished milestones are:
  - a new 45-epoch detector was trained, exported, and connected to new runtime variants
  - `v0.63` and `v0.71` were created specifically to use the new detector
  - training-log parsing and visualization scripts were added
  - a 45e vs 80e exported-model comparison experiment was completed
  - the current evidence supports selecting 45e as the final detector used in later system versions
- The most important things not yet fully finished are:
  - rewriting the thesis text around these new results in a polished way
  - deciding which detector comparison figures and tables will appear in the final thesis body
  - further multi-label system testing with the newer detector-backed runtime variants if needed

### 13.11 Suggested working order for the next thread
- Step 1:
  - reopen and continue the thesis first, especially Section `4.3.3`
- Step 2:
  - organize a formal comparison table for 20e / 80e / 45e model selection
- Step 3:
  - organize a formal table and figure set for 45e vs 80e detector performance on the 10-image test set
- Step 4:
  - only after the thesis wording is stabilized, return to program-side refinements or more tests
- Reason for this order:
  - the code-side evidence is already strong enough for writing
  - the current bottleneck is no longer model training itself, but converting completed work into clear thesis presentation

### 13.12 Notes to carry into the next thread
- When discussing the detector comparison in the thesis, prefer the wording:
  - "staged model selection"
  - "engineering availability and practical comparison result"
  - "45e was selected as the formal detector for later system integration"
- Avoid over-claiming unsupported metrics
  - do not treat this run as having a complete offline mAP comparison record
  - do not claim 80e superiority based on ad hoc visualization attempts
- Preferred evidence sources for next-thread work:
  - training curves:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\training_logs\label_det_m_45e`
  - stable detector comparison:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\model_compare_outputs\label_det_80e_vs_45e`
  - runtime code versions using the new model:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.63.py`
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.71.py`

## 14. v1.0 release-engineering update (2026-04-15)
### 14.1 New formal release line
- A new formal release-oriented code line was created:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v1.0.py`
- Related release-oriented config and launch files were created:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\app_config_v1.0.json`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\start_release_v1_0.ps1`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\start_release_v1_0.bat`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\start_release_v1_0_debug.ps1`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\start_release_v1_0_debug.bat`
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\prepare_release_v1_0_portable.ps1`
- The portable release folder is generated to:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\release_candidates\Mr6_Auto_OCR_Pipeline_v1.0`

### 14.2 Main engineering purpose of v1.0
- `v1.0` is not just another development script iteration.
- It is the first release-oriented branch intended to support:
  - portable use outside the original project directory
  - GUI-based demonstration for thesis Chapter 5
  - later conversion into a more executable-like packaged application
- This work is directly relevant for the thesis theme:
  - “自动化标签识别系统的工程化封装与应用演示”

### 14.3 Path portability problem and fix
- Problem:
  - old runtime behavior still depended on absolute local paths such as `E:/Mr.6_Auto_OCR_PipelineWithCodeX/...`
- Cause:
  - existing config JSON files overrode relative defaults in code
- Fix:
  - `v1.0` introduced a release-base-directory concept
  - portable relative paths are now used for:
    - watch folder
    - processed folder
    - error folder
    - JSON output folder
    - TXT output folder
    - visualization output folder
    - truth CSV
    - test record CSV
    - detector model directory
  - `app_config_v1.0.json` now stores relative paths for portability

### 14.4 Launcher problems and fixes
- Problem 1:
  - double-clicking the release script seemed to “flash and exit”
- Initial cause:
  - `.ps1` execution behavior was not a reliable click-to-run path under Windows
- Fix:
  - added `start_release_v1_0.bat` as the preferred clickable launcher

- Problem 2:
  - the launcher selected the wrong Python interpreter:
    - `C:\Users\26310\AppData\Local\Programs\Python\Python313\python.exe`
  - this caused:
    - `ModuleNotFoundError: No module named 'paddleocr'`
- Cause:
  - Python discovery order did not prioritize the intended runtime environment strongly enough
- Fix:
  - release launchers were updated to prioritize:
    - `E:\Anaconda3\envs\ocr_runtime\python.exe`
  - debug launchers were also added to preserve error output in:
    - `logs\startup_debug.log`

### 14.5 Release dependency completeness problem and fix
- Problem:
  - real-time monitoring in the release folder failed with:
    - `标签检测模型加载失败: No module named 'infer'`
- Cause:
  - the release folder originally copied only the exported detector model, but not PaddleDetection’s deploy-time Python inference helper code
- Fix:
  - release preparation was updated to copy:
    - `PaddleDetection-release-2.8.1\deploy\python`
  - verified critical file in release folder:
    - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\release_candidates\Mr6_Auto_OCR_Pipeline_v1.0\PaddleDetection-release-2.8.1\deploy\python\infer.py`

### 14.6 Real-time monitoring image-read problem and fix
- Problem:
  - in watch mode, copied images were repeatedly reported as:
    - `无法读取图片文件 ...`
- Cause:
  - watchdog reacted to file creation before file copying was fully complete
  - `cv2.imread()` was called too early
- Fix:
  - image-ready waiting logic was added:
    - check file exists
    - check file size stabilizes
    - retry image loading before giving up
- Thesis significance:
  - this is a concrete engineering reliability issue in real-time monitoring mode
  - useful as Chapter 5 material when describing the transition from prototype behavior to release-grade behavior

### 14.7 Manual / automatic output logic problem and fix
- Problem 1:
  - the GUI exposed “手动输出 / 自动输出”, but the behavior did not actually change correctly
- Concrete manifestation:
  - in watch mode, manual-output mode still auto-saved results
  - in single-image mode, the old branch structure around manual output was functionally meaningless
- Cause:
  - the output-mode state was passed through the code, but not properly enforced when writing JSON/TXT/visualization outputs
- Fix:
  - output saving logic was rewritten so that:
    - `自动输出` writes JSON / TXT / visualization directly
    - `手动输出` skips automatic output writing

- Problem 2:
  - the old manual-save button only covered the latest text summary and did not distinguish JSON from TXT
- Fix:
  - the manual-save UI was redesigned into:
    - `手动保存当前 JSON`
    - `手动保存当前 TXT`
    - `批量保存监听结果`

- Problem 3:
  - in watch mode, manual output still needed per-image separated saving rather than mixing multiple images together
- Fix:
  - a pending manual-output queue was added for watch mode
  - each monitored image now stores:
    - `image_name`
    - readable summary text
    - structured result payload
  - batch-saving now writes per-image outputs such as:
    - `m001_识别结果.json`
    - `m001_OCR_results.txt`
    - `m002_识别结果.json`
    - `m002_OCR_results.txt`

### 14.8 GUI layout iteration problems and lessons
- Problem:
  - the first `v1.0` GUI revisions were not good enough
  - several iterations produced:
    - crowded left control panel
    - clipped Chinese labels
    - hidden browse buttons
    - layouts worse than the earlier accepted `v0.71` feel
- Fixes applied across iterations:
  - changed the overall page to left control panel + right output panel
  - widened the left control region
  - adjusted path input rows repeatedly
  - shortened browse button text to `选择`
  - tuned panel stretching and scrolling behavior
- Important thesis lesson:
  - engineering packaging is not only “making it run outside the project folder”
  - it also requires multiple GUI usability corrections based on real runtime screenshots and user feedback

### 14.9 Release build script robustness problem and fix
- Problem:
  - release regeneration sometimes failed because debug log files such as `startup_debug.log` were still locked
- Fix:
  - `prepare_release_v1_0_portable.ps1` was updated so it can:
    - tolerate locked items in the release directory
    - refresh releasable files while keeping locked logs when necessary

### 14.10 Current status of v1.0
- `v1.0` is now the first formal release-oriented branch.
- It currently supports:
  - relative-path configuration
  - portable release-folder generation
  - GUI launch through `bat` / `ps1`
  - detector inference in release mode
  - watch-mode image-read stabilization
  - corrected manual / automatic output behavior
  - per-image manual batch-saving for watch mode
- Remaining next-stage goals:
  - continue GUI polishing
  - continue function regression testing
  - package the release folder further into a real executable application if feasible

### 14.11 Code-side regression verification completed
- A direct code-side regression check was run against `v1.0` using the `ocr_runtime` environment.
- The regression did not rely only on GUI clicking; it directly executed the underlying single-image worker and watch-mode handler logic.

- Test source image used:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\multiple_labels_test\m001.jpg`

- Test cases covered:
  - single-image mode with automatic output
  - single-image mode with manual output
  - watch-mode handler with automatic output
  - watch-mode handler with manual output

- Verified results:
  - single-image automatic output:
    - success = `True`
    - JSON output files = `1`
    - TXT output files = `1`
    - visualization files = `1`
    - processed image count = `1`

  - single-image manual output:
    - success = `True`
    - JSON output files = `0`
    - TXT output files = `0`
    - visualization files = `0`
    - processed image count = `1`
    - result payload available for manual save = `True`
    - readable summary text length > `0`

  - watch-mode automatic output:
    - success = `True`
    - JSON output files = `1`
    - TXT output files = `1`
    - visualization files = `1`
    - processed image count = `1`
    - pending manual-output queue count = `0`

  - watch-mode manual output:
    - success = `True`
    - JSON output files = `0`
    - TXT output files = `0`
    - visualization files = `0`
    - processed image count = `1`
    - pending manual-output queue count = `1`
    - pending result payload available = `True`

- Interpretation:
  - the current `v1.0` code-side logic now matches the intended output-mode design
  - automatic output and manual output are no longer behaving identically
  - watch-mode manual output is now capable of accumulating per-image pending results for later batch saving

- Important limitation:
  - this regression was code-side / logic-side, not a full end-user GUI interaction sweep
  - final confidence still requires additional GUI-side confirmation of:
    - button state correctness
    - manual-save button behavior
    - watch-mode batch-save interaction

## 15. v1.0 standalone packaging and installer build (2026-04-16)

### 15.1 Goal of this stage
- The original `v1.0` release folder could already run as a portable package, but it still depended on an external Python environment.
- The next engineering goal was to move from:
  - portable release folder
  to:
  - self-contained standalone package
  - installable Windows setup program

### 15.2 Packaging route decision
- Multiple packaging paths were considered:
  - directly freezing everything into a single `.exe`
  - bundling the validated runtime environment and then wrapping it with an installer
- Final decision:
  - do not force `PaddleOCR + PaddlePaddle + PyQt5 + pyzbar` into a single frozen executable at this stage
  - instead use the safer route:
    - build a standalone folder with bundled `ocr_runtime`
    - then create a Windows installer from that standalone folder
- Reason:
  - the current dependency set is heavy and includes detector inference, OCR, GUI, barcode decoding and multiple compiled dependencies
  - bundling the already-validated runtime environment is closer to the tested execution path and is more suitable for a graduation-project release

### 15.3 Toolchain investigation results
- The following facts were confirmed locally:
  - `ocr_runtime` environment exists
  - `conda-pack` is available at:
    - `E:\Anaconda3\Scripts\conda-pack.exe`
  - `PyInstaller` is not currently installed
  - `Nuitka` is not currently installed
  - `Inno Setup` was not initially installed and had to be installed separately
- A rough size check was also performed:
  - `ocr_runtime` environment size is about `3.09 GB`
  - portable `v1.0` release folder size is about `100 MB`
- Implication:
  - the final installer would be relatively large
  - but this path would be much more robust than a risky one-file freeze attempt

### 15.4 Code and script preparation completed
- To support future standalone deployment, the `v1.0` launch scripts were updated:
  - `start_release_v1_0.ps1`
  - `start_release_v1_0_debug.ps1`
- Important improvement:
  - both launchers now preferentially look for:
    - `runtime_env\python.exe`
    - `runtime_env\Scripts\python.exe`
  - before falling back to external system or conda Python
- This means the same launcher logic now supports both:
  - the ordinary portable release folder
  - the new self-contained standalone release folder

### 15.5 New packaging assets added
- New standalone-build script:
  - `build_release_v1_0_standalone.ps1`
- New Inno Setup installer script:
  - `installer_assets\Mr6_Auto_OCR_Pipeline_v1.0.iss`
- New packaging guidance documents:
  - `release_assets\Mr6_Auto_OCR_Pipeline_v1.0\PACKAGING_NOTES.zh-CN.md`
  - `release_assets\Mr6_Auto_OCR_Pipeline_v1.0\PACKAGING_NOTES.en.md`
- Existing release generator also continued to be used:
  - `prepare_release_v1_0_portable.ps1`

### 15.6 First standalone-build issue and fix
- Problem:
  - the first version of `build_release_v1_0_standalone.ps1` incorrectly tried to run:
    - `python -m conda_pack`
  - this failed with:
    - `No module named conda_pack.__main__`
- Cause:
  - `conda-pack` on this machine is installed as an executable entry point, not as a directly runnable `python -m` module
- Fix:
  - the script was changed to call:
    - `E:\Anaconda3\Scripts\conda-pack.exe`
  - and to build the runtime archive using:
    - `--format zip`
- Result:
  - the standalone build script successfully packed the `ocr_runtime` environment

### 15.7 Standalone release folder successfully generated
- After the fix, the following command completed successfully:
  - `powershell -ExecutionPolicy Bypass -File .\build_release_v1_0_standalone.ps1`
- The build process completed these stages:
  - rebuilding the portable `v1.0` release folder
  - packing `ocr_runtime` with `conda-pack`
  - copying the portable release into a new standalone directory
  - expanding the packed runtime into `runtime_env`
  - running `conda-unpack`
- Output directory:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_standalone`

### 15.8 Standalone release test result
- The standalone folder was manually tested after generation.
- Result:
  - it could launch and run without relying on the original external runtime arrangement in the previous way
  - no blocking issue was reported before moving to installer creation

### 15.9 Inno Setup compile issue 1 and fix
- Problem:
  - the initial Inno Setup script used:
    - `compiler:Languages\ChineseSimplified.isl`
  - but this file was not present in the installed `Inno Setup 6` language directory
- Symptom:
  - compile aborted at the language-loading stage
- Fix:
  - the Chinese language entry was removed from:
    - `installer_assets\Mr6_Auto_OCR_Pipeline_v1.0.iss`
  - the installer was temporarily switched to English-only interface
- Reasoning:
  - installer functionality matters more than installer UI language at this stage
  - multilingual installer UI can be revisited later if necessary

### 15.10 Inno Setup compile issue 2 and fix
- Problem:
  - during compression of the standalone directory, the installer compile aborted again
  - the long file paths inside:
    - `runtime_env\Lib\site-packages\modelscope\...`
    and other large packages caused Windows path-length pressure
- Investigation:
  - the longest file paths in the standalone tree were measured and found to reach about:
    - `280` characters
  - since the source directory prefix was also very long, Inno Setup was effectively pushed into long-path failure territory
- Fix:
  - instead of changing the runtime contents immediately, a shorter virtual drive path was created using:
    - `subst R: E:\Mr.6_Auto_OCR_PipelineWithCodeX\release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_standalone`
  - then the Inno Setup script source directory was temporarily changed from the long absolute path to:
    - `R:\`
- Result:
  - the source-path length was greatly reduced
  - the installer compile completed successfully

### 15.11 Installer successfully built
- Final outcome:
  - the Windows installer was successfully compiled after shortening the source path with `subst`
- Installer output directory:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\release_installers`
- This means the project has now reached a new stage:
  - from script-only prototype
  - to portable release folder
  - and finally to an installable Windows release package

### 15.12 Important engineering lessons from this stage
- Packaging work is not “just pressing one compile button”.
- The actual engineering difficulties came from:
  - runtime-environment bundling
  - launcher portability
  - installer language compatibility
  - Windows path-length limits
  - large third-party dependency trees
- These are valuable thesis materials because they reflect real engineering deployment issues rather than only algorithm or model issues.

### 15.13 Current packaging-related outputs
- Main release script:
  - `prepare_release_v1_0_portable.ps1`
- Standalone-build script:
  - `build_release_v1_0_standalone.ps1`
- Installer script:
  - `installer_assets\Mr6_Auto_OCR_Pipeline_v1.0.iss`
- Portable release folder:
  - `release_candidates\Mr6_Auto_OCR_Pipeline_v1.0`
- Standalone release folder:
  - `release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_standalone`
- Installer output folder:
  - `release_installers`

### 15.14 Suggested next-stage tasks
- Verify the installed version after real installation:
  - GUI launch
  - single-image recognition
  - watch-mode startup
- Continue polishing:
  - installer metadata
  - release naming
- final GitHub Release assets
- Write thesis content for the new engineering/deployment chapter based on this packaging process

## 16. Adaptive-strategy retuning and retest update (2026-04-22)

### 16.1 New tuned adaptive-strategy branch
- A new tuned branch was created from the detector-integrated adaptive version:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v0.71_tuned.py`
- Main purpose:
  - improve multi-label count prediction on the 10-image test set
  - specifically outperform `v0.63` in practical label-count comparison

### 16.2 Core strategy adjustment
- The tuned version keeps the adaptive-profile framework of `v0.71`, but adds a new tail-box refinement rule after candidate selection.
- Main added logic:
  - if the third detected box is much weaker than the first two, suppress likely redundant detection (`3 -> 2`)
  - if a fourth detected box has sufficiently strong confidence, keep it instead of forcing the result back toward `target_boxes = 3`
- Practical motivation:
  - the original `v0.71` had a strong tendency to bias 2-label and 4-label images toward 3 predicted labels
  - the new rule reduces that bias without retraining the detector

### 16.3 Diagnostic scripts added
- A dedicated diagnostic script was added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\diagnose_v071_adaptive.py`
- Purpose:
  - inspect per-image adaptive-profile outputs and confirm how many valid label boxes each profile produces
  - verify whether the detector itself can already output 2 / 3 / 4 boxes before later post-processing

- A quick evaluation script was also added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\evaluate_v071_tuned_counts.py`
- Purpose:
  - compute a direct label-count summary for the 10-image multi-label set

### 16.4 Important diagnostic conclusion
- Diagnosis showed that the detector itself could already produce:
  - 2 valid boxes on `m002.png`
  - 4 valid boxes on `m003.jpg`
  - 4 valid boxes on `m009.jpg`
- Therefore the bottleneck was not mainly the detector model itself, but the adaptive candidate-selection / tail-box decision logic.

### 16.5 Tuned evaluation result
- Evaluation output:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\v0_71_tuned_eval.csv`
- Result summary:
  - total images: 10
  - exact-match images: 8
  - exact-match rate: 0.8000
  - mean absolute error: 0.3000
- Comparison against the previous practical `v0.63` result:
  - `v0.63`: 7 / 10 exact-match
  - `v0.71_tuned`: 8 / 10 exact-match
- Interpretation:
  - `v0.71_tuned` is now better than `v0.63` on exact label-count correctness
  - however, MAE remained `0.3000`, because the tuned version reduced the number of wrong images but one remaining wrong case still introduced a larger single-image error

### 16.6 Same-format batch test CSV for tuned version
- A batch runner was added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\run_v071_tuned_grouping_test.py`
- Output file:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\v0_71_tuned_grouping_test_records.csv`
- This CSV uses the same field structure as the earlier grouping-test record files:
  - `recorded_at`
  - `image_name`
  - `actual_label_count`
  - `predicted_label_count`
  - `label_count_correct`
  - `over_split`
  - `over_merge`
  - `success`
  - `elapsed_seconds`
  - `error`

### 16.7 Same-protocol retest for v0.63
- To avoid using mixed timing sources, `v0.63` was re-run with a same-style batch test script:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\run_v063_grouping_test_retest.py`
- New output file:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\v0_63_grouping_test_records_retest.csv`
- Retest summary:
  - total images: 10
  - successful images: 10
  - exact-match images: 7
  - exact-match rate: 0.7000
  - oversplit images: 1
  - overmerge images: 2
  - mean absolute error: 0.3000
  - average processing time: 2.9241 s

### 16.8 v0.63 vs v0.71_tuned comparison table generated
- A comparison builder script was added:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\build_v063_vs_v071_tuned_compare.py`
- Output file:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\v0_63_vs_v0_71_tuned_compare.csv`
- CSV fields:
  - `image_name`
  - `actual_label_count`
  - `v0_63_predicted_label_count`
  - `v0_71_predicted_label_count`
  - `v0_63_label_count_correct`
  - `v0_71_label_count_correct`
  - `v0_63_elapsed_seconds`
  - `v0_71_elapsed_seconds`
  - `note`
- Current note categories already present in the file:
  - `both_correct`
  - `v0.71_better`
  - `v0.71_worse`

### 16.9 Why exact-match improved but MAE did not decrease
- Current explanation agreed during analysis:
  - `v0.71_tuned` reduced the number of wrong images overall
  - but one remaining oversplit case introduced a larger single-image count error
  - therefore:
    - exact-match rate increased
    - MAE stayed unchanged
- This is a reasonable thesis discussion point and should not be treated as an error in metric calculation.

### 16.10 v1.0 synchronized with tuned adaptive logic
- The tuned adaptive box-refinement logic was also ported into:
  - `E:\Mr.6_Auto_OCR_PipelineWithCodeX\auto_ocr_pipeline_v1.0.py`
- Meaning:
  - the current release-oriented branch now inherits the improved adaptive-threshold behavior
  - later repackaging / installer rebuilding should use this updated `v1.0`

### 16.11 Repository synchronization status clarified
- A later remote check confirmed that GitHub `main` already contains the organized appendix support materials:
  - `appendix1_code_overview`
  - `appendix2_dataset_overview`
  - `appendix3_training_and_model_compare`
  - `appendix4_test_records`
- Meaning:
  - the earlier local-only mismatch was caused by the local repository still being aligned to an older branch snapshot
  - the thesis statements about GitHub-hosted appendix materials are now broadly consistent with the remote repository state
- Remaining repository-side work is therefore focused on:
  - syncing the local working copy to `main`
  - adding the newer release-oriented `v1.0` files and packaging scripts
  - keeping the release pipeline consistent with the tuned adaptive-threshold results

### 16.12 Release-material supplement prepared
- To close the gap between thesis Chapter 5 and the repository, a release-oriented supplement set was prepared for upload:
  - `auto_ocr_pipeline_v1.0.py`
  - `app_config_v1.0.json`
  - `prepare_release_v1_0_portable.ps1`
  - `build_release_v1_0_standalone.ps1`
  - `start_release_v1_0.ps1`
  - `start_release_v1_0.bat`
  - `start_release_v1_0_debug.ps1`
  - `start_release_v1_0_debug.bat`
  - `installer_assets\\Mr6_Auto_OCR_Pipeline_v1.0.iss`
  - `release_assets\\Mr6_Auto_OCR_Pipeline_v1.0\\*`
- The Inno Setup script was also revised to avoid the previous hard-coded `R:\` source path and now points to the relative standalone release directory under `release_candidates`.
