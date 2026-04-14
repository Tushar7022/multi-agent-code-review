import json
import time
import logging
from anthropic import Anthropic
from agents.state import AgentState
from agents.prompts import SYNTHESIZER_PROMPT
from models import Issue
from json_repair import repair_json

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
AGENT_ORDER = ["security", "performance", "maintainability"]


def synthesizer_agent(state: AgentState) -> dict:
    code = state["code"]
    filename = state.get("filename") or "submitted_code"

    all_issues = (
        state.get("security_issues", []) +
        state.get("performance_issues", []) +
        state.get("maintainability_issues", [])
    )

    user_message = _build_user_message(code, filename, all_issues)

    result = None
    for attempt in range(MAX_RETRIES):
        try:
            result = _call_llm(user_message, filename)
            break
        except Exception as e:
            logger.error(f"Synthesizer attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])

    if result is None:
        logger.warning("Synthesizer failed — falling back to raw agent outputs")
        return {
            "final_issues": sorted(all_issues, key=lambda i: SEVERITY_RANK[i.severity]),
            "summary": "Synthesis failed. Showing raw agent findings.",
            "fixed_code": code,
        }

    # reconstruct full issues from merged indices
    final_issues = _reconstruct_issues(
        result.get("merged_issues", []),
        all_issues,
        filename
    )

    # append new issues Sonnet found
    final_issues += result.get("new_issues", [])

    return {
        "final_issues": final_issues,
        "summary": result["summary"],
        "fixed_code": result["fixed_code"],
    }


def _build_user_message(code: str, filename: str, all_issues: list) -> str:
    # send stripped fields only — Sonnet doesn't need evidence/llm_reasoning to merge
    indexed = [
        {
            "index": i,
            "agent": issue.agent,
            "category": issue.category,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "file": issue.file,
            "line": issue.line,
            "suggested_fix": issue.suggested_fix,
        }
        for i, issue in enumerate(all_issues)
    ]

    return f"""
FILENAME: {filename}

AGENT ISSUES ({len(all_issues)} total):
{json.dumps(indexed, indent=2)}

ORIGINAL SOURCE CODE:
{code}

Perform synthesis following all 3 steps. Return JSON object.
"""


def _reconstruct_issues(merged_issues: list, all_issues: list, filename: str) -> list[Issue]:
    result = []

    for group in merged_issues:
        indices = group.get("indices", [])
        if not indices:
            continue

        # validate indices
        valid = [i for i in indices if 0 <= i < len(all_issues)]
        if not valid:
            continue

        # pick best representative — prefer security agent, then performance, then maintainability
        def agent_priority(idx):
            agent = all_issues[idx].agent
            return AGENT_ORDER.index(agent) if agent in AGENT_ORDER else 99

        best_idx = min(valid, key=agent_priority)
        base = all_issues[best_idx]

        # agent_agreement from which agents contributed
        agent_agreement = list({all_issues[i].agent for i in valid})

        # confidence based on how many agents agree
        n = len(agent_agreement)
        confidence = 1.0 if n == 3 else 0.67 if n == 2 else 0.33

        try:
            issue = Issue(
                agent="synthesizer",
                category=group.get("category", base.category),
                issue_type=group.get("issue_type", base.issue_type),
                severity=group.get("severity", base.severity),
                file=base.file,
                line=base.line,
                evidence=base.evidence,
                llm_reasoning=base.llm_reasoning,
                suggested_fix=base.suggested_fix,
                confidence=confidence,
                agent_agreement=agent_agreement,
                cross_domain_notes=group.get("cross_domain_notes", None),
            )
            result.append(issue)
        except Exception as e:
            logger.warning(f"Skipping malformed merged issue: {e}")

    # sort by severity
    return sorted(result, key=lambda i: SEVERITY_RANK[i.severity])


def _parse_new_issues(items: list, filename: str) -> list[Issue]:
    issues = []
    for item in items:
        try:
            issue = Issue(
                agent="synthesizer",
                category=item.get("category", "security"),
                issue_type=item.get("issue_type", "Unknown"),
                severity=item.get("severity", "low"),
                file=item.get("file", filename),
                line=max(1, int(item.get("line", 1))),
                evidence=item.get("evidence", ""),
                llm_reasoning=item.get("llm_reasoning", ""),
                suggested_fix=item.get("suggested_fix", ""),
                confidence=0.4,
                agent_agreement=["synthesizer"],
                cross_domain_notes=None,
            )
            issues.append(issue)
        except Exception as e:
            logger.warning(f"Skipping malformed new issue from synthesizer: {e}")
    return issues


def _call_llm(user_message: str, filename: str) -> dict:
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=[{"type": "text", "text": SYNTHESIZER_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        logger.warning("Synthesizer: no JSON object found in response")
        return None

    raw = raw[start:end+1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"Synthesizer: JSON parse failed: {e} — attempting repair")
        try:
            parsed = json.loads(repair_json(raw))
            logger.info("Synthesizer: JSON repaired successfully")
        except Exception:
            logger.warning("Synthesizer: repair failed too")
            return None

    return {
        "merged_issues": parsed.get("merged_issues", []),
        "new_issues": _parse_new_issues(parsed.get("new_issues", []), filename),
        "summary": parsed.get("summary", ""),
        "fixed_code": parsed.get("fixed_code", "")
    }