from pathlib import Path
import json
import re

from datasets import load_dataset

# ---------- CONFIG ----------
OUTPUT_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = OUTPUT_DIR / "samples"
GROUND_TRUTH_FILE = OUTPUT_DIR / "ground_truth.json"
NUM_SAMPLES = 20

SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# ---------- HELPERS ----------
def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
    return name.strip("_") or "sample"

def guess_issue_type_from_id(sample_id: str) -> str:
    sid = sample_id.upper()

    cwe_map = {
        "CWE-20": "Improper Input Validation",
        "CWE-22": "Path Traversal",
        "CWE-78": "OS Command Injection",
        "CWE-79": "Cross-Site Scripting",
        "CWE-89": "SQL Injection",
        "CWE-94": "Code Injection",
        "CWE-113": "HTTP Header Injection",
        "CWE-117": "Log Injection",
        "CWE-190": "Integer Overflow",
        "CWE-209": "Information Exposure Through Error Message",
        "CWE-295": "Improper Certificate Validation",
        "CWE-327": "Use of Broken or Risky Cryptographic Algorithm",
        "CWE-330": "Use of Insufficiently Random Values",
        "CWE-352": "Cross-Site Request Forgery",
        "CWE-377": "Insecure Temporary File",
        "CWE-434": "Unrestricted File Upload",
        "CWE-502": "Unsafe Deserialization",
        "CWE-601": "Open Redirect",
        "CWE-611": "XML External Entity Injection",
        "CWE-732": "Incorrect Permission Assignment",
        "CWE-798": "Hardcoded Credentials",
        "CWE-918": "Server-Side Request Forgery",
    }

    for cwe, issue in cwe_map.items():
        if cwe in sid:
            return issue

    return "Security Vulnerability"

def guess_severity(issue_type: str) -> str:
    critical = {
        "SQL Injection",
        "OS Command Injection",
        "Code Injection",
        "Unsafe Deserialization",
        "Server-Side Request Forgery",
    }
    high = {
        "HTTP Header Injection",
        "Path Traversal",
        "Cross-Site Scripting",
        "XML External Entity Injection",
        "Hardcoded Credentials",
        "Unrestricted File Upload",
    }

    if issue_type in critical:
        return "critical"
    if issue_type in high:
        return "high"
    return "medium"

def guess_line_number(code: str, issue_type: str) -> int:
    patterns = {
        "SQL Injection": [r"execute\s*\(", r"SELECT .* \+"],
        "OS Command Injection": [r"os\.system\s*\(", r"subprocess\."],
        "Unsafe Deserialization": [r"yaml\.load\s*\(", r"pickle\.loads?\s*\("],
        "HTTP Header Injection": [r"headers\.add\s*\(", r"set_header\s*\("],
        "Path Traversal": [r"open\s*\(", r"send_file\s*\(", r"join\s*\("],
        "Cross-Site Scripting": [r"render", r"response\.write", r"mark_safe"],
        "Code Injection": [r"eval\s*\(", r"exec\s*\("],
        "Hardcoded Credentials": [r"password\s*=", r"secret\s*=", r"api_key\s*="],
        "Server-Side Request Forgery": [r"requests\.(get|post)\s*\(", r"urlopen\s*\("],
    }

    lines = code.splitlines()
    issue_patterns = patterns.get(issue_type, [])

    for idx, line in enumerate(lines, start=1):
        for pattern in issue_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return idx

    # fallback: first non-empty line
    for idx, line in enumerate(lines, start=1):
        if line.strip():
            return idx

    return 1

# ---------- LOAD DATASET ----------
print("Loading SecurityEval dataset...")
dataset = load_dataset("s2e-lab/SecurityEval", split="train")

ground_truth = []
saved = 0

for row in dataset:
    if saved >= NUM_SAMPLES:
        break

    sample_id = str(row.get("ID", f"sample_{saved+1}"))
    code = row.get("Insecure_code", "")

    if not code or not code.strip():
        continue

    file_name = f"{saved+1:03d}_{sanitize_filename(sample_id)}.py"
    file_path = SAMPLES_DIR / file_name

    file_path.write_text(code, encoding="utf-8")

    issue_type = guess_issue_type_from_id(sample_id)
    severity = guess_severity(issue_type)
    line = guess_line_number(code, issue_type)

    ground_truth.append(
        {
            "file": file_name,
            "issues": [
                {
                    "category": "security",
                    "issue_type": issue_type,
                    "severity": severity,
                    "line": line,
                }
            ],
            "source": "SecurityEval",
            "source_id": sample_id,
        }
    )

    saved += 1
    print(f"Saved {file_name}")

with GROUND_TRUTH_FILE.open("w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2)

print(f"\nDone. Saved {saved} Python samples to: {SAMPLES_DIR}")
print(f"Ground truth saved to: {GROUND_TRUTH_FILE}")