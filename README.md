# Mr.6's Auto OCR Pipeline

`Mr.6's Auto OCR Pipeline` 是一个面向标签图像场景的本地化自动识别项目，目标是完成标签区域处理、文字识别、条码/二维码识别以及结构化结果输出，并逐步发展为可发布、可安装的桌面应用。

本仓库同时保留了项目从原型验证到发布版的主要脚本、测试记录整理脚本、附录材料索引以及 Windows 发布相关资源，适合用于了解项目实现过程、复现实验记录和获取最终发布版。

## 项目特点

- 面向标签图像场景的 OCR 流程实现
- 包含多阶段版本脚本，便于查看功能演进
- 提供多标签场景的测试与对比脚本
- 提供发布目录构建、独立运行环境打包和安装器脚本
- 附带适合论文/项目归档的附录材料整理目录

## 版本概览

仓库保留了若干具有代表性的版本脚本：

- `auto_ocr_pipeline_v0.1.py`
  - 自动化监听与结果归档的早期实现
- `auto_ocr_pipeline_v0.2gui.py`
  - 引入基础 GUI 的版本
- `auto_ocr_pipeline_v0.4.py`
  - 多标签问题分析与初始分组思路
- `auto_ocr_pipeline_v0.5.py`
  - 多标签聚类分组与规则修正
- `auto_ocr_pipeline_v0.63.py`
  - 标签检测模型接入后的阶段性版本
- `auto_ocr_pipeline_v0.71.py`
  - 自适应策略与进一步界面完善的版本
- `auto_ocr_pipeline_v0.71_tuned.py`
  - 针对多标签测试继续调优的策略版本
- `auto_ocr_pipeline_v1.0.py`
  - 面向正式发布整理的版本

其中，若你希望优先查看当前最接近最终发布形态的代码，建议从以下文件开始：

- [auto_ocr_pipeline_v1.0.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/auto_ocr_pipeline_v1.0.py)
- [app_config_v1.0.json](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/app_config_v1.0.json)

## 仓库结构

当前远端仓库的主要内容如下：

```text
Mr.6-s-Auto-OCR-Pipeline/
├─ appendix_materials/
├─ installer_assets/
├─ label_dataset_voc/
├─ label_dataset_voc_pd/
├─ release_assets/
├─ test/
├─ app_config_v1.0.json
├─ auto_ocr_pipeline_v0.1.py
├─ auto_ocr_pipeline_v0.2gui.py
├─ auto_ocr_pipeline_v0.2gui_paper.py
├─ auto_ocr_pipeline_v0.4.py
├─ auto_ocr_pipeline_v0.5.py
├─ auto_ocr_pipeline_v0.5_paper.py
├─ auto_ocr_pipeline_v0.63.py
├─ auto_ocr_pipeline_v0.63_paper.py
├─ auto_ocr_pipeline_v0.71.py
├─ auto_ocr_pipeline_v0.71_tuned.py
├─ auto_ocr_pipeline_v1.0.py
├─ build_release_v1_0_standalone.ps1
├─ build_v063_vs_v071_tuned_compare.py
├─ diagnose_v071_adaptive.py
├─ evaluate_v071_tuned_counts.py
├─ prepare_release_v1_0_portable.ps1
├─ progress.md
├─ run_v063_grouping_test_retest.py
├─ run_v071_tuned_grouping_test.py
├─ start_release_v1_0.bat
├─ start_release_v1_0.ps1
├─ start_release_v1_0_debug.bat
└─ start_release_v1_0_debug.ps1
```

### 目录说明

#### `appendix_materials/`

用于整理项目附录型材料，目前包含：

- `appendix1_code_overview`
  - 核心代码文件说明
- `appendix2_dataset_overview`
  - 数据集结构与组织说明
- `appendix3_training_and_model_compare`
  - 训练相关材料与模型对比记录
- `appendix4_test_records`
  - 各阶段测试记录与对比 CSV
- `appendix5_release_materials`
  - 发布版脚本与打包材料说明

#### `installer_assets/`

Windows 安装器相关脚本目录，当前主要包含：

- `Mr6_Auto_OCR_Pipeline_v1.0.iss`

该文件可用于 Inno Setup 编译安装包。

#### `label_dataset_voc/`

标签检测相关数据集目录，保留了原始 VOC 风格的数据组织形式。

#### `label_dataset_voc_pd/`

用于训练/适配框架的数据集组织目录，适合与检测训练流程配合查看。

#### `release_assets/`

发布版说明文档目录。  
当前包含中英文 README、打包说明等发布资源，可用于最终发布包内文档。

#### `test/`

保留早期测试与原型验证相关脚本。

## 关键脚本说明

### 运行与发布相关

- [prepare_release_v1_0_portable.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/prepare_release_v1_0_portable.ps1)
  - 生成便携发布目录
- [build_release_v1_0_standalone.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/build_release_v1_0_standalone.ps1)
  - 构建带运行环境的 standalone 发布目录
- [start_release_v1_0.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0.ps1)
  - PowerShell 启动脚本
- [start_release_v1_0.bat](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0.bat)
  - Windows 批处理启动脚本
- [start_release_v1_0_debug.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0_debug.ps1)
- [start_release_v1_0_debug.bat](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0_debug.bat)
  - 调试启动脚本

### 测试与对比相关

- [run_v071_tuned_grouping_test.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/run_v071_tuned_grouping_test.py)
  - 运行 `v0.71_tuned` 的批量测试
- [run_v063_grouping_test_retest.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/run_v063_grouping_test_retest.py)
  - 重新运行 `v0.63` 的同口径测试
- [evaluate_v071_tuned_counts.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/evaluate_v071_tuned_counts.py)
  - 评估 `v0.71_tuned` 的标签数量判断结果
- [diagnose_v071_adaptive.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/diagnose_v071_adaptive.py)
  - 用于分析自适应策略行为
- [build_v063_vs_v071_tuned_compare.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/build_v063_vs_v071_tuned_compare.py)
  - 生成 `v0.63` 与 `v0.71_tuned` 的逐图对比表

## 如何使用

### 1. 查看项目实现

如果你想快速理解项目实现路线，建议按照以下顺序阅读：

1. `auto_ocr_pipeline_v0.2gui.py`
2. `auto_ocr_pipeline_v0.5.py`
3. `auto_ocr_pipeline_v0.63.py`
4. `auto_ocr_pipeline_v0.71.py`
5. `auto_ocr_pipeline_v0.71_tuned.py`
6. `auto_ocr_pipeline_v1.0.py`

### 2. 查看测试与对比材料

建议结合以下目录一起阅读：

- [appendix_materials](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/appendix_materials)
- [build_v063_vs_v071_tuned_compare.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/build_v063_vs_v071_tuned_compare.py)
- [run_v071_tuned_grouping_test.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/run_v071_tuned_grouping_test.py)

### 3. 构建发布版

如果你希望在本地重建发布流程，推荐顺序如下：

1. 运行 `prepare_release_v1_0_portable.ps1`
2. 运行 `build_release_v1_0_standalone.ps1`
3. 使用 Inno Setup 打开 `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0.iss`
4. 编译新的安装包

## 发布资源

发布版相关文档位于：

- [release_assets/Mr6_Auto_OCR_Pipeline_v1.0](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/release_assets/Mr6_Auto_OCR_Pipeline_v1.0)

如果你是仓库使用者，建议优先从 GitHub Releases 页面获取最终安装包或发布资产，而不是手动拼接中间目录。

## 开发记录

项目的阶段性记录、问题分析和后续补充说明可参考：

- [progress.md](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/progress.md)

这个文件更适合想了解版本推进过程的读者；如果你只关心最终结果，可以直接阅读 `v1.0` 相关脚本与发布目录说明。

## 说明

本仓库当前更偏向“项目归档 + 版本记录 + 发布维护”的公开整理方式。  
因此，仓库中既有可运行脚本，也有测试对比、附录材料和发布支持文件。

若后续继续公开维护，建议进一步补充：

- `LICENSE`
- 更明确的环境配置说明
- Release 页面对应的版本更新日志

## 联系方式

Repository owner: [Sixmeister](https://github.com/Sixmeister)
