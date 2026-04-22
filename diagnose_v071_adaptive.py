import os
from pathlib import Path

os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"

import cv2  # noqa: E402
import importlib.util  # noqa: E402


def _load_module():
    root = Path(__file__).resolve().parent
    module_path = root / "auto_ocr_pipeline_v0.71_tuned.py"
    spec = importlib.util.spec_from_file_location("auto_ocr_pipeline_v0_71_tuned", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def main():
    root = Path(__file__).resolve().parent
    image_dir = root / "multiple_labels_test"
    model_dir = root / "PaddleDetection-release-2.8.1" / "output_inference" / "label_det_m_45e"

    detector = mod._get_label_detector(
        str(model_dir),
        use_gpu=False,
        score_threshold=0.3,
        log_callback=print,
    )

    for image_name in ["m001.jpg", "m002.png", "m003.jpg", "m009.jpg"]:
        image_path = image_dir / image_name
        image_cv = cv2.imread(str(image_path))
        h, w = image_cv.shape[:2]
        print(f"\n===== {image_name} =====")
        raw_boxes, filtered_boxes, stats, chosen = mod._detect_label_boxes_adaptive(
            detector,
            str(image_path),
            w,
            h,
            score_th=0.3,
            nms_iou=0.45,
            min_area_ratio=0.02,
            max_area_ratio=0.9,
            max_boxes=6,
            adaptive_enabled=True,
            target_boxes=3,
            log_callback=print,
            log_prefix="[diag] ",
        )
        print("chosen:", chosen)
        print("stats:", stats)
        print("final_boxes:", len(filtered_boxes))
        for idx, box in enumerate(filtered_boxes, start=1):
            print(f"  {idx}: {[round(v, 2) for v in box]}")


if __name__ == "__main__":
    main()
