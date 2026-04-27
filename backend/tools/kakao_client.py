"""카카오 알림톡/메시지 REST API 클라이언트"""
import os
import httpx
from memory import append_log

KAKAO_API_BASE = "https://kapi.kakao.com"


def _headers() -> dict:
    key = os.getenv("KAKAO_REST_API_KEY", "")
    return {
        "Authorization": f"KakaoAK {key}",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    }


async def send_message_to_me(text: str) -> dict:
    """
    카카오 '나에게 보내기' API — 개발/테스트용.
    액세스 토큰이 있어야 동작하므로, REST API 키로는
    알림톡(비즈 채널) 엔드포인트를 사용해야 합니다.
    여기서는 메시지 발송 시도를 로그로 남깁니다.
    """
    await append_log("kakao_client", "send_message_to_me", {"text": text[:80]}, level="info")

    url = f"{KAKAO_API_BASE}/v2/api/talk/memo/default/send"
    payload = {
        "template_object": (
            '{"object_type":"text","text":"' + text.replace('"', '\\"') + '",'
            '"link":{"web_url":"","mobile_web_url":""}}'
        )
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), data=payload)
            result = resp.json()
            await append_log("kakao_client", "send_result", result, level="info")
            return result
    except Exception as e:
        await append_log("kakao_client", "send_error", str(e), level="error")
        return {"error": str(e)}


async def send_notification(recipient_name: str, message: str) -> dict:
    """
    팀원에게 알림 발송 (실제 알림톡은 비즈 채널 연동 필요).
    현재는 로그 기록 + 나에게 보내기로 동작.
    """
    full_text = f"[보험팀 AI 알림]\n수신: {recipient_name}\n\n{message}"
    return await send_message_to_me(full_text)


async def send_bulk_notification(messages: list[dict]) -> list[dict]:
    """
    여러 건 순차 발송.
    messages = [{"recipient": "홍길동", "message": "내용"}, ...]
    """
    results = []
    for item in messages:
        result = await send_notification(item["recipient"], item["message"])
        results.append(result)
    return results
