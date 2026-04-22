# 跳过了不成功的0.3版本，直接进入了0.4版本。
# v0.5：在不牺牲文字/码识别稳定性的前提下，重点优化多标签分组策略与性能。
# v0.61：接入 PaddleDetection 训练出的标签检测模型，优先按标签框分配文字/码，提升多标签分割稳定性。
# v0.62：加入检测框过滤(NMS/面积/TopK) + 按框裁剪OCR，显著提升多标签场景稳定性。
# v0.7：加入自适应阈值/自适应NMS，多轮尝试后自动选择更接近目标标签数的结果。
# v0.71：基于 v0.7，默认切换到新训练并导出的 label_det_m_45e 模型。
# v0.71_tuned：针对 10 张多标签测试图进一步优化自适应候选选择与尾框抑制逻辑。
# 本版本默认模型: PaddleDetection-release-2.8.1/output_inference/label_det_m_45e

import sys
import os
import json
import math
import csv
import statistics
import time
import threading
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
    CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "app_config_v071_tuned.json")

    def load_config():
        """从JSON文件加载配置"""
        default_config = {
            "watch_dir": str(Path(__file__).resolve().parent / "watch_directory"),
            "output_dir": str(Path(__file__).resolve().parent / "json_directory"),
            "processed_dir": str(Path(__file__).resolve().parent / "processed_directory"),
            "error_dir": str(Path(__file__).resolve().parent / "error_directory"),
            "visual_output_dir": str(Path(__file__).resolve().parent / "visual_outputs"),
            "txt_output_dir": str(Path(__file__).resolve().parent / "output_directory"),
            "manual_output": True,
            "label_det_model_dir": "./PaddleDetection-release-2.8.1/output_inference/label_det_m_45e",
            "label_det_score_threshold": 0.3,
            "label_det_use_gpu": False,
            "label_det_nms_iou": 0.45,
            "label_det_max_boxes": 6,
            "label_det_min_area_ratio": 0.02,
            "label_det_max_area_ratio": 0.9,
            "label_det_crop_margin": 8,
            "label_det_use_crop_ocr": True,
            "label_det_adaptive_enabled": True,
            "label_det_target_boxes": 3,
            "ocr_use_gpu": False,
            "ground_truth_csv": str(Path(__file__).resolve().parent / "multiple_labels_test" / "truth.csv"),
            "test_record_csv": str(Path(__file__).resolve().parent / "v0_71_tuned_grouping_test_records.csv")
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

    # --- 通用辅助函数 ---

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
            print(f"加载真值表失败: {e}")
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
            "recorded_at", "image_name", "actual_label_count", "predicted_label_count",
            "label_count_correct", "over_split", "over_merge", "success", "elapsed_seconds", "error"
        ]
        file_exists = csv_file.exists()
        with open(csv_file, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def _create_ocr_engine(use_gpu=False):
        """兼容 PaddleOCR 2.x/3.x 的初始化参数。"""
        try:
            return PaddleOCR(use_textline_orientation=True, lang='ch', use_gpu=use_gpu)
        except TypeError:
            return PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=use_gpu)

    def _run_ocr(ocr_engine, image_path):
        """兼容 PaddleOCR 2.x/3.x 的调用方式。"""
        if hasattr(ocr_engine, "predict"):
            return ocr_engine.predict(image_path)
        if hasattr(ocr_engine, "ocr"):
            return ocr_engine.ocr(image_path, cls=True)
        return []
    def _resolve_path(path_value):
        if not path_value:
            return path_value
        if os.path.isabs(path_value):
            return path_value
        return os.path.abspath(os.path.join(os.path.dirname(__file__), path_value))

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

    def _bbox_area(b):
        return max(0.0, (b[2] - b[0])) * max(0.0, (b[3] - b[1]))

    def _bbox_iou(a, b):
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        if inter <= 0:
            return 0.0
        union = _bbox_area(a) + _bbox_area(b) - inter
        return inter / max(1.0, union)

    def _bbox_intersection_area(a, b):
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    def _bbox_containment(a, b):
        inter = _bbox_intersection_area(a, b)
        if inter <= 0:
            return 0.0
        return inter / max(1.0, min(_bbox_area(a), _bbox_area(b)))

    def _poly_to_bbox(poly):
        if not poly:
            return [0, 0, 0, 0]
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return [min(xs), min(ys), max(xs), max(ys)]

    def _nms_boxes(boxes, iou_threshold=0.45):
        # boxes: list of [x1,y1,x2,y2,score]
        if not boxes:
            return []
        boxes_sorted = sorted(boxes, key=lambda b: b[4], reverse=True)
        kept = []
        for b in boxes_sorted:
            keep = True
            for k in kept:
                if _bbox_iou(b, k) >= iou_threshold:
                    keep = False
                    break
            if keep:
                kept.append(b)
        return kept

    def _filter_label_boxes(boxes, img_w, img_h, score_th=0.3, nms_iou=0.45,
                            min_area_ratio=0.02, max_area_ratio=0.9, max_boxes=6):
        if not boxes:
            return []
        img_area = max(1.0, img_w * img_h)
        # clamp to image bounds first to avoid negative/oversized boxes
        clamped = []
        for b in boxes:
            cb = _clamp_box(b, img_w, img_h, margin=0)
            if cb is None:
                continue
            clamped.append([float(cb[0]), float(cb[1]), float(cb[2]), float(cb[3]), float(b[4])])
        # score filter
        filtered = [b for b in clamped if b[4] >= score_th]
        # area filter
        area_filtered = []
        for b in filtered:
            area = _bbox_area(b)
            ratio = area / img_area
            if ratio < min_area_ratio or ratio > max_area_ratio:
                continue
            area_filtered.append(b)
        # NMS
        nmsed = _nms_boxes(area_filtered, iou_threshold=nms_iou)
        # limit count
        nmsed = sorted(nmsed, key=lambda b: b[4], reverse=True)
        if max_boxes and len(nmsed) > max_boxes:
            nmsed = nmsed[:max_boxes]
        return nmsed

    def _filter_label_boxes_with_stats(boxes, img_w, img_h, score_th=0.3, nms_iou=0.45,
                                       min_area_ratio=0.02, max_area_ratio=0.9, max_boxes=6):
        stats = {
            "input": 0,
            "clamped": 0,
            "score": 0,
            "area": 0,
            "nms": 0,
            "merged": 0
        }
        if not boxes:
            return [], stats
        stats["input"] = len(boxes)
        img_area = max(1.0, img_w * img_h)

        clamped = []
        for b in boxes:
            cb = _clamp_box(b, img_w, img_h, margin=0)
            if cb is None:
                continue
            clamped.append([float(cb[0]), float(cb[1]), float(cb[2]), float(cb[3]), float(b[4])])
        stats["clamped"] = len(clamped)

        filtered = [b for b in clamped if b[4] >= score_th]
        stats["score"] = len(filtered)

        area_filtered = []
        for b in filtered:
            area = _bbox_area(b)
            ratio = area / img_area
            if ratio < min_area_ratio or ratio > max_area_ratio:
                continue
            area_filtered.append(b)
        stats["area"] = len(area_filtered)

        nmsed = _nms_boxes(area_filtered, iou_threshold=nms_iou)
        nmsed = sorted(nmsed, key=lambda b: b[4], reverse=True)
        if max_boxes and len(nmsed) > max_boxes:
            nmsed = nmsed[:max_boxes]
        stats["nms"] = len(nmsed)
        merged = _merge_redundant_label_boxes(nmsed, max_boxes=max_boxes)
        stats["merged"] = len(merged)
        stats["score_sum"] = round(sum(b[4] for b in merged), 4)
        return merged, stats

    def _merge_redundant_label_boxes(boxes, containment_th=0.72, iou_th=0.35, max_boxes=6):
        if not boxes:
            return []
        merged = []
        for b in sorted(boxes, key=lambda x: x[4], reverse=True):
            merged_into_existing = False
            for idx, cur in enumerate(merged):
                if _bbox_iou(b, cur) >= iou_th or _bbox_containment(b, cur) >= containment_th:
                    union_box = [
                        min(b[0], cur[0]),
                        min(b[1], cur[1]),
                        max(b[2], cur[2]),
                        max(b[3], cur[3]),
                        max(b[4], cur[4]),
                    ]
                    merged[idx] = union_box
                    merged_into_existing = True
                    break
            if not merged_into_existing:
                merged.append(list(b))
        merged = sorted(merged, key=lambda x: x[4], reverse=True)
        if max_boxes and len(merged) > max_boxes:
            merged = merged[:max_boxes]
        return merged

    def _build_adaptive_profiles(score_th, nms_iou, max_boxes, min_area_ratio, max_area_ratio):
        profiles = [
            {
                "name": "base",
                "score_th": score_th,
                "nms_iou": nms_iou,
                "max_boxes": max_boxes,
                "min_area_ratio": min_area_ratio,
                "max_area_ratio": max_area_ratio,
            },
            {
                "name": "recover_more",
                "score_th": max(0.18, score_th - 0.07),
                "nms_iou": min(0.90, nms_iou + 0.10),
                "max_boxes": max_boxes,
                "min_area_ratio": max(0.0005, min_area_ratio * 0.5),
                "max_area_ratio": min(0.995, max_area_ratio),
            },
            {
                "name": "recover_sparse",
                "score_th": max(0.12, score_th - 0.12),
                "nms_iou": min(0.92, nms_iou + 0.15),
                "max_boxes": max_boxes,
                "min_area_ratio": max(0.0005, min_area_ratio * 0.25),
                "max_area_ratio": min(0.995, max_area_ratio),
            },
        ]

        uniq = []
        seen = set()
        for p in profiles:
            key = (
                round(p["score_th"], 4),
                round(p["nms_iou"], 4),
                int(p["max_boxes"]),
                round(p["min_area_ratio"], 6),
                round(p["max_area_ratio"], 6),
            )
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        return uniq

    def _candidate_rank(box_count, target_boxes):
        if box_count == target_boxes:
            return 4
        if target_boxes > 1 and box_count == target_boxes - 1:
            return 3
        if box_count > 0:
            return 2
        return 0

    def _select_adaptive_candidate(candidates, target_boxes):
        if not candidates:
            return None

        def sort_key(item):
            box_count = item["stats"].get("merged", item["stats"].get("nms", 0))
            return (
                _candidate_rank(box_count, target_boxes),
                -abs(box_count - target_boxes),
                item["stats"].get("score_sum", 0.0),
                -item["index"],
            )

        return max(candidates, key=sort_key)

    def _refine_box_count_by_scores(boxes, log_callback=None, log_prefix=""):
        """
        基于尾部框置信度做轻量修正：
        - 若第3个框明显偏弱，则倾向抑制 3->2
        - 若第4个框足够可信，则保留 4 个框
        该规则专门用于缓解“固定 target=3”带来的偏置。
        """
        if not boxes:
            return boxes

        ordered = sorted(boxes, key=lambda x: x[4], reverse=True)
        scores = [float(b[4]) for b in ordered]

        if len(ordered) == 3:
            s1, s2, s3 = scores
            if s3 < 0.65 and (s2 - s3) > 0.25:
                if log_callback:
                    log_callback(
                        f"{log_prefix}尾框修正: 第3框置信度偏弱(score3={s3:.2f}, gap23={(s2 - s3):.2f})，3->2"
                    )
                return ordered[:2]

        if len(ordered) >= 4:
            s3 = scores[2]
            s4 = scores[3]
            if s4 >= 0.58:
                if log_callback:
                    log_callback(
                        f"{log_prefix}尾框修正: 第4框置信度可信(score4={s4:.2f})，保留4框"
                    )
                return ordered
            if (s3 - s4) > 0.30:
                if log_callback:
                    log_callback(
                        f"{log_prefix}尾框修正: 第4框明显偏弱(score4={s4:.2f}, gap34={(s3 - s4):.2f})，截为3框"
                    )
                return ordered[:3]

        return ordered

    def _detect_label_boxes_adaptive(detector, image_path, img_w, img_h, score_th=0.3, nms_iou=0.45,
                                     min_area_ratio=0.02, max_area_ratio=0.9, max_boxes=6,
                                     adaptive_enabled=True, target_boxes=3, log_callback=None, log_prefix=""):
        raw_boxes = _detect_label_boxes(detector, image_path, score_threshold=score_th)
        profiles = _build_adaptive_profiles(score_th, nms_iou, max_boxes, min_area_ratio, max_area_ratio)
        if not adaptive_enabled:
            profiles = profiles[:1]

        candidates = []
        for idx, profile in enumerate(profiles):
            filtered_boxes, stats = _filter_label_boxes_with_stats(
                raw_boxes,
                img_w,
                img_h,
                score_th=profile["score_th"],
                nms_iou=profile["nms_iou"],
                min_area_ratio=profile["min_area_ratio"],
                max_area_ratio=profile["max_area_ratio"],
                max_boxes=profile["max_boxes"]
            )
            candidate = {
                "index": idx,
                "profile": profile,
                "stats": stats,
                "boxes": filtered_boxes
            }
            candidates.append(candidate)
            if log_callback:
                log_callback(
                    f"{log_prefix}自适应[{profile['name']}]: score={profile['score_th']:.2f} "
                    f"nms={profile['nms_iou']:.2f} max={profile['max_boxes']} "
                    f"-> raw={stats['input']} score={stats['score']} area={stats['area']} "
                    f"nms={stats['nms']} merged={stats['merged']}"
                )

        chosen = _select_adaptive_candidate(candidates, target_boxes)
        if chosen is None:
            return raw_boxes, [], {"input": 0, "clamped": 0, "score": 0, "area": 0, "nms": 0}, None
        refined_boxes = _refine_box_count_by_scores(
            chosen["boxes"],
            log_callback=log_callback,
            log_prefix=log_prefix
        )
        chosen_stats = dict(chosen["stats"])
        chosen_stats["merged"] = len(refined_boxes)
        chosen_stats["score_sum"] = round(sum(b[4] for b in refined_boxes), 4)
        return raw_boxes, refined_boxes, chosen_stats, chosen["profile"]

    def _clamp_box(b, w, h, margin=0):
        x1 = max(0, int(b[0] - margin))
        y1 = max(0, int(b[1] - margin))
        x2 = min(w - 1, int(b[2] + margin))
        y2 = min(h - 1, int(b[3] + margin))
        if x2 <= x1 or y2 <= y1:
            return None
        return [x1, y1, x2, y2]

    def _run_crop_ocr(ocr_engine, image_cv, crop_box):
        x1, y1, x2, y2 = crop_box
        crop = image_cv[y1:y2, x1:x2]
        if crop.size == 0:
            return []
        # PaddleOCR accepts ndarray directly
        ocr_results = _run_ocr(ocr_engine, crop)
        if not ocr_results:
            return []
        ocr_result = ocr_results[0] if isinstance(ocr_results, list) and ocr_results else ocr_results
        items = _extract_text_items_from_ocr_result(ocr_result)
        # offset to global coords
        for item in items:
            b = item["bbox"]
            item["bbox"] = [b[0] + x1, b[1] + y1, b[2] + x1, b[3] + y1]
        return items

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

    def _build_label_groups(text_items, code_items):
        # 过滤空文本，避免碎片化
        text_items = [t for t in text_items if t.get("text") and str(t.get("text")).strip()]

        items = text_items + code_items
        if not items:
            return []

        # 纯净版：仅做基础空间聚类，不做锚点/合并/强制切分
        groups = _cluster_items(items)

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

    # --- 标签检测模型接入 ---
    _LABEL_DETECTOR = None
    _LABEL_DETECTOR_ERR = None
    _LABEL_DETECTOR_CFG = None
    _LABEL_DETECTOR_LOCK = threading.Lock()

    def _get_label_detector(model_dir, use_gpu=False, score_threshold=0.3, log_callback=None):
        global _LABEL_DETECTOR, _LABEL_DETECTOR_ERR, _LABEL_DETECTOR_CFG
        model_dir = _resolve_path(model_dir)
        if not model_dir or not os.path.isdir(model_dir):
            _LABEL_DETECTOR_ERR = f"标签检测模型目录不存在: {model_dir}"
            if log_callback:
                log_callback(f"    -> 标签检测模型不可用: {_LABEL_DETECTOR_ERR}")
            return None

        cfg_key = (model_dir, bool(use_gpu), float(score_threshold))
        if _LABEL_DETECTOR is not None and _LABEL_DETECTOR_CFG == cfg_key:
            return _LABEL_DETECTOR
        if _LABEL_DETECTOR_ERR is not None and _LABEL_DETECTOR_CFG == cfg_key:
            return None

        with _LABEL_DETECTOR_LOCK:
            if _LABEL_DETECTOR is not None and _LABEL_DETECTOR_CFG == cfg_key:
                return _LABEL_DETECTOR
            if _LABEL_DETECTOR_ERR is not None and _LABEL_DETECTOR_CFG == cfg_key:
                return None
            try:
                deploy_dir = os.path.join(
                    os.path.dirname(__file__),
                    "PaddleDetection-release-2.8.1",
                    "deploy",
                    "python"
                )
                if deploy_dir not in sys.path:
                    sys.path.insert(0, deploy_dir)
                from infer import Detector
                device = "GPU" if use_gpu else "CPU"
                _LABEL_DETECTOR = Detector(
                    model_dir=model_dir,
                    device=device,
                    threshold=score_threshold
                )
                _LABEL_DETECTOR_ERR = None
                _LABEL_DETECTOR_CFG = cfg_key
                if log_callback:
                    log_callback(f"    -> 标签检测模型已加载: {model_dir} | 设备: {device}")
            except Exception as e:
                _LABEL_DETECTOR = None
                _LABEL_DETECTOR_ERR = str(e)
                _LABEL_DETECTOR_CFG = cfg_key
                if log_callback:
                    log_callback(f"    -> 标签检测模型加载失败: {e}")
        return _LABEL_DETECTOR

    def _get_label_detector_error():
        return _LABEL_DETECTOR_ERR

    def _detect_label_boxes(detector, image_path, score_threshold=0.3):
        if detector is None:
            return []
        try:
            results = detector.predict_image([str(image_path)], visual=False, save_results=False)
            boxes = results.get("boxes")
            if boxes is None or len(boxes) == 0:
                return []
            label_boxes = []
            for row in boxes:
                cls_id, score, x1, y1, x2, y2 = row.tolist()
                label_boxes.append([float(x1), float(y1), float(x2), float(y2), float(score)])
            return label_boxes
        except Exception:
            return []

    def _assign_items_to_label_boxes(text_items, code_items, label_boxes):
        if not label_boxes:
            return _build_label_groups(text_items, code_items)

        # 排序标签框，确保ID稳定
        label_boxes_sorted = sorted(label_boxes, key=lambda b: (b[1], b[0]))
        label_entries = []
        for idx, b in enumerate(label_boxes_sorted, start=1):
            label_entries.append({
                "label_id": idx,
                "bbox": [int(b[0]), int(b[1]), int(b[2]), int(b[3])],
                "texts": [],
                "codes": []
            })

        def _pick_label(item_bbox):
            cx, cy = _bbox_center(item_bbox)
            candidates = []
            for i, b in enumerate(label_entries):
                bb = b["bbox"]
                if bb[0] <= cx <= bb[2] and bb[1] <= cy <= bb[3]:
                    area = max(1.0, (bb[2] - bb[0]) * (bb[3] - bb[1]))
                    candidates.append((area, i))
            if candidates:
                candidates.sort(key=lambda x: x[0])
                return candidates[0][1]

            # 如果不在任何框内，分配到最近中心
            best_idx = 0
            best_dist = None
            for i, b in enumerate(label_entries):
                bx, by = _bbox_center(b["bbox"])
                dist = math.hypot(cx - bx, cy - by)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_idx = i
            return best_idx

        for item in text_items:
            label_idx = _pick_label(item["bbox"])
            label_entries[label_idx]["texts"].append({
                "text": item["text"],
                "score": item.get("score"),
                "bbox": [int(v) for v in item["bbox"]]
            })

        for item in code_items:
            label_idx = _pick_label(item["bbox"])
            label_entries[label_idx]["codes"].append({
                "type": item["code_type"],
                "data": item["data"],
                "bbox": [int(v) for v in item["bbox"]]
            })

        for entry in label_entries:
            entry["texts"].sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))

        return label_entries

    def _split_group_by_gap(group):
        # 预留：纯净版不启用，仅保留函数以便后续调优
        return [group]

    def _extract_text_items_from_ocr_result(ocr_result):
        text_items = []
        ocr_json = getattr(ocr_result, "json", None)

        # PaddleOCR 2.x: list[list[box, (text, score)]]
        if isinstance(ocr_result, list) and ocr_result:
            # 单张图片时直接是列表
            if isinstance(ocr_result[0], (list, tuple)):
                for item in ocr_result:
                    if not isinstance(item, (list, tuple)) or len(item) < 2:
                        continue
                    box = item[0]
                    text_tuple = item[1] if len(item) > 1 else None
                    if not text_tuple:
                        continue
                    text = text_tuple[0] if len(text_tuple) > 0 else None
                    score = text_tuple[1] if len(text_tuple) > 1 else None
                    if text is None or str(text).strip() == "":
                        continue
                    bbox = _poly_to_bbox(box) if isinstance(box, list) else [0, 0, 0, 0]
                    text_items.append({
                        "type": "text",
                        "text": text,
                        "score": score,
                        "bbox": bbox
                    })
                return text_items

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
        image_path_obj = Path(image_path)
        visual_name = f"{image_path_obj.stem}_ocr_res_img{image_path_obj.suffix}"
        visual_path = visual_dir / visual_name

        # PaddleOCR 3.x: result_obj 有 save_to_img
        if hasattr(result_obj, "save_to_img"):
            result_obj.save_to_img(str(visual_dir))
            return str(visual_path)

        # PaddleOCR 2.x: list 结果，使用 draw_ocr
        try:
            from paddleocr import draw_ocr
            image = cv2.imread(str(image_path_obj))
            if image is None:
                return ""
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            boxes = []
            txts = []
            scores = []
            for item in result_obj:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                boxes.append(item[0])
                text_tuple = item[1] if len(item) > 1 else None
                if text_tuple:
                    txts.append(text_tuple[0])
                    scores.append(text_tuple[1] if len(text_tuple) > 1 else None)
            if boxes:
                vis = draw_ocr(image_rgb, boxes, txts, scores)
                if hasattr(vis, "save"):
                    vis.save(str(visual_path))
                else:
                    cv2.imwrite(str(visual_path), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
                return str(visual_path)
        except Exception:
            return ""

    def _save_visual_result_from_items(text_items, image_path, visual_output_dir, label_boxes=None):
        if not visual_output_dir:
            return ""
        visual_dir = Path(visual_output_dir)
        visual_dir.mkdir(parents=True, exist_ok=True)
        image_path_obj = Path(image_path)
        visual_name = f"{image_path_obj.stem}_ocr_res_img{image_path_obj.suffix}"
        visual_path = visual_dir / visual_name
        try:
            from paddleocr import draw_ocr
            image = cv2.imread(str(image_path_obj))
            if image is None:
                return ""
            # draw label boxes first
            if label_boxes:
                for b in label_boxes:
                    x1, y1, x2, y2 = [int(v) for v in b[:4]]
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            boxes = []
            txts = []
            scores = []
            for item in text_items:
                b = item.get("bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = [int(v) for v in b]
                boxes.append([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
                txts.append(item.get("text", ""))
                scores.append(item.get("score", None))
            vis = draw_ocr(image_rgb, boxes, txts, scores) if boxes else image_rgb
            if hasattr(vis, "save"):
                vis.save(str(visual_path))
            else:
                cv2.imwrite(str(visual_path), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
            return str(visual_path)
        except Exception:
            return ""


    # --- 1. 实时监控模式所需的核心类 (修改以使用配置) ---

    class ImageHandler(FileSystemEventHandler):
        """
        文件系统事件处理器，专门处理图片文件的创建事件。
        """
        def __init__(self, ocr_engine, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir,
                     manual_output, log_callback, label_det_model_dir, label_det_score_threshold, label_det_use_gpu,
                     label_det_nms_iou, label_det_max_boxes, label_det_min_area_ratio, label_det_max_area_ratio,
                     label_det_crop_margin, label_det_use_crop_ocr,
                     label_det_adaptive_enabled=True, label_det_target_boxes=3,
                     truth_csv_path="", test_record_csv=""):
            super().__init__()
            self.ocr = ocr_engine
            self.processed_path = Path(processed_dir)
            self.error_path = Path(error_dir)
            self.output_path = Path(output_dir)
            self.visual_output_path = Path(visual_output_dir) if visual_output_dir else None
            self.txt_output_path = Path(txt_output_dir) if txt_output_dir else None
            self.manual_output = manual_output
            self.log_callback = log_callback # GUI的日志回调函数
            self.label_det_model_dir = label_det_model_dir
            self.label_det_score_threshold = label_det_score_threshold
            self.label_det_use_gpu = label_det_use_gpu
            self.label_det_nms_iou = label_det_nms_iou
            self.label_det_max_boxes = label_det_max_boxes
            self.label_det_min_area_ratio = label_det_min_area_ratio
            self.label_det_max_area_ratio = label_det_max_area_ratio
            self.label_det_crop_margin = label_det_crop_margin
            self.label_det_use_crop_ocr = label_det_use_crop_ocr
            self.label_det_adaptive_enabled = label_det_adaptive_enabled
            self.label_det_target_boxes = label_det_target_boxes
            self.truth_map = load_ground_truth_map(truth_csv_path)
            self.test_record_csv = test_record_csv
            self.label_detector = _get_label_detector(
                self.label_det_model_dir,
                use_gpu=self.label_det_use_gpu,
                score_threshold=self.label_det_score_threshold,
                log_callback=self.log_callback
            )
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
            start_time = time.perf_counter()
            try:
                # --- 1. 加载图片 ---
                image_cv = cv2.imread(str(image_path))
                if image_cv is None:
                    self.log_callback(f"    -> 无法读取图片文件 {image_path}")
                    return False

                img_h, img_w = image_cv.shape[:2]

                # --- 2. 标签检测 ---
                label_boxes, filtered_boxes, filter_stats, chosen_profile = _detect_label_boxes_adaptive(
                    self.label_detector,
                    image_path,
                    img_w,
                    img_h,
                    score_th=self.label_det_score_threshold,
                    nms_iou=self.label_det_nms_iou,
                    min_area_ratio=self.label_det_min_area_ratio,
                    max_area_ratio=self.label_det_max_area_ratio,
                    max_boxes=self.label_det_max_boxes,
                    adaptive_enabled=self.label_det_adaptive_enabled,
                    target_boxes=self.label_det_target_boxes,
                    log_callback=self.log_callback,
                    log_prefix="    -> "
                )

                text_items = []
                code_items = []
                labels = []
                ocr_result = None

                if self.log_callback:
                    self.log_callback(
                        f"    -> 标签检测框统计: raw={filter_stats['input']} clamp={filter_stats['clamped']} "
                        f"score={filter_stats['score']} area={filter_stats['area']} "
                        f"nms={filter_stats['nms']} merged={filter_stats['merged']}"
                    )
                    if chosen_profile is not None:
                        self.log_callback(
                            f"    -> 采用检测策略: {chosen_profile['name']} "
                            f"(score={chosen_profile['score_th']:.2f}, nms={chosen_profile['nms_iou']:.2f})"
                        )
                # --- 3. 通过标签框裁剪 OCR（优先） ---
                if filtered_boxes and self.label_det_use_crop_ocr:
                    self.log_callback(f"    -> 标签检测框数量: {len(filtered_boxes)}")
                    for idx, b in enumerate(filtered_boxes, start=1):
                        clamp = _clamp_box(b, img_w, img_h, margin=self.label_det_crop_margin)
                        if not clamp:
                            continue
                        crop_texts = _run_crop_ocr(self.ocr, image_cv, clamp)
                        text_items.extend(crop_texts)
                        crop_codes = []
                        crop = image_cv[clamp[1]:clamp[3], clamp[0]:clamp[2]]
                        for obj in pyzbar.decode(crop):
                            rect = obj.rect
                            bbox = [
                                rect.left + clamp[0],
                                rect.top + clamp[1],
                                rect.left + rect.width + clamp[0],
                                rect.top + rect.height + clamp[1]
                            ]
                            crop_codes.append({
                                "type": "code",
                                "code_type": obj.type,
                                "data": obj.data.decode("utf-8"),
                                "bbox": bbox
                            })
                        labels.append({
                            "label_id": idx,
                            "bbox": [int(v) for v in clamp],
                            "texts": [
                                {
                                    "text": t["text"],
                                    "score": t.get("score"),
                                    "bbox": [int(v) for v in t["bbox"]]
                                } for t in sorted(crop_texts, key=lambda x: (x["bbox"][1], x["bbox"][0]))
                            ],
                            "codes": [
                                {
                                    "type": c["code_type"],
                                    "data": c["data"],
                                    "bbox": [int(v) for v in c["bbox"]]
                                } for c in crop_codes
                            ]
                        })

                # --- 3b. 有框但不裁剪：全图 OCR + 按框分配 ---
                if filtered_boxes and (not self.label_det_use_crop_ocr) and (not labels):
                    self.log_callback(f"    -> 标签检测框数量: {len(filtered_boxes)}")
                    self.log_callback("    正在进行 OCR 识别...")
                    ocr_results = _run_ocr(self.ocr, str(image_path))
                    if not ocr_results:
                        self.log_callback("    -> OCR 返回空结果")
                        return False
                    ocr_result = ocr_results[0] if isinstance(ocr_results, list) and ocr_results else ocr_results
                    text_items = _extract_text_items_from_ocr_result(ocr_result)
                    for obj in pyzbar.decode(image_cv):
                        rect = obj.rect
                        bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                        code_items.append({
                            "type": "code",
                            "code_type": obj.type,
                            "data": obj.data.decode("utf-8"),
                            "bbox": bbox
                        })
                    labels = _assign_items_to_label_boxes(text_items, code_items, filtered_boxes)

                # --- 4. 回退全图 OCR + 聚类 ---
                if not labels:
                    self.log_callback("    -> 未检测到标签框，已回退到聚类分组")
                    self.log_callback("    正在进行 OCR 识别...")
                    ocr_results = _run_ocr(self.ocr, str(image_path))
                    if not ocr_results:
                        self.log_callback("    -> OCR 返回空结果")
                        return False
                    ocr_result = ocr_results[0] if isinstance(ocr_results, list) and ocr_results else ocr_results
                    text_items = _extract_text_items_from_ocr_result(ocr_result)
                    if not text_items:
                        debug_path = self.output_path / f"{image_path.stem}_ocr_debug.json"
                        try:
                            debug_path.parent.mkdir(parents=True, exist_ok=True)
                            if hasattr(ocr_result, "save_to_json"):
                                try:
                                    ocr_result.save_to_json(str(debug_path))
                                except Exception:
                                    with open(debug_path, "w", encoding="utf-8") as f:
                                        json.dump(getattr(ocr_result, "json", {}), f, ensure_ascii=False, indent=2)
                            else:
                                with open(debug_path, "w", encoding="utf-8") as f:
                                    json.dump(ocr_result, f, ensure_ascii=False, indent=2)
                            self.log_callback(f"    -> 未解析到文字，已输出调试JSON: {debug_path}")
                        except Exception as e:
                            self.log_callback(f"    -> 未解析到文字，调试JSON保存失败: {e}")

                    self.log_callback("    正在进行码识别...")
                    for obj in pyzbar.decode(image_cv):
                        rect = obj.rect
                        bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                        code_items.append({
                            "type": "code",
                            "code_type": obj.type,
                            "data": obj.data.decode("utf-8"),
                            "bbox": bbox
                        })
                    labels = _build_label_groups(text_items, code_items)

                elapsed_seconds = time.perf_counter() - start_time

                # --- 5. 保存结构化结果 ---
                base_name = image_path.stem
                output_path = self.output_path / f"{base_name}_识别结果.json"

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
                    if ocr_result is not None:
                        visual_path = _save_visual_result(ocr_result, image_path, str(self.visual_output_path))
                    else:
                        visual_path = _save_visual_result_from_items(
                            text_items,
                            image_path,
                            str(self.visual_output_path),
                            label_boxes=filtered_boxes
                        )
                    if visual_path:
                        self.log_callback(f"    -> 可视化结果已保存至: {visual_path}")

                # --- 7. 质量评估与文件移动 ---
                ocr_success = len(text_items) > 0
                code_success = len(code_items) > 0

                if ocr_success or code_success:
                    dest_file = self.processed_path / image_path.name
                    os.replace(str(image_path), str(dest_file))
                    self.log_callback(f"    -> 文件移动到已处理文件夹: {dest_file}")
                    test_row = build_grouping_test_record(
                        image_path.name, len(labels), elapsed_seconds, self.truth_map, True
                    )
                    append_grouping_test_record(self.test_record_csv, test_row)
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
                        image_path.name, len(labels), elapsed_seconds, self.truth_map, False,
                        error="未识别到有效文本或编码信息"
                    )
                    append_grouping_test_record(self.test_record_csv, test_row)
                    self.log_callback(f"    -> 处理耗时: {elapsed_seconds:.4f} s")
                    return False
                        
            except Exception as e:
                try:
                    elapsed_seconds = time.perf_counter() - start_time
                except Exception:
                    elapsed_seconds = 0.0
                self.log_callback(f"    -> 处理图片 {image_path.name} 时发生错误: {e}")
                append_grouping_test_record(
                    self.test_record_csv,
                    build_grouping_test_record(image_path.name, 0, elapsed_seconds, self.truth_map, False, error=str(e))
                )
                return False


    class WatcherThread(QThread):
        """
        用于在后台启动和停止 watchdog 监控的线程。
        """
        log_signal = pyqtSignal(str)
        
        def __init__(self, watch_dir, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir,
                     manual_output, label_det_model_dir, label_det_score_threshold, label_det_use_gpu,
                     label_det_nms_iou, label_det_max_boxes, label_det_min_area_ratio, label_det_max_area_ratio,
                     label_det_crop_margin, label_det_use_crop_ocr,
                     label_det_adaptive_enabled, label_det_target_boxes,
                     ocr_use_gpu=False, truth_csv_path="", test_record_csv=""):
            super().__init__()
            self.watch_dir = watch_dir
            self.processed_dir = processed_dir
            self.error_dir = error_dir
            self.output_dir = output_dir
            self.visual_output_dir = visual_output_dir
            self.txt_output_dir = txt_output_dir
            self.manual_output = manual_output
            self.label_det_model_dir = label_det_model_dir
            self.label_det_score_threshold = label_det_score_threshold
            self.label_det_use_gpu = label_det_use_gpu
            self.label_det_nms_iou = label_det_nms_iou
            self.label_det_max_boxes = label_det_max_boxes
            self.label_det_min_area_ratio = label_det_min_area_ratio
            self.label_det_max_area_ratio = label_det_max_area_ratio
            self.label_det_crop_margin = label_det_crop_margin
            self.label_det_use_crop_ocr = label_det_use_crop_ocr
            self.label_det_adaptive_enabled = label_det_adaptive_enabled
            self.label_det_target_boxes = label_det_target_boxes
            self.ocr_use_gpu = ocr_use_gpu
            self.truth_csv_path = truth_csv_path
            self.test_record_csv = test_record_csv
            self.observer = Observer()
            self.ocr = _create_ocr_engine(use_gpu=self.ocr_use_gpu)

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
                self.label_det_model_dir,
                self.label_det_score_threshold,
                self.label_det_use_gpu,
                self.label_det_nms_iou,
                self.label_det_max_boxes,
                self.label_det_min_area_ratio,
                self.label_det_max_area_ratio,
                self.label_det_crop_margin,
                self.label_det_use_crop_ocr,
                self.label_det_adaptive_enabled,
                self.label_det_target_boxes,
                self.truth_csv_path,
                self.test_record_csv
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


    # --- 2. 单次识别模式所需的核心类 (修改以使用配置) ---

    class OcrWorker(QThread):
        """
        后台工作线程，用于执行OCR和码识别，防止GUI界面冻结。
        """
        finished_signal = pyqtSignal(dict)  # 任务完成信号，携带结果数据
        progress_signal = pyqtSignal(str)  # 进度更新信号
        log_signal = pyqtSignal(str)  # 线程安全日志

        def __init__(self, image_path, processed_dir, error_dir, output_dir, visual_output_dir, txt_output_dir,
                     manual_output, label_det_model_dir, label_det_score_threshold, label_det_use_gpu,
                     label_det_nms_iou, label_det_max_boxes, label_det_min_area_ratio, label_det_max_area_ratio,
                     label_det_crop_margin, label_det_use_crop_ocr,
                     label_det_adaptive_enabled, label_det_target_boxes,
                     ocr_use_gpu=False, truth_csv_path="", test_record_csv=""):
            super().__init__()
            self.image_path = image_path
            self.processed_dir = processed_dir
            self.error_dir = error_dir
            self.output_dir = output_dir
            self.visual_output_dir = visual_output_dir
            self.txt_output_dir = txt_output_dir
            self.manual_output = manual_output
            self.label_det_model_dir = label_det_model_dir
            self.label_det_score_threshold = label_det_score_threshold
            self.label_det_use_gpu = label_det_use_gpu
            self.label_det_nms_iou = label_det_nms_iou
            self.label_det_max_boxes = label_det_max_boxes
            self.label_det_min_area_ratio = label_det_min_area_ratio
            self.label_det_max_area_ratio = label_det_max_area_ratio
            self.label_det_crop_margin = label_det_crop_margin
            self.label_det_use_crop_ocr = label_det_use_crop_ocr
            self.label_det_adaptive_enabled = label_det_adaptive_enabled
            self.label_det_target_boxes = label_det_target_boxes
            self.ocr_use_gpu = ocr_use_gpu
            self.truth_map = load_ground_truth_map(truth_csv_path)
            self.test_record_csv = test_record_csv
            self.ocr = _create_ocr_engine(use_gpu=self.ocr_use_gpu)
            self.label_detector = _get_label_detector(
                self.label_det_model_dir,
                use_gpu=self.label_det_use_gpu,
                score_threshold=self.label_det_score_threshold,
                log_callback=self._emit_log
            )

        def _emit_log(self, message):
            try:
                self.log_signal.emit(message)
            except Exception:
                pass

        def run(self):
            """
            在后台线程中执行识别任务。
            """
            try:
                start_time = time.perf_counter()
                results = {"success": False, "raw_result": "", "output_path": "", "visual_output_path": ""}
                label_det_error = ""

                self.progress_signal.emit("正在加载图片...")
                image_cv = cv2.imread(self.image_path)
                if image_cv is None:
                    raise ValueError(f"无法读取图片文件 {self.image_path}")

                img_h, img_w = image_cv.shape[:2]

                # --- 1. 标签检测 ---
                label_boxes = []
                self._emit_log(f"[单次] Detector model_dir: {self.label_det_model_dir}")
                infer_cfg_path = os.path.join(_resolve_path(self.label_det_model_dir), "infer_cfg.yml")
                self._emit_log(f"[单次] infer_cfg.yml exists: {os.path.isfile(infer_cfg_path)}")
                self._emit_log(f"[单次] image_path exists: {os.path.isfile(self.image_path)}")
                self._emit_log(f"[单次] Detector type: {type(self.label_detector)}")
                self._emit_log(
                    f"[单次] det_params: score={self.label_det_score_threshold} nms_iou={self.label_det_nms_iou} "
                    f"max_boxes={self.label_det_max_boxes} min_area={self.label_det_min_area_ratio} "
                    f"max_area={self.label_det_max_area_ratio} adaptive={self.label_det_adaptive_enabled} "
                    f"target={self.label_det_target_boxes}"
                )
                if self.label_detector is None:
                    label_det_error = _get_label_detector_error() or "未知原因"

                label_boxes, filtered_boxes, filter_stats, chosen_profile = _detect_label_boxes_adaptive(
                    self.label_detector,
                    self.image_path,
                    img_w,
                    img_h,
                    score_th=self.label_det_score_threshold,
                    nms_iou=self.label_det_nms_iou,
                    min_area_ratio=self.label_det_min_area_ratio,
                    max_area_ratio=self.label_det_max_area_ratio,
                    max_boxes=self.label_det_max_boxes,
                    adaptive_enabled=self.label_det_adaptive_enabled,
                    target_boxes=self.label_det_target_boxes,
                    log_callback=self._emit_log,
                    log_prefix="[单次] "
                )

                text_items = []
                code_items = []
                labels = []
                ocr_result = None

                self._emit_log(
                    f"[单次] 标签检测框统计: raw={filter_stats['input']} clamp={filter_stats['clamped']} "
                    f"score={filter_stats['score']} area={filter_stats['area']} "
                    f"nms={filter_stats['nms']} merged={filter_stats['merged']}"
                )
                if chosen_profile is not None:
                    self._emit_log(
                        f"[单次] 采用检测策略: {chosen_profile['name']} "
                        f"(score={chosen_profile['score_th']:.2f}, nms={chosen_profile['nms_iou']:.2f})"
                    )
                # --- 2. 通过标签框裁剪 OCR（优先） ---
                if filtered_boxes and self.label_det_use_crop_ocr:
                    self._emit_log(f"[单次] 标签检测框数量: {len(filtered_boxes)}")
                    for idx, b in enumerate(filtered_boxes, start=1):
                        clamp = _clamp_box(b, img_w, img_h, margin=self.label_det_crop_margin)
                        if not clamp:
                            continue
                        crop_texts = _run_crop_ocr(self.ocr, image_cv, clamp)
                        text_items.extend(crop_texts)
                        crop_codes = []
                        crop = image_cv[clamp[1]:clamp[3], clamp[0]:clamp[2]]
                        for obj in pyzbar.decode(crop):
                            rect = obj.rect
                            bbox = [
                                rect.left + clamp[0],
                                rect.top + clamp[1],
                                rect.left + rect.width + clamp[0],
                                rect.top + rect.height + clamp[1]
                            ]
                            crop_codes.append({
                                "type": "code",
                                "code_type": obj.type,
                                "data": obj.data.decode("utf-8"),
                                "bbox": bbox
                            })
                        labels.append({
                            "label_id": idx,
                            "bbox": [int(v) for v in clamp],
                            "texts": [
                                {
                                    "text": t["text"],
                                    "score": t.get("score"),
                                    "bbox": [int(v) for v in t["bbox"]]
                                } for t in sorted(crop_texts, key=lambda x: (x["bbox"][1], x["bbox"][0]))
                            ],
                            "codes": [
                                {
                                    "type": c["code_type"],
                                    "data": c["data"],
                                    "bbox": [int(v) for v in c["bbox"]]
                                } for c in crop_codes
                            ]
                        })

                # --- 2b. 有框但不裁剪：全图 OCR + 按框分配 ---
                if filtered_boxes and (not self.label_det_use_crop_ocr) and (not labels):
                    self._emit_log(f"[单次] 标签检测框数量: {len(filtered_boxes)}")
                    self.progress_signal.emit("正在进行 OCR 识别...")
                    ocr_results = _run_ocr(self.ocr, self.image_path)
                    if not ocr_results:
                        raise ValueError("OCR 返回空结果")
                    ocr_result = ocr_results[0] if isinstance(ocr_results, list) and ocr_results else ocr_results
                    text_items = _extract_text_items_from_ocr_result(ocr_result)
                    code_items = []
                    for obj in pyzbar.decode(image_cv):
                        rect = obj.rect
                        bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                        code_items.append({
                            "type": "code",
                            "code_type": obj.type,
                            "data": obj.data.decode("utf-8"),
                            "bbox": bbox
                        })
                    labels = _assign_items_to_label_boxes(text_items, code_items, filtered_boxes)

                # --- 3. 如果没有可用标签框，回退全图 OCR + 聚类 ---
                if not labels:
                    if not filtered_boxes:
                        self._emit_log("[单次] 未检测到标签框，已回退到聚类分组")
                    # OCR 全图
                    self.progress_signal.emit("正在进行 OCR 识别...")
                    ocr_results = _run_ocr(self.ocr, self.image_path)
                    if not ocr_results:
                        raise ValueError("OCR 返回空结果")
                    ocr_result = ocr_results[0] if isinstance(ocr_results, list) and ocr_results else ocr_results
                    text_items = _extract_text_items_from_ocr_result(ocr_result)
                    if not text_items:
                        debug_path = Path(self.output_dir) / f"{Path(self.image_path).stem}_ocr_debug.json"
                        try:
                            debug_path.parent.mkdir(parents=True, exist_ok=True)
                            if hasattr(ocr_result, "save_to_json"):
                                try:
                                    ocr_result.save_to_json(str(debug_path))
                                except Exception:
                                    with open(debug_path, "w", encoding="utf-8") as f:
                                        json.dump(getattr(ocr_result, "json", {}), f, ensure_ascii=False, indent=2)
                            else:
                                with open(debug_path, "w", encoding="utf-8") as f:
                                    json.dump(ocr_result, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                    # 码识别全图
                    self.progress_signal.emit("正在进行码识别...")
                    for obj in pyzbar.decode(image_cv):
                        rect = obj.rect
                        bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                        code_items.append({
                            "type": "code",
                            "code_type": obj.type,
                            "data": obj.data.decode("utf-8"),
                            "bbox": bbox
                        })
                    labels = _build_label_groups(text_items, code_items)

                # --- 4. 生成可读摘要 ---
                image_path_obj = Path(self.image_path)
                results["raw_result"] = _format_labels_summary(labels)

                # --- 5. 保存结构化结果 ---
                base_name = image_path_obj.stem
                if self.manual_output:
                    output_path = Path(self.output_dir) / f"{base_name}_识别结果.json"
                else:
                    output_path = Path(self.output_dir) / f"{base_name}_识别结果.json"

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
                if ocr_result is not None:
                    results["visual_output_path"] = _save_visual_result(
                        ocr_result,
                        self.image_path,
                        self.visual_output_dir
                    )
                else:
                    results["visual_output_path"] = _save_visual_result_from_items(
                        text_items,
                        self.image_path,
                        self.visual_output_dir,
                        label_boxes=filtered_boxes
                    )

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

                append_grouping_test_record(
                    self.test_record_csv,
                    build_grouping_test_record(image_path_obj.name, len(labels), elapsed_seconds, self.truth_map, True)
                )
                if self.truth_map.get(image_path_obj.name) is not None:
                    self._emit_log(
                        f"[单次] 标签数量评估: 实际={self.truth_map.get(image_path_obj.name)} 预测={len(labels)}"
                    )
                self._emit_log(f"[单次] 处理耗时: {elapsed_seconds:.4f} s")

                results["success"] = True
                results["label_det_error"] = label_det_error

                self.finished_signal.emit(results)

            except Exception as e:
                elapsed_seconds = time.perf_counter() - start_time if 'start_time' in locals() else 0.0
                append_grouping_test_record(
                    self.test_record_csv,
                    build_grouping_test_record(Path(self.image_path).name, 0, elapsed_seconds, self.truth_map, False, error=str(e))
                )
                error_results = {
                    "success": False,
                    "error": str(e),
                    "raw_result": f"处理失败: {str(e)}",
                    "output_path": "",
                    "visual_output_path": "",
                    "label_det_error": _get_label_detector_error()
                }
                try:
                    if self.error_dir:
                        target_path = Path(self.error_dir)
                        target_path.mkdir(parents=True, exist_ok=True)
                        dest_file = target_path / Path(self.image_path).name
                        os.replace(self.image_path, str(dest_file))
                except Exception:
                    pass
                self.finished_signal.emit(error_results)


    # --- 3. 主窗口类 (修复与优化版) ---

    class MainWindow(QMainWindow):
        """
        主窗口类，定义GUI界面和交互逻辑。
        """
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Mr.6's Auto OCR Pipeline v0.71 (label_det_m_45e)")
            self.setGeometry(100, 80, 1040, 760)

            # 加载配置
            self.config = load_config()
            self.watch_dir = self.config.get("watch_dir", str(Path(__file__).resolve().parent / "watch_directory"))
            self.output_dir = self.config.get("output_dir", str(Path(__file__).resolve().parent / "json_directory"))
            self.processed_dir = self.config.get("processed_dir", str(Path(__file__).resolve().parent / "processed_directory"))
            self.error_dir = self.config.get("error_dir", str(Path(__file__).resolve().parent / "error_directory"))
            self.visual_output_dir = self.config.get("visual_output_dir", str(Path(__file__).resolve().parent / "visual_outputs"))
            self.txt_output_dir = self.config.get("txt_output_dir", str(Path(__file__).resolve().parent / "output_directory"))
            self.manual_output = self.config.get("manual_output", True)
            self.label_det_model_dir = self.config.get(
                "label_det_model_dir",
                "./PaddleDetection-release-2.8.1/output_inference/label_det"
            )
            self.label_det_score_threshold = float(self.config.get("label_det_score_threshold", 0.3))
            self.label_det_use_gpu = bool(self.config.get("label_det_use_gpu", False))
            self.label_det_nms_iou = float(self.config.get("label_det_nms_iou", 0.45))
            self.label_det_max_boxes = int(self.config.get("label_det_max_boxes", 6))
            self.label_det_min_area_ratio = float(self.config.get("label_det_min_area_ratio", 0.02))
            self.label_det_max_area_ratio = float(self.config.get("label_det_max_area_ratio", 0.9))
            self.label_det_crop_margin = int(self.config.get("label_det_crop_margin", 8))
            self.label_det_use_crop_ocr = bool(self.config.get("label_det_use_crop_ocr", True))
            self.label_det_adaptive_enabled = bool(self.config.get("label_det_adaptive_enabled", True))
            self.label_det_target_boxes = int(self.config.get("label_det_target_boxes", 3))
            self.ocr_use_gpu = bool(self.config.get("ocr_use_gpu", False))
            self.ground_truth_csv = self.config.get("ground_truth_csv", str(Path(__file__).resolve().parent / "multiple_labels_test" / "truth.csv"))
            self.test_record_csv = self.config.get("test_record_csv", str(Path(__file__).resolve().parent / "v0_71_grouping_test_records.csv"))

            # 存储单次识别的最新结果，用于手动保存
            self.last_raw_result = ""

            # 中央窗口部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            self.apply_modern_theme()
            
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
            self.clear_display_btn = QPushButton("清空当前输出框")
            self.clear_display_btn.clicked.connect(self.clear_output_display)

            # 输出模式切换
            self.output_mode_label = QLabel(f"当前输出模式: {'手动输出' if self.manual_output else '自动输出'}")
            self.update_output_mode_label_style()
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
            utility_btn_hbox = QHBoxLayout()
            utility_btn_hbox.addWidget(self.clear_outputs_btn)
            utility_btn_hbox.addWidget(self.clear_display_btn)
            settings_layout.addLayout(utility_btn_hbox)
            
            output_mode_hbox = QHBoxLayout()
            output_mode_hbox.addWidget(self.output_mode_label)
            output_mode_hbox.addStretch()
            output_mode_hbox.addWidget(self.toggle_output_mode_btn)
            settings_layout.addLayout(output_mode_hbox)

            main_layout.addWidget(settings_group)

            # --- 模式切换按钮 ---
            switch_mode_layout = QHBoxLayout()
            self.mode_label = QLabel("当前模式: 单次识别")
            self.update_mode_label_style()
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
            self.result_display.setPlaceholderText("这里会显示识别日志、标签检测结果、自适应策略选择与耗时信息。")
            self.result_display.setFont(QFont("Consolas", 10))
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

        def apply_modern_theme(self):
            self.setStyleSheet("""
                QWidget {
                    background-color: #f7f7f8;
                    color: #202123;
                    font-family: "Segoe UI", "Microsoft YaHei";
                    font-size: 10pt;
                }
                QMainWindow {
                    background-color: #f7f7f8;
                }
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 14px;
                    margin-top: 14px;
                    font-weight: 600;
                    padding-top: 12px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 6px;
                    color: #111827;
                }
                QLabel {
                    color: #374151;
                }
                QLineEdit, QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #d1d5db;
                    border-radius: 10px;
                    padding: 8px 10px;
                    selection-background-color: #10a37f;
                }
                QLineEdit:focus, QTextEdit:focus {
                    border: 1px solid #10a37f;
                }
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #d1d5db;
                    border-radius: 10px;
                    padding: 8px 14px;
                    color: #111827;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #f3f4f6;
                    border-color: #9ca3af;
                }
                QPushButton:pressed {
                    background-color: #e5e7eb;
                }
                QPushButton:disabled {
                    background-color: #f3f4f6;
                    color: #9ca3af;
                }
                QProgressBar {
                    border: 1px solid #d1d5db;
                    border-radius: 8px;
                    background: #ffffff;
                    text-align: center;
                    min-height: 18px;
                }
                QProgressBar::chunk {
                    background-color: #10a37f;
                    border-radius: 7px;
                }
                QFrame[frameShape="4"] {
                    color: #e5e7eb;
                }
            """)

        def update_output_mode_label_style(self):
            badge_bg = "#dcfce7" if self.manual_output else "#fef3c7"
            badge_fg = "#166534" if self.manual_output else "#92400e"
            self.output_mode_label.setStyleSheet(
                f"font-weight: 700; color: {badge_fg}; background-color: {badge_bg}; "
                "border-radius: 10px; padding: 6px 10px;"
            )

        def update_mode_label_style(self):
            self.mode_label.setStyleSheet(
                "font-weight: 700; color: #0f172a; background-color: #e0f2fe; "
                "border-radius: 10px; padding: 6px 10px;"
            )

        def closeEvent(self, event):
            """窗口关闭时保存配置"""
            try:
                if self.worker and self.worker.isRunning():
                    self.worker.requestInterruption()
                    self.worker.wait(5000)
            except Exception:
                pass
            try:
                if self.watcher_thread and self.watcher_thread.isRunning():
                    self.watcher_thread.stop_watching()
                    self.watcher_thread.wait(5000)
            except Exception:
                pass
            self.config["watch_dir"] = self.watch_dir_input.text() if hasattr(self, "watch_dir_input") else self.watch_dir
            self.config["output_dir"] = self.output_dir_input.text()
            self.config["processed_dir"] = self.processed_dir_input.text() if hasattr(self, "processed_dir_input") else self.processed_dir
            self.config["error_dir"] = self.error_dir_input.text() if hasattr(self, "error_dir_input") else self.error_dir
            self.config["visual_output_dir"] = self.visual_output_dir_input.text()
            self.config["txt_output_dir"] = self.txt_output_dir_input.text()
            self.config["manual_output"] = self.manual_output
            self.config["label_det_model_dir"] = self.label_det_model_dir
            self.config["label_det_score_threshold"] = self.label_det_score_threshold
            self.config["label_det_use_gpu"] = self.label_det_use_gpu
            self.config["label_det_nms_iou"] = self.label_det_nms_iou
            self.config["label_det_max_boxes"] = self.label_det_max_boxes
            self.config["label_det_min_area_ratio"] = self.label_det_min_area_ratio
            self.config["label_det_max_area_ratio"] = self.label_det_max_area_ratio
            self.config["label_det_crop_margin"] = self.label_det_crop_margin
            self.config["label_det_use_crop_ocr"] = self.label_det_use_crop_ocr
            self.config["label_det_adaptive_enabled"] = self.label_det_adaptive_enabled
            self.config["label_det_target_boxes"] = self.label_det_target_boxes
            self.config["ocr_use_gpu"] = self.ocr_use_gpu
            self.config["ground_truth_csv"] = self.truth_csv_input.text() if hasattr(self, "truth_csv_input") else self.ground_truth_csv
            self.config["test_record_csv"] = self.test_record_csv_input.text() if hasattr(self, "test_record_csv_input") else self.test_record_csv
            save_config(self.config)
            event.accept()

        def toggle_output_mode(self):
            """切换手动/自动输出模式"""
            self.manual_output = not self.manual_output
            self.output_mode_label.setText(f"当前输出模式: {'手动输出' if self.manual_output else '自动输出'}")
            self.update_output_mode_label_style()
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
            
            self.update_mode_label_style()
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
                self.status_label.setStyleSheet(
                    "color: #065f46; background-color: #d1fae5; border-radius: 10px; padding: 6px 10px;"
                )

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

                btn_hbox = QHBoxLayout()
                btn_hbox.addWidget(self.select_button)
                self.dynamic_content_layout.addLayout(btn_hbox)
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
                QMessageBox.warning(self, "警告", "请填写处理后、异常、JSON、可视化、TXT文件夹路径。")
                return

            self.worker = OcrWorker(
                file_path,
                processed_dir,
                error_dir,
                output_dir,
                visual_output_dir,
                txt_output_dir,
                self.manual_output,
                self.label_det_model_dir,
                self.label_det_score_threshold,
                self.label_det_use_gpu,
                self.label_det_nms_iou,
                self.label_det_max_boxes,
                self.label_det_min_area_ratio,
                self.label_det_max_area_ratio,
                self.label_det_crop_margin,
                self.label_det_use_crop_ocr,
                self.label_det_adaptive_enabled,
                self.label_det_target_boxes,
                self.ocr_use_gpu,
                truth_csv_path,
                test_record_csv
            )
            self.worker.finished_signal.connect(self.on_single_process_finished)
            self.worker.progress_signal.connect(self.on_progress_update)
            self.worker.log_signal.connect(self.log_message)
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

            label_det_error = results.get("label_det_error")
            if label_det_error:
                self.result_display.append(f"[标签检测模型错误] {label_det_error}")
            self.result_display.append(display_text)
            if self.worker:
                try:
                    self.worker.quit()
                    self.worker.wait(5000)
                except Exception:
                    pass
                try:
                    self.worker.deleteLater()
                except Exception:
                    pass
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
                QMessageBox.warning(self, "警告", "请填写所有文件夹路径。")
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
                self.label_det_model_dir,
                self.label_det_score_threshold,
                self.label_det_use_gpu,
                self.label_det_nms_iou,
                self.label_det_max_boxes,
                self.label_det_min_area_ratio,
                self.label_det_max_area_ratio,
                self.label_det_crop_margin,
                self.label_det_use_crop_ocr,
                self.label_det_adaptive_enabled,
                self.label_det_target_boxes,
                self.ocr_use_gpu,
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

        def clear_output_display(self):
            """清空输出日志框"""
            self.result_display.clear()


    def main():
        """主函数，启动GUI应用。"""
        print("=== 正在启动Mr.6's Auto OCR Pipeline... ===")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())


    if __name__ == "__main__":
        main()
