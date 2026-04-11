# 跳过了不成功的0.3版本，直接进入了0.4版本。
# v0.5：在不牺牲文字/码识别稳定性的前提下，重点优化多标签分组策略与性能。
# 这么写注释感觉自己也像个专业人士了……

import sys
import os
import json
import math
import csv
import time
import statistics
from datetime import datetime
from pathlib import Path

# --- 为了抑制警告，沿用之前的机制 ---
if os.environ.get('PADDLE_SUPPRESS_WARNINGS') != '1':
    os.environ['PADDLE_SUPPRESS_WARNINGS'] = '1'
    import subprocess
    result = subprocess.run([sys.executable] + sys.argv, env=os.environ)
    sys.exit(result.returncode)
else:
    # --- 导入所有库 ---
    from paddleocr import PaddleOCR
    from pyzbar import pyzbar
    import cv2
    import numpy as np
    import re
    
    # 导入 watchdog 相关模块
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                                 QFileDialog, QTextEdit, QVBoxLayout, 
                                 QWidget, QLabel, QMessageBox, QProgressBar,
                                 QHBoxLayout, QLineEdit, QFrame, QGroupBox)
    from PyQt5.QtCore import QThread, pyqtSignal, Qt
    from PyQt5.QtGui import QFont


    # --- 配置文件管理 ---
    BASE_DIR = Path(r"E:\Mr.6_Auto_OCR_PipelineWithCodeX")
    CONFIG_FILE_PATH = str(BASE_DIR / "app_config_v05.json")

    def load_config():
        """从JSON文件加载配置"""
        default_config = {
            "watch_dir": str(BASE_DIR / "watch_directory"),
            "output_dir": str(BASE_DIR / "json_directory"),
            "processed_dir": str(BASE_DIR / "processed_directory"),
            "error_dir": str(BASE_DIR / "error_directory"),
            "visual_output_dir": str(BASE_DIR / "visual_outputs"),
            "txt_output_dir": str(BASE_DIR / "output_directory"),
            "manual_output": True,
            "ground_truth_csv": str(BASE_DIR / "multiple_labels_test" / "truth.csv"),
            "test_record_csv": str(BASE_DIR / "v0_5_grouping_test_records.csv")
        }
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保加载的配置包含所有必要的键
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                return config
            except Exception as e:
                print(f"加载配置文件失败: {e}, 使用默认配置")
        return default_config

    def save_config(config):
        """将配置保存到JSON文件"""
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def load_ground_truth_map(csv_path):
        truth_map = {}
        if not csv_path:
            return truth_map
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return truth_map
        try:
            with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    image_name = (row.get("image_name") or "").strip()
                    actual_count = (row.get("actual_label_count") or "").strip()
                    if not image_name or not actual_count:
                        continue
                    try:
                        truth_map[image_name] = int(actual_count)
                    except ValueError:
                        continue
        except Exception as e:
            print(f"读取真值表失败: {e}")
        return truth_map

    def build_grouping_test_record(image_name, predicted_count, elapsed_seconds, truth_map, success, error=""):
        actual_count = truth_map.get(image_name)
        label_count_correct = ""
        over_split = ""
        over_merge = ""
        if actual_count is not None:
            if predicted_count == actual_count:
                label_count_correct = "Yes"
                over_split = "No"
                over_merge = "No"
            elif predicted_count > actual_count:
                label_count_correct = "No"
                over_split = "Yes"
                over_merge = "No"
            else:
                label_count_correct = "No"
                over_split = "No"
                over_merge = "Yes"

        return {
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "image_name": image_name,
            "actual_label_count": "" if actual_count is None else actual_count,
            "predicted_label_count": predicted_count,
            "label_count_correct": label_count_correct,
            "over_split": over_split,
            "over_merge": over_merge,
            "success": "Yes" if success else "No",
            "elapsed_seconds": f"{elapsed_seconds:.4f}",
            "error": error
        }

    def append_grouping_test_record(record_csv_path, row):
        if not record_csv_path:
            return
        csv_file = Path(record_csv_path)
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "recorded_at",
            "image_name",
            "actual_label_count",
            "predicted_label_count",
            "label_count_correct",
            "over_split",
            "over_merge",
            "success",
            "elapsed_seconds",
            "error",
        ]
        file_exists = csv_file.exists()
        with open(csv_file, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    # --- 通用辅助函数 ---

    def _bbox_union(a, b):
        return [
            min(a[0], b[0]),
            min(a[1], b[1]),
            max(a[2], b[2]),
            max(a[3], b[3])
        ]

    def _bbox_expand(b, margin):
        return [b[0] - margin, b[1] - margin, b[2] + margin, b[3] + margin]

    def _bbox_intersect(a, b):
        return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])

    def _bbox_center(b):
        return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

    def _bbox_height(b):
        return max(1.0, b[3] - b[1])

    def _poly_to_bbox(poly):
        if not poly:
            return [0, 0, 0, 0]
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return [min(xs), min(ys), max(xs), max(ys)]

    def _overlap_ratio_1d(a1, a2, b1, b2):
        inter = max(0.0, min(a2, b2) - max(a1, b1))
        len_a = max(1.0, a2 - a1)
        len_b = max(1.0, b2 - b1)
        return inter / min(len_a, len_b)

    def _boxes_close(a, b, margin):
        if _bbox_intersect(_bbox_expand(a, margin), _bbox_expand(b, margin)):
            return True
        ax, ay = _bbox_center(a)
        bx, by = _bbox_center(b)
        dist_ok = math.hypot(ax - bx, ay - by) <= (margin * 2.2)
        if not dist_ok:
            return False
        overlap_x = _overlap_ratio_1d(a[0], a[2], b[0], b[2])
        overlap_y = _overlap_ratio_1d(a[1], a[3], b[1], b[3])
        return overlap_x > 0.2 or overlap_y > 0.2

    def _cluster_items(items, margin_override=None):
        if not items:
            return []

        heights = [_bbox_height(item["bbox"]) for item in items]
        median_height = statistics.median(heights) if heights else 20
        # 较大的间距，避免单标签被拆散
        margin = margin_override if margin_override is not None else max(18, int(median_height * 2.6))

        parent = list(range(len(items)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra = find(a)
            rb = find(b)
            if ra != rb:
                parent[rb] = ra

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if _boxes_close(items[i]["bbox"], items[j]["bbox"], margin):
                    union(i, j)

        groups = {}
        for i in range(len(items)):
            root = find(i)
            groups.setdefault(root, []).append(items[i])

        return list(groups.values())

    def _merge_groups(groups, margin):
        if not groups:
            return []
        merged = []
        used = [False] * len(groups)
        for i in range(len(groups)):
            if used[i]:
                continue
            current = list(groups[i])
            used[i] = True
            changed = True
            while changed:
                changed = False
                current_bbox = current[0]["bbox"]
                for item in current[1:]:
                    current_bbox = _bbox_union(current_bbox, item["bbox"])
                for j in range(len(groups)):
                    if used[j]:
                        continue
                    group_bbox = groups[j][0]["bbox"]
                    for item in groups[j][1:]:
                        group_bbox = _bbox_union(group_bbox, item["bbox"])
                    if _boxes_close(current_bbox, group_bbox, margin):
                        current.extend(groups[j])
                        used[j] = True
                        changed = True
            merged.append(current)
        return merged

    def _split_group_by_gap(group):
        if len(group) <= 4:
            return [group]

        heights = [_bbox_height(item["bbox"]) for item in group]
        median_height = statistics.median(heights) if heights else 20
        gap_threshold = max(40, int(median_height * 3.5))

        # 计算纵向/横向中心点间隙
        def best_gap(axis="y"):
            if axis == "y":
                centers = sorted([_bbox_center(i["bbox"])[1] for i in group])
            else:
                centers = sorted([_bbox_center(i["bbox"])[0] for i in group])
            gaps = [(centers[i+1] - centers[i], i) for i in range(len(centers)-1)]
            if not gaps:
                return 0, -1, centers
            gap, idx = max(gaps, key=lambda x: x[0])
            return gap, idx, centers

        gap_y, idx_y, centers_y = best_gap("y")
        gap_x, idx_x, centers_x = best_gap("x")

        if gap_y < gap_threshold and gap_x < gap_threshold:
            return [group]

        # 选择更明显的分割方向
        if gap_y >= gap_x:
            split_value = (centers_y[idx_y] + centers_y[idx_y + 1]) / 2.0
            top = [i for i in group if _bbox_center(i["bbox"])[1] <= split_value]
            bottom = [i for i in group if _bbox_center(i["bbox"])[1] > split_value]
            return [g for g in (top, bottom) if g]
        else:
            split_value = (centers_x[idx_x] + centers_x[idx_x + 1]) / 2.0
            left = [i for i in group if _bbox_center(i["bbox"])[0] <= split_value]
            right = [i for i in group if _bbox_center(i["bbox"])[0] > split_value]
            return [g for g in (left, right) if g]

    def _assign_texts_to_code_groups(text_items, code_items, margin):
        if not code_items:
            return [], text_items

        code_groups = [[c] for c in code_items]
        unassigned_texts = []

        for text in text_items:
            tx, ty = _bbox_center(text["bbox"])
            best_idx = -1
            best_dist = None

            for idx, group in enumerate(code_groups):
                group_bbox = group[0]["bbox"]
                for item in group[1:]:
                    group_bbox = _bbox_union(group_bbox, item["bbox"])

                gx, gy = _bbox_center(group_bbox)
                dist = math.hypot(tx - gx, ty - gy)
                if _boxes_close(text["bbox"], group_bbox, margin):
                    if best_dist is None or dist < best_dist:
                        best_dist = dist
                        best_idx = idx

            if best_idx >= 0:
                code_groups[best_idx].append(text)
            else:
                unassigned_texts.append(text)

        return code_groups, unassigned_texts

    def _build_label_groups(text_items, code_items):
        # 过滤空文本，避免碎片化
        text_items = [t for t in text_items if t.get("text") and str(t.get("text")).strip()]

        items = text_items + code_items
        if not items:
            return []

        heights = [_bbox_height(item["bbox"]) for item in items]
        median_height = statistics.median(heights) if heights else 20
        base_margin = max(20, int(median_height * 2.6))

        # Step 1: 以码作为锚点先聚类，提升多标签稳定性
        code_groups, remaining_texts = _assign_texts_to_code_groups(text_items, code_items, base_margin)

        # Step 2: 对剩余文本再做空间聚类
        text_only_groups = _cluster_items(remaining_texts, margin_override=base_margin) if remaining_texts else []

        groups = code_groups + text_only_groups

        # Step 3: 合并过度拆散的组（更保守）
        groups = _merge_groups(groups, margin=max(26, int(median_height * 3.6)))

        # Step 4: 如果分组过少，尝试按明显空隙再切分（提升多标签召回）
        refined = []
        for group in groups:
            splits = _split_group_by_gap(group)
            if len(splits) == 1:
                refined.append(group)
            else:
                # 再次尝试一次切分（最多两层）
                for g in splits:
                    refined.extend(_split_group_by_gap(g))
        groups = refined

        labels = []

        for idx, group in enumerate(groups, start=1):
            group_bbox = group[0]["bbox"]
            for item in group[1:]:
                group_bbox = _bbox_union(group_bbox, item["bbox"])

            texts = [i for i in group if i["type"] == "text"]
            codes = [i for i in group if i["type"] == "code"]

            texts.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))

            labels.append({
                "label_id": idx,
                "bbox": [int(v) for v in group_bbox],
                "texts": [
                    {
                        "text": t["text"],
                        "score": t.get("score"),
                        "bbox": [int(v) for v in t["bbox"]]
                    } for t in texts
                ],
                "codes": [
                    {
                        "type": c["code_type"],
                        "data": c["data"],
                        "bbox": [int(v) for v in c["bbox"]]
                    } for c in codes
                ]
            })

        return labels

    def _extract_text_items_from_ocr_result(ocr_result):
        text_items = []
        if isinstance(ocr_result, list) and ocr_result:
            first_page = ocr_result[0]
            if isinstance(first_page, list):
                for item in first_page:
                    if not isinstance(item, (list, tuple)) or len(item) < 2:
                        continue
                    text_info = item[1]
                    if not isinstance(text_info, (list, tuple)) or len(text_info) < 2:
                        continue
                    text = text_info[0]
                    score = text_info[1]
                    bbox = _poly_to_bbox(item[0]) if item[0] else [0, 0, 0, 0]
                    if text is None or str(text).strip() == "":
                        continue
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": score,
                        "bbox": bbox
                    })
                return text_items

        ocr_json = getattr(ocr_result, "json", None)

        if isinstance(ocr_json, list) and ocr_json:
            # 有些版本直接给 list[dict]
            if isinstance(ocr_json[0], dict):
                ocr_json = ocr_json[0]
            else:
                # list 中直接是条目
                for item in ocr_json:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text") or item.get("ocr_text")
                    if text is None:
                        continue
                    box = item.get("bbox") or item.get("box") or item.get("points") or item.get("text_box")
                    if box and isinstance(box, list) and len(box) == 4 and isinstance(box[0], (int, float)):
                        bbox = box
                    elif box and isinstance(box, list):
                        bbox = _poly_to_bbox(box)
                    else:
                        bbox = [0, 0, 0, 0]
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": item.get("score"),
                        "bbox": bbox
                    })
                return text_items

        if isinstance(ocr_json, dict):
            # 兼容 {"res": {...}} 结构
            if "res" in ocr_json and isinstance(ocr_json["res"], (dict, list)):
                ocr_json = ocr_json["res"]
                if isinstance(ocr_json, list) and ocr_json:
                    # 取第一页/第一项
                    if isinstance(ocr_json[0], dict):
                        ocr_json = ocr_json[0]
                    else:
                        # list 中直接是条目
                        for item in ocr_json:
                            if not isinstance(item, dict):
                                continue
                            text = item.get("text") or item.get("ocr_text")
                            if text is None or str(text).strip() == "":
                                continue
                            box = item.get("bbox") or item.get("box") or item.get("points") or item.get("text_box")
                            if box and isinstance(box, list) and len(box) == 4 and isinstance(box[0], (int, float)):
                                bbox = box
                            elif box and isinstance(box, list):
                                bbox = _poly_to_bbox(box)
                            else:
                                bbox = [0, 0, 0, 0]
                            text_items.append({
                                "type": "text",
                                "text": text,
                                "score": item.get("score"),
                                "bbox": bbox
                            })
                        return text_items

            rec_texts = (
                ocr_json.get("rec_texts")
                or ocr_json.get("ocr_texts")
                or ocr_json.get("texts")
                or []
            )
            rec_scores = (
                ocr_json.get("rec_scores")
                or ocr_json.get("scores")
                or []
            )
            rec_boxes = ocr_json.get("rec_boxes") or ocr_json.get("dt_boxes") or ocr_json.get("boxes") or []
            rec_polys = (
                ocr_json.get("rec_polys")
                or ocr_json.get("dt_polys")
                or ocr_json.get("det_polys")
                or []
            )

            if rec_boxes and len(rec_boxes) == len(rec_texts):
                for idx, text in enumerate(rec_texts):
                    if text is None or str(text).strip() == "":
                        continue
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": rec_scores[idx] if idx < len(rec_scores) else None,
                        "bbox": rec_boxes[idx]
                    })
                return text_items

            if rec_polys and len(rec_polys) == len(rec_texts):
                for idx, text in enumerate(rec_texts):
                    if text is None or str(text).strip() == "":
                        continue
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": rec_scores[idx] if idx < len(rec_scores) else None,
                        "bbox": _poly_to_bbox(rec_polys[idx])
                    })
                return text_items

            # 只有文本没有框时也保留
            if rec_texts and not rec_boxes and not rec_polys:
                for idx, text in enumerate(rec_texts):
                    if text is None or str(text).strip() == "":
                        continue
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": rec_scores[idx] if idx < len(rec_scores) else None,
                        "bbox": [0, 0, 0, 0]
                    })
                return text_items

            # 兼容 list[dict] 结构
            items = ocr_json.get("items") or ocr_json.get("res") or ocr_json.get("results") or []
            if items and isinstance(items, list):
                for item in items:
                    text = item.get("text")
                    if text is None:
                        text = item.get("ocr_text")
                    if text is None or str(text).strip() == "":
                        continue
                    box = item.get("bbox") or item.get("box") or item.get("points") or item.get("text_box")
                    if box and isinstance(box, list) and len(box) == 4 and isinstance(box[0], (int, float)):
                        bbox = box
                    elif box and isinstance(box, list):
                        bbox = _poly_to_bbox(box)
                    else:
                        bbox = [0, 0, 0, 0]
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": item.get("score"),
                        "bbox": bbox
                    })
                return text_items

        # 兜底：从属性里尝试拿文本列表
        res_attr = getattr(ocr_result, "res", None) or getattr(ocr_result, "results", None)
        if isinstance(res_attr, list) and res_attr:
            for item in res_attr:
                if not isinstance(item, dict):
                    continue
                text = item.get("text") or item.get("ocr_text")
                if text is None or str(text).strip() == "":
                    continue
                box = item.get("bbox") or item.get("box") or item.get("points") or item.get("text_box")
                if box and isinstance(box, list) and len(box) == 4 and isinstance(box[0], (int, float)):
                    bbox = box
                elif box and isinstance(box, list):
                    bbox = _poly_to_bbox(box)
                else:
                    bbox = [0, 0, 0, 0]
                text_items.append({
                    "type": "text",
                    "text": text,
                    "score": item.get("score"),
                    "bbox": bbox
                })
            return text_items

        fallback_texts = getattr(ocr_result, "rec_texts", None) or []
        fallback_scores = getattr(ocr_result, "rec_scores", None) or []
        fallback_boxes = getattr(ocr_result, "rec_boxes", None) or []
        for idx, text in enumerate(fallback_texts):
            if text is None or str(text).strip() == "":
                continue
            box = fallback_boxes[idx] if idx < len(fallback_boxes) else [0, 0, 0, 0]
            text_items.append({
                "type": "text",
                "text": text,
                "score": fallback_scores[idx] if idx < len(fallback_scores) else None,
                "bbox": box
            })

        return text_items

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
                    lines.append(f"    - [{c['type']}] {c['data']}")
            else:
                lines.append("  码: [无]")
        return "\n".join(lines)

    def _save_visual_result(result_obj, image_path, visual_output_dir):
        if not visual_output_dir:
            return ""
        visual_dir = Path(visual_output_dir)
        visual_dir.mkdir(parents=True, exist_ok=True)
        result_obj.save_to_img(str(visual_dir))

        image_path_obj = Path(image_path)
        visual_name = f"{image_path_obj.stem}_ocr_res_img{image_path_obj.suffix}"
        return str(visual_dir / visual_name)


    # --- 1. 实时监控模式所需的核心类  ---

    class ImageHandler(FileSystemEventHandler):
        """
        文件系统事件处理器，专门处理图片文件的创建事件。
        """
        def __init__(self, ocr_engine, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir, manual_output, log_callback, truth_csv_path="", record_csv_path=""):
            super().__init__()
            self.ocr = ocr_engine
            self.processed_path = Path(processed_dir)
            self.error_path = Path(error_dir)
            self.output_path = Path(output_dir)
            self.visual_output_path = Path(visual_output_dir) if visual_output_dir else None
            self.txt_output_path = Path(txt_output_dir) if txt_output_dir else None
            self.manual_output = manual_output
            self.log_callback = log_callback # GUI的日志回调函数
            self.truth_map = load_ground_truth_map(truth_csv_path)
            self.record_csv_path = record_csv_path
            # 确保目标文件夹存在
            self.processed_path.mkdir(parents=True, exist_ok=True)
            self.error_path.mkdir(parents=True, exist_ok=True)
            self.output_path.mkdir(parents=True, exist_ok=True)
            if self.visual_output_path:
                self.visual_output_path.mkdir(parents=True, exist_ok=True)
            if self.txt_output_path:
                self.txt_output_path.mkdir(parents=True, exist_ok=True)

        def on_created(self, event):
            """
            当文件被创建时调用此方法。
            """
            if event.is_directory:
                return

            file_path = Path(event.src_path)
            # 只处理图片文件
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                self.log_callback(f"[{datetime.now()}] 检测到新图片: {file_path.name}")
                
                # 调用处理函数
                success = self.process_image(file_path)
                
                # 日志反馈
                if success:
                    self.log_callback(f"  -> 识别成功")
                else:
                    self.log_callback("  -> 识别失败或效果差，移动到异常文件夹")

        def process_image(self, image_path):
            """
            处理单张图片的核心逻辑。
            返回 True 表示处理成功（或至少识别到了一些东西）。
            返回 False 表示处理失败或效果极差。
            """
            try:
                start_time = time.perf_counter()
                # --- 1. 加载图片 ---
                image_cv = cv2.imread(str(image_path))
                if image_cv is None:
                    self.log_callback(f"    -> 无法读取图片文件 {image_path}")
                    return False

                # --- 2. OCR 识别 (PaddleOCR 3.x) ---
                self.log_callback("    正在进行 OCR 识别...")
                ocr_results = self.ocr.ocr(str(image_path))
                if not ocr_results:
                    self.log_callback("    -> OCR 返回空结果")
                    return False

                text_items = _extract_text_items_from_ocr_result(ocr_results)
                if not text_items:
                    debug_path = self.output_path / f"{image_path.stem}_ocr_debug.json"
                    try:
                        debug_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(debug_path, "w", encoding="utf-8") as f:
                            json.dump(ocr_results, f, ensure_ascii=False, indent=2)
                        self.log_callback(f"    -> 未解析到文字，已输出调试JSON: {debug_path}")
                    except Exception as e:
                        self.log_callback(f"    -> 未解析到文字，调试JSON保存失败: {e}")

                # --- 3. 码识别 ---
                self.log_callback("    正在进行码识别...")
                decoded_objects = pyzbar.decode(image_cv)
                code_items = []
                for obj in decoded_objects:
                    rect = obj.rect
                    bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                    code_items.append({
                        "type": "code",
                        "code_type": obj.type,
                        "data": obj.data.decode("utf-8"),
                        "bbox": bbox
                    })

                # --- 4. 标签分组 ---
                labels = _build_label_groups(text_items, code_items)
                elapsed_seconds = time.perf_counter() - start_time

                # --- 5. 保存结构化结果 ---
                base_name = image_path.stem
                if self.manual_output:
                    output_path = self.output_path / f"{base_name}_识别结果.json"
                else:
                    output_path = image_path.parent / f"{base_name}_识别结果.json"

                result_payload = {
                    "image": image_path.name,
                    "recognized_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "label_count": len(labels),
                    "labels": labels
                }

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result_payload, f, ensure_ascii=False, indent=2)

                self.log_callback(f"    -> 结构化结果已保存至: {output_path}")

                # --- 6. 保存TXT结果 ---
                if self.txt_output_path:
                    txt_name = f"{image_path.stem}_OCR_results.txt"
                    txt_path = self.txt_output_path / txt_name
                    try:
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(_format_labels_summary(labels))
                        self.log_callback(f"    -> TXT结果已保存至: {txt_path}")
                    except Exception as e:
                        self.log_callback(f"    -> TXT保存失败: {e}")

                # --- 6. 保存可视化结果 ---
                visual_path = ""
                if self.visual_output_path:
                    self.log_callback("    -> 当前环境下未输出 OCR 可视化图片。")

                # --- 7. 质量评估与文件移动 ---
                ocr_success = len(text_items) > 0
                code_success = len(code_items) > 0

                if ocr_success or code_success:
                    dest_file = self.processed_path / image_path.name
                    os.replace(str(image_path), str(dest_file))
                    self.log_callback(f"    -> 文件移动到已处理文件夹: {dest_file}")
                    test_row = build_grouping_test_record(
                        image_path.name,
                        len(labels),
                        elapsed_seconds,
                        self.truth_map,
                        True
                    )
                    append_grouping_test_record(self.record_csv_path, test_row)
                    if test_row["actual_label_count"] != "":
                        self.log_callback(
                            f"    -> 标签数量评估: 实际={test_row['actual_label_count']}，预测={test_row['predicted_label_count']}，"
                            f"正确={test_row['label_count_correct']}，误拆分={test_row['over_split']}，误合并={test_row['over_merge']}"
                        )
                    self.log_callback(f"    -> 处理耗时: {elapsed_seconds:.4f} s")
                    return True
                else:
                    dest_file = self.error_path / image_path.name
                    os.replace(str(image_path), str(dest_file))
                    self.log_callback(f"    -> 文件移动到异常文件夹: {dest_file}")
                    test_row = build_grouping_test_record(
                        image_path.name,
                        len(labels),
                        elapsed_seconds,
                        self.truth_map,
                        False,
                        error="未识别到有效文本或编码信息"
                    )
                    append_grouping_test_record(self.record_csv_path, test_row)
                    self.log_callback(f"    -> 处理耗时: {elapsed_seconds:.4f} s")
                    return False
                        
            except Exception as e:
                self.log_callback(f"    -> 处理图片 {image_path.name} 时发生错误: {e}")
                try:
                    elapsed_seconds = time.perf_counter() - start_time
                except Exception:
                    elapsed_seconds = 0.0
                test_row = build_grouping_test_record(
                    image_path.name,
                    0,
                    elapsed_seconds,
                    self.truth_map,
                    False,
                    error=str(e)
                )
                append_grouping_test_record(self.record_csv_path, test_row)
                return False


    class WatcherThread(QThread):
        """
        用于在后台启动和停止 watchdog 监控的线程。
        """
        log_signal = pyqtSignal(str)
        
        def __init__(self, watch_dir, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir, manual_output, truth_csv_path="", record_csv_path=""):
            super().__init__()
            self.watch_dir = watch_dir
            self.processed_dir = processed_dir
            self.error_dir = error_dir
            self.output_dir = output_dir
            self.visual_output_dir = visual_output_dir
            self.txt_output_dir = txt_output_dir
            self.manual_output = manual_output
            self.truth_csv_path = truth_csv_path
            self.record_csv_path = record_csv_path
            self.observer = Observer()
            self.ocr = PaddleOCR(lang='ch', use_gpu=False)

        def run(self):
            """
            启动监控。
            """
            event_handler = ImageHandler(
                self.ocr,
                self.processed_dir,
                self.error_dir,
                self.output_dir,
                self.visual_output_dir,
                self.txt_output_dir,
                self.manual_output,
                self.log_signal.emit,
                self.truth_csv_path,
                self.record_csv_path
            )
            self.observer.schedule(event_handler, self.watch_dir, recursive=False)
            self.observer.start()
            
            try:
                while not self.isInterruptionRequested(): # 使用 isInterruptionRequested 检查停止信号
                    self.msleep(1000)  # 休眠1秒，避免CPU占用过高
            finally:
                self.observer.stop()
                self.observer.join()
                self.log_signal.emit("--- 监控已停止 ---")

        def stop_watching(self):
            """
            请求停止监控。
            """
            self.requestInterruption()


    # --- 2. 单次识别模式所需的核心类  ---

    class OcrWorker(QThread):
        """
        后台工作线程，用于执行OCR和码识别，防止GUI界面冻结。
        """
        finished_signal = pyqtSignal(dict)  # 任务完成信号，携带结果数据
        progress_signal = pyqtSignal(str)  # 进度更新信号

        def __init__(self, image_path, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir, manual_output, truth_csv_path="", record_csv_path=""):
            super().__init__()
            self.image_path = image_path
            self.processed_dir = processed_dir
            self.error_dir = error_dir
            self.output_dir = output_dir
            self.visual_output_dir = visual_output_dir
            self.txt_output_dir = txt_output_dir
            self.manual_output = manual_output
            self.truth_map = load_ground_truth_map(truth_csv_path)
            self.record_csv_path = record_csv_path
            self.ocr = PaddleOCR(lang='ch', use_gpu=False)

        def run(self):
            """
            在后台线程中执行识别任务。
            """
            try:
                start_time = time.perf_counter()
                results = {"success": False, "raw_result": "", "output_path": "", "visual_output_path": ""}

                self.progress_signal.emit("正在加载图片...")
                image_cv = cv2.imread(self.image_path)
                if image_cv is None:
                    raise ValueError(f"无法读取图片文件 {self.image_path}")

                # --- 1. OCR 识别 (PaddleOCR 3.x) ---
                self.progress_signal.emit("正在进行 OCR 识别...")
                ocr_results = self.ocr.ocr(self.image_path)
                if not ocr_results:
                    raise ValueError("OCR 返回空结果")

                text_items = _extract_text_items_from_ocr_result(ocr_results)
                if not text_items:
                    debug_path = Path(self.output_dir) / f"{Path(self.image_path).stem}_ocr_debug.json"
                    try:
                        debug_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(debug_path, "w", encoding="utf-8") as f:
                            json.dump(ocr_results, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                # --- 2. 码识别 ---
                self.progress_signal.emit("正在进行码识别...")
                decoded_objects = pyzbar.decode(image_cv)
                code_items = []
                for obj in decoded_objects:
                    rect = obj.rect
                    bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                    code_items.append({
                        "type": "code",
                        "code_type": obj.type,
                        "data": obj.data.decode("utf-8"),
                        "bbox": bbox
                    })

                # --- 3. 标签分组 ---
                labels = _build_label_groups(text_items, code_items)
                elapsed_seconds = time.perf_counter() - start_time

                # --- 4. 生成可读摘要 ---
                image_path_obj = Path(self.image_path)
                results["raw_result"] = _format_labels_summary(labels)

                # --- 5. 保存结构化结果 ---
                base_name = image_path_obj.stem
                if self.manual_output:
                    output_path = Path(self.output_dir) / f"{base_name}_识别结果.json"
                else:
                    output_path = image_path_obj.parent / f"{base_name}_识别结果.json"

                result_payload = {
                    "image": image_path_obj.name,
                    "recognized_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "label_count": len(labels),
                    "labels": labels
                }

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result_payload, f, ensure_ascii=False, indent=2)

                results["output_path"] = str(output_path)

                # --- 6. 保存可视化结果 ---
                results["visual_output_path"] = ""

                # --- 6. 保存TXT结果 ---
                if self.txt_output_dir:
                    txt_name = f"{image_path_obj.stem}_OCR_results.txt"
                    txt_path = Path(self.txt_output_dir) / txt_name
                    try:
                        txt_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(results["raw_result"])
                    except Exception:
                        pass

                # --- 7. 移动原图片 ---
                try:
                    target_dir = self.processed_dir
                    if target_dir:
                        target_path = Path(target_dir)
                        target_path.mkdir(parents=True, exist_ok=True)
                        dest_file = target_path / image_path_obj.name
                        os.replace(self.image_path, str(dest_file))
                except Exception:
                    pass

                results["success"] = True
                test_row = build_grouping_test_record(
                    image_path_obj.name,
                    len(labels),
                    elapsed_seconds,
                    self.truth_map,
                    True
                )
                append_grouping_test_record(self.record_csv_path, test_row)
                if test_row["actual_label_count"] != "":
                    results["raw_result"] += (
                        f"\n\n[标签数量评估]\n"
                        f"实际标签数: {test_row['actual_label_count']}\n"
                        f"预测标签数: {test_row['predicted_label_count']}\n"
                        f"标签数量判断正确: {test_row['label_count_correct']}\n"
                        f"误拆分: {test_row['over_split']}\n"
                        f"误合并: {test_row['over_merge']}"
                    )
                results["raw_result"] += f"\n\n[处理耗时]\n{elapsed_seconds:.4f} s"

                self.finished_signal.emit(results)

            except Exception as e:
                try:
                    elapsed_seconds = time.perf_counter() - start_time
                except Exception:
                    elapsed_seconds = 0.0
                error_results = {
                    "success": False,
                    "error": str(e),
                    "raw_result": f"处理失败: {str(e)}",
                    "output_path": "",
                    "visual_output_path": ""
                }
                try:
                    if self.error_dir:
                        target_path = Path(self.error_dir)
                        target_path.mkdir(parents=True, exist_ok=True)
                        dest_file = target_path / Path(self.image_path).name
                        os.replace(self.image_path, str(dest_file))
                except Exception:
                    pass
                test_row = build_grouping_test_record(
                    Path(self.image_path).name,
                    0,
                    elapsed_seconds,
                    self.truth_map,
                    False,
                    error=str(e)
                )
                append_grouping_test_record(self.record_csv_path, test_row)
                self.finished_signal.emit(error_results)


    # --- 3. 主窗口类  ---

    class MainWindow(QMainWindow):
        """
        主窗口类，定义GUI界面和交互逻辑。
        """
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Mr.6's Auto OCR Pipeline v0.5")
            self.setGeometry(100, 100, 800, 700)

            # 加载配置
            self.config = load_config()
            self.watch_dir = self.config.get("watch_dir", str(BASE_DIR / "watch_directory"))
            self.output_dir = self.config.get("output_dir", str(BASE_DIR / "json_directory"))
            self.processed_dir = self.config.get("processed_dir", str(BASE_DIR / "processed_directory"))
            self.error_dir = self.config.get("error_dir", str(BASE_DIR / "error_directory"))
            self.visual_output_dir = self.config.get("visual_output_dir", str(BASE_DIR / "visual_outputs"))
            self.txt_output_dir = self.config.get("txt_output_dir", str(BASE_DIR / "output_directory"))
            self.manual_output = self.config.get("manual_output", True)
            self.ground_truth_csv = self.config.get("ground_truth_csv", str(BASE_DIR / "multiple_labels_test" / "truth.csv"))
            self.test_record_csv = self.config.get("test_record_csv", str(BASE_DIR / "v0_5_grouping_test_records.csv"))

            # 存储单次识别的最新结果，用于手动保存
            self.last_raw_result = ""

            # 中央窗口部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 主布局
            main_layout = QVBoxLayout(central_widget)

            # --- 全局设置区域 ---
            settings_group = QGroupBox("全局设置")
            settings_layout = QVBoxLayout(settings_group)

            # 输出文件夹设置
            output_dir_hbox = QHBoxLayout()
            self.output_dir_label = QLabel("JSON输出文件夹")
            self.output_dir_input = QLineEdit(self.output_dir)
            self.browse_output_dir_btn = QPushButton("浏览...")
            self.browse_output_dir_btn.clicked.connect(lambda: self.browse_directory(self.output_dir_input))
            output_dir_hbox.addWidget(self.output_dir_label)
            output_dir_hbox.addWidget(self.output_dir_input)
            output_dir_hbox.addWidget(self.browse_output_dir_btn)

            # 可视化输出文件夹设置
            visual_output_dir_hbox = QHBoxLayout()
            self.visual_output_dir_label = QLabel("可视化输出文件夹")
            self.visual_output_dir_input = QLineEdit(self.visual_output_dir)
            self.browse_visual_output_dir_btn = QPushButton("浏览...")
            self.browse_visual_output_dir_btn.clicked.connect(lambda: self.browse_directory(self.visual_output_dir_input))
            visual_output_dir_hbox.addWidget(self.visual_output_dir_label)
            visual_output_dir_hbox.addWidget(self.visual_output_dir_input)
            visual_output_dir_hbox.addWidget(self.browse_visual_output_dir_btn)

            # TXT输出文件夹设置
            txt_output_dir_hbox = QHBoxLayout()
            self.txt_output_dir_label = QLabel("TXT输出文件夹")
            self.txt_output_dir_input = QLineEdit(self.txt_output_dir)
            self.browse_txt_output_dir_btn = QPushButton("浏览...")
            self.browse_txt_output_dir_btn.clicked.connect(lambda: self.browse_directory(self.txt_output_dir_input))
            txt_output_dir_hbox.addWidget(self.txt_output_dir_label)
            txt_output_dir_hbox.addWidget(self.txt_output_dir_input)
            txt_output_dir_hbox.addWidget(self.browse_txt_output_dir_btn)
            
            # 清除输出按钮
            self.clear_outputs_btn = QPushButton("清除所有输出文件")
            self.clear_outputs_btn.clicked.connect(self.clear_all_outputs)

            # 输出模式切换
            self.output_mode_label = QLabel(f"当前输出模式: {'手动输出' if self.manual_output else '自动输出'}")
            self.output_mode_label.setStyleSheet("font-weight: bold; color: green;" if self.manual_output else "font-weight: bold; color: orange;")
            self.toggle_output_mode_btn = QPushButton('切换输出模式')
            self.toggle_output_mode_btn.clicked.connect(self.toggle_output_mode)

            settings_layout.addLayout(output_dir_hbox)
            settings_layout.addLayout(visual_output_dir_hbox)
            settings_layout.addLayout(txt_output_dir_hbox)

            truth_csv_hbox = QHBoxLayout()
            self.truth_csv_label = QLabel("真值表CSV")
            self.truth_csv_input = QLineEdit(self.ground_truth_csv)
            self.browse_truth_csv_btn = QPushButton("浏览...")
            self.browse_truth_csv_btn.clicked.connect(lambda: self.browse_file(self.truth_csv_input, "CSV文件 (*.csv)"))
            truth_csv_hbox.addWidget(self.truth_csv_label)
            truth_csv_hbox.addWidget(self.truth_csv_input)
            truth_csv_hbox.addWidget(self.browse_truth_csv_btn)

            test_record_csv_hbox = QHBoxLayout()
            self.test_record_csv_label = QLabel("测试记录CSV")
            self.test_record_csv_input = QLineEdit(self.test_record_csv)
            self.browse_test_record_csv_btn = QPushButton("浏览...")
            self.browse_test_record_csv_btn.clicked.connect(lambda: self.browse_save_file(self.test_record_csv_input, "CSV文件 (*.csv)"))
            test_record_csv_hbox.addWidget(self.test_record_csv_label)
            test_record_csv_hbox.addWidget(self.test_record_csv_input)
            test_record_csv_hbox.addWidget(self.browse_test_record_csv_btn)

            settings_layout.addLayout(truth_csv_hbox)
            settings_layout.addLayout(test_record_csv_hbox)
            settings_layout.addWidget(self.clear_outputs_btn)
            
            output_mode_hbox = QHBoxLayout()
            output_mode_hbox.addWidget(self.output_mode_label)
            output_mode_hbox.addStretch()
            output_mode_hbox.addWidget(self.toggle_output_mode_btn)
            settings_layout.addLayout(output_mode_hbox)

            main_layout.addWidget(settings_group)

            # --- 模式切换按钮 ---
            switch_mode_layout = QHBoxLayout()
            self.mode_label = QLabel("当前模式: 单次识别")
            self.mode_label.setStyleSheet("font-weight: bold; color: blue;")
            self.toggle_mode_btn = QPushButton('切换为实时监控模式')
            self.toggle_mode_btn.clicked.connect(self.toggle_mode)
            
            switch_mode_layout.addWidget(self.mode_label)
            switch_mode_layout.addStretch()
            switch_mode_layout.addWidget(self.toggle_mode_btn)
            main_layout.addLayout(switch_mode_layout)

            # --- 分隔线 ---
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            main_layout.addWidget(separator)

            # --- 动态内容区(根据模式切换) ---
            self.dynamic_content_widget = QWidget()
            self.dynamic_content_layout = QVBoxLayout(self.dynamic_content_widget)
            main_layout.addWidget(self.dynamic_content_widget)

            # --- 输出区标题 ---
            self.output_section_label = QLabel("输出")
            self.output_section_label.setFont(QFont("Arial", 10, QFont.Bold))
            self.output_section_label.setStyleSheet("color: #0066CC;") # 蓝色
            main_layout.addWidget(self.output_section_label)

            # --- 日志/结果显示区域---
            self.result_display = QTextEdit()
            self.result_display.setReadOnly(True)
            main_layout.addWidget(self.result_display)

            # --- 手动保存按钮 (始终可见) ---
            self.save_manual_btn = QPushButton("手动保存当前结果到输出文件夹")
            self.save_manual_btn.clicked.connect(self.save_current_result_manually)
            self.save_manual_btn.setEnabled(False) # 初始时禁用
            main_layout.addWidget(self.save_manual_btn)

            # 初始化为单次识别模式
            self.current_mode = "single" 
            self.watcher_thread = None
            self.worker = None
            self.update_ui_for_mode()

        def closeEvent(self, event):
            """窗口关闭时保存配置"""
            self.config["watch_dir"] = self.watch_dir_input.text() if hasattr(self, "watch_dir_input") else self.watch_dir
            self.config["output_dir"] = self.output_dir_input.text()
            self.config["processed_dir"] = self.processed_dir_input.text() if hasattr(self, "processed_dir_input") else self.processed_dir
            self.config["error_dir"] = self.error_dir_input.text() if hasattr(self, "error_dir_input") else self.error_dir
            self.config["visual_output_dir"] = self.visual_output_dir_input.text()
            self.config["txt_output_dir"] = self.txt_output_dir_input.text()
            self.config["manual_output"] = self.manual_output
            self.config["ground_truth_csv"] = self.truth_csv_input.text()
            self.config["test_record_csv"] = self.test_record_csv_input.text()
            save_config(self.config)
            event.accept()

        def toggle_output_mode(self):
            """切换手动/自动输出模式"""
            self.manual_output = not self.manual_output
            self.output_mode_label.setText(f"当前输出模式: {'手动输出' if self.manual_output else '自动输出'}")
            self.output_mode_label.setStyleSheet("font-weight: bold; color: green;" if self.manual_output else "font-weight: bold; color: orange;")
            self.log_message(f"--- 输出模式已切换为: {'手动输出' if self.manual_output else '自动输出'} ---")

        def clear_all_outputs(self):
            """清除指定输出文件夹内的所有txt文件"""
            output_path = Path(self.output_dir_input.text().strip())
            if not output_path.exists() or not output_path.is_dir():
                QMessageBox.warning(self, "警告", f"输出文件夹路径无效: {output_path}")
                return

            txt_files = list(output_path.glob("*.txt"))
            if not txt_files:
                QMessageBox.information(self, "信息", f"输出文件夹 '{output_path}' 中没有找到任何 .txt 文件。")
                return

            reply = QMessageBox.question(self, '确认', f'您确定要删除 "{output_path}" 文件夹中共 {len(txt_files)} 个 .txt 文件吗？此操作不可逆！',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                deleted_count = 0
                for txt_file in txt_files:
                    try:
                        txt_file.unlink()
                        deleted_count += 1
                    except OSError as e:
                        self.log_message(f"删除文件 {txt_file} 失败: {e}")
                
                QMessageBox.information(self, "完成", f"已成功删除 {deleted_count} 个 .txt 文件。")
                self.log_message(f"--- 清除 {deleted_count} 个输出文件 ---")

        def save_current_result_manually(self):
            """手动将当前显示的结果保存到指定的输出文件夹"""
            current_text = self.result_display.toPlainText()
            if not current_text.strip():
                QMessageBox.information(self, "信息", "当前没有可保存的内容。")
                return
            
            if not self.last_raw_result.strip():
                 QMessageBox.information(self, "信息", "没有最新的识别结果可供保存。请先进行一次识别。")
                 return

            output_path = Path(self.output_dir_input.text().strip())
            if not output_path.exists() or not output_path.is_dir():
                QMessageBox.critical(self, "错误", f"输出文件夹路径无效: {output_path}")
                return

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"手动保存_{timestamp}.txt"
            full_path = output_path / filename

            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(self.last_raw_result) # 保存原始格式的结果
                QMessageBox.information(self, "成功", f"结果已手动保存至:\n{full_path}")
                self.log_message(f"--- 手动保存结果到 {full_path} ---")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件时出错: {e}")


        def toggle_mode(self):
            """切换当前工作模式。"""
            if self.current_mode == "single":
                # 切换到监控模式
                self.current_mode = "watch"
                self.mode_label.setText("当前模式: 实时监控")
                self.toggle_mode_btn.setText('切换为单次识别模式')
                self.log_message("--- 模式已切换为: 实时监控 ---")
            else:
                # 切换到单次识别模式
                self.current_mode = "single"
                self.mode_label.setText("当前模式: 单次识别")
                self.toggle_mode_btn.setText('切换为实时监控模式')
                # 如果监控正在运行，先停止
                if self.watcher_thread and self.watcher_thread.isRunning():
                    self.stop_watching()
                self.log_message("--- 模式已切换为: 单次识别 ---")
            
            self.update_ui_for_mode()

        def update_ui_for_mode(self):
            """根据当前模式更新UI控件。"""
            # --- 关键修复：完全清空动态内容区域的布局和控件 ---
            while self.dynamic_content_layout.count():
                child = self.dynamic_content_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())
                    child.layout().deleteLater()
            
            # --- 重新创建新模式的UI ---
            if self.current_mode == "single":
                # --- 单次识别模式UI ---
                self.select_button = QPushButton('选择图片并识别')
                self.select_button.clicked.connect(self.select_and_process_image)
                self.progress_bar = QProgressBar()
                self.progress_bar.setVisible(False)
                self.status_label = QLabel('就绪')

                processed_hbox = QHBoxLayout()
                self.processed_dir_label = QLabel("原图归档文件夹（处理后）:")
                self.processed_dir_input = QLineEdit(self.processed_dir)
                self.browse_processed_dir_btn = QPushButton("浏览...")
                self.browse_processed_dir_btn.clicked.connect(lambda: self.browse_directory(self.processed_dir_input))
                processed_hbox.addWidget(self.processed_dir_input)
                processed_hbox.addWidget(self.browse_processed_dir_btn)

                error_hbox = QHBoxLayout()
                self.error_dir_label = QLabel("异常图片文件夹:")
                self.error_dir_input = QLineEdit(self.error_dir)
                self.browse_error_dir_btn = QPushButton("浏览...")
                self.browse_error_dir_btn.clicked.connect(lambda: self.browse_directory(self.error_dir_input))
                error_hbox.addWidget(self.error_dir_input)
                error_hbox.addWidget(self.browse_error_dir_btn)

                self.dynamic_content_layout.addWidget(self.select_button)
                self.dynamic_content_layout.addWidget(self.processed_dir_label)
                self.dynamic_content_layout.addLayout(processed_hbox)
                self.dynamic_content_layout.addWidget(self.error_dir_label)
                self.dynamic_content_layout.addLayout(error_hbox)
                self.dynamic_content_layout.addWidget(self.progress_bar)
                self.dynamic_content_layout.addWidget(self.status_label)

            elif self.current_mode == "watch":
                # --- 实时监控模式UI ---
                self.watch_dir_label = QLabel("监控文件夹")
                self.watch_dir_input = QLineEdit(self.watch_dir)
                self.browse_watch_dir_btn = QPushButton("浏览...")
                self.browse_watch_dir_btn.clicked.connect(lambda: self.browse_directory(self.watch_dir_input))

                dir_hbox = QHBoxLayout()
                dir_hbox.addWidget(self.watch_dir_input)
                dir_hbox.addWidget(self.browse_watch_dir_btn)
                
                self.processed_dir_label = QLabel("原图归档文件夹（处理后）:")
                self.processed_dir_input = QLineEdit(self.processed_dir)
                self.browse_processed_dir_btn = QPushButton("浏览...")
                self.browse_processed_dir_btn.clicked.connect(lambda: self.browse_directory(self.processed_dir_input))

                processed_hbox = QHBoxLayout()
                processed_hbox.addWidget(self.processed_dir_input)
                processed_hbox.addWidget(self.browse_processed_dir_btn)
                
                self.error_dir_label = QLabel("异常图片文件夹")
                self.error_dir_input = QLineEdit(self.error_dir)
                self.browse_error_dir_btn = QPushButton("浏览...")
                self.browse_error_dir_btn.clicked.connect(lambda: self.browse_directory(self.error_dir_input))

                error_hbox = QHBoxLayout()
                error_hbox.addWidget(self.error_dir_input)
                error_hbox.addWidget(self.browse_error_dir_btn)

                self.start_watch_btn = QPushButton("开始监控")
                self.start_watch_btn.clicked.connect(self.start_watching)
                self.stop_watch_btn = QPushButton("停止监控")
                self.stop_watch_btn.clicked.connect(self.stop_watching)
                self.stop_watch_btn.setEnabled(False) # 初始时禁用

                button_hbox = QHBoxLayout()
                button_hbox.addWidget(self.start_watch_btn)
                button_hbox.addWidget(self.stop_watch_btn)

                self.dynamic_content_layout.addWidget(self.watch_dir_label)
                self.dynamic_content_layout.addLayout(dir_hbox)
                self.dynamic_content_layout.addWidget(self.processed_dir_label)
                self.dynamic_content_layout.addLayout(processed_hbox)
                self.dynamic_content_layout.addWidget(self.error_dir_label)
                self.dynamic_content_layout.addLayout(error_hbox)
                self.dynamic_content_layout.addLayout(button_hbox)

        def clear_layout(self, layout):
            """递归清空一个布局内的所有子布局和控件。"""
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())
                    child.layout().deleteLater()

        def browse_directory(self, line_edit):
            """通用的目录浏览函数。"""
            directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
            if directory:
                line_edit.setText(directory)

        def browse_file(self, line_edit, file_filter):
            file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", file_filter)
            if file_path:
                line_edit.setText(file_path)

        def browse_save_file(self, line_edit, file_filter):
            file_path, _ = QFileDialog.getSaveFileName(self, "选择保存路径", line_edit.text().strip() or "", file_filter)
            if file_path:
                line_edit.setText(file_path)

        # --- 单次识别模式相关方法 ---
        def select_and_process_image(self):
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择要识别的图片",
                "",
                "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff);;所有文件(*)"
            )
            
            if not file_path:
                return  # 用户取消了选择

            self.select_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.status_label.setText("正在处理...")

            # 使用当前配置的输出目录和模式
            # 单次识别模式下需要处理后/异常/输出/可视化文件夹
            processed_dir = self.processed_dir_input.text().strip()
            error_dir = self.error_dir_input.text().strip()
            output_dir = self.output_dir_input.text().strip()
            visual_output_dir = self.visual_output_dir_input.text().strip()
            txt_output_dir = self.txt_output_dir_input.text().strip()
            truth_csv_path = self.truth_csv_input.text().strip()
            test_record_csv = self.test_record_csv_input.text().strip()

            if not all([processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir, truth_csv_path, test_record_csv]):
                QMessageBox.warning(self, "警告", "请填写处理后、异常、JSON、可视化、TXT、真值表CSV和测试记录CSV路径。")
                return

            self.worker = OcrWorker(
                file_path,
                processed_dir,
                error_dir,
                output_dir,
                visual_output_dir,
                txt_output_dir,
                self.manual_output,
                truth_csv_path,
                test_record_csv
            )
            self.worker.finished_signal.connect(self.on_single_process_finished)
            self.worker.progress_signal.connect(self.on_progress_update)
            self.worker.start()

        def on_progress_update(self, status):
            self.status_label.setText(status)

        def on_single_process_finished(self, results):
            self.select_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.progress_bar.setRange(0, 100) # Reset to determinate
            
            image_path_str = self.worker.image_path
            image_path_obj = Path(image_path_str)
            base_name = image_path_obj.stem

            if results["success"]:
                # 保存原始结果用于手动保存
                self.last_raw_result = results.get("raw_result", "")
                self.save_manual_btn.setEnabled(True) # 识别成功后启用手动保存按钮

                output_path = results.get("output_path", "")
                visual_path = results.get("visual_output_path", "")
                if visual_path:
                    self.status_label.setText(f"识别完成，结果已保存到: {output_path} | 可视化: {visual_path}")
                else:
                    self.status_label.setText(f"识别完成，结果已保存到: {output_path}")
                
                display_text = self.last_raw_result # 显示原始格式的结果

            else:
                error_msg = f"处理失败: {results.get('error', '未知错误')}"
                self.status_label.setText(error_msg)
                display_text = error_msg
                self.save_manual_btn.setEnabled(False) # 失败时禁用手动保存

            self.result_display.setPlainText(display_text)
            self.worker = None


        # --- 实时监控模式相关方法 ---
        def start_watching(self):
            watch_dir = self.watch_dir_input.text().strip()
            processed_dir = self.processed_dir_input.text().strip()
            error_dir = self.error_dir_input.text().strip()
            output_dir = self.output_dir_input.text().strip()
            visual_output_dir = self.visual_output_dir_input.text().strip()
            txt_output_dir = self.txt_output_dir_input.text().strip()
            truth_csv_path = self.truth_csv_input.text().strip()
            test_record_csv = self.test_record_csv_input.text().strip()

            if not all([watch_dir, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir, truth_csv_path, test_record_csv]):
                QMessageBox.warning(self, "警告", "请填写所有文件夹路径和测试记录路径。")
                return
            
            if not os.path.isdir(watch_dir):
                QMessageBox.critical(self, "错误", f"监控文件夹路径不存在: {watch_dir}")
                return

            self.watcher_thread = WatcherThread(
                watch_dir,
                processed_dir,
                error_dir,
                output_dir,
                visual_output_dir,
                txt_output_dir,
                self.manual_output,
                truth_csv_path,
                test_record_csv
            )
            self.watcher_thread.log_signal.connect(self.log_message)
            
            self.watcher_thread.start()
            self.start_watch_btn.setEnabled(False)
            self.stop_watch_btn.setEnabled(True)
            self.log_message(f"--- 开始监控文件夹: {watch_dir} ---")

        def stop_watching(self):
            if self.watcher_thread and self.watcher_thread.isRunning():
                self.watcher_thread.stop_watching() # 发送停止信号
                self.watcher_thread.wait() # 等待线程结束
                self.watcher_thread = None
            self.start_watch_btn.setEnabled(True)
            self.stop_watch_btn.setEnabled(False)
            self.log_message("--- 用户已请求停止监控 ---")

        def log_message(self, message):
            """将消息追加到日志显示区域"""
            self.result_display.append(message)


    def main():
        """主函数，启动GUI应用。"""
        print("=== 正在启动Mr.6's Auto OCR Pipeline... ===")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())


    if __name__ == "__main__":
        main()
