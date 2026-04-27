"""Notion API 클라이언트 — 고객 DB·멤버 DB 조회/업데이트"""
import os
import httpx
from typing import Any

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def _headers() -> dict:
    token = os.getenv("NOTION_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def query_database(db_id: str, filter_body: dict | None = None) -> list[dict]:
    """데이터베이스 전체 페이지 목록 반환 (페이지네이션 자동 처리)"""
    url = f"{BASE_URL}/databases/{db_id}/query"
    body: dict = {}
    if filter_body:
        body["filter"] = filter_body

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            resp = await client.post(url, headers=_headers(), json=body)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            body["start_cursor"] = data["next_cursor"]
    return results


async def get_page(page_id: str) -> dict:
    url = f"{BASE_URL}/pages/{page_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def update_page(page_id: str, properties: dict) -> dict:
    url = f"{BASE_URL}/pages/{page_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(url, headers=_headers(), json={"properties": properties})
        resp.raise_for_status()
        return resp.json()


async def create_page(db_id: str, properties: dict) -> dict:
    url = f"{BASE_URL}/pages"
    body = {"parent": {"database_id": db_id}, "properties": properties}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=_headers(), json=body)
        resp.raise_for_status()
        return resp.json()


def extract_text(prop: dict) -> str:
    """Notion 속성에서 텍스트 추출 헬퍼"""
    ptype = prop.get("type", "")
    if ptype == "title":
        items = prop.get("title", [])
    elif ptype == "rich_text":
        items = prop.get("rich_text", [])
    else:
        return str(prop.get(ptype, ""))
    return "".join(t.get("plain_text", "") for t in items)


def extract_select(prop: dict) -> str:
    sel = prop.get("select") or {}
    return sel.get("name", "")


def extract_date(prop: dict) -> str:
    date = prop.get("date") or {}
    return date.get("start", "")


def extract_number(prop: dict) -> float | None:
    return prop.get("number")


async def get_customer_db() -> list[dict]:
    db_id = os.getenv("NOTION_CUSTOMER_DB_ID", "")
    return await query_database(db_id)


async def get_member_db() -> list[dict]:
    db_id = os.getenv("NOTION_MEMBER_DB_ID", "")
    return await query_database(db_id)
