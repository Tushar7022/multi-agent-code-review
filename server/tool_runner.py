import subprocess
import tempfile
import json
import os
import logging
from models import Language
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

def run_tools(code: str, language: Language, filename: str | None = None) -> dict:
    suffix = ".py" if language == "python" else ".js"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        results = {"semgrep": [], "bandit": [], "ruff": [], "eslint": []}

        if language == "python":
            tasks = {
                "semgrep": lambda: _run_semgrep(tmp_path),
                "bandit":  lambda: _run_bandit(tmp_path),
                "ruff":    lambda: _run_ruff(tmp_path),
            }
        else:
            tasks = {
                "semgrep": lambda: _run_semgrep(tmp_path),
                "eslint":  lambda: _run_eslint(tmp_path),
            }

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(fn): name for name, fn in tasks.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.warning(f"{name} failed in thread: {e}")

        return results

    finally:
        os.unlink(tmp_path)


def _run_semgrep(path: str, language: str = "python") -> list:
    try:
        config = "p/python" if language == "python" else "p/javascript"
        result = subprocess.run(
            ["semgrep", "--json", f"--config={config}", 
             "--no-git-ignore",    # don't skip files based on .gitignore
             "--quiet",            # suppress progress output from stderr
             path],
            capture_output=True, text=True, timeout=60   # increased to 60s
        )
        if not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        return data.get("results", [])
    except subprocess.TimeoutExpired:
        logger.warning("Semgrep timed out — skipping")
        return []
    except json.JSONDecodeError:
        logger.warning("Semgrep returned invalid JSON")
        return []
    except Exception as e:
        logger.warning(f"Semgrep failed: {e}")
        return []


def _run_bandit(path: str) -> list:
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", path],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        return data.get("results", [])
    except Exception as e:
        logger.warning(f"Bandit failed: {e}")
        return []


def _run_ruff(path: str) -> list:
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", path],
            capture_output=True, text=True, timeout=30
        )
        # ruff returns empty output if no issues — handle that
        if not result.stdout.strip():
            return []
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Ruff failed: {e}")
        return []


def _run_eslint(path: str) -> list:
    try:
        rules = json.dumps({
            "no-var": "error",
            "no-unused-vars": "error",
            "no-eval": "error",
            "no-implied-eval": "error",
            "no-new-func": "error",
            "no-await-in-loop": "error",
            "no-loop-func": "error",
            "no-constant-condition": "error",
            "no-unreachable": "error",
            "no-duplicate-case": "error",
            "no-empty": "error",
            "eqeqeq": "error",
            "curly": "error",
            "no-throw-literal": "error",
            "prefer-const": "error",
            "no-console": "warn",
            "handle-callback-err": "error",
            "no-process-exit": "warn",
            "complexity": ["warn", 10],
            "max-depth": ["warn", 4],
            "max-params": ["warn", 5],
        })

        result = subprocess.run(
            [
                "eslint",
                "--format=json",
                "--no-eslintrc",
                "--rule", rules,
                "--env", "node",
                "--env", "es2021",
                "--parser-options", "ecmaVersion:2021",
                path
            ],
            capture_output=True, text=True, timeout=30
        )

        if not result.stdout.strip():
            return []

        data = json.loads(result.stdout)
        messages = []
        for file_result in data:
            messages.extend(file_result.get("messages", []))
        return messages

    except Exception as e:
        logger.warning(f"ESLint failed: {e}")
        return []