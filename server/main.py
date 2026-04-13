import time
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import ReviewRequest, ReviewResponse
from language_detector import detect_language
from tool_runner import run_tools
from output_normalizer import normalize
from agents.graph import review_graph

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Code Review System")

# allow React dev server to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # quick check to verify server is running
    return {"status": "ok"}


@app.post("/review", response_model=ReviewResponse)
def review_code(request: ReviewRequest):
    start_time = time.time()
    session_id = uuid.uuid4()

    logger.info(f"Review started — session {session_id}")

    # step 1 — detect language
    language = request.language or detect_language(request.code, request.filename)
    logger.info(f"Language detected: {language}")

    # step 2 — run static analysis tools
    try:
        tool_outputs = run_tools(request.code, language, request.filename)
    except Exception as e:
        logger.error(f"Tool runner failed: {e}")
        tool_outputs = {"semgrep": [], "bandit": [], "ruff": [], "eslint": []}

    # step 3 — normalize tool outputs into categorized findings
    normalized = normalize(tool_outputs, request.filename)
    logger.info(
        f"Findings — security: {len(normalized['security_findings'])}, "
        f"performance: {len(normalized['performance_findings'])}, "
        f"maintainability: {len(normalized['maintainability_findings'])}"
    )

    # step 4 — run LangGraph pipeline
    try:
        result = review_graph.invoke({
            "code":                     request.code,
            "language":                 language,
            "filename":                 request.filename,
            "tool_outputs":             tool_outputs,
            "security_findings":        normalized["security_findings"],
            "performance_findings":     normalized["performance_findings"],
            "maintainability_findings": normalized["maintainability_findings"],
            "security_issues":          [],
            "performance_issues":       [],
            "maintainability_issues":   [],
            "final_issues":             [],
            "summary":                  "",
            "fixed_code":               "",
        })
    except Exception as e:
        logger.error(f"LangGraph pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

    # step 5 — build response
    final_issues = result.get("final_issues", [])
    processing_time = int((time.time() - start_time) * 1000)

    logger.info(
        f"Review complete — {len(final_issues)} issues found "
        f"in {processing_time}ms"
    )

    return ReviewResponse(
        session_id=session_id,
        language=language,
        issues=final_issues,
        total_issues=len(final_issues),
        summary=result.get("summary", ""),
        fixed_code=result.get("fixed_code", request.code),
        processing_time_ms=processing_time,
    )