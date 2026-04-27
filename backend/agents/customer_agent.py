"""
고객 관리 에이전트
- 신규 고객 환영 메시지 발송
- VIP 고객 정기 케어
- 이탈 위험 고객 긴급 대응
"""
import os
import anthropic
from tools.notion_client import get_customer_db, extract_text, extract_select, extract_date, update_page
from tools.kakao_client import send_notification
from memory import update_agent_status, append_log

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "send_kakao_to_customer",
        "description": "고객에게 카카오 알림 메시지 발송",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "message": {"type": "string", "description": "발송할 메시지 내용"},
            },
            "required": ["customer_name", "message"],
        },
    },
    {
        "name": "update_customer_status",
        "description": "노션 고객 DB의 상태값 업데이트",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "new_status": {"type": "string", "description": "새 상태값 (예: 케어완료, VIP, 활성)"},
            },
            "required": ["page_id", "new_status"],
        },
    },
    {
        "name": "log_customer_action",
        "description": "고객 관련 조치 사항 로그 기록",
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
    if tool_name == "send_kakao_to_customer":
        result = await send_notification(tool_input["customer_name"], tool_input["message"])
        return f"카카오 발송 완료: {result}"
    elif tool_name == "update_customer_status":
        await update_page(tool_input["page_id"], {
            "상태": {"select": {"name": tool_input["new_status"]}}
        })
        return f"상태 업데이트 완료: {tool_input['new_status']}"
    elif tool_name == "log_customer_action":
        await append_log("customer_agent", tool_input["action"], tool_input["detail"])
        return "로그 기록 완료"
    return "알 수 없는 도구"


async def run(focus: str) -> str:
    await update_agent_status("customer_agent", "running", focus)
    await append_log("customer_agent", "start", focus)

    try:
        customers = await get_customer_db()
        customer_list = []
        for p in customers[:30]:
            props = p.get("properties", {})
            customer_list.append({
                "page_id": p["id"],
                "name": extract_text(props.get("이름", props.get("Name", {}))),
                "status": extract_select(props.get("상태", props.get("Status", {}))),
                "contract_date": extract_date(props.get("계약일", props.get("ContractDate", {}))),
                "expire_date": extract_date(props.get("만기일", props.get("ExpireDate", {}))),
            })

        import json
        customer_json = json.dumps(customer_list, ensure_ascii=False, indent=2)

        system_prompt = """당신은 보험팀 고객 관리 전문 AI 에이전트입니다.
고객 데이터를 분석하여 필요한 조치를 자율적으로 취하세요.

우선순위:
1. 이탈위험/위험 상태 고객 → 즉시 카카오 메시지 발송 + 상태 업데이트
2. 신규 고객 (계약일 7일 이내) → 환영 메시지 발송
3. VIP 고객 → 월 1회 감사 메시지

모든 조치는 log_customer_action으로 기록하세요."""

        user_message = f"""집중 처리 지시: {focus}

고객 목록:
{customer_json}

위 고객들을 분석하고 필요한 조치를 즉시 실행하세요."""

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
                final_result = " ".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
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

        await update_agent_status("customer_agent", "idle", final_result[:200])
        return final_result

    except Exception as e:
        await update_agent_status("customer_agent", "error", str(e))
        await append_log("customer_agent", "error", str(e), level="error")
        return f"오류: {e}"
