from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

from routers.agent_router import router as agent_router
from routers.log_router import router as log_router
from agents.orchestrator import run_daily_orchestration
from agents.marketing_agent import run_instagram, run_facebook, run_naver_blog

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 매일 오전 9시 오케스트레이터 자동 실행
    scheduler.add_job(run_daily_orchestration, "cron", hour=9, minute=0, id="daily_orch")
    # 마케팅 에이전트: 인스타(월·수·금 9시), 페이스북(화·목 7시), 블로그(월 8시)
    scheduler.add_job(run_instagram,  "cron", day_of_week="mon,wed,fri", hour=9,  minute=0, id="mkt_instagram")
    scheduler.add_job(run_facebook,   "cron", day_of_week="tue,thu",     hour=7,  minute=0, id="mkt_facebook")
    scheduler.add_job(run_naver_blog, "cron", day_of_week="mon",         hour=8,  minute=0, id="mkt_naver")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="보험팀 자율 AI 에이전트",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router, prefix="/api/agents", tags=["agents"])
app.include_router(log_router, prefix="/api/logs", tags=["logs"])


@app.get("/")
async def root():
    return {"status": "running", "message": "보험팀 자율 AI 에이전트 시스템 가동 중"}


@app.post("/api/trigger")
async def manual_trigger():
    """수동으로 오케스트레이터 즉시 실행"""
    await run_daily_orchestration()
    return {"status": "triggered", "message": "오케스트레이터 실행 완료"}
