# Mr.6's Auto OCR Pipeline

## 项目简介

本仓库用于保存本人本科毕业论文《基于深度学习的自动化标签识别系统的设计与实现》所对应的项目代码、数据集、训练补充材料以及论文附录相关文件。

本项目围绕工业标签自动识别任务展开，目标是在本地环境下实现一套能够处理标签图片的自动化识别系统。系统主要包括以下几个部分：

- 图像输入与自动化处理
- 标签区域划分
- OCR 文字识别
- 条码与二维码识别
- 识别结果保存与输出
- 图形界面交互
- 多标签场景下的标签检测模型训练与系统集成

项目从早期的原型验证脚本出发，逐步发展为支持 GUI、文件夹实时监听、多标签聚类分组、标签检测模型接入以及自适应阈值策略优化的完整研究型原型系统。

---

## 与毕业论文的对应关系

本仓库中的主要内容与论文第4章和附录部分相对应：

- 正文第4章：
  对应系统设计、版本迭代、数据集制作、模型训练和系统测试内容
- 附录1：
  核心代码文件说明
- 附录2：
  标签检测数据集样例与标注示例
- 附录3：
  训练配置与模型对比补充结果
- 附录4：
  系统测试原始数据与测试记录附表

为了避免论文正文和附录篇幅过长，部分完整原始材料未全部直接放入论文，而是整理后保存在本仓库中，供查阅和复核。

---

## 仓库主要内容说明

### 1. 系统代码文件

仓库根目录中保留了论文中提到的主要版本代码，包括但不限于：

- `auto_ocr_pipeline_v0.1.py`
- `auto_ocr_pipeline_v0.2gui.py`
- `auto_ocr_pipeline_v0.4.py`
- `auto_ocr_pipeline_v0.5.py`
- `auto_ocr_pipeline_v0.63.py`
- `auto_ocr_pipeline_v0.71.py`

这些文件分别对应论文正文第4章中的不同开发阶段。

其中：

- `v0.1` 主要对应自动化处理原型
- `v0.2gui` 对应 GUI 初版与实时监听模式
- `v0.4` 对应多标签分组过渡阶段
- `v0.5` 对应基于 OCR 文本框聚类的多标签处理版本
- `v0.63` 对应引入标签检测模型后的系统集成版本
- `v0.71` 对应引入自适应阈值策略与界面优化后的版本

测试原型脚本位于：

- `test/`

---

### 2. 数据集相关目录

标签检测模型训练所使用的数据集主要包括：

- `label_dataset_voc/`
- `label_dataset_voc_pd/`

其中：

- `label_dataset_voc/`
  保存原始 VOC 风格数据，包括图片、XML 标注文件以及训练/验证划分文件
- `label_dataset_voc_pd/`
  保存按 PaddleDetection 训练要求进一步整理后的数据集目录，包括类别文件、列表文件和 `VOCdevkit/VOC2007` 结构

这两部分内容主要对应论文附录2。

---

### 3. 训练与模型比较材料

与标签检测模型训练和模型对比相关的补充材料主要包括：

- `training_logs/`
- `model_compare_outputs/`
- `multiple_labels_test/truth.csv`

其中：

- `training_logs/label_det_m_45e/`
  保存45轮训练的日志、训练过程 CSV 和训练曲线图
- `model_compare_outputs/label_det_80e_vs_45e/`
  保存45轮与80轮模型对比结果
- `model_compare_outputs/three_model_rerun_fair_20260409/`
  保存三模型对比结果
- `multiple_labels_test/truth.csv`
  保存多标签测试真值表

这部分材料主要对应论文附录3。

---

### 4. 测试记录与附录材料目录

与论文附录对应的整理材料位于：

- `appendix_materials/`

目前建议重点查看以下子目录：

#### `appendix_materials/appendix1_code_overview/`
用于说明附录1核心代码文件与论文正文的对应关系。

#### `appendix_materials/appendix2_dataset_overview/`
用于说明附录2中数据集样例、目录结构和类别文件的组织方式。

#### `appendix_materials/appendix3_training_and_model_compare/`
用于说明附录3中训练配置、训练日志、曲线图和模型对比材料的组织方式。

#### `appendix_materials/appendix4_test_records/`
用于说明附录4中系统测试原始数据与测试记录附表的组织方式。

这部分目录主要起到“论文附录导航”和“补充材料索引”的作用。

---

## 建议阅读顺序

如果你是指导教师、评阅教师或需要快速了解项目内容的读者，建议按以下顺序查看本仓库：

1. 阅读本 README，了解项目整体结构
2. 查看 `appendix_materials/appendix1_code_overview/`
   了解论文正文与关键代码文件之间的对应关系
3. 查看 `appendix_materials/appendix2_dataset_overview/`
   了解数据集构成、样例与目录结构
4. 查看 `appendix_materials/appendix3_training_and_model_compare/`
   了解训练配置、训练过程与模型比较
5. 查看 `appendix_materials/appendix4_test_records/`
   了解各阶段测试原始记录与逐图比较结果
6. 若需核对具体实现，再回到仓库根目录查看对应版本代码

---

## 关于论文附录材料的说明

本仓库中与论文附录有关的材料，遵循如下组织方式：

- 论文中保留必要的节选、代表性图表和简要说明
- 更完整的代码、数据集、训练日志、CSV 测试记录和逐图对比表保存在仓库中
- 仓库中的 `appendix_materials/` 目录用于帮助读者快速定位附录对应材料

因此，若论文附录中提到“完整材料见仓库”或“相关原始记录见 GitHub 仓库”，一般可优先从 `appendix_materials/` 目录进入，再根据说明定位到具体文件。

---

## 说明

本仓库主要服务于毕业论文答辩、材料归档和项目留存，因此在内容组织上兼顾了“项目本体结构”和“论文附录查阅便利性”。

如需复现训练、测试或查看完整原始记录，建议结合论文正文和本仓库目录一并阅读。
