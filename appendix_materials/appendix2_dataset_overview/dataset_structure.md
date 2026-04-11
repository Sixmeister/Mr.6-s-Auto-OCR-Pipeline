## 数据集目录结构说明

### 1. 原始 VOC 风格数据集

```text
label_dataset_voc/
├─ Annotations/
│  ├─ 001.xml
│  ├─ 001(1).xml
│  ├─ 013.xml
│  └─ ...
├─ ImageSets/
│  └─ Main/
│     ├─ train.txt
│     └─ val.txt
└─ JPEGImages/
   ├─ 001.jpg
   ├─ 001(1).jpg
   ├─ 013.jpg
   └─ ...
```

说明：
- `JPEGImages/` 保存原始图片和增强图片。
- `Annotations/` 保存与图片对应的 VOC XML 标注文件。
- `ImageSets/Main/` 保存训练集与验证集划分文件。

### 2. PaddleDetection 训练目录

```text
label_dataset_voc_pd/
├─ label_list.txt
├─ trainval.txt
├─ test.txt
└─ VOCdevkit/
   └─ VOC2007/
      ├─ Annotations/
      └─ JPEGImages/
```

说明：
- `label_list.txt` 中定义类别名为 `label`。
- `trainval.txt` 和 `test.txt` 用于训练框架读取数据列表。
- `VOCdevkit/VOC2007/` 目录结构与 PaddleDetection 的 VOC 数据集要求保持一致。

### 3. 与论文附录2的对应关系

- 附录2-1：标签检测数据集原始样本
- 附录2-2：数据增强样例对比
- 附录2-3：标签检测标注文件示例
- 附录2-4：数据集目录结构与类别文件
- 附表2-1：标签检测数据集划分情况
