# Mr.6 Auto OCR Pipeline v1.0 发布包说明

## 1. 发布包简介

`Mr6_Auto_OCR_Pipeline_v1.0` 是本项目的便携式发布目录，面向本地运行、论文演示和功能验证场景。  
该版本基于 `v0.71` 的检测集成路线继续工程化整理而成，重点完成了以下工作：

- 将主程序、配置文件、启动脚本、模型目录和默认输入输出目录整理到同一发布包内
- 将配置中的核心路径改为相对路径，便于整个文件夹整体搬移
- 保留单次识别与实时监控两种主要运行模式
- 集成标签检测模型、OCR 识别、码识别、结果保存与日志输出
- 提供调试启动脚本，便于排查环境或依赖问题

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

其中各目录作用如下：

| 目录/文件 | 作用 |
| --- | --- |
| `auto_ocr_pipeline_v1.0.py` | 主程序文件，负责 GUI、识别流程、结果保存与模式切换 |
| `app_config_v1.0.json` | 默认配置文件，保存路径、模型目录、阈值和模式参数 |
| `start_release_v1_0.bat` | 推荐启动入口，适合双击运行 |
| `start_release_v1_0.ps1` | PowerShell 启动脚本 |
| `start_release_v1_0_debug.bat` | 调试启动入口，启动失败时优先使用 |
| `logs/` | 调试日志目录，主要保存启动日志 |
| `watch_directory/` | 实时监控模式的输入目录 |
| `processed_directory/` | 处理成功后的原图归档目录 |
| `error_directory/` | 处理失败或效果异常图片的归档目录 |
| `json_directory/` | JSON 结构化结果默认输出目录 |
| `output_directory/` | TXT 文本结果默认输出目录 |
| `visual_outputs/` | 可视化结果图默认输出目录 |
| `multiple_labels_test/` | 随包附带的多标签测试样例与真值表 |
| `PaddleDetection-release-2.8.1/` | 标签检测推理所需的部署辅助代码与导出模型 |

## 3. 运行环境要求

当前发布包还不是完全脱离 Python 环境的独立安装程序，因此运行前需要满足以下条件：

- 操作系统：Windows
- Python 运行环境可用
- 推荐使用本项目已有的 `ocr_runtime` 虚拟环境
- 环境中需要具备以下核心依赖：
  - `paddleocr`
  - `paddlepaddle`
  - `opencv-python`
  - `PyQt5`
  - `watchdog`
  - `pyzbar`
  - `numpy`

如果双击启动失败，最常见原因通常是：

- 没有找到正确的 Python 解释器
- 当前 Python 环境缺少 `paddleocr`
- 运行环境与训练/测试环境不一致

## 4. 推荐启动方式

### 4.1 普通启动

最推荐直接双击：

```powershell
start_release_v1_0.bat
```

该脚本会优先尝试调用适合当前项目的 Python 解释器，并启动 GUI。

### 4.2 PowerShell 启动

如果你已经手动进入发布目录，也可以执行：

```powershell
.\start_release_v1_0.ps1
```

### 4.3 调试启动

若程序启动后闪退，或者没有正常出现界面，请运行：

```powershell
start_release_v1_0_debug.bat
```

随后查看：

```text
logs/startup_debug.log
```

该日志通常可以帮助定位如下问题：

- Python 解释器路径不正确
- `paddleocr` 等依赖缺失
- 相对路径失效
- 模型目录未找到

## 5. 程序的主要运行模式

### 5.1 单次识别模式

适合手动选择单张图片进行测试或演示。  
典型流程如下：

1. 启动程序
2. 保持“单次识别”模式
3. 点击选择图片
4. 程序执行标签检测、OCR 识别、码识别和结果整理
5. 在右侧输出区查看识别日志与结果
6. 根据当前输出模式自动保存，或手动点击保存按钮

### 5.2 实时监控模式

适合批量测试或模拟生产场景中的持续输入。

典型流程如下：

1. 将模式切换为“实时监控”
2. 确认 `watch_directory` 为监控输入目录
3. 点击开始监控
4. 将图片复制到 `watch_directory`
5. 程序识别完成后自动将原图移动到成功或异常目录

## 6. 输出结果说明

程序支持以下几类输出结果：

| 输出类型 | 默认目录 | 内容 |
| --- | --- | --- |
| JSON 结果 | `json_directory/` | 标签数量、标签框、识别文本、码识别结果等结构化数据 |
| TXT 结果 | `output_directory/` | 便于人工阅读的纯文本识别结果 |
| 可视化结果 | `visual_outputs/` | 识别结果可视化图片 |
| 调试日志 | `logs/` | 启动日志和排障信息 |

另外，程序还支持两种输出策略：

- 自动输出：识别完成后自动保存 JSON、TXT 和可视化结果
- 手动输出：识别完成后由用户手动点击按钮保存结果

## 7. 配置文件说明

发布包默认使用：

```text
app_config_v1.0.json
```

该配置文件中保存了：

- 输入输出目录
- 标签检测模型目录
- 真值表 CSV 路径
- 结果记录 CSV 路径
- 检测阈值和 NMS 参数
- 是否启用自适应策略
- 是否启用手动输出

本版本的一个关键改动是：

- 配置中多数路径已改为相对路径
- 只要整个发布目录结构保持不变，就可以整体复制到别的位置继续使用

## 8. 随包附带的测试材料

为了方便功能验证，发布包内附带了：

- `multiple_labels_test/` 中的多标签测试图片
- `multiple_labels_test/truth.csv` 真值表

这些文件可用于：

- 单次识别测试
- 多标签检测效果演示
- 结果记录 CSV 的对照验证

## 9. 常见问题处理

### 9.1 双击后没有出现界面

优先执行：

```text
start_release_v1_0_debug.bat
```

然后检查：

```text
logs/startup_debug.log
```

### 9.2 提示缺少 `paddleocr`

说明当前启动脚本调用到的 Python 环境中未安装 `paddleocr`。  
建议切换到本项目使用过的 `ocr_runtime` 环境后再运行。

### 9.3 实时监控模式读不到图片

通常是因为图片刚写入目录时文件仍被占用。本版本已经加入了等待文件稳定的处理机制，但仍建议：

- 图片完整复制后再开始识别
- 尽量避免网络盘或同步盘上的延迟写入

### 9.4 标签检测模型加载失败

请确认以下目录存在：

```text
PaddleDetection-release-2.8.1/output_inference/label_det_m_45e
```

并确认部署辅助代码存在：

```text
PaddleDetection-release-2.8.1/deploy/python
```

## 10. 适合发布包进一步扩展的方向

当前 `v1.0` 已经具备“便携式发布目录”的基本形态，但若后续继续工程化，还可以进一步推进：

- 打包为真正的独立安装程序或单文件可执行程序
- 增加图标、版本信息与安装向导
- 增加专用的依赖检测界面
- 增加更完整的日志导出与异常报告功能

## 11. 建议的交付方式

若需要向老师、同学或测试人员提供本程序，建议直接打包整个：

```text
Mr6_Auto_OCR_Pipeline_v1.0
```

文件夹，而不是只单独发送 `.py` 文件。  
这样可以确保：

- 相对路径配置不失效
- 模型目录完整
- 默认输入输出目录完整
- 文档与启动脚本完整

## 12. 联系项目上下文

本发布包对应的核心程序版本为：

```text
auto_ocr_pipeline_v1.0.py
```

该版本可以理解为本项目在论文后期形成的首个正式发布候选版本，用于展示自动化标签识别系统在工程化整理、相对路径配置、GUI 优化和标签检测集成方面的阶段性成果。
