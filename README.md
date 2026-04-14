# Multi-Agent AI System for Automated Code Review
## Technical Specification — for developers and AI coding assistants

---

## What This Project Is

A backend system that performs automated code review on Python and JavaScript code using a multi-agent pipeline. Three LLM agents (Security, Performance, Maintainability) run in parallel via LangGraph. Each agent is grounded by static analysis tool output and reasons using ReAct-style prompting. A Synthesizer agent merges all outputs into a final prioritized report and generates fixed code. FastAPI serves as the HTTP layer with both a standard JSON endpoint and a Server-Sent Events (SSE) streaming endpoint. React + Vite (TypeScript) is the frontend.

---

## Tech Stack

- **FastAPI** — HTTP server, receives code, runs static tools, calls LangGraph pipeline
- **LangGraph** — orchestrates 3 parallel agents + synthesizer, manages shared state
- **Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)** — LLM for the 3 specialist agents (Security, Performance, Maintainability)
- **Claude Sonnet 4.6 (`claude-sonnet-4-6`)** — LLM for the Synthesizer agent (higher capacity for merging + code generation)
- **Semgrep** — static analysis, security patterns, Python + JS
- **Bandit** — static analysis, security vulnerabilities, Python only
- **Ruff** — static analysis, lint + style, Python only
- **ESLint** — static analysis, lint + style, JS only
- **json-repair** — fallback JSON parsing for malformed LLM responses
- **React + Vite (TypeScript)** — frontend, code input + real-time streaming results

---

## Complete File Structure

```
MultiAgent/
│
├── server/
│   ├── main.py                   # FastAPI app, routes: /health, /review, /stream
│   ├── models.py                 # Pydantic schemas: ReviewRequest, Issue, ReviewResponse
│   ├── language_detector.py      # Detects python vs javascript from filename or code
│   ├── tool_runner.py            # Runs Semgrep / Bandit / Ruff / ESLint via subprocess
│   ├── output_normalizer.py      # Normalizes tool output into categorized findings
│   │
│   └── agents/
│       ├── state.py              # LangGraph AgentState TypedDict
│       ├── graph.py              # Wires agents into fan-out/fan-in StateGraph
│       ├── prompts.py            # System prompt constants for all 4 agents
│       ├── security_agent.py
│       ├── performance_agent.py
│       ├── maintainability_agent.py
│       └── synthesizer_agent.py
│
├── client/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── types.ts              # TypeScript types mirroring server Pydantic models
│       └── components/
│           ├── Header.tsx
│           ├── CodeInput.tsx
│           ├── ProgressPanel.tsx  # SSE stream consumer, drives real-time UI updates
│           ├── IssueCard.tsx
│           ├── SeverityBadge.tsx
│           ├── AgentBadge.tsx
│           └── SummaryCard.tsx
│
├── evaluation/
│   ├── ground_truth.json         # Hand-labeled issues for 30 sample files
│   ├── prep_dataset.py           # Prepares sample files for evaluation
│   ├── run_eval.py               # Sends all samples to /review, writes predictions.json
│   └── compute_metrics.py        # Computes precision/recall/F1/severity accuracy
│   └── samples/                  # 30 Python + JS files with known vulnerabilities
│
├── .env
├── requirements.txt
└── README.md
```

---

## Request/Response Flow

### Standard (`POST /review`)
```
POST /review { code, filename, language? }
        ↓
language_detector.py         → returns "python" or "javascript"
tool_runner.py               → runs relevant static tools via subprocess
output_normalizer.py         → normalizes all tool outputs to categorized findings
        ↓
LangGraph graph.py kicks off
        ↓
security_agent.py     ─┐
performance_agent.py  ─┼─ all run in parallel, each makes one LLM call (Claude Haiku)
maintainability_agent ─┘
        ↓
synthesizer_agent.py         → merges, deduplicates, ranks, generates fixed code (Claude Sonnet)
        ↓
FastAPI returns JSON ReviewResponse
```

### Streaming (`POST /stream`)
Same pipeline but yields SSE events as each stage completes:
```
data: {"event": "language", "language": "python"}
data: {"event": "tools_done"}
data: {"event": "security_done", "issues": [...]}
data: {"event": "performance_done", "issues": [...]}
data: {"event": "maintainability_done", "issues": [...]}
data: {"event": "synthesis_done", "issues": [...], "summary": "...", "fixed_code": "..."}
data: {"event": "done"}
```
The frontend (`ProgressPanel.tsx`) consumes this stream and updates the UI incrementally as each agent finishes.

---

## File-by-File Spec

### `server/main.py`
- FastAPI app with CORS enabled for `http://localhost:5173` (Vite dev server)
- `GET /health` — liveness check, returns `{"status": "ok"}`
- `POST /review` — standard JSON endpoint, accepts `ReviewRequest`, returns `ReviewResponse`
- `POST /stream` — SSE streaming endpoint, same pipeline but yields events per-stage via `StreamingResponse`
- Both routes run: language_detector → tool_runner → output_normalizer → `review_graph.invoke()` / `review_graph.stream()`

### `server/models.py`
Pydantic models:

```python
class ReviewRequest(BaseModel):
    code: str                          # min_length=1
    filename: Optional[str] = None
    language: Optional[Language] = None  # if None, language_detector figures it out

class Issue(BaseModel):
    agent: AgentType                   # "security" | "performance" | "maintainability" | "synthesizer"
    category: Category                 # "security" | "performance" | "maintainability"
    issue_type: str
    severity: SeverityLevel            # "critical" | "high" | "medium" | "low"
    file: str
    line: int                          # ge=1
    evidence: str                      # raw static tool output that flagged this
    llm_reasoning: str                 # LLM's explanation
    suggested_fix: str
    confidence: float                  # 0.0–1.0 based on agent agreement
    agent_agreement: List[AgentType]   # which agents flagged this issue
    cross_domain_notes: Optional[str]  # synthesizer insight linking multiple domains

class ReviewResponse(BaseModel):
    session_id: UUID
    language: Language
    issues: List[Issue]
    total_issues: int
    summary: str
    fixed_code: str                    # full corrected code with all fixes applied
    processing_time_ms: int            # ge=0
```

### `server/language_detector.py`
- Input: code string + optional filename
- If filename ends in `.py` → python
- If filename ends in `.js/.ts/.jsx/.tsx` → javascript
- If no filename: scans for Python keywords (`def`, `import`, `print()`) vs JS keywords (`const`, `let`, `function`, `=>`)
- Returns: `"python"` or `"javascript"`

### `server/tool_runner.py`
- Input: code string, language string, optional filename
- Writes code to a temp file using `tempfile.NamedTemporaryFile`
- Runs tools via `subprocess.run()` with `timeout=30`
- For Python: runs Semgrep + Bandit + Ruff
- For JavaScript: runs Semgrep + ESLint
- Each tool called with JSON output flag
- Returns dict: `{ "semgrep": [...], "bandit": [...], "ruff": [...], "eslint": [...] }`
- If a tool fails or times out: logs warning, returns empty list for that tool (graceful degradation)

Tool commands:
```
semgrep --json --config=p/python --no-git-ignore --quiet <file>
bandit -f json -q <file>
ruff check --output-format=json <file>
eslint --format=json --no-eslintrc --rule {...} --env node <file>
```

### `server/output_normalizer.py`
- Input: raw dict from tool_runner, optional filename
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
- Returns: dict with keys `security_findings`, `performance_findings`, `maintainability_findings`
- Semgrep + Bandit → `security_findings`
- ESLint performance rules (`no-await-in-loop`, `no-loop-func`) → `performance_findings`
- Ruff + ESLint style rules → `maintainability_findings`
- Severity mapping: error→high, warning→medium, info→low

### `server/agents/state.py`
LangGraph state schema shared across all nodes:
```python
class AgentState(TypedDict):
    # INPUT
    code: str
    language: Language
    filename: Optional[str]

    # STATIC TOOL OUTPUTS
    tool_outputs: dict
    security_findings: List[dict]
    performance_findings: List[dict]
    maintainability_findings: List[dict]

    # AGENT OUTPUTS (Annotated with operator.add for parallel writes)
    security_issues: Annotated[List[Issue], operator.add]
    performance_issues: Annotated[List[Issue], operator.add]
    maintainability_issues: Annotated[List[Issue], operator.add]

    # SYNTHESIZER OUTPUT
    final_issues: List[Issue]
    summary: str
    fixed_code: str
```

### `server/agents/graph.py`
- Defines the LangGraph `StateGraph`
- Nodes: `security`, `performance`, `maintainability`, `synthesizer`
- `security` + `performance` + `maintainability` run as parallel nodes (fan-out from START)
- `synthesizer` runs after all three complete (fan-in)
- Compiled graph exposed as `review_graph = build_graph().compile()`
- `main.py` calls: `review_graph.invoke(initial_state)` or `review_graph.stream(initial_state)`

### `server/agents/prompts.py`
Contains system prompts for all agents as string constants:

- `SECURITY_PROMPT` — security-focused reviewer; given Semgrep + Bandit output + source code; reasons step by step; verifies true/false positives; finds false negatives; returns JSON array of issues
- `PERFORMANCE_PROMPT` — same structure, focused on scalability, slow algorithms, inefficient patterns
- `MAINTAINABILITY_PROMPT` — same structure, focused on readability, structure, complexity, naming
- `SYNTHESIZER_PROMPT` — merges findings from all three agents using an **index-based approach**: the LLM receives a numbered list of all issues (stripped to key fields) and returns `merged_issues` (groups of issue indices with cross-domain notes), `new_issues` (issues the synthesizer itself discovers), `summary`, and `fixed_code`; Python code then reconstructs full Issue objects from the index references

### `server/agents/security_agent.py` / `performance_agent.py` / `maintainability_agent.py`
All three follow the same pattern:
- LangGraph node function: `def <name>_agent(state: AgentState) -> dict`
- Pulls `state["code"]` and `state["<category>_findings"]`
- Builds user message: findings as formatted JSON + full source code
- Calls Claude Haiku API with the relevant prompt as system message
- Uses `cache_control: {"type": "ephemeral"}` on the system prompt for prompt caching
- Strips markdown fences and extracts JSON array from response
- Falls back to `json_repair` if `json.loads` fails
- If static tools returned nothing: prompt says "No static analysis findings available. Analyze directly."
- Returns `{"<category>_issues": [Issue, ...]}`

### `server/agents/synthesizer_agent.py`
- LangGraph node function: `def synthesizer_agent(state: AgentState) -> dict`
- Collects all three agent outputs from state and builds an **indexed flat array** of all issues (stripped to: index, agent, category, issue_type, severity, file, line, suggested_fix) to reduce token usage
- Calls Claude Sonnet API with `SYNTHESIZER_PROMPT` (`max_tokens=8096`)
- Retry logic: up to 3 attempts with exponential backoff (2s, 4s, 8s) on failure
- Fallback: if all retries fail, returns raw agent outputs merged without deduplication
- LLM returns JSON with shape `{"merged_issues": [...], "new_issues": [...], "summary": "...", "fixed_code": "..."}`
  - `merged_issues`: each entry has `indices` (pointing back to the flat array), `issue_type`, `severity`, `category`, `cross_domain_notes`
  - `new_issues`: issues Sonnet itself discovers, with full fields
- Two Python helper functions reconstruct final Issue objects:
  - `_reconstruct_issues()` — pulls original Issue objects by index, derives `confidence` (1.0 = all 3 agents, 0.67 = 2 agents, 0.33 = 1 agent) and `agent_agreement` from which agents had matching indices
  - `_parse_new_issues()` — converts new_issues dicts into Issue objects with `agent="synthesizer"`
- Uses `json_repair` as fallback for malformed LLM JSON
- Returns `{"final_issues": [...], "summary": "...", "fixed_code": "..."}`

---

## Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=your_key_here
```

---

## Python Dependencies (`requirements.txt`)

```
fastapi
uvicorn
pydantic
python-dotenv
anthropic
langgraph
langchain-anthropic
semgrep
bandit
ruff
json-repair
```

---

## Frontend Overview (React + Vite + TypeScript)

Two-screen UI driven by the SSE stream:

1. **Idle screen** (`App.tsx` + `CodeInput.tsx`) — textarea for code, optional filename/language fields, submit button; agent pills showing Security / Performance / Maintainability / Synthesizer
2. **Results screen** (`ProgressPanel.tsx`) — connects to `POST /stream`, updates UI in real time as each agent completes; shows per-agent issue cards, then final synthesized results

Components:
- `Header.tsx` — status bar showing `ready` / `running` / `done`
- `CodeInput.tsx` — code textarea + submit
- `ProgressPanel.tsx` — SSE consumer; renders live agent progress; clears per-agent issue lists once `synthesis_done` fires and displays final merged issues immediately on arrival
- `IssueCard.tsx` — shows: agent badge, severity badge, issue_type, file:line, evidence, llm_reasoning, suggested_fix, cross_domain_notes
- `SeverityBadge.tsx` — colored badge: Critical=red, High=orange, Medium=yellow, Low=gray
- `AgentBadge.tsx` — colored badge per agent type
- `SummaryCard.tsx` — renders synthesizer summary text

`client/src/types.ts` — TypeScript interfaces mirroring all server Pydantic models + SSE stream event union type.

---

## Evaluation

### Dataset
30 sample files in `evaluation/samples/`:
- Python files labeled with CWE numbers (CWE-020 input validation, CWE-022 path traversal, CWE-078 OS command injection, CWE-079 XSS, CWE-080 stored XSS, CWE-089 SQL injection, CWE-090 LDAP injection)
- JavaScript files with known security and performance issues

### Running Evaluation
```bash
# 1. Start the server
cd server && uvicorn main:app --reload

# 2. Send all samples through the pipeline
cd evaluation && python run_eval.py
# Writes predictions.json

# 3. Compute metrics
python compute_metrics.py
```

### Metrics
- **Precision, Recall, F1** — computed per category (security, performance) and overall
- **Severity Accuracy** — % of TP issues where predicted severity matches ground truth
- **Duplicate Rate** — duplicate issues / total predicted issues
- **Average Processing Time** — per-file average in seconds

Matching uses ±3 line tolerance and normalized issue-type matching (synonym map + word overlap).

### `ground_truth.json` format
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

## Running the Project

```bash
# Backend
cd server
pip install -r ../requirements.txt
uvicorn main:app --reload
# Server runs on http://localhost:8000

# Frontend
cd client
npm install
npm run dev
# UI runs on http://localhost:5173
```

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

```bash
# Health check
curl http://localhost:8000/health
# {"status": "ok"}
```
