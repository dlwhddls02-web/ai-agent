"""
에이전트 공유 메모리 — 실행 로그 및 상태를 인메모리로 관리.
재시작 시 초기화되며, 프로덕션에서는 Redis/DB로 교체 가능.
"""
from datetime import datetime
from typing import Any
import asyncio

_lock = asyncio.Lock()

# 에이전트별 최신 상태
agent_status: dict[str, dict] = {
    "orchestrator": {"status": "idle", "last_run": None, "summary": ""},
    "customer_agent": {"status": "idle", "last_run": None, "summary": ""},
    "contract_agent": {"status": "idle", "last_run": None, "summary": ""},
    "schedule_agent": {"status": "idle", "last_run": None, "summary": ""},
    "report_agent": {"status": "idle", "last_run": None, "summary": ""},
    "marketing_agent": {"status": "idle", "last_run": None, "summary": ""},
}

# 시간순 행동 로그 (최대 500건 유지)
action_logs: list[dict] = []
MAX_LOGS = 500


async def update_agent_status(agent_name: str, status: str, summary: str = "") -> None:
    async with _lock:
        agent_status[agent_name] = {
            "status": status,
            "last_run": datetime.now().isoformat(),
            "summary": summary,
        }


async def append_log(agent_name: str, action: str, detail: Any = None, level: str = "info") -> None:
    async with _lock:
        entry = {
            "id": len(action_logs) + 1,
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": action,
            "detail": detail,
            "level": level,
        }
        action_logs.append(entry)
        if len(action_logs) > MAX_LOGS:
            action_logs.pop(0)


def get_all_status() -> dict:
    return dict(agent_status)


def get_logs(limit: int = 100, agent: str | None = None) -> list[dict]:
    logs = list(reversed(action_logs))
    if agent:
        logs = [l for l in logs if l["agent"] == agent]
    return logs[:limit]
