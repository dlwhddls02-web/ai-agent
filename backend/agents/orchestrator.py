"""
오케스트레이터 에이전트
- 매일 오전 9시 자동 실행 (main.py APScheduler)
- 노션 DB 전체 스캔 → Claude가 상황 분석 → 하위 에이전트 호출 결정
- 툴 호출 루프로 완전 자율 동작
"""
import os
import json
import anthropic
from tools.notion_client import get_customer_db, get_member_db, extract_text, extract_select, extract_date
from memory import update_agent_status, append_log

MODEL = "claude-sonnet-4-6"

# ──────────────────────────────────────────────
# 오케스트레이터가 호출할 수 있는 도구 정의
# ──────────────────────────────────────────────
TOOLS = [
    {
        "name": "run_customer_agent",
        "description": "고객 관리 에이전트 실행. 신규 고객 환영 메시지, VIP 고객 관리, 이탈 위험 고객 케어를 자동 수행.",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {"type": "string", "description": "처리 우선순위 설명 (예: 이탈 위험 고객 3명 집중 케어)"}
            },
            "required": ["focus"],
        },
    },
    {
        "name": "run_contract_agent",
        "description": "계약 관리 에이전트 실행. 만기 임박 계약 갱신 알림, 실효 위험 계약 처리를 수행.",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {"type": "string", "description": "처리 우선순위 설명"}
            },
            "required": ["focus"],
        },
    },
    {
        "name": "run_schedule_agent",
        "description": "일정 관리 에이전트 실행. 오늘/이번 주 상담 일정 확인 및 팀원 알림 발송.",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {"type": "string", "description": "처리 우선순위 설명"}
            },
            "required": ["focus"],
        },
    },
    {
        "name": "run_report_agent",
        "description": "보고서 에이전트 실행. 일일/주간 실적 집계 및 팀장 보고서 자동 생성.",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {"type": "string", "description": "보고서 유형 및 범위"}
            },
            "required": ["focus"],
        },
    },
    {
        "name": "log_decision",
        "description": "오케스트레이터의 판단과 이유를 로그에 기록.",
        "input_schema": {
            "type": "object",
            "properties": {
                "decision": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["decision", "reason"],
        },
    },
]


def _summarize_customers(pages: list[dict]) -> str:
    """노션 고객 DB를 Claude에게 전달할 요약 텍스트로 변환"""
    rows = []
    for p in pages[:50]:  # 토큰 절약: 최대 50건
        props = p.get("properties", {})
        name = extract_text(props.get("이름", props.get("Name", {})))
        status = extract_select(props.get("상태", props.get("Status", {})))
        contract_date = extract_date(props.get("계약일", props.get("ContractDate", {})))
        expire_date = extract_date(props.get("만기일", props.get("ExpireDate", {})))
        rows.append(f"- {name} | 상태:{status} | 계약:{contract_date} | 만기:{expire_date}")
    return "\n".join(rows) if rows else "데이터 없음"


def _summarize_members(pages: list[dict]) -> str:
    rows = []
    for p in pages[:20]:
        props = p.get("properties", {})
        name = extract_text(props.get("이름", props.get("Name", {})))
        role = extract_select(props.get("역할", props.get("Role", {})))
        rows.append(f"- {name} | 역할:{role}")
    return "\n".join(rows) if rows else "데이터 없음"


async def _dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """도구 이름에 따라 하위 에이전트를 실제 호출"""
    from agents.customer_agent import run as run_customer
    from agents.contract_agent import run as run_contract
    from agents.schedule_agent import run as run_schedule
    from agents.report_agent import run as run_report

    focus = tool_input.get("focus", "")
    if tool_name == "run_customer_agent":
        result = await run_customer(focus)
    elif tool_name == "run_contract_agent":
        result = await run_contract(focus)
    elif tool_name == "run_schedule_agent":
        result = await run_schedule(focus)
    elif tool_name == "run_report_agent":
        result = await run_report(focus)
    elif tool_name == "log_decision":
        await append_log("orchestrator", tool_input["decision"], tool_input["reason"])
        result = "결정 기록 완료"
    else:
        result = f"알 수 없는 도구: {tool_name}"

    return result


async def run_daily_orchestration() -> None:
    """매일 자동 실행되는 메인 오케스트레이션 루프"""
    await update_agent_status("orchestrator", "running", "노션 스캔 시작")
    await append_log("orchestrator", "daily_start", "오케스트레이션 시작")

    try:
        # 1. 노션 데이터 수집
        customers = await get_customer_db()
        members = await get_member_db()

        customer_summary = _summarize_customers(customers)
        member_summary = _summarize_members(members)

        system_prompt = """당신은 보험팀 전체를 총괄하는 자율 AI 오케스트레이터입니다.
노션 데이터베이스를 분석하고, 오늘 반드시 처리해야 할 업무를 파악하여
적절한 하위 에이전트를 호출하세요.

판단 기준:
- 이탈 위험 고객(상태: 이탈위험/위험) → customer_agent 즉시 실행
- 만기 30일 이내 계약 → contract_agent 실행
- 오늘 상담 일정 있는 고객 → schedule_agent 실행
- 매일 일일보고서 → report_agent 항상 실행
- 모든 판단은 log_decision으로 기록

반드시 한국어로 소통하고, 구체적인 고객명/건수를 언급하세요."""

        user_message = f"""오늘 날짜 기준 보험팀 현황 분석 후 필요한 에이전트를 호출하세요.

[고객 DB 현황 - 총 {len(customers)}명]
{customer_summary}

[팀원 현황 - 총 {len(members)}명]
{member_summary}

위 데이터를 분석하고 오늘 처리할 업무를 결정하세요."""

        # 2. Claude 툴 호출 루프
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": user_message}]

        iteration = 0
        max_iterations = 10  # 무한 루프 방지

        while iteration < max_iterations:
            iteration += 1
            response = await client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            # assistant 응답을 대화 히스토리에 추가
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # 텍스트 응답 추출
                final_text = " ".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                await update_agent_status("orchestrator", "idle", final_text[:200])
                await append_log("orchestrator", "daily_complete", final_text[:300])
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        await append_log("orchestrator", f"tool_call:{block.name}", block.input)
                        result_text = await _dispatch_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        })

                messages.append({"role": "user", "content": tool_results})

        if iteration >= max_iterations:
            await update_agent_status("orchestrator", "idle", "최대 반복 횟수 도달")

    except Exception as e:
        await update_agent_status("orchestrator", "error", str(e))
        await append_log("orchestrator", "error", str(e), level="error")
        raise
