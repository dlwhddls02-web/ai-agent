from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import memory
from agents import orchestrator, customer_agent, contract_agent, schedule_agent, report_agent, marketing_agent

router = APIRouter()


class RunRequest(BaseModel):
    focus: str = "일반 처리"


@router.get("/status")
async def get_all_status():
    """전체 에이전트 상태 조회"""
    return memory.get_all_status()


@router.post("/orchestrator/run")
async def trigger_orchestrator(background_tasks: BackgroundTasks):
    """오케스트레이터 즉시 실행 (백그라운드)"""
    background_tasks.add_task(orchestrator.run_daily_orchestration)
    return {"status": "triggered", "agent": "orchestrator"}


@router.post("/customer/run")
async def trigger_customer(req: RunRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(customer_agent.run, req.focus)
    return {"status": "triggered", "agent": "customer_agent", "focus": req.focus}


@router.post("/contract/run")
async def trigger_contract(req: RunRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(contract_agent.run, req.focus)
    return {"status": "triggered", "agent": "contract_agent", "focus": req.focus}


@router.post("/schedule/run")
async def trigger_schedule(req: RunRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(schedule_agent.run, req.focus)
    return {"status": "triggered", "agent": "schedule_agent", "focus": req.focus}


@router.post("/report/run")
async def trigger_report(req: RunRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(report_agent.run, req.focus)
    return {"status": "triggered", "agent": "report_agent", "focus": req.focus}


@router.post("/marketing/run")
async def trigger_marketing(req: RunRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(marketing_agent.run, req.focus)
    return {"status": "triggered", "agent": "marketing_agent", "focus": req.focus}


@router.post("/marketing/instagram")
async def trigger_marketing_instagram(background_tasks: BackgroundTasks):
    background_tasks.add_task(marketing_agent.run_instagram)
    return {"status": "triggered", "agent": "marketing_agent", "platform": "instagram"}


@router.post("/marketing/facebook")
async def trigger_marketing_facebook(background_tasks: BackgroundTasks):
    background_tasks.add_task(marketing_agent.run_facebook)
    return {"status": "triggered", "agent": "marketing_agent", "platform": "facebook"}


@router.post("/marketing/naver")
async def trigger_marketing_naver(background_tasks: BackgroundTasks):
    background_tasks.add_task(marketing_agent.run_naver_blog)
    return {"status": "triggered", "agent": "marketing_agent", "platform": "naver_blog"}


@router.get("/marketing/contents")
async def get_marketing_contents(platform: str | None = None, limit: int = 20):
    """노션에 저장된 마케팅 콘텐츠 목록 조회"""
    from tools.marketing_notion import list_contents, PLATFORM
    platform_map = {
        "instagram": PLATFORM.INSTAGRAM,
        "facebook": PLATFORM.FACEBOOK,
        "naver": PLATFORM.NAVER_BLOG,
    }
    p = platform_map.get(platform) if platform else None
    return await list_contents(platform=p, limit=limit)


@router.get("/{agent_name}/status")
async def get_agent_status(agent_name: str):
    status = memory.get_all_status()
    if agent_name not in status:
        raise HTTPException(status_code=404, detail=f"에이전트 '{agent_name}'를 찾을 수 없습니다.")
    return status[agent_name]
