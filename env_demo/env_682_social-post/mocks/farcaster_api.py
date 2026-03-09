"""
Farcaster API Mock - 模拟 Farcaster API

Mock Neynar API 用于测试 Cast 发布和回复功能。
"""

import random
import hashlib
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Farcaster Mock API")


class CastRequest(BaseModel):
    text: str
    image_path: Optional[str] = None


class ReplyRequest(BaseModel):
    cast_hash: str
    text: str
    image_path: Optional[str] = None


def generate_cast_hash(text: str) -> str:
    """生成模拟的 Cast hash"""
    random_bytes = str(random.randint(0, 999999)).encode()
    hash_input = text.encode() + random_bytes
    return "0x" + hashlib.sha256(hash_input).hexdigest()[:64]


@app.post("/casts")
async def create_cast(request: CastRequest, authorization: Optional[str] = Header(None)):
    """创建 Cast"""
    byte_count = len(request.text.encode("utf-8"))
    if byte_count > 320:
        raise HTTPException(status_code=400, detail="Cast exceeds 320 bytes")

    cast_hash = generate_cast_hash(request.text)

    return {
        "hash": cast_hash,
        "text": request.text,
        "url": f"https://farcaster.xyz/~/conversations/{cast_hash}",
        "cost": "0.001 USDC",
    }


@app.post("/casts/reply")
async def reply_to_cast(request: ReplyRequest, authorization: Optional[str] = Header(None)):
    """回复 Cast"""
    byte_count = len(request.text.encode("utf-8"))
    if byte_count > 320:
        raise HTTPException(status_code=400, detail="Reply exceeds 320 bytes")

    reply_hash = generate_cast_hash(request.text)

    return {
        "hash": reply_hash,
        "text": request.text,
        "url": f"https://farcaster.xyz/~/conversations/{reply_hash}",
        "parent_hash": request.cast_hash,
        "cost": "0.001 USDC",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
