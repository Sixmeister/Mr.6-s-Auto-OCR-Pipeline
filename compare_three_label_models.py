import argparse
import csv
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare three exported label detection models on the same labeled test set."
    )
    parser.add_argument("--model-1", required=True, help="Path to first exported model directory.")
    parser.add_argument("--model-2", required=True, help="Path to second exported model directory.")
    parser.add_argument("--model-3", required=True, help="Path to third exported model directory.")
    parser.add_argument("--name-1", default="model_1", help="Display name for first model.")
    parser.add_argument("--name-2", default="model_2", help="Display name for second model.")
    parser.add_argument("--name-3", default="model_3", help="Display name for third model.")
    parser.add_argument("--image-dir", required=True, help="Directory containing test images.")
    parser.add_argument("--truth-csv", required=True, help="CSV with image_name and actual_label_count.")
    parser.add_argument("--output-dir", required=True, help="Directory for visual outputs and CSV reports.")
    parser.add_argument("--threshold-1", type=float, default=0.5, help="Confidence threshold for first model.")
    parser.add_argument("--threshold-2", type=float, default=0.5, help="Confidence threshold for second model.")
    parser.add_argument("--threshold-3", type=float, default=0.5, help="Confidence threshold for third model.")
    parser.add_argument("--device", default="CPU", help="Inference device, normally CPU or GPU.")
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
    results = detector.predict_image([str(image_path)], visual=True, save_results=False)
    boxes = results.get("boxes")
    if boxes is None:
        return []
    filtered = []
    for row in boxes.tolist():
        if len(row) >= 2 and float(row[1]) >= threshold:
            filtered.append(row)
    return filtered


def summarize(rows, prefix):
    total = len(rows)
    exact = sum(1 for row in rows if row[f"{prefix}_match"] == 1)
    abs_error_sum = sum(row[f"{prefix}_abs_error"] for row in rows)
    over_detect = sum(1 for row in rows if row[f"{prefix}_pred_count"] > row["actual_label_count"])
    under_detect = sum(1 for row in rows if row[f"{prefix}_pred_count"] < row["actual_label_count"])
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


def write_summary(path, summaries, names):
    lines = []
    for idx, (prefix, summary) in enumerate(summaries.items(), start=1):
        display_name = names[prefix]
        lines.extend(
            [
                f"{display_name}:",
                f"  total_images={summary['total_images']}",
                f"  exact_match_images={summary['exact_match_images']}",
                f"  exact_match_rate={summary['exact_match_rate']:.4f}",
                f"  mean_abs_error={summary['mean_abs_error']:.4f}",
                f"  over_detect_images={summary['over_detect_images']}",
                f"  under_detect_images={summary['under_detect_images']}",
                "",
            ]
        )

    best_prefix = max(summaries, key=lambda key: summaries[key]["exact_match_rate"])
    lines.append(f"Conclusion: {names[best_prefix]} has the highest exact-match rate.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    Detector = ensure_ppdet_importable(project_root)

    image_dir = Path(args.image_dir).resolve()
    truth_csv = Path(args.truth_csv).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = [
        ("m1", args.name_1, Path(args.model_1).resolve(), args.threshold_1),
        ("m2", args.name_2, Path(args.model_2).resolve(), args.threshold_2),
        ("m3", args.name_3, Path(args.model_3).resolve(), args.threshold_3),
    ]

    detectors = {}
    names = {}
    for prefix, display_name, model_dir, threshold in configs:
        vis_dir = output_dir / display_name
        vis_dir.mkdir(parents=True, exist_ok=True)
        detectors[prefix] = (
            Detector(
                model_dir=str(model_dir),
                device=args.device.upper(),
                threshold=threshold,
                output_dir=str(vis_dir),
            ),
            threshold,
        )
        names[prefix] = display_name

    truth_rows = load_truth_rows(truth_csv)
    compare_rows = []

    for row in truth_rows:
        image_name = row["image_name"]
        image_path = image_dir / image_name
        if not image_path.exists():
            raise FileNotFoundError(f"Missing image: {image_path}")

        out_row = {
            "image_name": image_name,
            "actual_label_count": row["actual_label_count"],
        }
        actual = row["actual_label_count"]

        for prefix, _, _, _ in configs:
            detector, threshold = detectors[prefix]
            boxes = detect_and_visualize(detector, image_path, threshold)
            pred = len(boxes)
            out_row[f"{names[prefix]}_pred_count"] = pred
            out_row[f"{names[prefix]}_match"] = 1 if pred == actual else 0
            out_row[f"{names[prefix]}_abs_error"] = abs(pred - actual)

        compare_rows.append(out_row)

    summaries = {prefix: summarize(compare_rows, names[prefix]) for prefix, _, _, _ in configs}

    fieldnames = ["image_name", "actual_label_count"]
    for prefix, _, _, _ in configs:
        display_name = names[prefix]
        fieldnames.extend(
            [
                f"{display_name}_pred_count",
                f"{display_name}_match",
                f"{display_name}_abs_error",
            ]
        )

    write_csv(output_dir / "model_compare.csv", compare_rows, fieldnames)
    write_summary(output_dir / "summary.txt", summaries, names)

    print(f"Saved compare CSV to: {output_dir / 'model_compare.csv'}")
    print(f"Saved summary to: {output_dir / 'summary.txt'}")
    for prefix, summary in summaries.items():
        print(f"{names[prefix]} exact-match rate: {summary['exact_match_rate']:.4f}")


if __name__ == "__main__":
    main()
