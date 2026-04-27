"""
마케팅 에이전트
- 인스타그램: 월·수·금 오전 9시 자동 생성 (짧고 감성적, 해시태그 10개+)
- 페이스북:   화·목 오전 7시 자동 생성 (정보성, 중간 길이)
- 네이버 블로그: 매주 월요일 자동 생성 (SEO 최적화, 1000자+)
- 생성된 콘텐츠는 노션 마케팅DB에 자동 저장
"""
import os
from datetime import datetime
import anthropic
from tools.marketing_notion import save_content_to_notion, PLATFORM
from memory import update_agent_status, append_log

MODEL = "claude-sonnet-4-6"

# 8개 주제 × 서브토픽 목록 — 8일 주기 순환이므로 7일 안에 절대 중복 없음
TOPICS = [
    {"topic": "건강보험",   "subtopics": ["실손보험", "암보험", "3대질병"]},
    {"topic": "자동차보험", "subtopics": ["갱신", "할인", "특약"]},
    {"topic": "생명보험",   "subtopics": ["종신보험", "정기보험"]},
    {"topic": "치아보험",   "subtopics": []},
    {"topic": "어린이보험", "subtopics": []},
    {"topic": "운전자보험", "subtopics": []},
    {"topic": "간병보험",   "subtopics": []},
    {"topic": "화재보험",   "subtopics": []},
]


def _get_today_topic() -> dict:
    """
    오늘 날짜의 절대 일수(ordinal)를 주제 수로 나눈 나머지로 주제 선택.
    → 같은 날은 플랫폼 무관하게 항상 동일 주제
    → 8일 주기 순환이므로 연속 7일 안에 동일 주제 절대 중복 없음
    """
    from datetime import date
    return TOPICS[date.today().toordinal() % len(TOPICS)]

TOOLS = [
    {
        "name": "generate_instagram_content",
        "description": "인스타그램용 보험 마케팅 콘텐츠 생성 및 노션 저장",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "보험 주제 (예: 건강보험)"},
                "title": {"type": "string", "description": "콘텐츠 제목"},
                "body": {"type": "string", "description": "본문 내용 (이모지 포함, 200자 내외)"},
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "해시태그 목록 (# 포함, 최소 10개)",
                },
            },
            "required": ["topic", "title", "body", "hashtags"],
        },
    },
    {
        "name": "generate_facebook_content",
        "description": "페이스북용 보험 마케팅 콘텐츠 생성 및 노션 저장",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string", "description": "정보성 본문 (400~600자)"},
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "해시태그 목록 (5개 내외)",
                },
            },
            "required": ["topic", "title", "body", "hashtags"],
        },
    },
    {
        "name": "generate_naver_blog_content",
        "description": "네이버 블로그용 SEO 최적화 콘텐츠 생성 및 노션 저장",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "title": {"type": "string", "description": "SEO를 고려한 블로그 제목"},
                "body": {"type": "string", "description": "상세 본문 (1000자 이상, 소제목 포함)"},
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "블로그 태그 (8개 내외)",
                },
                "seo_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "주요 SEO 키워드 목록",
                },
            },
            "required": ["topic", "title", "body", "hashtags", "seo_keywords"],
        },
    },
    {
        "name": "log_marketing_action",
        "description": "마케팅 에이전트 조치 기록",
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
    hashtags = tool_input.get("hashtags", [])
    hashtag_str = " ".join(hashtags)

    if tool_name == "generate_instagram_content":
        page_id = await save_content_to_notion(
            platform=PLATFORM.INSTAGRAM,
            title=tool_input["title"],
            body=tool_input["body"],
            hashtags=hashtag_str,
            topic=tool_input["topic"],
        )
        await append_log("marketing_agent", "instagram_saved", {
            "title": tool_input["title"],
            "notion_page": page_id,
        })
        return f"인스타그램 콘텐츠 노션 저장 완료 (page_id: {page_id})"

    elif tool_name == "generate_facebook_content":
        page_id = await save_content_to_notion(
            platform=PLATFORM.FACEBOOK,
            title=tool_input["title"],
            body=tool_input["body"],
            hashtags=hashtag_str,
            topic=tool_input["topic"],
        )
        await append_log("marketing_agent", "facebook_saved", {
            "title": tool_input["title"],
            "notion_page": page_id,
        })
        return f"페이스북 콘텐츠 노션 저장 완료 (page_id: {page_id})"

    elif tool_name == "generate_naver_blog_content":
        seo_note = "SEO 키워드: " + ", ".join(tool_input.get("seo_keywords", []))
        full_body = tool_input["body"] + f"\n\n{seo_note}"
        page_id = await save_content_to_notion(
            platform=PLATFORM.NAVER_BLOG,
            title=tool_input["title"],
            body=full_body,
            hashtags=hashtag_str,
            topic=tool_input["topic"],
        )
        await append_log("marketing_agent", "naver_blog_saved", {
            "title": tool_input["title"],
            "notion_page": page_id,
        })
        return f"네이버 블로그 콘텐츠 노션 저장 완료 (page_id: {page_id})"

    elif tool_name == "log_marketing_action":
        await append_log("marketing_agent", tool_input["action"], tool_input["detail"])
        return "로그 기록 완료"

    return "알 수 없는 도구"


def _build_system_prompt() -> str:
    return """당신은 보험 전문가 이종인 팀장의 관점으로 마케팅 콘텐츠를 작성하는 AI 에이전트입니다.

작성 원칙:
- 광고처럼 보이지 않게, 고객에게 진심으로 도움이 되는 정보를 제공
- 이종인 팀장의 10년+ 현장 경험에서 나온 실질적인 조언 스타일
- 어렵고 딱딱한 보험 용어 → 쉽고 친근한 일상 언어로 변환
- 독자가 읽고 나서 "아, 나도 한번 점검해봐야겠다"는 마음이 들도록 작성

플랫폼별 톤:
- 인스타그램: 감성적, 짧고 임팩트 있게, 이모지 적극 활용, 해시태그 10개 이상
- 페이스북: 정보성, 신뢰감 있는 중간 톤, 구체적인 사례 포함
- 네이버 블로그: SEO 최적화, 소제목(##) 활용, 구체적 수치/사례 포함, 1000자 이상

절대 금지:
- "지금 바로 가입하세요" 같은 직접적 광고 문구
- 과장된 수익 약속
- 법적으로 문제될 수 있는 보장 확정 표현"""


async def run(focus: str = "오늘의 마케팅 콘텐츠 생성") -> str:
    await update_agent_status("marketing_agent", "running", focus)
    await append_log("marketing_agent", "start", focus)

    today = datetime.now()
    weekday = today.weekday()  # 플랫폼 스케줄 결정에만 사용
    topic_info = _get_today_topic()
    topic = topic_info["topic"]
    subtopics = topic_info["subtopics"]
    date_str = today.strftime("%Y년 %m월 %d일")

    # 요일별 생성할 플랫폼 결정
    platform_tasks = []
    if weekday in (0, 2, 4):   # 월·수·금 → 인스타그램
        platform_tasks.append("instagram")
    if weekday in (1, 3):       # 화·목 → 페이스북
        platform_tasks.append("facebook")
    if weekday == 0:            # 월요일 → 네이버 블로그도 함께
        platform_tasks.append("naver_blog")

    # focus에 특정 플랫폼이 명시된 경우 오버라이드
    if "인스타" in focus or "instagram" in focus.lower():
        platform_tasks = ["instagram"]
    elif "페이스북" in focus or "facebook" in focus.lower():
        platform_tasks = ["facebook"]
    elif "블로그" in focus or "naver" in focus.lower():
        platform_tasks = ["naver_blog"]
    elif "전체" in focus or "all" in focus.lower():
        platform_tasks = ["instagram", "facebook", "naver_blog"]

    if not platform_tasks:
        platform_tasks = ["instagram"]  # 기본값

    platforms_str = ", ".join(platform_tasks)

    subtopic_hint = f"세부 키워드: {', '.join(subtopics)}" if subtopics else ""

    user_message = f"""오늘({date_str}) 보험 마케팅 콘텐츠를 생성해주세요.

오늘의 주제: {topic}
{subtopic_hint}
생성할 플랫폼: {platforms_str}
추가 지시: {focus}

각 플랫폼에 맞는 도구를 호출하여 콘텐츠를 생성하고 노션에 저장하세요.
생성 전에 log_marketing_action으로 시작 로그를 남기세요."""

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": user_message}]

    final_result = ""
    try:
        for _ in range(10):
            response = await client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=_build_system_prompt(),
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
                        await append_log("marketing_agent", f"tool_call:{block.name}", block.input)
                        res = await _dispatch(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": res,
                        })
                messages.append({"role": "user", "content": tool_results})

        summary = f"{topic} 콘텐츠 생성 완료 ({platforms_str})"
        await update_agent_status("marketing_agent", "idle", summary)
        await append_log("marketing_agent", "complete", summary)
        return final_result or summary

    except Exception as e:
        await update_agent_status("marketing_agent", "error", str(e))
        await append_log("marketing_agent", "error", str(e), level="error")
        return f"오류: {e}"


async def run_instagram() -> str:
    return await run("인스타그램 콘텐츠 생성")


async def run_facebook() -> str:
    return await run("페이스북 콘텐츠 생성")


async def run_naver_blog() -> str:
    return await run("네이버 블로그 콘텐츠 생성")
