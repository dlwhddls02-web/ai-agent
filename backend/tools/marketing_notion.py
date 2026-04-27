"""
마케팅 콘텐츠 전용 노션 클라이언트
- 마케팅DB 자동 생성 (없을 경우)
- 콘텐츠 저장: 날짜, 플랫폼, 제목, 내용, 해시태그, 상태
"""
import os
from datetime import datetime
from enum import StrEnum
import httpx
from memory import append_log

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# 마케팅DB는 고객DB의 부모 페이지를 공유하거나
# 환경변수 NOTION_MARKETING_DB_ID 로 직접 지정
MARKETING_DB_ID_ENV = "NOTION_MARKETING_DB_ID"


class PLATFORM(StrEnum):
    INSTAGRAM  = "인스타그램"
    FACEBOOK   = "페이스북"
    NAVER_BLOG = "네이버블로그"


class STATUS(StrEnum):
    DRAFT     = "대기"
    SCHEDULED = "예약"
    PUBLISHED = "발행"


def _headers() -> dict:
    token = os.getenv("NOTION_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _rich_text(text: str) -> list[dict]:
    """긴 텍스트를 2000자 단위로 분할하여 rich_text 블록 리스트 생성"""
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks] if chunks else [{"type": "text", "text": {"content": ""}}]


async def _get_or_create_db() -> str:
    """
    NOTION_MARKETING_DB_ID 환경변수가 있으면 그대로 사용.
    없으면 NOTION_CUSTOMER_DB_ID 의 상위 페이지에 새 DB를 자동 생성.
    """
    db_id = os.getenv(MARKETING_DB_ID_ENV, "").strip()
    if db_id:
        return db_id

    # 부모 페이지 탐색 (고객DB의 parent 활용)
    customer_db_id = os.getenv("NOTION_CUSTOMER_DB_ID", "").strip()
    if not customer_db_id:
        raise ValueError("NOTION_MARKETING_DB_ID 또는 NOTION_CUSTOMER_DB_ID 환경변수가 필요합니다.")

    async with httpx.AsyncClient(timeout=30) as client:
        # 고객 DB 정보로 부모 페이지 ID 가져오기
        resp = await client.get(f"{BASE_URL}/databases/{customer_db_id}", headers=_headers())
        resp.raise_for_status()
        db_info = resp.json()
        parent = db_info.get("parent", {})

        # 마케팅 DB 신규 생성
        new_db = {
            "parent": parent,
            "title": [{"type": "text", "text": {"content": "📢 마케팅 콘텐츠 DB"}}],
            "properties": {
                "제목": {"title": {}},
                "날짜": {"date": {}},
                "플랫폼": {
                    "select": {
                        "options": [
                            {"name": PLATFORM.INSTAGRAM,  "color": "pink"},
                            {"name": PLATFORM.FACEBOOK,   "color": "blue"},
                            {"name": PLATFORM.NAVER_BLOG, "color": "green"},
                        ]
                    }
                },
                "주제": {"rich_text": {}},
                "해시태그": {"rich_text": {}},
                "상태": {
                    "select": {
                        "options": [
                            {"name": STATUS.DRAFT,     "color": "gray"},
                            {"name": STATUS.SCHEDULED, "color": "yellow"},
                            {"name": STATUS.PUBLISHED, "color": "green"},
                        ]
                    }
                },
                "글자수": {"number": {"format": "number"}},
            },
        }
        create_resp = await client.post(f"{BASE_URL}/databases", headers=_headers(), json=new_db)
        create_resp.raise_for_status()
        created = create_resp.json()
        new_id = created["id"]

        await append_log("marketing_notion", "db_created", f"마케팅DB 신규 생성: {new_id}")
        # 런타임 캐시 (재시작 전까지 유효)
        os.environ[MARKETING_DB_ID_ENV] = new_id
        return new_id


async def save_content_to_notion(
    platform: PLATFORM,
    title: str,
    body: str,
    hashtags: str,
    topic: str,
    status: STATUS = STATUS.DRAFT,
) -> str:
    """
    마케팅 콘텐츠를 노션 DB에 저장하고 생성된 page_id를 반환.
    본문은 페이지 children 블록으로 저장 (properties 2000자 제한 우회).
    """
    db_id = await _get_or_create_db()
    today_str = datetime.now().strftime("%Y-%m-%d")
    char_count = len(body)

    properties = {
        "제목":    {"title": _rich_text(title[:2000])},
        "날짜":    {"date": {"start": today_str}},
        "플랫폼":  {"select": {"name": platform}},
        "주제":    {"rich_text": _rich_text(topic[:200])},
        "해시태그":{"rich_text": _rich_text(hashtags[:2000])},
        "상태":    {"select": {"name": status}},
        "글자수":  {"number": char_count},
    }

    # 본문은 paragraph 블록으로 분할 저장 (2000자 단위)
    body_chunks = [body[i:i+2000] for i in range(0, max(len(body), 1), 2000)]
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        }
        for chunk in body_chunks
    ]

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties,
        "children": children,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BASE_URL}/pages", headers=_headers(), json=payload)
        resp.raise_for_status()
        page = resp.json()
        page_id = page["id"]

    await append_log("marketing_notion", "content_saved", {
        "platform": platform,
        "title": title[:60],
        "chars": char_count,
        "page_id": page_id,
    })
    return page_id


async def _fetch_page_body(client: httpx.AsyncClient, page_id: str) -> str:
    """페이지 children 블록을 순서대로 읽어 본문 전체 텍스트 반환"""
    url = f"{BASE_URL}/blocks/{page_id}/children"
    texts: list[str] = []
    params: dict = {"page_size": 100}

    while True:
        resp = await client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()

        for block in data.get("results", []):
            block_type = block.get("type", "")
            rich = block.get(block_type, {}).get("rich_text", [])
            chunk = "".join(t.get("plain_text", "") for t in rich)
            if chunk:
                texts.append(chunk)

        if not data.get("has_more"):
            break
        params["start_cursor"] = data["next_cursor"]

    return "\n".join(texts)


async def list_contents(platform: PLATFORM | None = None, limit: int = 20) -> list[dict]:
    """마케팅DB 콘텐츠 목록 조회 (플랫폼 필터 선택). body는 children 블록에서 읽음."""
    db_id = await _get_or_create_db()
    query_body: dict = {"page_size": limit, "sorts": [{"property": "날짜", "direction": "descending"}]}

    if platform:
        query_body["filter"] = {"property": "플랫폼", "select": {"equals": platform}}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/databases/{db_id}/query",
            headers=_headers(),
            json=query_body,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

        items = []
        for page in results:
            props = page.get("properties", {})

            def get_title(p):
                return "".join(t.get("plain_text", "") for t in p.get("title", []))

            def get_text(p):
                return "".join(t.get("plain_text", "") for t in p.get("rich_text", []))

            # children 블록에서 본문 전체 텍스트 로드
            body_text = await _fetch_page_body(client, page["id"])

            items.append({
                "page_id":  page["id"],
                "title":    get_title(props.get("제목", {})),
                "body":     body_text,
                "platform": props.get("플랫폼", {}).get("select", {}).get("name", ""),
                "topic":    get_text(props.get("주제", {})),
                "hashtags": get_text(props.get("해시태그", {})),
                "status":   props.get("상태", {}).get("select", {}).get("name", ""),
                "date":     props.get("날짜", {}).get("date", {}).get("start", ""),
                "chars":    props.get("글자수", {}).get("number", 0),
            })

    return items


async def update_content_status(page_id: str, status: STATUS) -> None:
    """콘텐츠 상태 업데이트 (대기 → 예약 → 발행)"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            f"{BASE_URL}/pages/{page_id}",
            headers=_headers(),
            json={"properties": {"상태": {"select": {"name": status}}}},
        )
        resp.raise_for_status()
    await append_log("marketing_notion", "status_updated", {"page_id": page_id, "status": status})
