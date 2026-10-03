import re
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app import db
from app.catalog import JOBS, JOB_BY_ID
from app.rag import all_documents, get_chroma_collection, seed_sample_knowledge
from app.services import answer_question, build_analysis, build_plan, demo_mode, plan_as_markdown
from app.settings import setting

app = FastAPI(title="AI 职业规划助手 API", version="0.1.0")


@app.middleware("http")
async def visit_storage(request, call_next):
    """A browser visit never implicitly inherits another visit's personal data.

    Unscoped API clients retain access to the original local database. Knowledge
    and model configuration remain shared. This is local workspace isolation,
    not an authentication mechanism.
    """
    session_id = request.headers.get("X-Career-Session")
    if session_id is None:
        return await call_next(request)
    if not re.fullmatch(r"[0-9a-f]{32}", session_id):
        return JSONResponse({"detail": "访问标识无效，请刷新页面后重试。"}, status_code=400)
    personal_routes = {"profile", "chat", "conversations", "analyses", "analysis", "plans", "experience-feedback"}
    if request.url.path.strip("/").split("/")[0] not in personal_routes:
        return await call_next(request)
    with db.session_database(session_id):
        # Idempotent initialization also serializes concurrent first requests
        # through SQLite; never assume an existing file already has its schema.
        await run_in_threadpool(db.init_db)
        return await call_next(request)


@app.get("/")
def root():
    """Provide a useful response when the API host is opened directly."""
    return {
        "name": "AI 职业规划助手 API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


class ProfileInput(BaseModel):
    grade: str = ""
    major: str = ""
    skills: List[str] = Field(default_factory=list)
    experience_text: str = ""
    interests: List[str] = Field(default_factory=list)
    target_city: str = ""
    weekly_hours: int = Field(default=5, ge=1, le=40)


class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    job_category: str
    conversation_id: Optional[int] = None


class FeedbackInput(BaseModel):
    job_category: str
    choice: str
    task_status: Optional[str] = None
    interest: Optional[int] = Field(default=None, ge=1, le=5)
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    continue_interest: Optional[int] = Field(default=None, ge=1, le=5)
    note: str = Field(default="", max_length=1000)


class PlanInput(BaseModel):
    duration_weeks: int = Field(default=4, ge=1, le=12)
    weekly_hours: Optional[int] = Field(default=None, ge=1, le=40)


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    collection = get_chroma_collection()
    indexed = bool(collection and collection.count())
    return {
        "mode": "demo" if demo_mode() else "model",
        "model": setting("LLM_MODEL") if not demo_mode() else "",
        "embedding_enabled": bool(setting("EMBEDDING_MODEL")),
        "retrieval_mode": "vector" if indexed and setting("EMBEDDING_MODEL") else "keyword",
    }


@app.get("/jobs")
def jobs():
    return JOBS


@app.get("/knowledge/status")
def knowledge_status():
    collection = get_chroma_collection()
    indexed_chunks = collection.count() if collection else 0
    return {
        "collection": "career_knowledge_v2",
        "indexed_documents": indexed_chunks,
        "indexed_chunks": indexed_chunks,
        "source_documents": len(all_documents()),
        "retrieval_mode": "vector" if indexed_chunks else "keyword",
    }


@app.post("/knowledge/index")
def index_knowledge():
    try:
        result = seed_sample_knowledge()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="知識庫入庫失敗：{0}".format(str(exc)))
    if not result.get("available"):
        raise HTTPException(status_code=503, detail="当前环境没有安装 Chroma，无法建立向量索引")
    if not result.get("configured"):
        raise HTTPException(status_code=409, detail="请先配置兼容的 Embedding 模型后再进行向量入库")
    return {"collection": "career_knowledge_v2", **result}


@app.get("/profile")
def get_profile():
    return db.get_profile()


@app.put("/profile")
def put_profile(profile: ProfileInput):
    return db.save_profile(profile.dict())


@app.get("/conversations")
def conversations():
    return db.list_conversations()


@app.get("/analyses")
def analyses():
    return db.list_analyses()


@app.get("/conversations/{conversation_id}/messages")
def messages(conversation_id: int):
    return db.get_messages(conversation_id)


@app.post("/chat")
def chat(payload: ChatInput):
    if payload.job_category not in JOB_BY_ID:
        raise HTTPException(status_code=422, detail="请选择有效岗位")
    try:
        return answer_question(payload.question, payload.job_category, payload.conversation_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/experience-feedback")
def experience_feedback(payload: FeedbackInput):
    if payload.job_category not in JOB_BY_ID or payload.choice not in ("started", "skipped"):
        raise HTTPException(status_code=422, detail="体验任务数据无效")
    data = payload.dict()
    task_status = data.pop("task_status")
    task_status = task_status or ("skipped" if data["choice"] == "skipped" else "started")
    if task_status not in ("started", "completed", "skipped"):
        raise HTTPException(status_code=422, detail="体验任务状态无效")
    if (data["choice"] == "skipped") != (task_status == "skipped"):
        raise HTTPException(status_code=422, detail="跳过状态与体验选择不一致")
    data["task_status"] = task_status
    db.save_feedback(**data)
    return {"status": "saved"}


@app.get("/experience-feedback")
def get_experience_feedback():
    return db.list_feedback()


@app.post("/analysis/{job_category}")
def analysis(job_category: str):
    try:
        return build_analysis(job_category)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/plans/{job_category}")
def create_plan(job_category: str, payload: Optional[PlanInput] = None):
    try:
        duration_weeks = payload.duration_weeks if payload else 4
        weekly_hours = payload.weekly_hours if payload else None
        return build_plan(job_category, duration_weeks, weekly_hours)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/plans")
def plans():
    return db.list_plans()


@app.get("/plans/{plan_id}/markdown")
def export_plan(plan_id: int):
    plan_row = db.get_plan(plan_id)
    if not plan_row:
        raise HTTPException(status_code=404, detail="找不到这份计划")
    return {"markdown": plan_as_markdown(plan_row["plan"], db.get_profile())}
