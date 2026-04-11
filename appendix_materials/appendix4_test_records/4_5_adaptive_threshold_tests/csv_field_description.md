## CSV 字段说明

本文件用于说明附录4相关测试记录 CSV 中常见字段的含义。

| 字段名 | 含义 |
|---|---|
| recorded_at | 记录生成时间 |
| mode | 测试模式，通常为 single 或 watch |
| image_name | 测试图片文件名 |
| ocr_valid | OCR 是否识别到有效文本 |
| code_valid | 是否识别到有效条码或二维码 |
| ocr_line_count | OCR 识别出的文本行数 |
| code_count | 识别到的码数量 |
| actual_label_count | 真值中的实际标签数量 |
| predicted_label_count | 系统预测得到的标签数量 |
| label_count_correct | 标签数量判断是否正确 |
| over_split | 是否发生误拆分 |
| over_merge | 是否发生误合并 |
| success | 本次处理是否成功 |
| elapsed_seconds | 单张图片处理耗时 |
| error | 错误信息 |
