import importlib.util
import os
import time
from pathlib import Path

import cv2

os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"


def _load_module():
    root = Path(__file__).resolve().parent
    module_path = root / "auto_ocr_pipeline_v0.63.py"
    spec = importlib.util.spec_from_file_location("auto_ocr_pipeline_v0_63", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _iter_truth(mod, csv_path):
    truth_map = mod.load_ground_truth_map(str(csv_path))
    for name in sorted(truth_map.keys()):
        yield name, truth_map[name]


def main():
    root = Path(__file__).resolve().parent
    mod = _load_module()

    image_dir = root / "multiple_labels_test_enhanced"
    truth_csv = image_dir / "truth.csv"
    out_csv = root / "v0_63_grouping_test_records_enhanced50.csv"

    # Keep the same v0.63 detector-side settings as the 10-image retest.
    label_det_model_dir = root / "PaddleDetection-release-2.8.1" / "output_inference" / "label_det_m_45e"
    score_th = 0.32
    nms_iou = 0.75
    max_boxes = 3
    min_area_ratio = 0.002
    max_area_ratio = 0.98
    crop_margin = 8
    use_crop_ocr = True

    truth_map = mod.load_ground_truth_map(str(truth_csv))
    ocr = mod._create_ocr_engine(use_gpu=False)
    detector = mod._get_label_detector(
        str(label_det_model_dir),
        use_gpu=False,
        score_threshold=score_th,
        log_callback=lambda *_: None,
    )

    if out_csv.exists():
        out_csv.unlink()

    for image_name, _actual in _iter_truth(mod, truth_csv):
        image_path = image_dir / image_name
        start = time.perf_counter()
        try:
            image_cv = cv2.imread(str(image_path))
            if image_cv is None:
                raise ValueError(f"unable to read image: {image_path}")
            img_h, img_w = image_cv.shape[:2]

            raw_boxes = mod._detect_label_boxes(detector, str(image_path), score_threshold=score_th)
            filtered_boxes, _stats = mod._filter_label_boxes_with_stats(
                raw_boxes,
                img_w,
                img_h,
                score_th=score_th,
                nms_iou=nms_iou,
                min_area_ratio=min_area_ratio,
                max_area_ratio=max_area_ratio,
                max_boxes=max_boxes,
            )

            labels = []
            if filtered_boxes and use_crop_ocr:
                for idx, b in enumerate(filtered_boxes, start=1):
                    clamp = mod._clamp_box(b, img_w, img_h, margin=crop_margin)
                    if not clamp:
                        continue
                    crop_texts = mod._run_crop_ocr(ocr, image_cv, clamp)
                    crop_codes = []
                    crop = image_cv[clamp[1]:clamp[3], clamp[0]:clamp[2]]
                    for obj in mod.pyzbar.decode(crop):
                        rect = obj.rect
                        bbox = [
                            rect.left + clamp[0],
                            rect.top + clamp[1],
                            rect.left + rect.width + clamp[0],
                            rect.top + rect.height + clamp[1],
                        ]
                        crop_codes.append(
                            {
                                "type": "code",
                                "code_type": obj.type,
                                "data": obj.data.decode("utf-8"),
                                "bbox": bbox,
                            }
                        )
                    labels.append(
                        {
                            "label_id": idx,
                            "bbox": [int(v) for v in clamp],
                            "texts": crop_texts,
                            "codes": crop_codes,
                        }
                    )
            else:
                ocr_results = mod._run_ocr(ocr, str(image_path))
                if not ocr_results:
                    raise ValueError("OCR returned empty result")
                ocr_result = ocr_results[0] if isinstance(ocr_results, list) else ocr_results
                text_items = mod._extract_text_items_from_ocr_result(ocr_result)
                code_items = []
                for obj in mod.pyzbar.decode(image_cv):
                    rect = obj.rect
                    bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                    code_items.append(
                        {
                            "type": "code",
                            "code_type": obj.type,
                            "data": obj.data.decode("utf-8"),
                            "bbox": bbox,
                        }
                    )
                labels = mod._build_label_groups(text_items, code_items)

            elapsed = time.perf_counter() - start
            row = mod.build_grouping_test_record(image_name, len(labels), elapsed, truth_map, True)
            mod.append_grouping_test_record(str(out_csv), row)
        except Exception as e:
            elapsed = time.perf_counter() - start
            row = mod.build_grouping_test_record(image_name, 0, elapsed, truth_map, False, error=str(e))
            mod.append_grouping_test_record(str(out_csv), row)

    print(f"out_csv={out_csv}")


if __name__ == "__main__":
    main()
