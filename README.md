# Mr.6's Auto OCR Pipeline

`Mr.6's Auto OCR Pipeline` 是一个面向标签图像场景的本地自动识别系统项目，核心任务包括标签区域处理、OCR 文字识别、条码/二维码识别、多标签分离、结构化结果输出，以及最终的 Windows GUI 与发布工程化。

本公开仓库以“项目展示 + 论文支撑材料归档”为主要目标，保留了项目从原型验证到发布整理过程中的代表性源码版本、附录材料、实验记录、模型比较结果与发布资源，便于读者了解实现路径并复核论文中的主要实验结论。

## 仓库主要内容

当前仓库主要包含四类公开材料：

- 从早期原型到 `v1.0` 发布版主线的代表性源码版本。
- 用于支撑论文的附录型实验材料。
- 标签检测模型训练与模型比较结果。
- Windows 发布、打包与安装器相关资源。

## 主要版本路径

仓库中较重要的脚本版本包括：

- `auto_ocr_pipeline_v0.5.py`
  - OCR 聚类分组与规则修正阶段。
- `auto_ocr_pipeline_v0.63.py`
  - 检测优先、聚类回退的系统阶段。
- `auto_ocr_pipeline_v0.71.py`
  - 早期候选框自适应选择探索阶段。
- `auto_ocr_pipeline_v0.71_tuned.py`
  - 基于原始 10 张多标签测试图调优得到的历史 tuned 分支。
- `auto_ocr_pipeline_v0.7_retuned.py`
  - 在 50 张扩样本验证后新建的 retuned 分支，用于减少检测模型输出与系统最终输出之间的系统级损耗。
- `auto_ocr_pipeline_v1.0.py`
  - 面向公开发布整理的主线版本，现已同步 `v0.7_retuned` 的候选框选择优化逻辑。

如果你只想优先查看最接近最终交付形态的代码，建议从以下文件开始：

- `auto_ocr_pipeline_v1.0.py`
- `app_config_v1.0.json`

## 公开实验重点

### 1. 扩充后的多标签验证（`enhanced50`）

原始多标签实验基于 10 张测试图完成。为配合论文修订，本项目进一步构建了包含 50 张增强多标签图像的测试集，并严格沿用原有评估口径完成扩样本复核。

50 张测试集上的关键系统级结果如下：

- `v0.5`：
  - exact-match `14/50`
  - MAE `1.2000`
- `v0.63`：
  - exact-match `36/50`
  - MAE `0.2800`
- `v0.71_tuned` 历史 tuned 分支：
  - exact-match `9/50`
  - MAE `1.4800`
  - 说明原先在小样本上调出的规则未能稳定泛化到扩样本测试集。
- `v0.7_retuned`：
  - exact-match `47/50`
  - MAE `0.0600`
  - 将系统级结果重新拉回到 45 轮检测模型本身的强计数能力附近。

### 2. 扩样本条件下的标签检测模型比较

在同一套 50 张多标签测试图像上，检测模型本身的计数结果如下：

- `20` 轮 / early 模型：
  - exact-match `0/50`
  - MAE `2.8800`
- `80` 轮模型：
  - exact-match `0/50`
  - MAE `2.8200`
- `45` 轮模型：
  - exact-match `47/50`
  - MAE `0.0600`

这也是后续系统分支继续采用 45 轮检测模型作为核心标签检测模型的主要原因。

## 附录材料导航

公开论文支撑材料统一整理在 `appendix_materials/` 目录下。

### `appendix_materials/appendix1_code_overview/`

用于说明代表性源码文件及其与论文正文的对应关系。

### `appendix_materials/appendix2_dataset_overview/`

用于说明标签检测数据集的结构、样例与整理方式。

### `appendix_materials/appendix3_training_and_model_compare/`

用于保存训练说明与检测模型比较结果。

其中重要目录包括：

- `model_compare_45e_vs_80e/`
  - 历史 10 张测试集上的 45 轮与 80 轮模型比较结果。
- `model_compare_three_models/`
  - 历史 10 张测试集上的三模型比较结果。
- `model_compare_45e_vs_80e_enhanced50/`
  - 50 张扩样本测试集上的 45 轮与 80 轮模型比较结果。
- `model_compare_three_models_enhanced50/`
  - 50 张扩样本测试集上的 early / 80e / 45e 三模型比较结果。
- `truth_table/`
  - 历史 10 张测试集真值表。
- `truth_table_enhanced50/`
  - 50 张扩样本测试集真值表。

### `appendix_materials/appendix4_test_records/`

用于保存系统级测试记录与对比结果。

历史 10 张测试材料仍然保留：

- `4_3_multi_label_grouping_tests/`
- `4_4_label_detector_integration_tests/`
- `4_5_adaptive_threshold_tests/`

本轮论文修订新增的 50 张测试材料目录包括：

- `4_3_multi_label_grouping_tests_enhanced50/`
  - `v0.5` 在 50 张测试集上的结果。
- `4_4_label_detector_integration_tests_enhanced50/`
  - `v0.63` 在 50 张测试集上的结果，以及 `v0.5 vs v0.63` 对比结果。
- `4_5_candidate_selection_optimization_tests_enhanced50/`
  - `v0.71_tuned` 在扩样本上的失稳结果。
  - `v0.7_retuned` 的新结果。
  - `v0.63 vs v0.7_retuned` 对比结果。
  - 以及该测试集对应的真值表与样本清单。

### `appendix_materials/appendix5_release_materials/`

用于保存发布版映射说明与打包整理支撑材料。

## 发布材料

仓库中保留了发布版整理与打包相关资源，包括：

- `release_assets/`
- `installer_assets/`
- `prepare_release_v1_0_portable.ps1`
- `build_release_v1_0_standalone.ps1`
- `prepare_release_v1_0_retuned_portable.ps1`
- `build_release_v1_0_retuned_standalone.ps1`
- `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0_retuned.iss`

其中，`v1.0 retuned` 路线已经把 `v0.7_retuned` 的候选框选择优化逻辑同步回发布主线，并按下列经验成功完成重新打包：

- 打包前清理 standalone 环境冗余文件；
- 使用 `subst R:` 缩短路径；
- 从缩短路径后的 standalone 目录执行 Inno Setup 编译。

## 建议阅读顺序

如果你希望快速了解项目全貌，推荐按以下顺序阅读：

1. `development_progress.md`
2. `auto_ocr_pipeline_v0.5.py`
3. `auto_ocr_pipeline_v0.63.py`
4. `auto_ocr_pipeline_v0.7_retuned.py`
5. `auto_ocr_pipeline_v1.0.py`
6. `appendix_materials/`

## 仓库维护者

Repository owner: [Sixmeister](https://github.com/Sixmeister)