"""
Twitter API Mock - 模拟 Twitter API

Mock Twitter API 用于测试发布和回复功能。
"""

import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Twitter Mock API")


class TweetRequest(BaseModel):
    text: str
    account: Optional[str] = None
    image_path: Optional[str] = None
    vary: Optional[bool] = False


class ReplyRequest(BaseModel):
    tweet_id: str
    text: str
    account: Optional[str] = None
    image_path: Optional[str] = None


@app.post("/tweets")
async def create_tweet(request: TweetRequest):
    """创建推文"""
    char_count = len(request.text)
    if char_count > 280:
        raise HTTPException(status_code=400, detail="Tweet exceeds 280 characters")

    tweet_id = str(random.randint(1000000000000000000, 9999999999999999999))

    return {
        "tweet_id": tweet_id,
        "text": request.text,
        "url": f"https://twitter.com/user/status/{tweet_id}",
        "account": request.account or "default",
    }


@app.post("/tweets/reply")
async def reply_to_tweet(request: ReplyRequest):
    """回复推文"""
    char_count = len(request.text)
    if char_count > 280:
        raise HTTPException(status_code=400, detail="Reply exceeds 280 characters")

    reply_id = str(random.randint(1000000000000000000, 9999999999999999999))

    return {
        "tweet_id": reply_id,
        "text": request.text,
        "url": f"https://twitter.com/user/status/{reply_id}",
        "in_reply_to": request.tweet_id,
        "account": request.account or "default",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
