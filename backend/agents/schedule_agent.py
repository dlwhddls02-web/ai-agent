"""
일정 관리 에이전트
- 오늘/이번주 상담 일정 파악
- 담당 팀원에게 카카오 알림 발송
- 일정 충돌 감지 및 보고
"""
import os
import json
from datetime import datetime, timedelta
import anthropic
from tools.notion_client import get_customer_db, get_member_db, extract_text, extract_select, extract_date
from tools.kakao_client import send_notification
from memory import update_agent_status, append_log

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "send_schedule_alert",
        "description": "팀원에게 오늘 상담 일정 알림 발송",
        "input_schema": {
            "type": "object",
            "properties": {
                "member_name": {"type": "string"},
                "schedule_summary": {"type": "string", "description": "오늘 상담 목록 요약"},
            },
            "required": ["member_name", "schedule_summary"],
        },
    },
    {
        "name": "send_customer_reminder",
        "description": "상담 예정 고객에게 리마인더 발송",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "schedule_time": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["customer_name", "schedule_time", "message"],
        },
    },
    {
        "name": "log_schedule_action",
        "description": "일정 관련 조치 기록",
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
    if tool_name == "send_schedule_alert":
        msg = f"[오늘 상담 일정 알림]\n{tool_input['schedule_summary']}"
        result = await send_notification(tool_input["member_name"], msg)
        await append_log("schedule_agent", "schedule_alert_sent", tool_input["member_name"])
        return f"일정 알림 발송 완료: {result}"

    elif tool_name == "send_customer_reminder":
        result = await send_notification(tool_input["customer_name"], tool_input["message"])
        await append_log("schedule_agent", "customer_reminder_sent", tool_input["customer_name"])
        return f"고객 리마인더 발송 완료: {result}"

    elif tool_name == "log_schedule_action":
        await append_log("schedule_agent", tool_input["action"], tool_input["detail"])
        return "로그 기록 완료"

    return "알 수 없는 도구"


async def run(focus: str) -> str:
    await update_agent_status("schedule_agent", "running", focus)
    await append_log("schedule_agent", "start", focus)

    try:
        customers = await get_customer_db()
        members = await get_member_db()

        today_str = datetime.now().strftime("%Y-%m-%d")
        week_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        schedule_items = []
        for p in customers:
            props = p.get("properties", {})
            consult_date = extract_date(props.get("상담일", props.get("ConsultDate", {})))
            if consult_date and today_str <= consult_date[:10] <= week_end:
                schedule_items.append({
                    "customer_name": extract_text(props.get("이름", props.get("Name", {}))),
                    "consult_date": consult_date,
                    "assigned_member": extract_select(props.get("담당자", props.get("Assignee", {}))),
                    "status": extract_select(props.get("상태", props.get("Status", {}))),
                })

        member_list = []
        for p in members:
            props = p.get("properties", {})
            member_list.append({
                "name": extract_text(props.get("이름", props.get("Name", {}))),
                "role": extract_select(props.get("역할", props.get("Role", {}))),
            })

        system_prompt = """당신은 보험팀 일정 관리 전문 AI 에이전트입니다.
오늘과 이번 주 상담 일정을 분석하고 필요한 알림을 발송하세요.

우선순위:
1. 오늘 상담 고객 → 담당 팀원에게 일정 알림 + 고객에게 리마인더
2. 내일 상담 고객 → 담당 팀원 사전 알림
3. 이번 주 상담 요약 → 팀 전체 공유

모든 조치는 log_schedule_action으로 기록."""

        user_message = f"""집중 처리 지시: {focus}
오늘 날짜: {today_str}

이번 주 상담 일정 ({len(schedule_items)}건):
{json.dumps(schedule_items, ensure_ascii=False, indent=2)}

팀원 목록:
{json.dumps(member_list, ensure_ascii=False, indent=2)}

필요한 알림을 즉시 발송하세요."""

        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        messages = [{"role": "user", "content": user_message}]

        final_result = ""
        for _ in range(8):
            response = await client.messages.create(
                model=MODEL,
                max_tokens=2048,
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

        await update_agent_status("schedule_agent", "idle", final_result[:200])
        return final_result

    except Exception as e:
        await update_agent_status("schedule_agent", "error", str(e))
        await append_log("schedule_agent", "error", str(e), level="error")
        return f"오류: {e}"
