# v1.0 安装版打包说明

当前项目已经具备制作“自带运行环境安装版”的基础条件。

## 推荐路线

与其直接尝试将 `PaddleOCR + PaddlePaddle + PyQt5 + pyzbar` 强行冻结成单文件可执行程序，更稳妥的方式是：

1. 先生成一个自带 `ocr_runtime` 运行环境的独立发布目录
2. 再使用安装器工具将该目录封装为安装包

这样做的优点是：

- 更接近当前已经验证通过的运行环境
- 对 OCR、Paddle 和二维码依赖更稳定
- 更容易排查问题
- 更适合毕业设计项目的工程化交付

## 已准备好的文件

- `build_release_v1_0_standalone.ps1`
  - 作用：生成自带 `ocr_runtime` 的独立运行目录
- `installer_assets/Mr6_Auto_OCR_Pipeline_v1.0.iss`
  - 作用：供 Inno Setup 编译为 Windows 安装程序

## 使用步骤

### 1. 生成独立运行目录

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release_v1_0_standalone.ps1
```

执行成功后，生成目录为：

```text
release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_standalone
```

### 2. 安装 Inno Setup

如果本机尚未安装 Inno Setup，请先安装。

### 3. 编译安装包

用 Inno Setup 打开：

```text
installer_assets\Mr6_Auto_OCR_Pipeline_v1.0.iss
```

然后点击编译，即可得到安装程序。

## 注意事项

- `ocr_runtime` 环境体积较大，当前约 3 GB，因此安装包不会太小
- 若后续需要进一步压缩体积，可以再考虑精简环境或改走 PyInstaller/Nuitka 路线
- 如果 `conda-unpack` 未正确注入独立环境，首次独立运行前需要重新检查打包结果
