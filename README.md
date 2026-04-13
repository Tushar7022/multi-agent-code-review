# Multi-Agent AI System for Automated Code Review
## Technical Specification — for developers and AI coding assistants

---

## What This Project Is

A backend system that performs automated code review on Python and JavaScript code using a multi-agent pipeline. Three LLM agents (Security, Performance, Maintainability) run in parallel via LangGraph. Each agent is grounded by static analysis tool output and reasons using ReAct-style prompting. A Synthesizer agent merges all outputs into a final prioritized report and generates fixed code. FastAPI serves as the HTTP layer. React + Vite is the frontend.

---

## Tech Stack

- **FastAPI** — HTTP server, receives code, runs static tools, calls LangGraph pipeline
- **LangGraph** — orchestrates 3 parallel agents + synthesizer, manages shared state
- **Claude Haiku API (Anthropic)** — LLM for the 3 specialist agents (Security, Performance, Maintainability)
- **Claude Sonnet API (Anthropic)** — LLM for the Synthesizer agent (higher capacity for merging + code generation)
- **Semgrep** — static analysis, security patterns, Python + JS
- **Bandit** — static analysis, security vulnerabilities, Python only
- **Ruff** — static analysis, lint + style, Python only
- **ESLint** — static analysis, lint + style, JS only
- **React + Vite** — frontend, code input + results display

---

## Complete File Structure

```
multi-agent-code-review/
│
├── server/
│   ├── main.py
│   ├── models.py
│   ├── language_detector.py
│   ├── tool_runner.py
│   ├── output_normalizer.py
│   │
│   └── agents/
│       ├── state.py
│       ├── graph.py
│       ├── prompts.py
│       ├── security_agent.py
│       ├── performance_agent.py
│       ├── maintainability_agent.py
│       └── synthesizer_agent.py
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── CodeInput.jsx
│       ├── ReviewResults.jsx
│       ├── IssueCard.jsx
│       ├── SeverityBadge.jsx
│       ├── LoadingSpinner.jsx
│       └── api.js
│
├── evaluation/
│   ├── ground_truth.json
│   ├── run_baselines.py
│   ├── compute_metrics.py
│   └── duplicate_checker.py
│
├── .env
├── requirements.txt
└── README.md
```

---

## Request/Response Flow

```
POST /review { code, filename }
        ↓
language_detector.py         → returns "python" or "javascript"
tool_runner.py               → runs relevant static tools via subprocess
output_normalizer.py         → normalizes all tool outputs to common Issue schema
        ↓
LangGraph graph.py kicks off
        ↓
security_agent.py     ─┐
performance_agent.py  ─┼─ all run in parallel, each makes one LLM call
maintainability_agent ─┘
        ↓
synthesizer_agent.py         → merges, deduplicates, ranks, generates fixed code (Claude Sonnet)
        ↓
FastAPI returns JSON response
```

---

## File-by-File Spec

### `server/main.py`
- FastAPI app with CORS enabled for localhost:5173 (Vite dev server)
- Single route: `POST /review`
- Accepts `ReviewRequest`, returns `ReviewResponse`
- Calls language_detector → tool_runner → output_normalizer → graph.invoke()
- Returns final issues list + session_id + fixed_code + processing_time_ms

### `server/models.py`
Pydantic models:

```python
class ReviewRequest(BaseModel):
    code: str
    filename: Optional[str] = None

class Issue(BaseModel):
    agent: str              # "security" | "performance" | "maintainability"
    issue_type: str         # short name e.g. "SQL Injection"
    severity: str           # "critical" | "high" | "medium" | "low"
    file: str
    line: int
    evidence: str           # raw static tool output that flagged this
    llm_reasoning: str      # LLM's explanation
    suggested_fix: str

class ReviewResponse(BaseModel):
    session_id: str
    language: str
    issues: List[Issue]
    total_issues: int
    summary: str
    fixed_code: str         # synthesizer-generated corrected version of the input code
    processing_time_ms: int
```

### `server/language_detector.py`
- Input: code string + optional filename
- If filename ends in .py → python
- If filename ends in .js/.ts/.jsx/.tsx → javascript
- If no filename: scan for Python keywords (def, import, print()) vs JS keywords (const, let, function, =>)
- Returns: "python" or "javascript"

### `server/tool_runner.py`
- Input: code string, language string
- Writes code to a temp file using tempfile.NamedTemporaryFile
- Runs tools via subprocess.run() with timeout=30
- For Python: runs Semgrep + Bandit + Ruff
- For JavaScript: runs Semgrep + ESLint
- Each tool called with JSON output flag
- Returns dict: { "semgrep": [...], "bandit": [...], "ruff": [...], "eslint": [...] }
- If a tool fails or times out: logs warning, returns empty list for that tool (graceful degradation)

Tool commands:
```
semgrep --json --config=p/python --no-git-ignore --quiet <file>
bandit -f json -q <file>
ruff check --output-format=json <file>
eslint --format=json --no-eslintrc --rule {...} --env node <file>
```

### `server/output_normalizer.py`
- Input: raw dict from tool_runner
- Normalizes each tool's output into a common format:
```python
{
    "tool": "semgrep",
    "rule_id": "...",
    "message": "...",
    "file": "...",
    "line": 12,
    "severity": "high"
}
```
- Returns: dict with keys "security_findings", "performance_findings", "maintainability_findings"
- Semgrep + Bandit → security_findings
- ESLint performance rules (no-await-in-loop, no-loop-func) → performance_findings
- Ruff + ESLint style rules → maintainability_findings
- Severity mapping: error→high, warning→medium, info→low

### `server/agents/state.py`
LangGraph state schema shared across all nodes:
```python
from typing import TypedDict, List, Optional, Annotated
import operator

class AgentState(TypedDict):
    code: str
    language: str
    filename: Optional[str]
    tool_outputs: dict                              # normalized outputs from output_normalizer
    security_issues: Annotated[List[Issue], operator.add]
    performance_issues: Annotated[List[Issue], operator.add]
    maintainability_issues: Annotated[List[Issue], operator.add]
    final_issues: List[Issue]                       # output of synthesizer
    summary: str                                    # synthesizer summary text
    fixed_code: str                                 # synthesizer-generated corrected code
```

### `server/agents/graph.py`
- Defines the LangGraph StateGraph
- Nodes: security_agent, performance_agent, maintainability_agent, synthesizer_agent
- security + performance + maintainability run as parallel nodes (fan-out)
- synthesizer runs after all three complete (fan-in)
- Entry point: START → [security, performance, maintainability] in parallel → synthesizer → END
- Compiled graph exposed as `review_graph = graph.compile()`
- main.py calls: `result = review_graph.invoke(initial_state)`

### `server/agents/prompts.py`
Contains system prompts for all agents as string constants:

- `SECURITY_PROMPT` — "You are a security-focused code reviewer. You are given Semgrep and Bandit output and the source code. Reason about each finding step by step. Verify true/false positives. Find false negatives Semgrep/Bandit missed. Return ONLY a JSON array of issues with fields: issue_type, severity, file, line, evidence, llm_reasoning, suggested_fix."
- `PERFORMANCE_PROMPT` — same structure, focused on scalability, slow algorithms, inefficient patterns
- `MAINTAINABILITY_PROMPT` — same structure, focused on readability, structure, complexity, naming
- `SYNTHESIZER_PROMPT` — "You are given findings from three code review agents. Merge into a single prioritized list. Remove exact duplicates (same file+line+category). When severity conflicts, keep highest. Assign confidence scores. Identify cross-domain linkages. Generate fixed_code applying all suggested fixes. Return a JSON object with: issues (array), summary (string), fixed_code (string)."

### `server/agents/security_agent.py`
- LangGraph node function: `def security_agent(state: AgentState) -> AgentState`
- Pulls `state["code"]` and `state["tool_outputs"]["security_findings"]`
- Builds user message: security findings as formatted string + full source code
- Calls Claude Haiku API with SECURITY_PROMPT as system prompt
- Uses `cache_control: {"type": "ephemeral"}` for prompt caching
- Parses JSON from response (handles markdown code fences)
- If static tools returned empty: prompt says "no tool output available, analyze directly"
- Updates and returns state with `security_issues` populated

### `server/agents/performance_agent.py`
- Same structure as security_agent
- Uses `state["tool_outputs"]["performance_findings"]`
- Uses PERFORMANCE_PROMPT
- Updates `performance_issues` in state

### `server/agents/maintainability_agent.py`
- Same structure as security_agent
- Uses `state["tool_outputs"]["maintainability_findings"]`
- Uses MAINTAINABILITY_PROMPT
- Updates `maintainability_issues` in state

### `server/agents/synthesizer_agent.py`
- LangGraph node function: `def synthesizer_agent(state: AgentState) -> AgentState`
- Pulls security_issues + performance_issues + maintainability_issues from state
- Calls Claude Sonnet API with SYNTHESIZER_PROMPT (max_tokens=8096)
- Retry logic: up to 3 attempts with exponential backoff (2s, 4s, 8s) on API failure
- Fallback: if all retries fail, returns raw agent outputs merged without deduplication
- Steps performed:
  1. Deduplication: remove issues where file + line + category are identical
  2. Severity conflict resolution: if duplicate found with different severity, keep highest
  3. Confidence scoring: 1.0 if all 3 agents agree, 0.5 for solo agent finding
  4. Cross-domain linking: identifies when one domain issue causes another
  5. Code fixing: generates corrected version of the input code with all fixes applied
- Updates state with `final_issues`, `summary`, and `fixed_code`

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=your_key_here
```

---

## Python Dependencies (requirements.txt)

```
fastapi
uvicorn
pydantic
python-dotenv
anthropic
langgraph
semgrep
bandit
ruff
```

---

## Frontend Overview (React + Vite)

Simple 2-screen UI:
1. `CodeInput.jsx` — textarea for code, language selector, submit button
2. `ReviewResults.jsx` — renders list of IssueCard components grouped by severity

`api.js` — single POST call to `http://localhost:8000/review`

`IssueCard.jsx` — shows: agent badge, severity badge, issue_type, file:line, evidence, llm_reasoning, suggested_fix

`SeverityBadge.jsx` — colored badge: Critical=red, High=orange, Medium=yellow, Low=gray

---

## Evaluation

### Baselines
- B1: Static tools only, no LLM (tool_runner + output_normalizer output directly)
- B2: Single LLM agent, no tools (just code → LLM → issues)
- B3: Single LLM with all tool outputs combined
- B4: Single LLM with tool outputs for summarization only

### Metrics
- Precision, Recall, F1 per agent and for final output
- Severity Accuracy: % of issues where predicted severity matches ground truth
- Duplicate Rate: duplicate issues / total issues
- Average processing time in seconds

### ground_truth.json format
```json
[
  {
    "file": "example.py",
    "line": 12,
    "issue_type": "SQL Injection",
    "severity": "critical",
    "category": "security",
    "cwe": "CWE-89"
  }
]
```

---

## Build Order

1. `models.py` — define all schemas first
2. `language_detector.py` — simple, no dependencies
3. `tool_runner.py` — subprocess calls, needs tools installed
4. `output_normalizer.py` — depends on tool_runner output format
5. `agents/state.py` — TypedDict, no dependencies
6. `agents/prompts.py` — just strings
7. `agents/security_agent.py` + `performance_agent.py` + `maintainability_agent.py`
8. `agents/synthesizer_agent.py`
9. `agents/graph.py` — wires all agents together
10. `main.py` — wires everything end to end
11. Frontend after backend is manually tested via curl/Postman
12. Evaluation scripts last

---

## Manual Test (curl)

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import os\nuser_input = input()\nos.system(user_input)",
    "filename": "test.py"
  }'
```

Expected: at least one critical security issue flagging OS command injection.
