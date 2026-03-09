"""
Typefully API Mock - 模拟 Typefully API

Typefully 是社交媒体排程工具，支持 X, LinkedIn, Threads, Bluesky, Mastodon。
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Header, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

app = FastAPI(title="Typefully Mock API")

MOCK_SOCIAL_SETS = [
    {"id": "123456", "name": "Main Account", "platform": "x"},
    {"id": "789012", "name": "LinkedIn Page", "platform": "linkedin"},
]

MOCK_DRAFTS = [
    {
        "id": "111111",
        "status": "draft",
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
        "publish_at": None,
        "content": [{"text": "Just shipped a new feature!"}],
    },
    {
        "id": "222222",
        "status": "scheduled",
        "created_at": "2026-03-02T14:00:00Z",
        "updated_at": "2026-03-02T14:00:00Z",
        "publish_at": "2026-03-10T09:00:00Z",
        "content": [{"text": "Check out our latest update!"}],
    },
    {
        "id": "333333",
        "status": "published",
        "created_at": "2026-02-15T08:00:00Z",
        "updated_at": "2026-02-20T12:00:00Z",
        "publish_at": "2026-02-20T12:00:00Z",
        "content": [{"text": "Exciting news coming soon..."}],
    },
]

next_draft_id = 444444


def verify_auth(authorization: Optional[str] = Header(None)):
    """验证 API 认证"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return True


@app.get("/social-sets")
async def list_social_sets(authorization: Optional[str] = Header(None)):
    """List social sets"""
    verify_auth(authorization)
    return MOCK_SOCIAL_SETS


@app.get("/social-sets/{social_set_id}/drafts")
async def list_drafts(
    social_set_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, description="Max results"),
    authorization: Optional[str] = Header(None),
):
    """List drafts"""
    verify_auth(authorization)

    drafts = MOCK_DRAFTS.copy()

    if status:
        drafts = [d for d in drafts if d["status"] == status]

    return drafts[:limit]


@app.get("/social-sets/{social_set_id}/drafts/{draft_id}")
async def get_draft(social_set_id: str, draft_id: str, authorization: Optional[str] = Header(None)):
    """Get a single draft"""
    verify_auth(authorization)

    for draft in MOCK_DRAFTS:
        if str(draft["id"]) == draft_id:
            return draft

    raise HTTPException(status_code=404, detail="Draft not found")


@app.post("/social-sets/{social_set_id}/drafts")
async def create_draft(
    social_set_id: str, body: Dict[str, Any], authorization: Optional[str] = Header(None)
):
    """Create a new draft"""
    global next_draft_id
    verify_auth(authorization)

    draft_id = str(next_draft_id)
    next_draft_id += 1

    platforms = body.get("platforms", {})
    posts = []
    for platform, config in platforms.items():
        if isinstance(config, dict) and "posts" in config:
            posts.extend(config["posts"])

    publish_at = body.get("publish_at")
    status = "scheduled" if publish_at else "draft"

    new_draft = {
        "id": draft_id,
        "status": status,
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z",
        "publish_at": publish_at,
        "content": posts,
    }

    MOCK_DRAFTS.insert(0, new_draft)

    return new_draft


@app.put("/social-sets/{social_set_id}/drafts/{draft_id}")
async def update_draft(
    social_set_id: str,
    draft_id: str,
    body: Dict[str, Any],
    authorization: Optional[str] = Header(None),
):
    """Update a draft"""
    verify_auth(authorization)

    for draft in MOCK_DRAFTS:
        if str(draft["id"]) == draft_id:
            if "publish_at" in body:
                draft["publish_at"] = body["publish_at"]
                if body["publish_at"]:
                    draft["status"] = "scheduled"
                elif draft["status"] == "scheduled":
                    draft["status"] = "draft"

            if "platforms" in body:
                platforms = body["platforms"]
                posts = []
                for platform, config in platforms.items():
                    if isinstance(config, dict) and "posts" in config:
                        posts.extend(config["posts"])
                draft["content"] = posts

            draft["updated_at"] = datetime.now().isoformat() + "Z"
            return draft

    raise HTTPException(status_code=404, detail="Draft not found")


@app.delete("/social-sets/{social_set_id}/drafts/{draft_id}")
async def delete_draft(
    social_set_id: str, draft_id: str, authorization: Optional[str] = Header(None)
):
    """Delete a draft"""
    verify_auth(authorization)

    for i, draft in enumerate(MOCK_DRAFTS):
        if str(draft["id"]) == draft_id:
            MOCK_DRAFTS.pop(i)
            return {"success": True, "id": draft_id}

    raise HTTPException(status_code=404, detail="Draft not found")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
