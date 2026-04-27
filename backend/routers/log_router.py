from fastapi import APIRouter, Query
import memory

router = APIRouter()


@router.get("/")
async def get_logs(
    limit: int = Query(default=100, le=500),
    agent: str | None = Query(default=None),
):
    """행동 로그 조회 (최신순). agent 파라미터로 특정 에이전트 필터링 가능."""
    return memory.get_logs(limit=limit, agent=agent)


@router.delete("/")
async def clear_logs():
    """로그 초기화 (개발용)"""
    memory.action_logs.clear()
    return {"status": "cleared"}
