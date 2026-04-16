# Mr.6's Auto OCR Pipeline

本项目是一个面向物料标签场景的本地化自动识别系统，用于完成标签区域检测、文字识别、条码/二维码识别以及结构化结果输出。

项目最初从 OCR 与码识别链路验证出发，随后逐步发展为支持多标签场景、标签检测模型接入、GUI 交互、实时监听和正式打包发布的完整系统。当前仓库已经包含从原型脚本到 `v1.0` 正式发布候选版的主要开发成果。

## Project Overview

This repository contains a local automatic OCR pipeline for material labels.  
It supports label-region detection, OCR, barcode/QR decoding, GUI interaction, watch-mode processing, and Windows release packaging.

## 核心功能

- 单张图片识别
- 实时监听文件夹并自动处理新图片
- 标签区域检测与多标签分组
- OCR 文字识别
- 条码/二维码识别
- JSON / TXT / 可视化结果输出
- 手动输出与自动输出两种结果保存模式
- Windows 便携版与安装包发布流程

## 版本进展概览

- `v0.1` - `v0.2gui`
  - 完成 OCR 与码识别原型验证，建立基础 GUI
- `v0.4` - `v0.5`
  - 面向多标签场景引入聚类分组与测试记录机制
- `v0.61` - `v0.63`
  - 接入标签检测模型，开始使用“先检测标签区域，再识别内容”的路线
- `v0.7` - `v0.71`
  - 引入自适应阈值、自适应候选选择和进一步 GUI 优化
- `v1.0`
  - 完成发布导向整理、相对路径配置、便携目录、独立运行包和安装器构建流程

## 当前推荐版本

当前推荐关注的主版本为：

- [auto_ocr_pipeline_v1.0.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/auto_ocr_pipeline_v1.0.py)
- [app_config_v1.0.json](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/app_config_v1.0.json)

如果你只是想直接使用程序，而不是从源码运行，请优先前往 GitHub 的 `Releases` 页面下载安装包。

## 仓库主要结构

```text
Mr.6-s-Auto-OCR-Pipeline/
+-- auto_ocr_pipeline_v0.1.py ~ auto_ocr_pipeline_v1.0.py
+-- app_config_*.json
+-- start_release_v1_0.ps1 / .bat
+-- start_release_v1_0_debug.ps1 / .bat
+-- prepare_release_v1_0_portable.ps1
+-- build_release_v1_0_standalone.ps1
+-- installer_assets/
+-- release_assets/
+-- test/
+-- multiple_labels_test/
+-- single_label_test/
+-- label_dataset_voc/
+-- label_dataset_voc_pd/
+-- training_logs/
+-- PaddleDetection-release-2.8.1/
+-- appendix_materials/
+-- progress.md
```

### 目录说明

- `auto_ocr_pipeline_v*.py`
  - 各阶段主要程序版本
- `installer_assets/`
  - Windows 安装器脚本
- `release_assets/`
  - 发布包说明文档、打包说明
- `test/`
  - 早期原型验证脚本
- `multiple_labels_test/`
  - 多标签测试图片与真值表
- `single_label_test/`
  - 单标签测试样本
- `label_dataset_voc/` / `label_dataset_voc_pd/`
  - 标签检测数据集及其适配后的目录组织
- `training_logs/`
  - 标签检测模型训练日志与曲线输出
- `PaddleDetection-release-2.8.1/`
  - 检测模型训练、导出与推理依赖框架
- `appendix_materials/`
  - 论文附录整理材料
- `progress.md`
  - 项目开发进度、问题记录与解决过程

## 运行方式

### 1. 从源码运行

推荐使用项目中已经验证过的运行环境，例如：

- `ocr_runtime`

主发布版启动文件：

- [start_release_v1_0.bat](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0.bat)
- [start_release_v1_0.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0.ps1)

调试启动文件：

- [start_release_v1_0_debug.bat](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0_debug.bat)
- [start_release_v1_0_debug.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_release_v1_0_debug.ps1)

### 2. 下载安装包运行

如果你不想配置 Python 环境，建议直接前往 GitHub `Releases` 下载 `v1.0` 安装包。

本项目已经完成：

- 便携发布目录构建
- 自带运行环境的独立运行目录构建
- Windows 安装器打包

## 发布与打包相关文件

- [prepare_release_v1_0_portable.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/prepare_release_v1_0_portable.ps1)
  - 生成便携发布目录
- [build_release_v1_0_standalone.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/build_release_v1_0_standalone.ps1)
  - 生成自带运行环境的独立运行目录
- [installer_assets\Mr6_Auto_OCR_Pipeline_v1.0.iss](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/installer_assets/Mr6_Auto_OCR_Pipeline_v1.0.iss)
  - Inno Setup 安装器脚本

## 标签检测模型训练相关文件

- [start_label_det_45e_training.ps1](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/start_label_det_45e_training.ps1)
- [monitor_training_log.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/monitor_training_log.py)
- [compare_three_label_models.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/compare_three_label_models.py)
- [compare_exported_label_models.py](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/compare_exported_label_models.py)

## 论文与工程化说明

本仓库同时服务于毕业设计项目开发与论文写作，因此除代码外，还保留了：

- 数据集整理材料
- 模型训练记录
- 测试记录
- 论文附录整理文件
- 开发进度记录

如果你是老师、同学或评阅者，建议优先阅读：

- [progress.md](/E:/Mr.6_Auto_OCR_PipelineWithCodeX/progress.md)
- `Releases` 页面中的安装包说明

## 推荐的 GitHub Release 资产

建议在 GitHub `Releases` 页面上传：

- `Mr6_Auto_OCR_Pipeline_v1.0_Setup.exe`

如果需要，也可以同时附上：

- 简短使用说明 PDF
- 版本更新说明

不建议把以下内容直接作为普通仓库文件长期提交：

- `release_candidates/`
- `release_installers/`
- 运行过程中生成的大量 JSON / TXT / 可视化结果

## License

当前仓库尚未单独整理正式开源许可证文件。  
如果后续准备以更规范的方式公开发布，建议补充 `LICENSE` 文件并明确第三方依赖的使用边界。

## Contact

Repository owner: [Sixmeister](https://github.com/Sixmeister)
