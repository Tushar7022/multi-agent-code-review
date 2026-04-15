import os
import time
import uuid
import logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import ReviewRequest, ReviewResponse
from language_detector import detect_language
from tool_runner import run_tools
from output_normalizer import normalize
from agents.graph import review_graph
from fastapi.responses import StreamingResponse
import asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Code Review System")

# FRONTEND_URL env var controls allowed origins.
# Defaults to localhost for local dev; set it on Render to your frontend URL.
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url],
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

@app.post("/stream")
async def stream_review(request: ReviewRequest):
    async def event_generator():
        # step 1 — detect language
        language = request.language or detect_language(request.code, request.filename)
        yield f"data: {json.dumps({'event': 'language', 'language': language})}\n\n"

        # step 2 — run tools
        try:
            tool_outputs = run_tools(request.code, language, request.filename)
        except Exception as e:
            logger.error(f"Tool runner failed: {e}")
            tool_outputs = {"semgrep": [], "bandit": [], "ruff": [], "eslint": []}

        normalized = normalize(tool_outputs, request.filename)
        yield f"data: {json.dumps({'event': 'tools_done'})}\n\n"

        # step 3 — run LangGraph pipeline with streaming
        initial_state = {
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
            "fixed_code": "", 
        }

        loop = asyncio.get_event_loop()

        async def stream_chunks():
            loop = asyncio.get_event_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def run():
                try:
                    for chunk in review_graph.stream(initial_state):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

            loop.run_in_executor(None, run)

            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk

        async for chunk in stream_chunks():
            node_name = list(chunk.keys())[0]

            if node_name == "security":
                issues = chunk["security"].get("security_issues", [])
                yield f"data: {json.dumps({'event': 'security_done', 'issues': [i.model_dump() for i in issues]})}\n\n"

            elif node_name == "performance":
                issues = chunk["performance"].get("performance_issues", [])
                yield f"data: {json.dumps({'event': 'performance_done', 'issues': [i.model_dump() for i in issues]})}\n\n"

            elif node_name == "maintainability":
                issues = chunk["maintainability"].get("maintainability_issues", [])
                yield f"data: {json.dumps({'event': 'maintainability_done', 'issues': [i.model_dump() for i in issues]})}\n\n"

            elif node_name == "synthesizer":
                final_issues = chunk["synthesizer"].get("final_issues", [])
                summary = chunk["synthesizer"].get("summary", "")
                fixed_code = chunk["synthesizer"].get("fixed_code", request.code)
                yield f"data: {json.dumps({'event': 'synthesis_done', 'issues': [i.model_dump() for i in final_issues], 'summary': summary, 'fixed_code': fixed_code})}\n\n"

        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )