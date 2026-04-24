import csv
from pathlib import Path


def _read_records(path: Path):
    data = {}
    if not path.exists():
        return data
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("image_name")
            if name:
                data[name] = row
    return data


def main():
    root = Path(__file__).resolve().parent
    truth_csv = root / "multiple_labels_test_enhanced" / "truth.csv"
    v05_csv = root / "v0_5_grouping_test_records_enhanced50.csv"
    v63_csv = root / "v0_63_grouping_test_records_enhanced50.csv"
    out_csv = root / "v0_5_vs_v0_63_compare_enhanced50.csv"

    truth = {}
    with open(truth_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            truth[r["image_name"]] = int(r["actual_label_count"])

    r05 = _read_records(v05_csv)
    r63 = _read_records(v63_csv)

    fieldnames = [
        "image_name",
        "actual_label_count",
        "v0_5_predicted_label_count",
        "v0_63_predicted_label_count",
        "v0_5_label_count_correct",
        "v0_63_label_count_correct",
        "note",
    ]

    rows = []
    for name in sorted(truth.keys()):
        actual = truth[name]
        a05 = r05.get(name, {})
        a63 = r63.get(name, {})
        rows.append(
            {
                "image_name": name,
                "actual_label_count": actual,
                "v0_5_predicted_label_count": int(a05.get("predicted_label_count", 0) or 0),
                "v0_63_predicted_label_count": int(a63.get("predicted_label_count", 0) or 0),
                "v0_5_label_count_correct": a05.get("label_count_correct", ""),
                "v0_63_label_count_correct": a63.get("label_count_correct", ""),
                "note": "enhanced50 clustering_vs_detector_first",
            }
        )

    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"out_csv={out_csv}")


if __name__ == "__main__":
    main()
