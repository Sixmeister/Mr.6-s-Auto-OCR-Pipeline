# Mr.6's Auto OCR Pipeline

`Mr.6's Auto OCR Pipeline` 是一个面向标签类图像场景的本地化自动识别项目，目标是完成标签区域处理、文字识别、条码/二维码识别与结构化结果输出，并逐步发展为可发布、可安装的 Windows 桌面应用。

本仓库保留了项目从原型验证到发布版整理过程中的代表性版本、测试记录整理脚本、附录材料索引以及发布相关资源，适合用于了解项目实现过程、查看阶段成果与获取发布版支持材料。

## 项目内容概览

仓库当前主要包含以下几类内容：

- 多个关键阶段的源码版本
- 标签检测与多标签场景相关的数据集目录
- 测试记录与对比分析脚本
- 项目附录材料整理目录
- Windows 发布与安装相关脚本
- 发布版说明资源

## 代表性版本

仓库中保留了若干具有代表性的版本脚本，用于展示项目的主要演进路径：

- `auto_ocr_pipeline_v0.1.py`
  - 早期自动化监听与归档原型
- `auto_ocr_pipeline_v0.2gui.py`
  - 引入基础图形界面的版本
- `auto_ocr_pipeline_v0.4.py`
  - 多标签问题分析与初步分组思路
- `auto_ocr_pipeline_v0.5.py`
  - 聚类分组与规则修正阶段
- `auto_ocr_pipeline_v0.63.py`
  - 接入标签检测模型后的阶段性版本
- `auto_ocr_pipeline_v0.71.py`
  - 引入自适应策略并继续完善界面
- `auto_ocr_pipeline_v0.71_tuned.py`
  - 面向多标签测试场景进一步调优的版本
- `auto_ocr_pipeline_v1.0.py`
  - 面向正式发布整理的版本

如果你希望优先查看当前最接近最终交付形态的代码，建议从以下文件开始：

- `auto_ocr_pipeline_v1.0.py`
- `app_config_v1.0.json`

## 仓库结构说明

### `appendix_materials/`

用于整理项目附录类材料，目前包含：

- `appendix1_code_overview`
  - 核心代码文件索引与说明
- `appendix2_dataset_overview`
  - 数据集结构与样例说明
- `appendix3_training_and_model_compare`
  - 训练日志与模型对比材料
- `appendix4_test_records`
  - 多阶段测试记录与对比结果
- `appendix5_release_materials`
  - 发布版与安装相关说明材料

### `installer_assets/`

Windows 安装器相关脚本目录，目前主要包含：

- `Mr6_Auto_OCR_Pipeline_v1.0.iss`

该文件可用于通过 Inno Setup 生成 Windows 安装包。

### `label_dataset_voc/`

标签检测相关数据集目录，保留 VOC 风格的数据组织形式，适合查看原始标注与训练数据结构。

### `label_dataset_voc_pd/`

与检测训练流程适配的数据集目录，用于配合检测模型训练或数据整理流程查看。

### `release_assets/`

发布版资源说明目录，目前主要用于存放发布包附带文档，如 README、运行说明等。

### `test/`

保留早期测试与原型验证相关脚本，用于辅助查看项目前期的实验与验证思路。

## 关键脚本说明

### 发布与安装相关

- `prepare_release_v1_0_portable.ps1`
  - 用于生成便携版发布目录
- `build_release_v1_0_standalone.ps1`
  - 用于构建带运行环境的 standalone 发布目录
- `start_release_v1_0.ps1`
- `start_release_v1_0.bat`
  - 正常启动脚本
- `start_release_v1_0_debug.ps1`
- `start_release_v1_0_debug.bat`
  - 调试启动脚本

### 测试与对比相关

- `run_v071_tuned_grouping_test.py`
  - 批量运行 `v0.71_tuned` 多标签测试
- `run_v063_grouping_test_retest.py`
  - 重跑 `v0.63` 同口径测试
- `evaluate_v071_tuned_counts.py`
  - 评估 `v0.71_tuned` 标签数判断结果
- `diagnose_v071_adaptive.py`
  - 分析自适应策略在测试样本中的表现
- `build_v063_vs_v071_tuned_compare.py`
  - 生成 `v0.63` 与 `v0.71_tuned` 的逐图对比表

## 阅读建议

如果你希望快速了解项目实现路线，推荐按以下顺序阅读：

1. `auto_ocr_pipeline_v0.2gui.py`
2. `auto_ocr_pipeline_v0.5.py`
3. `auto_ocr_pipeline_v0.63.py`
4. `auto_ocr_pipeline_v0.71.py`
5. `auto_ocr_pipeline_v0.71_tuned.py`
6. `auto_ocr_pipeline_v1.0.py`

如果你更关注测试记录和整理材料，建议优先查看：

- `appendix_materials/`
- `build_v063_vs_v071_tuned_compare.py`
- `run_v071_tuned_grouping_test.py`

## 发布版说明

发布相关资源位于：

- `release_assets/Mr6_Auto_OCR_Pipeline_v1.0`

若仅需要使用最终发布版，建议优先从仓库的 Release 页面获取安装包或发布资产。

## 开发进展

如需查看项目的公开开发脉络与阶段说明，可参考：

- `development_progress.md`

该文档主要用于概述项目的阶段演进、版本节点和当前仓库维护状态。

## 维护说明

当前仓库更偏向于“项目归档 + 版本记录 + 发布支持”的公开整理方式。仓库中既包含可运行源码，也保留了测试记录、附录材料和发布支持文件。

若后续继续维护，建议进一步补充：

- 更完整的环境依赖说明
- Release 更新记录
- 更标准化的公开文档结构

## Repository

Repository owner: [Sixmeister](https://github.com/Sixmeister)
