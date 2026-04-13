from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

# --- Type aliases for strict allowed values ---
# Using Literal means if someone passes "Security" or "HIGH" it will fail validation immediately
AgentType = Literal["security", "performance", "maintainability", "synthesizer"]
SeverityLevel = Literal["critical", "high", "medium", "low"]
Language = Literal["python", "javascript"]
Category = Literal["security", "performance", "maintainability"]


# What the frontend sends us when user clicks "Review"
class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=1)        # min_length=1 rejects empty submissions
    filename: Optional[str] = None
    language: Optional[Language] = None         # if None, language_detector.py figures it out


# One single issue found by an agent — atomic unit of the whole system
class Issue(BaseModel):
    agent: AgentType
    category: Category                          # used by synthesizer to deduplicate across agents
    issue_type: str
    severity: SeverityLevel
    file: str
    line: int = Field(..., ge=1)                # ge=1 means line numbers start at 1, never 0 or negative
    evidence: str                               # raw static tool output that flagged this
    llm_reasoning: str                          # why the LLM thinks this is actually a problem
    suggested_fix: str
    confidence: float = Field(..., ge=0.0, le=1.0)   # 0.0-1.0 based on agent agreement
    agent_agreement: List[AgentType]            # which agents flagged this issue
    cross_domain_notes: Optional[str] = None    # synthesizer insight linking multiple domains


# What we send back to the frontend after the full pipeline runs
class ReviewResponse(BaseModel):
    session_id: UUID
    language: Language
    issues: List[Issue]
    total_issues: int                           # frontend uses this for "Found X issues" header
    summary: str                                # synthesizer written summary paragraph
    fixed_code: str                             # full corrected code with all fixes applied
    processing_time_ms: int = Field(..., ge=0)