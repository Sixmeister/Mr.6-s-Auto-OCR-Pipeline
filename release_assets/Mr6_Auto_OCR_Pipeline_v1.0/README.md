# Mr.6 Auto OCR Pipeline v1.0 发布包说明

## 1. 发布包简介

`Mr6_Auto_OCR_Pipeline_v1.0` 是本项目的便携式发布目录，面向本地运行、论文演示和功能验证场景。

当前公开发布主线已经同步 `v0.7_retuned` 的候选框选择优化逻辑，目标不是改变 45 轮标签检测模型本身，而是尽量减少检测结果进入系统主流程时的系统级损耗，使发布版最终输出更接近检测模型在扩样本验证中的原始计数能力。

## 2. 发布包目录结构

建议将发布包根目录理解为“开箱即用的运行目录”。主要结构如下：

```text
Mr6_Auto_OCR_Pipeline_v1.0/
+-- auto_ocr_pipeline_v1.0.py
+-- app_config_v1.0.json
+-- start_release_v1_0.bat
+-- start_release_v1_0.ps1
+-- start_release_v1_0_debug.bat
+-- start_release_v1_0_debug.ps1
+-- README.md
+-- README.zh-CN.md
+-- README.en.md
+-- README.txt
+-- logs/
+-- watch_directory/
+-- processed_directory/
+-- error_directory/
+-- json_directory/
+-- output_directory/
+-- visual_outputs/
+-- multiple_labels_test/
+-- PaddleDetection-release-2.8.1/
    +-- deploy/python/
    +-- output_inference/label_det_m_45e/
```

## 3. 主要特性

- 基于 `auto_ocr_pipeline_v1.0.py` 的桌面 GUI 程序。
- 集成 45 轮导出标签检测模型。
- 支持单次识别与实时监控两种主要运行模式。
- 保留 OCR、条码/二维码识别、结果输出与日志记录流程。
- 默认路径采用相对路径，便于整体搬移。
- 已同步 retuned 候选框选择优化逻辑。

## 4. 运行环境说明

当前发布包存在两种使用方式：

1. 便携目录方式
   - 依赖本地可用的 Python / `ocr_runtime` 环境。
2. standalone / 安装器方式
   - 将运行环境一并打包到发布目录中，便于脱离开发环境运行。

如果双击启动失败，建议优先使用：

```text
start_release_v1_0_debug.bat
```

然后查看：

```text
logs/startup_debug.log
```

## 5. 打包与安装器说明

本项目当前验证成功的打包路线包括：

- `prepare_release_v1_0_portable.ps1`
- `build_release_v1_0_standalone.ps1`
- `prepare_release_v1_0_retuned_portable.ps1`
- `build_release_v1_0_retuned_standalone.ps1`
- `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0.iss`
- `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0_retuned.iss`

其中，重新发布 `v1.0 retuned` 时使用的是平行的 retuned 路线：

1. 生成新的 portable 目录；
2. 生成新的 standalone 目录；
3. 使用 `subst R:` 缩短路径；
4. 从缩短路径后的 standalone 目录执行 Inno Setup 编译。

## 6. 随包附带测试材料

为了方便功能验证，发布包内附带了：

- `multiple_labels_test/` 中的多标签测试图片；
- `multiple_labels_test/truth.csv` 真值表。

这些文件可用于单次识别测试、功能演示和结果核对。