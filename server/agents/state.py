from typing import TypedDict, List, Optional, Annotated
from models import Issue, Language
import operator


class AgentState(TypedDict):
    # --- INPUT ---
    code: str
    language: Language
    filename: Optional[str]

    # --- STATIC TOOL OUTPUTS ---
    tool_outputs: dict
    security_findings: List[dict]
    performance_findings: List[dict]
    maintainability_findings: List[dict]

    # --- AGENT OUTPUTS ---
    # Annotated with operator.add because parallel agents write to these simultaneously
    security_issues: Annotated[List[Issue], operator.add]
    performance_issues: Annotated[List[Issue], operator.add]
    maintainability_issues: Annotated[List[Issue], operator.add]

    # --- SYNTHESIZER OUTPUT ---
    final_issues: List[Issue]
    summary: str
    fixed_code: str