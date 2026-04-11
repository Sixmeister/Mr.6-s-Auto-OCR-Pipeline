import json
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


if os.environ.get("PADDLE_SUPPRESS_WARNINGS") != "1":
    os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"
    result = subprocess.run([sys.executable] + sys.argv, env=os.environ)
    raise SystemExit(result.returncode)


from paddleocr import PaddleOCR
from pyzbar import pyzbar
import cv2

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


BASE_DIR = Path(r"E:\Mr.6_Auto_OCR_PipelineWithCodeX")
CONFIG_FILE_PATH = BASE_DIR / "app_config_v04.json"


def load_config():
    default_config = {
        "output_dir": str(BASE_DIR / "outputs_v04"),
        "visual_output_dir": str(BASE_DIR / "visual_outputs_v04"),
        "manual_output": False,
    }
    if CONFIG_FILE_PATH.exists():
        try:
            config = json.loads(CONFIG_FILE_PATH.read_text(encoding="utf-8"))
            for key, value in default_config.items():
                config.setdefault(key, value)
            return config
        except Exception:
            return default_config
    return default_config


def save_config(config):
    CONFIG_FILE_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def _poly_to_bbox(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return [min(xs), min(ys), max(xs), max(ys)]


def _bbox_union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def _bbox_center(bbox):
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _bbox_height(bbox):
    return max(1.0, bbox[3] - bbox[1])


def _boxes_close(a, b, margin):
    ax, ay = _bbox_center(a)
    bx, by = _bbox_center(b)
    return math.hypot(ax - bx, ay - by) <= margin * 2


def _cluster_items(items):
    if not items:
        return []

    median_height = sorted([_bbox_height(item["bbox"]) for item in items])[len(items) // 2]
    margin = max(20, int(median_height * 2))
    groups = []

    for item in items:
        placed = False
        for group in groups:
            group_bbox = group[0]["bbox"]
            for group_item in group[1:]:
                group_bbox = _bbox_union(group_bbox, group_item["bbox"])
            if _boxes_close(item["bbox"], group_bbox, margin):
                group.append(item)
                placed = True
                break
        if not placed:
            groups.append([item])

    return groups


def _build_label_groups(text_items, code_items):
    items = text_items + code_items
    groups = _cluster_items(items)
    labels = []

    for idx, group in enumerate(groups, start=1):
        group_bbox = group[0]["bbox"]
        for item in group[1:]:
            group_bbox = _bbox_union(group_bbox, item["bbox"])

        texts = [item for item in group if item["type"] == "text"]
        codes = [item for item in group if item["type"] == "code"]
        texts.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))

        labels.append({
            "label_id": idx,
            "bbox": [int(v) for v in group_bbox],
            "texts": texts,
            "codes": codes,
        })

    return labels


def _format_labels_summary(labels):
    lines = [f"标签数量: {len(labels)}"]
    for label in labels:
        lines.append(f"\n标签 {label['label_id']}:")
        if label["texts"]:
            lines.append("  文本:")
            for t in label["texts"]:
                lines.append(f"    - {t['text']}")
        else:
            lines.append("  文本: [无]")
        if label["codes"]:
            lines.append("  码:")
            for c in label["codes"]:
                lines.append(f"    - [{c['code_type']}] {c['data']}")
        else:
            lines.append("  码: [无]")
    return "\n".join(lines)


class OcrWorker(QThread):
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(str)

    def __init__(self, image_path, output_dir):
        super().__init__()
        self.image_path = image_path
        self.output_dir = Path(output_dir)
        self.ocr = PaddleOCR(lang="ch", use_gpu=False)

    def run(self):
        try:
            self.progress_signal.emit("正在加载图片...")
            image_cv = cv2.imread(self.image_path)
            if image_cv is None:
                raise ValueError(f"无法读取图片文件: {self.image_path}")

            self.progress_signal.emit("正在执行 OCR ...")
            ocr_result = self.ocr.ocr(self.image_path)
            text_items = []
            if isinstance(ocr_result, list) and ocr_result and ocr_result[0] is not None:
                for line in ocr_result[0]:
                    if not isinstance(line, (list, tuple)) or len(line) < 2:
                        continue
                    text_info = line[1]
                    if not isinstance(text_info, (list, tuple)) or len(text_info) < 2:
                        continue
                    text_items.append({
                        "type": "text",
                        "text": text_info[0],
                        "score": text_info[1],
                        "bbox": _poly_to_bbox(line[0]),
                    })

            self.progress_signal.emit("正在识别码信息...")
            decoded_objects = pyzbar.decode(image_cv)
            code_items = []
            for obj in decoded_objects:
                rect = obj.rect
                code_items.append({
                    "type": "code",
                    "code_type": obj.type,
                    "data": obj.data.decode("utf-8", errors="replace"),
                    "bbox": [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height],
                })

            labels = _build_label_groups(text_items, code_items)
            summary = _format_labels_summary(labels)

            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{Path(self.image_path).stem}_识别结果_v04.json"
            payload = {
                "image": Path(self.image_path).name,
                "recognized_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "label_count": len(labels),
                "labels": labels,
            }
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            self.finished_signal.emit({
                "success": True,
                "raw_result": summary,
                "output_path": str(output_path),
            })
        except Exception as error:
            self.finished_signal.emit({
                "success": False,
                "raw_result": f"处理失败: {error}",
                "output_path": "",
            })


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mr.6_Auto_OCR_Pipeline v0.4")
        self.setMinimumSize(820, 620)

        self.config = load_config()
        self.worker = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("JSON输出目录"))
        self.output_dir_input = QLineEdit(self.config["output_dir"])
        self.browse_output_btn = QPushButton("浏览...")
        self.browse_output_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(self.browse_output_btn)
        main_layout.addLayout(output_layout)

        action_layout = QHBoxLayout()
        self.select_button = QPushButton("选择图片并识别")
        self.select_button.clicked.connect(self.select_and_process_image)
        action_layout.addWidget(self.select_button)
        main_layout.addLayout(action_layout)

        self.status_label = QLabel("状态: 等待识别")
        main_layout.addWidget(self.status_label)

        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        main_layout.addWidget(self.result_display)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出文件夹", self.output_dir_input.text())
        if directory:
            self.output_dir_input.setText(directory)

    def select_and_process_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要识别的图片",
            str(BASE_DIR),
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)",
        )
        if not file_path:
            return

        config = {
            "output_dir": self.output_dir_input.text().strip() or self.config["output_dir"],
            "visual_output_dir": self.config["visual_output_dir"],
            "manual_output": self.config["manual_output"],
        }
        save_config(config)

        self.select_button.setEnabled(False)
        self.status_label.setText("状态: 正在处理...")
        self.worker = OcrWorker(file_path, config["output_dir"])
        self.worker.progress_signal.connect(self.on_progress_update)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_progress_update(self, status):
        self.status_label.setText(f"状态: {status}")

    def on_finished(self, results):
        self.select_button.setEnabled(True)
        if results["success"]:
            self.status_label.setText(f"状态: 识别完成，结果已保存到 {results['output_path']}")
        else:
            self.status_label.setText("状态: 识别失败")
        self.result_display.setPlainText(results["raw_result"])
        self.worker = None


def main():
    print("=== 正在启动 v0.4 GUI 原型 ===")
    print("该版本特点：开始将多标签分组结果组织成标签级结构化输出。")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
