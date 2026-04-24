import argparse
import csv
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare exported label detection models on the same labeled test set."
    )
    parser.add_argument(
        "--model-a",
        required=True,
        help="Path to first exported model directory.",
    )
    parser.add_argument(
        "--model-b",
        required=True,
        help="Path to second exported model directory.",
    )
    parser.add_argument(
        "--name-a",
        default="model_a",
        help="Display name for first model.",
    )
    parser.add_argument(
        "--name-b",
        default="model_b",
        help="Display name for second model.",
    )
    parser.add_argument(
        "--image-dir",
        required=True,
        help="Directory containing test images.",
    )
    parser.add_argument(
        "--truth-csv",
        required=True,
        help="CSV with image_name and actual_label_count.",
    )
    parser.add_argument(
        "--output-dir",
        default="model_compare_outputs",
        help="Directory for visual outputs and CSV reports.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Confidence threshold used for both models.",
    )
    parser.add_argument(
        "--device",
        default="CPU",
        help="Inference device, normally CPU or GPU.",
    )
    return parser.parse_args()


def ensure_ppdet_importable(project_root):
    deploy_python = project_root / "PaddleDetection-release-2.8.1" / "deploy" / "python"
    sys.path.insert(0, str(deploy_python))
    from infer import Detector  # noqa: WPS433
    return Detector


def load_truth_rows(truth_csv_path):
    rows = []
    with truth_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "image_name": row["image_name"].strip(),
                    "actual_label_count": int(row["actual_label_count"]),
                }
            )
    return rows


def detect_and_visualize(detector, image_path, threshold):
    results = detector.predict_image(
        [str(image_path)],
        visual=True,
        save_results=False,
    )
    boxes = results.get("boxes")
    if boxes is None:
        return []
    filtered = []
    for row in boxes.tolist():
        if len(row) >= 2 and float(row[1]) >= threshold:
            filtered.append(row)
    return filtered


def box_count(box_rows):
    return len(box_rows)


def summarize(rows, name_key):
    total = len(rows)
    exact = sum(1 for row in rows if row[f"{name_key}_match"] == 1)
    abs_error_sum = sum(row[f"{name_key}_abs_error"] for row in rows)
    over_detect = sum(1 for row in rows if row[f"{name_key}_pred_count"] > row["actual_label_count"])
    under_detect = sum(1 for row in rows if row[f"{name_key}_pred_count"] < row["actual_label_count"])
    return {
        "total_images": total,
        "exact_match_images": exact,
        "exact_match_rate": (exact / total) if total else 0.0,
        "mean_abs_error": (abs_error_sum / total) if total else 0.0,
        "over_detect_images": over_detect,
        "under_detect_images": under_detect,
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, summary_a, summary_b, name_a, name_b):
    lines = [
        f"{name_a}:",
        f"  total_images={summary_a['total_images']}",
        f"  exact_match_images={summary_a['exact_match_images']}",
        f"  exact_match_rate={summary_a['exact_match_rate']:.4f}",
        f"  mean_abs_error={summary_a['mean_abs_error']:.4f}",
        f"  over_detect_images={summary_a['over_detect_images']}",
        f"  under_detect_images={summary_a['under_detect_images']}",
        "",
        f"{name_b}:",
        f"  total_images={summary_b['total_images']}",
        f"  exact_match_images={summary_b['exact_match_images']}",
        f"  exact_match_rate={summary_b['exact_match_rate']:.4f}",
        f"  mean_abs_error={summary_b['mean_abs_error']:.4f}",
        f"  over_detect_images={summary_b['over_detect_images']}",
        f"  under_detect_images={summary_b['under_detect_images']}",
    ]

    if summary_b["exact_match_rate"] > summary_a["exact_match_rate"]:
        lines.extend(["", f"Conclusion: {name_b} has the higher exact-match rate."])
    elif summary_b["exact_match_rate"] < summary_a["exact_match_rate"]:
        lines.extend(["", f"Conclusion: {name_a} has the higher exact-match rate."])
    else:
        lines.extend(["", "Conclusion: exact-match rates are equal."])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    Detector = ensure_ppdet_importable(project_root)

    model_a_dir = Path(args.model_a).resolve()
    model_b_dir = Path(args.model_b).resolve()
    image_dir = Path(args.image_dir).resolve()
    truth_csv = Path(args.truth_csv).resolve()
    output_dir = Path(args.output_dir).resolve()
    vis_a_dir = output_dir / args.name_a
    vis_b_dir = output_dir / args.name_b
    output_dir.mkdir(parents=True, exist_ok=True)
    vis_a_dir.mkdir(parents=True, exist_ok=True)
    vis_b_dir.mkdir(parents=True, exist_ok=True)

    detector_a = Detector(
        model_dir=str(model_a_dir),
        device=args.device.upper(),
        threshold=args.threshold,
        output_dir=str(vis_a_dir),
    )
    detector_b = Detector(
        model_dir=str(model_b_dir),
        device=args.device.upper(),
        threshold=args.threshold,
        output_dir=str(vis_b_dir),
    )

    truth_rows = load_truth_rows(truth_csv)
    compare_rows = []

    for row in truth_rows:
        image_name = row["image_name"]
        image_path = image_dir / image_name
        if not image_path.exists():
            raise FileNotFoundError(f"Missing image: {image_path}")

        boxes_a = detect_and_visualize(detector_a, image_path, args.threshold)
        boxes_b = detect_and_visualize(detector_b, image_path, args.threshold)
        pred_a = box_count(boxes_a)
        pred_b = box_count(boxes_b)
        actual = row["actual_label_count"]

        compare_rows.append(
            {
                "image_name": image_name,
                "actual_label_count": actual,
                f"{args.name_a}_pred_count": pred_a,
                f"{args.name_a}_match": 1 if pred_a == actual else 0,
                f"{args.name_a}_abs_error": abs(pred_a - actual),
                f"{args.name_b}_pred_count": pred_b,
                f"{args.name_b}_match": 1 if pred_b == actual else 0,
                f"{args.name_b}_abs_error": abs(pred_b - actual),
            }
        )

    summary_a = summarize(compare_rows, args.name_a)
    summary_b = summarize(compare_rows, args.name_b)

    compare_csv = output_dir / "model_compare.csv"
    summary_txt = output_dir / "summary.txt"
    write_csv(
        compare_csv,
        compare_rows,
        [
            "image_name",
            "actual_label_count",
            f"{args.name_a}_pred_count",
            f"{args.name_a}_match",
            f"{args.name_a}_abs_error",
            f"{args.name_b}_pred_count",
            f"{args.name_b}_match",
            f"{args.name_b}_abs_error",
        ],
    )
    write_summary(summary_txt, summary_a, summary_b, args.name_a, args.name_b)

    print(f"Saved compare CSV to: {compare_csv}")
    print(f"Saved summary to: {summary_txt}")
    print(f"{args.name_a} exact-match rate: {summary_a['exact_match_rate']:.4f}")
    print(f"{args.name_b} exact-match rate: {summary_b['exact_match_rate']:.4f}")


if __name__ == "__main__":
    main()
