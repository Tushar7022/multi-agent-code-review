import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_FILE = EVAL_DIR / "ground_truth.json"
PREDICTIONS_FILE = EVAL_DIR / "predictions.json"

LINE_TOLERANCE = 3  # predicted line can be within ±3 of ground truth line


def normalize_issue_type(issue_type: str) -> str:
    """Normalize issue names so loose matching is more reliable."""
    s = issue_type.lower().strip()

    noise_phrases = [
        "cwe-",
        "(cwe-",
        "(",
        ")",
        "via ",
        "potential ",
        "missing ",
        "unsafe ",
        "insecure ",
        "possible ",
        "direct ",
        "reflected ",
        "stored ",
        "directory ",
    ]

    for phrase in noise_phrases:
        s = s.replace(phrase, "")

    synonym_map = {
        # security
        "xss": "cross site scripting",
        "cross-site scripting": "cross site scripting",
        "sql injection": "sql injection",
        "command injection": "os command injection",
        "os command injection": "os command injection",
        "path traversal": "path traversal",
        "directory traversal": "path traversal",
        "ldap injection": "ldap injection",
        "server-side request forgery": "server side request forgery",
        "ssrf": "server side request forgery",
        "unsafe deserialization": "deserialization",
        "pickle deserialization": "deserialization",
        "xml external entity": "xxe",
        "xxe": "xxe",
        # performance
        "await inside loop": "await loop",
        "await in loop": "await loop",
        "no-await-in-loop": "await loop",
        "sequential network requests in loop": "await loop",
        "sequential requests in loop": "await loop",
        "o(n²) nested loop": "nested loop",
        "o(n^2) nested loop": "nested loop",
        "nested loop with linear array search": "nested loop",
        "inefficient string concatenation in loop": "string concatenation loop",
        "string concatenation in loop": "string concatenation loop",
        "redundant repeated sorting": "repeated sorting",
        "unnecessary repeated sorting": "repeated sorting",
        "repeated sorting operations": "repeated sorting",
        "repeated full-array scan in loop": "full array scan loop",
        "repeated filtering": "full array scan loop",
        "scan in loop": "full array scan loop",
        # open redirect variants
        "open redirect via insufficient url validation": "open redirect",
        "open redirect via": "open redirect",
        "url redirection": "open redirect",
        # xxe / input validation
        "xml external entity injection": "improper input validation",
        "xxe injection": "improper input validation",
        "xml external entity": "improper input validation",
        # path traversal variants
        "path traversal cwe-022": "path traversal",
        "path traversal / directory traversal": "path traversal",
        "path traversal via unsanitized filename": "path traversal",
        # ssrf variants
        "server-side request forgery ssrf": "server side request forgery",
        "ssrf / path traversal via unvalidated url input": "server side request forgery",
        # command injection variants
        "command injection cwe-78": "os command injection",
        "os command injection cwe-78": "os command injection",
        # yaml deserialization
        "unsafe yaml deserialization": "improper input validation",
        "yaml deserialization": "improper input validation",
        # ldap
        "ldap injection via search filter": "ldap injection",
        "ldap injection via distinguished name": "ldap injection",
    }

    for old, new in synonym_map.items():
        s = s.replace(old, new)

    s = " ".join(s.split())
    return s


def issue_type_matches(pred_issue: str, gt_issue: str) -> bool:
    """Loose but safer issue-type matching."""
    pred_norm = normalize_issue_type(pred_issue)
    gt_norm = normalize_issue_type(gt_issue)

    if pred_norm == gt_norm:
        return True

    if pred_norm in gt_norm or gt_norm in pred_norm:
        return True

    pred_words = set(pred_norm.split())
    gt_words = set(gt_norm.split())
    overlap = {w for w in (pred_words & gt_words) if len(w) > 2}

    # Need at least 2 overlapping meaningful words for a fuzzy match
    return len(overlap) >= 2


def is_match(pred: dict, gt: dict) -> bool:
    """True if prediction matches a ground-truth entry."""
    if pred["file"] != gt["file"]:
        return False

    if pred["category"] != gt["category"]:
        return False

    if abs(int(pred["line"]) - int(gt["line"])) > LINE_TOLERANCE:
        return False

    if not issue_type_matches(pred["issue_type"], gt["issue_type"]):
        return False

    return True


def severity_matches(pred: dict, gt: dict) -> bool:
    return pred.get("severity", "").lower() == gt.get("severity", "").lower()


def compute_matches(ground_truth: list, predictions: list):
    """
    Returns:
        tp_list: list of (pred, gt) matched pairs
        fp_list: list of unmatched predictions
        fn_list: list of unmatched ground-truth entries
    """
    unmatched_gt_indices = list(range(len(ground_truth)))
    fp_list = []
    tp_list = []

    for pred in predictions:
        matched = False

        for gt_index in unmatched_gt_indices[:]:
            gt = ground_truth[gt_index]
            if is_match(pred, gt):
                tp_list.append((pred, gt))
                unmatched_gt_indices.remove(gt_index)
                matched = True
                break

        if not matched:
            fp_list.append(pred)

    fn_list = [ground_truth[i] for i in unmatched_gt_indices]
    return tp_list, fp_list, fn_list


def compute_duplicate_rate(predictions: list) -> float:
    """Approximate duplicate rate among predictions."""
    seen = set()
    dupes = 0

    for p in predictions:
        key = (
            p["file"],
            p["category"],
            int(p["line"]),
            normalize_issue_type(p["issue_type"]),
        )
        if key in seen:
            dupes += 1
        seen.add(key)

    return dupes / len(predictions) if predictions else 0.0


def compute_category_metrics(ground_truth: list, predictions: list, category: str) -> dict:
    gt_cat = [g for g in ground_truth if g["category"] == category]
    pred_cat = [p for p in predictions if p["category"] == category]

    tp_list, fp_list, fn_list = compute_matches(gt_cat, pred_cat)

    tp = len(tp_list)
    fp = len(fp_list)
    fn = len(fn_list)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    sev_correct = sum(1 for pred, gt in tp_list if severity_matches(pred, gt))
    sev_acc = sev_correct / tp if tp > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "severity_accuracy": sev_acc,
    }


def compute_average_processing_time(predictions: list) -> float:
    """Average processing time per file, not per predicted issue."""
    file_times = {}

    for pred in predictions:
        file_name = pred["file"]
        file_times[file_name] = pred.get("processing_time_ms", 0)

    return sum(file_times.values()) / len(file_times) if file_times else 0.0


def main():
    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
        predictions = json.load(f)
    
    predictions = [p for p in predictions if p["category"] != "maintainability"]
    categories = ["security", "performance"]
    results = {}

    for cat in categories:
        results[cat] = compute_category_metrics(ground_truth, predictions, cat)

    tp_all, fp_all, fn_all = compute_matches(ground_truth, predictions)

    tp = len(tp_all)
    fp = len(fp_all)
    fn = len(fn_all)

    overall_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    overall_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    overall_f1 = (
        2 * overall_precision * overall_recall / (overall_precision + overall_recall)
        if (overall_precision + overall_recall) > 0
        else 0.0
    )

    sev_correct = sum(1 for pred, gt in tp_all if severity_matches(pred, gt))
    overall_severity_accuracy = sev_correct / tp if tp > 0 else 0.0

    duplicate_rate = compute_duplicate_rate(predictions)
    avg_time_ms = compute_average_processing_time(predictions)

    print()
    print("=" * 58)
    print("        MULTI-AGENT CODE REVIEW — EVALUATION")
    print("=" * 58)
    print(f"Ground truth issues : {len(ground_truth)}")
    print(f"Total predictions   : {len(predictions)}")
    print()

    for cat in categories:
        r = results[cat]
        print(f"{cat.upper()}")
        print(f"  TP={r['tp']}  FP={r['fp']}  FN={r['fn']}")
        print(f"  Precision         : {r['precision']:.2f}")
        print(f"  Recall            : {r['recall']:.2f}")
        print(f"  F1                : {r['f1']:.2f}")
        print(f"  Severity Accuracy : {r['severity_accuracy']:.2f}")
        print()

    print("OVERALL")
    print(f"  TP={tp}  FP={fp}  FN={fn}")
    print(f"  Precision         : {overall_precision:.2f}")
    print(f"  Recall            : {overall_recall:.2f}")
    print(f"  F1                : {overall_f1:.2f}")
    print(f"  Severity Accuracy : {overall_severity_accuracy:.2f}")
    print(f"  Duplicate Rate    : {duplicate_rate:.2%}")
    print(f"  Avg Process Time  : {avg_time_ms / 1000:.1f}s")
    print("=" * 58)
    print()


if __name__ == "__main__":
    main()