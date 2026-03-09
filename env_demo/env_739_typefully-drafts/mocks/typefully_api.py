"""
Typefully API Mock - 模拟 Typefully v2 API

Typefully 是一个社交媒体排程工具，支持 X、LinkedIn、Threads、Bluesky、Mastodon。
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Header, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
import random

app = FastAPI(title="Typefully Mock API")

MOCK_SOCIAL_SETS = [
    {"id": "123456", "handle": "myaccount", "platform": "x", "account_name": "My Main Account"},
    {"id": "789012", "handle": "mycompany", "platform": "linkedin", "account_name": "Company Page"},
]

MOCK_DRAFTS = [
    {
        "id": "8196074",
        "status": "draft",
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
        "publish_at": None,
        "platforms": {"x": {"enabled": True, "posts": [{"text": "Just shipped a new feature!"}]}},
    },
    {
        "id": "8196075",
        "status": "scheduled",
        "created_at": "2026-03-02T14:30:00Z",
        "updated_at": "2026-03-02T14:30:00Z",
        "publish_at": "2026-03-10T09:00:00Z",
        "platforms": {
            "x": {"enabled": True, "posts": [{"text": "Exciting update coming soon!"}]},
            "linkedin": {"enabled": True, "posts": [{"text": "Exciting update coming soon!"}]},
        },
    },
    {
        "id": "8196076",
        "status": "published",
        "created_at": "2026-02-15T08:00:00Z",
        "updated_at": "2026-02-15T08:00:00Z",
        "publish_at": "2026-02-15T12:00:00Z",
        "platforms": {
            "x": {"enabled": True, "posts": [{"text": "Check out our latest blog post!"}]}
        },
    },
]

draft_counter = 8196077


def verify_auth(authorization: str = Header(None)):
    """验证 API 认证"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return True


@app.get("/social-sets")
async def list_social_sets(authorization: str = Header(None)):
    """列出所有社交账号集"""
    verify_auth(authorization)
    return MOCK_SOCIAL_SETS


@app.get("/social-sets/{social_set_id}/drafts")
async def list_drafts(
    social_set_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, description="Max results"),
    authorization: str = Header(None),
):
    """列出草稿"""
    verify_auth(authorization)

    drafts = MOCK_DRAFTS.copy()
    if status:
        drafts = [d for d in drafts if d["status"] == status]

    return drafts[:limit]


@app.get("/social-sets/{social_set_id}/drafts/{draft_id}")
async def get_draft(social_set_id: str, draft_id: str, authorization: str = Header(None)):
    """获取单个草稿详情"""
    verify_auth(authorization)

    for draft in MOCK_DRAFTS:
        if draft["id"] == draft_id:
            return draft

    raise HTTPException(status_code=404, detail="Draft not found")


@app.post("/social-sets/{social_set_id}/drafts")
async def create_draft(social_set_id: str, request: Request, authorization: str = Header(None)):
    """创建草稿"""
    verify_auth(authorization)

    global draft_counter
    body = await request.json()

    new_draft = {
        "id": str(draft_counter),
        "status": "draft",
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z",
        "publish_at": body.get("publish_at"),
        "platforms": body.get("platforms", {}),
    }

    if new_draft["publish_at"] and new_draft["publish_at"] not in ("", "now", "next-free-slot"):
        new_draft["status"] = "scheduled"
    elif new_draft["publish_at"] == "now":
        new_draft["status"] = "published"

    MOCK_DRAFTS.append(new_draft)
    draft_counter += 1

    return new_draft


@app.put("/social-sets/{social_set_id}/drafts/{draft_id}")
async def update_draft(
    social_set_id: str, draft_id: str, request: Request, authorization: str = Header(None)
):
    """更新草稿"""
    verify_auth(authorization)

    for draft in MOCK_DRAFTS:
        if draft["id"] == draft_id:
            body = await request.json()

            if "publish_at" in body:
                draft["publish_at"] = body["publish_at"]
                if body["publish_at"] == "now":
                    draft["status"] = "published"
                elif body["publish_at"] and body["publish_at"] not in ("", "next-free-slot"):
                    draft["status"] = "scheduled"

            if "platforms" in body:
                draft["platforms"] = body["platforms"]

            draft["updated_at"] = datetime.now().isoformat() + "Z"
            return draft

    raise HTTPException(status_code=404, detail="Draft not found")


@app.delete("/social-sets/{social_set_id}/drafts/{draft_id}")
async def delete_draft(social_set_id: str, draft_id: str, authorization: str = Header(None)):
    """删除草稿"""
    verify_auth(authorization)

    for i, draft in enumerate(MOCK_DRAFTS):
        if draft["id"] == draft_id:
            MOCK_DRAFTS.pop(i)
            return {"message": "Draft deleted"}

    raise HTTPException(status_code=404, detail="Draft not found")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
