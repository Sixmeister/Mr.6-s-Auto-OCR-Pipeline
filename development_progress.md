# 项目开发进展

本文档用于概述 `Mr.6's Auto OCR Pipeline` 的公开开发脉络，并突出展示对仓库读者和论文支撑材料最重要的阶段性结果。

## 1. 项目目标

本项目旨在构建一套面向标签图像场景的本地自动识别流程，核心任务包括：

- 标签区域检测与分离；
- OCR 文字识别；
- 条码与二维码识别；
- 多标签分组；
- 结果结构化输出；
- Windows GUI 集成与发布工程化。

## 2. 主要公开开发阶段

### 阶段一：早期 OCR 与码识别原型验证

项目早期主要完成了本地 OCR 与码识别链路的验证，并形成了最初的自动处理流程。

代表文件：

- `auto_ocr_pipeline_v0.1.py`

### 阶段二：GUI 引入

在基础识别链路可运行后，项目引入了桌面图形界面，以便进行人工测试、路径配置与结果查看。

代表文件：

- `auto_ocr_pipeline_v0.2gui.py`

### 阶段三：基于 OCR 聚类的多标签分组

随着多标签图像变得重要，项目引入了基于 OCR 文本框空间关系的聚类分组方案，并加入了误拆分、误合并的规则修正逻辑。

代表文件：

- `auto_ocr_pipeline_v0.4.py`
- `auto_ocr_pipeline_v0.5.py`

历史 10 张测试结果：

- `v0.5`：exact-match `2/10`，原表未单列 MAE，平均耗时 `1.3482 s`

扩样本 50 张测试结果：

- `v0.5`：exact-match `14/50`，MAE `1.2000`，平均耗时 `1.4352 s`

### 阶段四：检测优先的系统集成

项目随后从“先识别、后分组”转向“先检测标签区域，再分别识别每个标签区域”。

这一阶段主要引入了：

- 检测优先流程；
- 检测框过滤；
- 检测不可用时回退到聚类分组。

代表文件：

- `auto_ocr_pipeline_v0.63.py`

历史 10 张测试结果：

- `v0.63`：exact-match `7/10`，MAE `0.3000`

扩样本 50 张测试结果：

- `v0.63`：exact-match `36/50`，MAE `0.2800`，平均耗时 `2.5564 s`

### 阶段五：历史自适应候选策略分支

项目后续曾围绕原始 10 张多标签测试图，对候选框自适应选择与 tuned 规则做过进一步探索。

代表文件：

- `auto_ocr_pipeline_v0.71.py`
- `auto_ocr_pipeline_v0.71_tuned.py`

历史 10 张测试结果：

- `v0.71_tuned`：exact-match `8/10`，MAE `0.3000`

但扩样本 50 张验证结果显示，原有的小样本 tuned 规则未能稳定泛化：

- `v0.71_tuned` 在 50 张测试集上：exact-match `9/50`，MAE `1.4800`

因此，不再适合将该历史 tuned 分支直接作为扩样本验证后的最终论文结论。

### 阶段六：`v0.7_retuned` 候选框选择优化分支

为了保留历史 `v0.71_tuned` 分支，同时继续提升扩样本结果，项目新建了 `v0.7_retuned` 分支。

该分支重点解决：

- 检测器接入到本地项目根目录的路径问题；
- 检测模型输出与系统最终输出之间的系统级损耗；
- 50 张扩样本条件下的候选框过滤与选择重调优。

代表文件：

- `auto_ocr_pipeline_v0.7_retuned.py`

扩样本 50 张测试结果：

- `v0.7_retuned`：exact-match `47/50`，MAE `0.0600`，平均耗时 `3.4147 s`

与同一测试集上的 `v0.63` 相比：

- `v0.63`：exact-match `36/50`，MAE `0.2800`
- `v0.7_retuned`：exact-match `47/50`，MAE `0.0600`

这一阶段最重要的结论不是“系统超过了检测模型本身”，而是系统集成策略已经被优化到能够更好地保留 45 轮检测模型原有的强计数能力。

### 阶段七：检测模型比较与模型选择

项目还在统一真值表与统一统计口径下，对多个导出的标签检测模型进行了比较。

历史 10 张测试结果：

- early 模型：exact-match `0/10`
- `80e` 模型：exact-match `0/10`
- `45e` 模型：exact-match `7/10`

扩样本 50 张测试结果：

- early 模型：exact-match `0/50`，MAE `2.8800`
- `80e` 模型：exact-match `0/50`，MAE `2.8200`
- `45e` 模型：exact-match `47/50`，MAE `0.0600`

这也是后续系统版本持续采用 45 轮检测模型作为核心模型的原因。

### 阶段八：发布工程化与 `v1.0`

在主要识别链路逐步稳定之后，项目进入发布整理阶段，开始面向 Windows 桌面交付进行工程化处理。

代表文件：

- `auto_ocr_pipeline_v1.0.py`

这一阶段主要完成了：

- 发布目录整理；
- standalone 运行环境准备；
- Windows 安装器生成；
- GUI 与路径配置的发布化调整。

验证成功的打包路径包括：

- 通过 `build_release_v1_0_standalone.ps1` 清理 standalone 环境冗余文件；
- 使用 `subst R:` 缩短路径；
- 在缩短后的路径下执行 Inno Setup 编译。

## 3. 公开附录材料

公开论文支撑材料统一整理在 `appendix_materials/` 下。

重要目录包括：

- `appendix1_code_overview/`
- `appendix2_dataset_overview/`
- `appendix3_training_and_model_compare/`
- `appendix4_test_records/`
- `appendix5_release_materials/`

其中，本轮论文修订新增的关键目录包括：

- `appendix3_training_and_model_compare/model_compare_45e_vs_80e_enhanced50/`
- `appendix3_training_and_model_compare/model_compare_three_models_enhanced50/`
- `appendix3_training_and_model_compare/truth_table_enhanced50/`
- `appendix4_test_records/4_3_multi_label_grouping_tests_enhanced50/`
- `appendix4_test_records/4_4_label_detector_integration_tests_enhanced50/`
- `appendix4_test_records/4_5_candidate_selection_optimization_tests_enhanced50/`

历史 10 张测试材料仍与新 50 张材料并列保留，以便追溯项目演进路径。

## 4. 当前公开仓库状态

当前仓库的公开整理方式主要面向以下用途：

- 代表性源码版本归档；
- 论文附录材料支撑；
- 检测模型比较结果公开；
- 发布与安装资源说明。

本地内部接力日志不属于公开仓库内容。公开读者应优先查看：

- `README.md`
- `development_progress.md`
- `appendix_materials/`

## 5. 建议阅读入口

如果你希望快速了解仓库主要内容，推荐从以下入口开始：

1. `README.md`
2. `development_progress.md`
3. `auto_ocr_pipeline_v0.63.py`
4. `auto_ocr_pipeline_v0.7_retuned.py`
5. `auto_ocr_pipeline_v1.0.py`
6. `appendix_materials/`
