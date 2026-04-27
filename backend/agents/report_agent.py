"""
보고서 에이전트
- 일일 실적 집계 (신규 계약, 갱신, 이탈)
- 주간 보고서 자동 생성
- 팀장에게 요약 카카오 발송
"""
import os
import json
from datetime import datetime, timedelta
import anthropic
from tools.notion_client import get_customer_db, get_member_db, extract_text, extract_select, extract_date, extract_number
from tools.kakao_client import send_notification
from memory import update_agent_status, append_log

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "send_daily_report",
        "description": "팀장에게 일일 보고서 카카오 발송",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "보고서 수신자 (팀장명)"},
                "report_content": {"type": "string", "description": "보고서 전문"},
            },
            "required": ["recipient", "report_content"],
        },
    },
    {
        "name": "send_weekly_report",
        "description": "주간 보고서 발송",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string"},
                "report_content": {"type": "string"},
            },
            "required": ["recipient", "report_content"],
        },
    },
    {
        "name": "calculate_metrics",
        "description": "실적 지표 계산 결과 기록",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string"},
                "value": {"type": "string"},
                "period": {"type": "string"},
            },
            "required": ["metric_name", "value", "period"],
        },
    },
    {
        "name": "log_report_action",
        "description": "보고서 생성 관련 조치 기록",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "detail": {"type": "string"},
            },
            "required": ["action", "detail"],
        },
    },
]


async def _dispatch(tool_name: str, tool_input: dict) -> str:
    if tool_name == "send_daily_report":
        result = await send_notification(tool_input["recipient"], tool_input["report_content"])
        await append_log("report_agent", "daily_report_sent", tool_input["recipient"])
        return f"일일 보고서 발송 완료: {result}"

    elif tool_name == "send_weekly_report":
        result = await send_notification(tool_input["recipient"], tool_input["report_content"])
        await append_log("report_agent", "weekly_report_sent", tool_input["recipient"])
        return f"주간 보고서 발송 완료: {result}"

    elif tool_name == "calculate_metrics":
        await append_log("report_agent", f"metric:{tool_input['metric_name']}", {
            "value": tool_input["value"],
            "period": tool_input["period"],
        })
        return f"지표 기록 완료: {tool_input['metric_name']} = {tool_input['value']}"

    elif tool_name == "log_report_action":
        await append_log("report_agent", tool_input["action"], tool_input["detail"])
        return "로그 기록 완료"

    return "알 수 없는 도구"


async def run(focus: str) -> str:
    await update_agent_status("report_agent", "running", focus)
    await append_log("report_agent", "start", focus)

    try:
        customers = await get_customer_db()
        members = await get_member_db()

        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

        # 실적 데이터 집계
        stats = {
            "total_customers": len(customers),
            "by_status": {},
            "new_this_week": 0,
            "expiring_30days": 0,
            "total_premium": 0,
        }

        for p in customers:
            props = p.get("properties", {})
            status = extract_select(props.get("상태", props.get("Status", {})))
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            contract_date = extract_date(props.get("계약일", props.get("ContractDate", {})))
            if contract_date and contract_date[:10] >= week_start:
                stats["new_this_week"] += 1

            expire_date = extract_date(props.get("만기일", props.get("ExpireDate", {})))
            if expire_date:
                try:
                    exp_dt = datetime.strptime(expire_date[:10], "%Y-%m-%d")
                    if 0 <= (exp_dt - today).days <= 30:
                        stats["expiring_30days"] += 1
                except Exception:
                    pass

            premium = extract_number(props.get("보험료", props.get("Premium", {})))
            if premium:
                stats["total_premium"] += premium

        member_names = []
        for p in members:
            props = p.get("properties", {})
            role = extract_select(props.get("역할", props.get("Role", {})))
            if role in ("팀장", "매니저", "Manager"):
                member_names.append(extract_text(props.get("이름", props.get("Name", {}))))

        team_leader = member_names[0] if member_names else "팀장"

        system_prompt = """당신은 보험팀 보고서 전문 AI 에이전트입니다.
수집된 실적 데이터를 분석하여 전문적인 보고서를 작성하고 팀장에게 발송하세요.

보고서 형식:
📊 [날짜] 보험팀 일일 보고서
─────────────────
■ 전체 현황
■ 신규/갱신/이탈 현황
■ 만기 임박 계약
■ 오늘의 주요 활동
■ 내일 예정 업무

먼저 calculate_metrics로 주요 지표를 기록한 후,
send_daily_report로 팀장에게 발송하세요."""

        user_message = f"""집중 처리 지시: {focus}
오늘 날짜: {today_str}
팀장: {team_leader}

집계 데이터:
{json.dumps(stats, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 일일 보고서를 작성하고 발송하세요."""

        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": user_message}]

        final_result = ""
        for _ in range(8):
            response = await client.messages.create(
                model=MODEL,
                max_tokens=3000,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                final_result = " ".join(b.text for b in response.content if hasattr(b, "text"))
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        res = await _dispatch(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": res,
                        })
                messages.append({"role": "user", "content": tool_results})

        await update_agent_status("report_agent", "idle", final_result[:200])
        return final_result

    except Exception as e:
        await update_agent_status("report_agent", "error", str(e))
        await append_log("report_agent", "error", str(e), level="error")
        return f"오류: {e}"
