import json
import time
import logging
from anthropic import Anthropic
from agents.state import AgentState
from agents.prompts import SYNTHESIZER_PROMPT
from models import Issue

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # exponential backoff in seconds


def synthesizer_agent(state: AgentState) -> AgentState:
    code = state["code"]
    filename = state.get("filename") or "submitted_code"

    # collect all agent outputs
    security_issues     = state.get("security_issues", [])
    performance_issues  = state.get("performance_issues", [])
    maintainability_issues = state.get("maintainability_issues", [])

    user_message = _build_user_message(
        code,
        filename,
        security_issues,
        performance_issues,
        maintainability_issues
    )

    # retry logic — synthesizer is most critical, worth retrying
    result = None
    for attempt in range(MAX_RETRIES):
        try:
            result = _call_llm(user_message, filename)
            break
        except Exception as e:
            logger.error(f"Synthesizer attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            else:
                logger.error("All synthesizer retries exhausted")

    # if all retries failed — fall back to raw agent outputs merged together
    if result is None:
        logger.warning("Synthesizer failed — falling back to raw agent outputs")
        fallback_issues = security_issues + performance_issues + maintainability_issues
        return {
            "final_issues": fallback_issues,
            "summary": "Synthesis failed. Showing raw agent findings.",
            "fixed_code": code,
        }

    return {
        "final_issues": result["issues"],
        "summary": result["summary"],
        "fixed_code": result["fixed_code"],
    }


def _build_user_message(
    code: str,
    filename: str,
    security_issues: list,
    performance_issues: list,
    maintainability_issues: list
) -> str:

    def issues_to_text(issues: list) -> str:
        if not issues:
            return "No issues found by this agent."
        # convert Issue objects to dicts for JSON serialization
        dicts = []
        for issue in issues:
            if hasattr(issue, "model_dump"):
                dicts.append(issue.model_dump())
            else:
                dicts.append(issue)
        return json.dumps(dicts, indent=2)

    return f"""
FILENAME: {filename}

SECURITY AGENT FINDINGS:
{issues_to_text(security_issues)}

PERFORMANCE AGENT FINDINGS:
{issues_to_text(performance_issues)}

MAINTAINABILITY AGENT FINDINGS:
{issues_to_text(maintainability_issues)}

ORIGINAL SOURCE CODE:
{code}

Perform cross-agent synthesis following all 8 steps. Return your response as a JSON object.
"""


def _call_llm(user_message: str, filename: str) -> dict:
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=[{"type": "text", "text": SYNTHESIZER_PROMPT, "cache_control": {"type": "ephemeral"}}],
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

    # extract JSON object even if there's extra text around it
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        logger.warning("Synthesizer: no JSON object found in response")
        return None

    raw = raw[start:end+1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"Synthesizer: JSON parse failed: {e}")
        return None

    # convert issue dicts to Issue objects
    issues = []
    for item in parsed.get("issues", []):
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
                confidence=float(item.get("confidence", 0.5)),
                agent_agreement=item.get("agent_agreement", ["synthesizer"]),
                cross_domain_notes=item.get("cross_domain_notes", None),
            )
            issues.append(issue)
        except Exception as e:
            logger.warning(f"Skipping malformed issue from synthesizer: {e}")
            continue

    return {
        "issues":     issues,
        "summary":    parsed.get("summary", ""),
        "fixed_code": parsed.get("fixed_code", "")
    }