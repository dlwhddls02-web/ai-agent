"""
계약 관리 에이전트
- 만기 30일 이내 계약 갱신 알림
- 실효 위험 계약 처리
- 계약 현황 집계
"""
import os
import json
from datetime import datetime, timedelta
import anthropic
from tools.notion_client import get_customer_db, extract_text, extract_select, extract_date, extract_number, update_page
from tools.kakao_client import send_notification
from memory import update_agent_status, append_log

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "send_renewal_notice",
        "description": "만기 임박 고객에게 갱신 안내 카카오 메시지 발송",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "expire_date": {"type": "string"},
                "days_left": {"type": "integer"},
                "message": {"type": "string"},
            },
            "required": ["customer_name", "expire_date", "days_left", "message"],
        },
    },
    {
        "name": "flag_lapse_risk",
        "description": "실효 위험 계약을 노션에서 상태 업데이트",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "customer_name": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["page_id", "customer_name", "reason"],
        },
    },
    {
        "name": "log_contract_action",
        "description": "계약 관련 조치 기록",
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


def _days_until(date_str: str) -> int | None:
    if not date_str:
        return None
    try:
        expire = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (expire - datetime.now()).days
    except Exception:
        return None


async def _dispatch(tool_name: str, tool_input: dict) -> str:
    if tool_name == "send_renewal_notice":
        msg = tool_input["message"]
        result = await send_notification(tool_input["customer_name"], msg)
        await append_log("contract_agent", "renewal_notice_sent", {
            "customer": tool_input["customer_name"],
            "days_left": tool_input["days_left"],
        })
        return f"갱신 안내 발송 완료: {result}"

    elif tool_name == "flag_lapse_risk":
        await update_page(tool_input["page_id"], {
            "상태": {"select": {"name": "실효위험"}}
        })
        await append_log("contract_agent", "lapse_risk_flagged", tool_input["customer_name"])
        return f"실효위험 플래그 설정: {tool_input['customer_name']}"

    elif tool_name == "log_contract_action":
        await append_log("contract_agent", tool_input["action"], tool_input["detail"])
        return "로그 기록 완료"

    return "알 수 없는 도구"


async def run(focus: str) -> str:
    await update_agent_status("contract_agent", "running", focus)
    await append_log("contract_agent", "start", focus)

    try:
        customers = await get_customer_db()
        today = datetime.now()

        contract_list = []
        for p in customers:
            props = p.get("properties", {})
            expire_date = extract_date(props.get("만기일", props.get("ExpireDate", {})))
            days_left = _days_until(expire_date)
            contract_list.append({
                "page_id": p["id"],
                "name": extract_text(props.get("이름", props.get("Name", {}))),
                "status": extract_select(props.get("상태", props.get("Status", {}))),
                "expire_date": expire_date,
                "days_left": days_left,
                "premium": extract_number(props.get("보험료", props.get("Premium", {}))),
            })

        # 관련 계약만 필터링 (만기 90일 이내 또는 실효위험)
        relevant = [
            c for c in contract_list
            if (c["days_left"] is not None and c["days_left"] <= 90)
            or c["status"] in ("실효위험", "위험")
        ]

        system_prompt = """당신은 보험팀 계약 관리 전문 AI 에이전트입니다.
만기 임박 및 실효 위험 계약을 분석하고 즉시 필요한 조치를 취하세요.

우선순위:
1. 만기 7일 이내 → 긴급 갱신 안내 (send_renewal_notice)
2. 만기 8~30일 → 갱신 권유 안내 (send_renewal_notice)
3. 만기 31~90일 → 사전 안내 (send_renewal_notice)
4. 실효위험 상태 → 즉시 flag_lapse_risk 처리

모든 조치는 log_contract_action으로 기록."""

        user_message = f"""집중 처리 지시: {focus}

관련 계약 목록 ({len(relevant)}건):
{json.dumps(relevant, ensure_ascii=False, indent=2)}

즉시 필요한 조치를 실행하세요."""

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

        await update_agent_status("contract_agent", "idle", final_result[:200])
        return final_result

    except Exception as e:
        await update_agent_status("contract_agent", "error", str(e))
        await append_log("contract_agent", "error", str(e), level="error")
        return f"오류: {e}"
