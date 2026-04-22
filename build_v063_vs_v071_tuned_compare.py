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


def _note(actual: int, p63: int, p71: int):
    if p63 == actual and p71 == actual:
        return "both_correct"
    if p63 == actual and p71 != actual:
        return "v0.71_worse"
    if p63 != actual and p71 == actual:
        return "v0.71_better"
    # both wrong
    d63 = abs(p63 - actual)
    d71 = abs(p71 - actual)
    if d71 < d63:
        return "v0.71_closer"
    if d71 > d63:
        return "v0.71_farther"
    return "both_wrong_equal"


def main():
    root = Path(__file__).resolve().parent
    truth_csv = root / "multiple_labels_test" / "truth.csv"
    v63_csv = root / "v0_63_grouping_test_records_retest.csv"
    v71_csv = root / "v0_71_tuned_grouping_test_records.csv"
    out_csv = root / "v0_63_vs_v0_71_tuned_compare.csv"

    # Load truth
    truth = {}
    with open(truth_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            truth[r["image_name"]] = int(r["actual_label_count"])

    r63 = _read_records(v63_csv)
    r71 = _read_records(v71_csv)

    fieldnames = [
        "image_name",
        "actual_label_count",
        "v0_63_predicted_label_count",
        "v0_71_predicted_label_count",
        "v0_63_label_count_correct",
        "v0_71_label_count_correct",
        "v0_63_elapsed_seconds",
        "v0_71_elapsed_seconds",
        "note",
    ]

    rows = []
    for name in sorted(truth.keys()):
        actual = truth[name]
        a63 = r63.get(name, {})
        a71 = r71.get(name, {})

        p63 = int(a63.get("predicted_label_count", 0) or 0)
        p71 = int(a71.get("predicted_label_count", 0) or 0)

        rows.append(
            {
                "image_name": name,
                "actual_label_count": actual,
                "v0_63_predicted_label_count": p63,
                "v0_71_predicted_label_count": p71,
                "v0_63_label_count_correct": a63.get("label_count_correct", ""),
                "v0_71_label_count_correct": a71.get("label_count_correct", ""),
                "v0_63_elapsed_seconds": a63.get("elapsed_seconds", ""),
                "v0_71_elapsed_seconds": a71.get("elapsed_seconds", ""),
                "note": _note(actual, p63, p71),
            }
        )

    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"out_csv={out_csv}")


if __name__ == "__main__":
    main()

