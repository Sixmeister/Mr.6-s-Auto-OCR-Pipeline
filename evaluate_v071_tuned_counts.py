import csv
import importlib.util
import os
from pathlib import Path

import cv2

os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"


def load_module():
    root = Path(__file__).resolve().parent
    module_path = root / "auto_ocr_pipeline_v0.71_tuned.py"
    spec = importlib.util.spec_from_file_location("auto_ocr_pipeline_v0_71_tuned", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    root = Path(__file__).resolve().parent
    image_dir = root / "multiple_labels_test"
    truth_csv = image_dir / "truth.csv"
    output_csv = root / "v0_71_tuned_eval.csv"
    model_dir = root / "PaddleDetection-release-2.8.1" / "output_inference" / "label_det_m_45e"
    mod = load_module()

    truth_map = mod.load_ground_truth_map(str(truth_csv))
    detector = mod._get_label_detector(
        str(model_dir),
        use_gpu=False,
        score_threshold=0.3,
        log_callback=lambda *_: None,
    )

    rows = []
    correct = 0
    abs_error_sum = 0
    for image_name, actual_count in truth_map.items():
        image_path = image_dir / image_name
        image_cv = cv2.imread(str(image_path))
        h, w = image_cv.shape[:2]
        _, filtered_boxes, _, chosen_profile = mod._detect_label_boxes_adaptive(
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
            log_callback=lambda *_: None,
        )
        predicted = len(filtered_boxes)
        is_correct = predicted == actual_count
        correct += int(is_correct)
        abs_error_sum += abs(predicted - actual_count)
        rows.append({
            "image_name": image_name,
            "actual_label_count": actual_count,
            "predicted_label_count": predicted,
            "label_count_correct": "Yes" if is_correct else "No",
            "over_split": "Yes" if predicted > actual_count else "No",
            "over_merge": "Yes" if predicted < actual_count else "No",
            "chosen_profile": "" if chosen_profile is None else chosen_profile["name"],
        })

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_name",
                "actual_label_count",
                "predicted_label_count",
                "label_count_correct",
                "over_split",
                "over_merge",
                "chosen_profile",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    print(f"total={total}")
    print(f"correct={correct}")
    print(f"accuracy={correct / total:.4f}")
    print(f"mae={abs_error_sum / total:.4f}")
    print(f"csv={output_csv}")


if __name__ == "__main__":
    main()
