# Multi-Agent AI Code Review

**Live demo → [multi-agent-code-review.vercel.app](https://multi-agent-code-review.vercel.app)**

Paste any Python or JavaScript code and get a full AI-powered review in seconds — security vulnerabilities, performance issues, maintainability problems, and a corrected version of your code.

---

## How It Works

Most code review tools run a single model over your code and return a flat list of warnings. This system runs **four specialized AI agents in parallel**, each focused on a different dimension of code quality, then a fifth agent synthesizes everything into a clean final report.

```
Your Code
    │
    ├── Static Analysis (Semgrep, Bandit, Ruff, ESLint)
    │
    ▼
┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│  Security   │  │  Performance    │  │  Maintainability    │
│   Agent     │  │    Agent        │  │      Agent          │
│ (Claude     │  │  (Claude        │  │   (Claude           │
│  Haiku)     │  │   Haiku)        │  │    Haiku)           │
└──────┬──────┘  └───────┬─────────┘  └──────────┬──────────┘
       │                 │                        │
       └─────────────────┼────────────────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │   Synthesizer    │
               │  (Claude Sonnet) │
               │                  │
               │ • Merges issues  │
               │ • Removes dupes  │
               │ • Fixed code     │
               │ • Summary        │
               └──────────────────┘
```

The three specialist agents run **simultaneously** — they don't wait for each other. The synthesizer then merges overlapping findings (e.g. if all three agents flag the same line), removes duplicates, adds cross-domain insights, and produces corrected code with all fixes applied.

Results stream to the UI in real time as each agent finishes — you see security findings appear before the other agents are even done.

---

## What Each Agent Does

**Security Agent** — Looks for vulnerabilities: SQL injection, command injection, XSS, path traversal, unsafe deserialization, hardcoded secrets, and more. Grounded by Semgrep + Bandit static analysis output.

**Performance Agent** — Finds bottlenecks: O(n²) loops, blocking operations, N+1 queries, memory leaks, unnecessary repeated work. Grounded by ESLint performance rules.

**Maintainability Agent** — Reviews code quality: missing error handling, poor naming, high complexity, magic numbers, code duplication. Grounded by Ruff + ESLint style rules.

**Synthesizer** — Reads all findings from the three agents, groups issues that point to the same root cause, finds anything all three missed, writes a 2–3 sentence summary, and rewrites the code with every fix applied.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI + Python |
| Agent Orchestration | LangGraph |
| AI Models | Claude Haiku 4.5 (specialist agents) · Claude Sonnet 4.6 (synthesizer) |
| Static Analysis | Semgrep · Bandit · Ruff · ESLint |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |

---

## Running Locally

**Backend**
```bash
cd server
pip install -r ../requirements.txt
# add ANTHROPIC_API_KEY to .env
uvicorn main:app --reload
# runs on http://localhost:8000
```

**Frontend**
```bash
cd client
npm install
npm run dev
# runs on http://localhost:5173
```

---

## Deployed

- Frontend: https://multi-agent-code-review.vercel.app
- Backend: https://multi-agent-code-review.onrender.com/health
