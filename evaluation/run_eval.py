from pathlib import Path
import json
import mimetypes
import requests

EVAL_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = EVAL_DIR / "samples"
OUTPUT_FILE = EVAL_DIR / "predictions.json"

API_URL = "http://localhost:8000/review"
TIMEOUT_SECONDS = 180


def detect_language_from_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return "javascript"
    return "python"


def flatten_prediction_issues(response_json: dict, sample_file: str) -> list[dict]:
    issues = response_json.get("issues", [])
    flattened = []

    for issue in issues:
        flattened.append({
            "file": issue.get("file", sample_file),
            "line": int(issue.get("line", 1)),
            "category": issue.get("category", ""),
            "issue_type": issue.get("issue_type", ""),
            "severity": issue.get("severity", ""),
            "agent": issue.get("agent", ""),
            "confidence": issue.get("confidence", 0.0),
            "processing_time_ms": response_json.get("processing_time_ms", 0),
        })

    return flattened


def main() -> None:
    if not SAMPLES_DIR.exists():
        raise FileNotFoundError(f"Samples directory not found: {SAMPLES_DIR}")

    sample_files = sorted(
        [
            path for path in SAMPLES_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx"}
        ]
    )

    if not sample_files:
        raise ValueError(f"No sample files found in: {SAMPLES_DIR}")

    all_predictions = []
    failed_files = []

    print(f"Found {len(sample_files)} sample files.")
    print(f"Sending requests to {API_URL}\n")

    for idx, sample_path in enumerate(sample_files, start=1):
        code = sample_path.read_text(encoding="utf-8")
        filename = sample_path.name
        language = detect_language_from_filename(filename)

        payload = {
            "code": code,
            "filename": filename,
            "language": language,
        }

        print(f"[{idx}/{len(sample_files)}] Reviewing {filename} ...")

        try:
            response = requests.post(API_URL, json=payload, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            response_json = response.json()

            flattened_issues = flatten_prediction_issues(response_json, filename)

            all_predictions.extend(flattened_issues)

            print(
                f"  Done -> {len(flattened_issues)} issues, "
                f"{response_json.get('processing_time_ms', 0)} ms"
            )

        except Exception as exc:
            print(f"  Failed -> {filename}: {exc}")
            failed_files.append(filename)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_predictions, f, indent=2)

    print("\nFinished.")
    print(f"Saved predictions to: {OUTPUT_FILE}")
    print(f"Total predicted issues: {len(all_predictions)}")

    if failed_files:
        print("\nFailed files:")
        for name in failed_files:
            print(f" - {name}")


if __name__ == "__main__":
    main()