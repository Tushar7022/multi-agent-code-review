import logging
from typing import Any

logger = logging.getLogger(__name__)

NormalizedFinding = dict

def normalize(tool_outputs: dict, filename: str | None = None) -> dict:
    display_name = filename or "submitted_code"

    security        = []
    performance     = []
    maintainability = []

    for finding in tool_outputs.get("semgrep", []):
        normalized = _normalize_semgrep(finding, display_name)
        if normalized:
            if _is_security_rule(normalized["rule_id"]):
                security.append(normalized)
            else:
                maintainability.append(normalized)

    for finding in tool_outputs.get("bandit", []):
        normalized = _normalize_bandit(finding, display_name)
        if normalized:
            security.append(normalized)

    for finding in tool_outputs.get("ruff", []):
        normalized = _normalize_ruff(finding, display_name)
        if normalized:
            maintainability.append(normalized)

    for finding in tool_outputs.get("eslint", []):
        normalized = _normalize_eslint(finding, display_name)
        if normalized:
            if _is_performance_rule(normalized["rule_id"]):
                performance.append(normalized)
            else:
                maintainability.append(normalized)

    return {
        "security_findings":        security,
        "performance_findings":     performance,
        "maintainability_findings": maintainability,
    }


def _normalize_semgrep(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        return {
            "tool":     "semgrep",
            "rule_id":  finding.get("check_id", "unknown"),
            "message":  finding.get("extra", {}).get("message", ""),
            "file":     filename,
            "line":     finding.get("start", {}).get("line", 1),
            "severity": _normalize_severity(finding.get("extra", {}).get("severity", "INFO")),
        }
    except Exception as e:
        logger.warning(f"Failed to normalize semgrep finding: {e}")
        return None


def _normalize_bandit(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        return {
            "tool":     "bandit",
            "rule_id":  finding.get("test_id", "unknown"),
            "message":  finding.get("issue_text", ""),
            "file":     filename,
            "line":     finding.get("line_number", 1),
            "severity": _normalize_severity(finding.get("issue_severity", "LOW")),
        }
    except Exception as e:
        logger.warning(f"Failed to normalize bandit finding: {e}")
        return None


def _normalize_ruff(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        return {
            "tool":     "ruff",
            "rule_id":  finding.get("code", "unknown"),
            "message":  finding.get("message", ""),
            "file":     filename,
            "line":     finding.get("location", {}).get("row", 1),
            "severity": "low",
        }
    except Exception as e:
        logger.warning(f"Failed to normalize ruff finding: {e}")
        return None


def _normalize_eslint(finding: dict, filename: str) -> NormalizedFinding | None:
    try:
        return {
            "tool":     "eslint",
            "rule_id":  finding.get("ruleId", "unknown"),
            "message":  finding.get("message", ""),
            "file":     filename,
            "line":     finding.get("line", 1),
            "severity": _normalize_severity(str(finding.get("severity", 1))),
        }
    except Exception as e:
        logger.warning(f"Failed to normalize eslint finding: {e}")
        return None


def _normalize_severity(raw: str) -> str:
    mapping = {
        "error":    "high",
        "warning":  "medium",
        "info":     "low",
        "high":     "high",
        "medium":   "medium",
        "low":      "low",
        "critical": "critical",
        "2":        "high",
        "1":        "medium",
    }
    return mapping.get(raw.lower(), "low")


def _is_security_rule(rule_id: str) -> bool:
    security_prefixes = [
        "python.security",
        "javascript.security",
        "generic.secrets",
        "injection",
        "xss",
        "sqli",
    ]
    return any(prefix in rule_id.lower() for prefix in security_prefixes)


def _is_performance_rule(rule_id: str) -> bool:
    performance_rules = [
        "no-loop-func",
        "no-await-in-loop",
        "prefer-const",
        "no-var",
    ]
    return any(rule in rule_id.lower() for rule in performance_rules)