from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse, FileResponse
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

app = FastAPI(title="Adaptive Traffic Theory Exam API")

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests"}
    )

class SizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if int(request.headers.get("content-length", 0)) > 50_000:
            return JSONResponse(
                status_code=413,
                content={"error": "Payload too large"}
            )
        return await call_next(request)

app.add_middleware(SizeLimitMiddleware)


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = FRONTEND_DIST = BASE_DIR / "quiz-ui" / "dist"

# # ✅ CORS MUST COME IMMEDIATELY AFTER app creation
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#     "http://localhost:5173",
#     "http://192.168.0.67:5173",
#     "http://192.168.0.70:5173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# ---------- MODELS ----------
class ExamRequest(BaseModel):
    level: str = "medium"

class SubmitRequest(BaseModel):
    exam: list
    answers: list
    level: str

# ---------- ROUTES ----------
@app.post("/api/exam")
@limiter.limit("10/minute")
def new_exam(request: Request, req: ExamRequest):
    from exam.exam_engine import generate_exam
    return {"exam": generate_exam(req.level)}

@app.post("/api/submit")
@limiter.limit("10/minute")
def submit(request: Request, req: SubmitRequest):
    from exam.exam_engine import grade_exam, next_level

    if len(req.exam) != len(req.answers):
        raise ValueError("Answer count does not match exam length")

    score, details = grade_exam(req.exam, req.answers)

    return {
        "score": score,
        "next_level": next_level(score, req.level),
        "details": details,
    }
# Serve React index.html
# @app.get("/")
# def serve_frontend():
#     return FileResponse(FRONTEND_DIR / "index.html")

app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
# Serve static assets
app.mount(
    "/assets",
    StaticFiles(directory=FRONTEND_DIR / "assets"),
    name="assets"
)



# uvicorn main:app --host 192.168.0.70 --port 8900