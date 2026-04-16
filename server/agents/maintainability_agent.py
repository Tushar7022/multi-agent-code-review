import json
import logging
from anthropic import Anthropic
from agents.state import AgentState
from agents.prompts import MAINTAINABILITY_PROMPT
from models import Issue
from json_repair import repair_json

logger = logging.getLogger(__name__)


def maintainability_agent(state: AgentState) -> dict:
    code = state["code"]
    filename = state.get("filename") or "submitted_code"
    maintainability_findings = state.get("maintainability_findings", [])

    user_message = _build_user_message(code, filename, maintainability_findings)

    try:
        issues = _call_llm(user_message, filename)
    except Exception as e:
        logger.error(f"Maintainability agent LLM call failed: {e}")
        issues = []

    return {"maintainability_issues": issues}


def _build_user_message(code: str, filename: str, findings: list) -> str:
    if findings:
        findings_text = json.dumps(findings, indent=2)
    else:
        findings_text = "No static analysis findings available. Analyze the code directly."

    return f"""
FILENAME: {filename}

STATIC ANALYSIS FINDINGS (Ruff + ESLint style rules):
{findings_text}

SOURCE CODE:
{code}

Review the code and findings above. Return your findings as a JSON array.
"""


def _call_llm(user_message: str, filename: str) -> list[Issue]:
    client = Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=[{"type": "text", "text": MAINTAINABILITY_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    raw = response.content[0].text.strip()

# strip markdown fences more robustly
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

# extract first JSON array if there's extra text around it
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        logger.warning("Maintainability agent: no JSON array found in response")
        return []
    raw = raw[start:end+1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"Maintainability agent: JSON parse failed: {e} — attempting repair")
        try:
            parsed = json.loads(repair_json(raw))
            logger.info("Maintainability agent: JSON repaired successfully")
        except Exception:
            logger.warning("Maintainability agent: repair failed too")
            return []

    issues = []
    for item in parsed:
        try:
            issue = Issue(
                agent="maintainability",
                category="maintainability",
                issue_type=item.get("issue_type", "Unknown"),
                severity=item.get("severity", "low"),
                file=item.get("file", filename),
                line=max(1, int(item.get("line", 1))),
                evidence=item.get("evidence", ""),
                llm_reasoning=item.get("llm_reasoning", ""),
                suggested_fix=item.get("suggested_fix", ""),
                confidence=float(item.get("confidence", 0.5)),
                agent_agreement=item.get("agent_agreement", ["maintainability"]),
                cross_domain_notes=item.get("cross_domain_notes", None),
            )
            issues.append(issue)
        except Exception as e:
            logger.warning(f"Skipping malformed issue from maintainability agent: {e}")
            continue

    return issues