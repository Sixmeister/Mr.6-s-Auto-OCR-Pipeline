import importlib.util
from pathlib import Path


_ROOT = Path(__file__).resolve().parent
_BASE_PATH = _ROOT / "_repo_sync" / "auto_ocr_pipeline_v0.71_tuned.py"
if not _BASE_PATH.exists():
    raise FileNotFoundError(f"Base tuned module was not found: {_BASE_PATH}")

_SPEC = importlib.util.spec_from_file_location("auto_ocr_pipeline_v0_71_tuned_base", _BASE_PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_BASE)

# Re-export the original module symbols first so this file can be used as a drop-in variant.
for _name, _value in vars(_BASE).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


_ORIG_LOAD_CONFIG = _BASE.load_config


def load_config():
    cfg = _ORIG_LOAD_CONFIG()
    cfg["label_det_score_threshold"] = 0.50
    cfg["label_det_nms_iou"] = 0.45
    cfg["label_det_max_boxes"] = 4
    cfg["label_det_min_area_ratio"] = 0.0005
    cfg["label_det_max_area_ratio"] = 0.98
    cfg["label_det_adaptive_enabled"] = True
    cfg["label_det_target_boxes"] = 4
    cfg["test_record_csv"] = str(_ROOT / "v0_7_retuned_grouping_test_records.csv")
    return cfg


def _filter_retuned_boxes_with_stats(boxes, img_w, img_h, score_th=0.5, max_boxes=4):
    stats = {
        "input": 0,
        "clamped": 0,
        "score": 0,
        "area": 0,
        "nms": 0,
        "merged": 0,
        "score_sum": 0.0,
    }
    if not boxes:
        return [], stats

    stats["input"] = len(boxes)
    clamped = []
    for b in boxes:
        cb = _BASE._clamp_box(b, img_w, img_h, margin=0)
        if cb is None:
            continue
        clamped.append([float(cb[0]), float(cb[1]), float(cb[2]), float(cb[3]), float(b[4])])
    stats["clamped"] = len(clamped)

    filtered = [b for b in clamped if b[4] >= score_th]
    filtered = sorted(filtered, key=lambda x: x[4], reverse=True)
    stats["score"] = len(filtered)
    stats["area"] = len(filtered)
    stats["nms"] = len(filtered)

    # The enhanced50 detector comparison showed the 45e detector is already count-faithful
    # at threshold 0.5, so keep the post-filter logic intentionally light here.
    if max_boxes and len(filtered) > max_boxes:
        filtered = filtered[:max_boxes]

    stats["merged"] = len(filtered)
    stats["score_sum"] = round(sum(b[4] for b in filtered), 4)
    return filtered, stats


def _build_retuned_profiles(score_th, nms_iou, max_boxes, min_area_ratio, max_area_ratio):
    return [
        {
            "name": "base_050",
            "score_th": max(0.50, score_th),
            "nms_iou": nms_iou,
            "max_boxes": min(4, max_boxes) if max_boxes else 4,
            "min_area_ratio": 0.0005,
            "max_area_ratio": 0.98,
        },
        {
            "name": "strict_055",
            "score_th": max(0.55, score_th + 0.05),
            "nms_iou": nms_iou,
            "max_boxes": min(4, max_boxes) if max_boxes else 4,
            "min_area_ratio": 0.0005,
            "max_area_ratio": 0.98,
        },
        {
            "name": "recover_045",
            "score_th": min(0.49, max(0.45, score_th - 0.05)),
            "nms_iou": nms_iou,
            "max_boxes": min(4, max_boxes) if max_boxes else 4,
            "min_area_ratio": 0.0005,
            "max_area_ratio": 0.98,
        },
        {
            "name": "recover_040",
            "score_th": min(0.44, max(0.40, score_th - 0.10)),
            "nms_iou": nms_iou,
            "max_boxes": min(4, max_boxes) if max_boxes else 4,
            "min_area_ratio": 0.0005,
            "max_area_ratio": 0.98,
        },
    ]


def _select_retuned_candidate(candidates):
    if not candidates:
        return None

    # Prefer the first reasonable 2-4 box candidate so we stay close to the detector's
    # natural count prediction instead of biasing everything toward a fixed target count.
    for name in ("base_050", "strict_055", "recover_045", "recover_040"):
        for item in candidates:
            if item["profile"]["name"] != name:
                continue
            count = item["stats"].get("merged", 0)
            if 2 <= count <= 4:
                return item

    # Fallback: prefer more non-zero boxes, then stronger score sum.
    return max(
        candidates,
        key=lambda item: (
            1 if item["stats"].get("merged", 0) > 0 else 0,
            item["stats"].get("merged", 0),
            item["stats"].get("score_sum", 0.0),
            -item["index"],
        ),
    )


def _refine_box_count_by_scores(boxes, log_callback=None, log_prefix=""):
    if not boxes:
        return boxes

    ordered = sorted(boxes, key=lambda x: x[4], reverse=True)
    scores = [float(b[4]) for b in ordered]

    if len(ordered) <= 2:
        return ordered

    if len(ordered) == 3:
        # Retuned mode intentionally stops suppressing 3 -> 2 aggressively.
        return ordered

    if len(ordered) == 4:
        s3 = scores[2]
        s4 = scores[3]
        if s4 < 0.32 and (s3 - s4) > 0.35:
            if log_callback:
                log_callback(
                    f"{log_prefix}retuned尾框修正: 第4框过弱(score4={s4:.2f}, gap34={(s3 - s4):.2f})，4->3"
                )
            return ordered[:3]
        return ordered

    if log_callback:
        log_callback(f"{log_prefix}retuned尾框修正: 截断到前4个高置信框")
    return ordered[:4]


def _detect_label_boxes_adaptive(detector, image_path, img_w, img_h, score_th=0.5, nms_iou=0.45,
                                 min_area_ratio=0.0005, max_area_ratio=0.98, max_boxes=4,
                                 adaptive_enabled=True, target_boxes=4, log_callback=None, log_prefix=""):
    raw_boxes = _BASE._detect_label_boxes(detector, image_path, score_threshold=score_th)
    profiles = _build_retuned_profiles(score_th, nms_iou, max_boxes, min_area_ratio, max_area_ratio)
    if not adaptive_enabled:
        profiles = profiles[:1]

    candidates = []
    for idx, profile in enumerate(profiles):
        filtered_boxes, stats = _filter_retuned_boxes_with_stats(
            raw_boxes,
            img_w,
            img_h,
            score_th=profile["score_th"],
            max_boxes=profile["max_boxes"],
        )
        candidate = {
            "index": idx,
            "profile": profile,
            "stats": stats,
            "boxes": filtered_boxes,
        }
        candidates.append(candidate)
        if log_callback:
            log_callback(
                f"{log_prefix}retuned[{profile['name']}]: score={profile['score_th']:.2f} "
                f"max={profile['max_boxes']} -> raw={stats['input']} kept={stats['merged']}"
            )

    chosen = _select_retuned_candidate(candidates)
    if chosen is None:
        return raw_boxes, [], {"input": 0, "clamped": 0, "score": 0, "area": 0, "nms": 0}, None

    refined_boxes = _refine_box_count_by_scores(
        chosen["boxes"],
        log_callback=log_callback,
        log_prefix=log_prefix,
    )
    chosen_stats = dict(chosen["stats"])
    chosen_stats["merged"] = len(refined_boxes)
    chosen_stats["score_sum"] = round(sum(b[4] for b in refined_boxes), 4)
    return raw_boxes, refined_boxes, chosen_stats, chosen["profile"]


def _get_label_detector(model_dir, use_gpu=False, score_threshold=0.5, log_callback=None):
    model_dir = str(Path(model_dir).resolve())
    if not Path(model_dir).is_dir():
        if log_callback:
            log_callback(f"    -> 标签检测模型不可用: {model_dir}")
        return None

    cfg_key = (model_dir, bool(use_gpu), float(score_threshold))
    if _BASE._LABEL_DETECTOR is not None and _BASE._LABEL_DETECTOR_CFG == cfg_key:
        return _BASE._LABEL_DETECTOR
    if _BASE._LABEL_DETECTOR_ERR is not None and _BASE._LABEL_DETECTOR_CFG == cfg_key:
        return None

    with _BASE._LABEL_DETECTOR_LOCK:
        if _BASE._LABEL_DETECTOR is not None and _BASE._LABEL_DETECTOR_CFG == cfg_key:
            return _BASE._LABEL_DETECTOR
        if _BASE._LABEL_DETECTOR_ERR is not None and _BASE._LABEL_DETECTOR_CFG == cfg_key:
            return None
        try:
            deploy_dir = str((_ROOT / "PaddleDetection-release-2.8.1" / "deploy" / "python").resolve())
            if deploy_dir not in _BASE.sys.path:
                _BASE.sys.path.insert(0, deploy_dir)
            from infer import Detector

            device = "GPU" if use_gpu else "CPU"
            _BASE._LABEL_DETECTOR = Detector(
                model_dir=model_dir,
                device=device,
                threshold=score_threshold,
            )
            _BASE._LABEL_DETECTOR_ERR = None
            _BASE._LABEL_DETECTOR_CFG = cfg_key
            if log_callback:
                log_callback(f"    -> retuned标签检测模型已加载: {model_dir} | 设备: {device}")
        except Exception as e:
            _BASE._LABEL_DETECTOR = None
            _BASE._LABEL_DETECTOR_ERR = str(e)
            _BASE._LABEL_DETECTOR_CFG = cfg_key
            if log_callback:
                log_callback(f"    -> retuned标签检测模型加载失败: {e}")
    return _BASE._LABEL_DETECTOR


# Patch the base module too, so any reused helpers/classes inside it resolve to the retuned logic.
_BASE.load_config = load_config
_BASE._get_label_detector = _get_label_detector
_BASE._detect_label_boxes_adaptive = _detect_label_boxes_adaptive
_BASE._refine_box_count_by_scores = _refine_box_count_by_scores

# Re-export patched names explicitly.
globals()["load_config"] = load_config
globals()["_get_label_detector"] = _get_label_detector
globals()["_detect_label_boxes_adaptive"] = _detect_label_boxes_adaptive
globals()["_refine_box_count_by_scores"] = _refine_box_count_by_scores
