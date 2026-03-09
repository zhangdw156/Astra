"""
Video API Mock - Mock external video search APIs

Simulates video search APIs for YouTube, TikTok, Instagram, and Twitter/X.
"""

import random
from typing import Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Video Search Mock API")


class Video(BaseModel):
    id: str
    title: str
    platform: str
    url: str
    duration: Optional[str] = None
    views: str
    likes: Optional[str] = None
    relevance_note: Optional[str] = None
    engagement: Optional[str] = None
    trend_score: Optional[str] = None


MOCK_VIDEOS = {
    "youtube": [
        Video(
            id="yt-001",
            title="Breaking: AI Breakthrough Changes Everything",
            platform="youtube",
            url="https://youtube.com/watch?v=abc123",
            duration="12:34",
            views="2.5M",
            likes="150K",
            relevance_note="Latest AI news from major tech channel",
        ),
        Video(
            id="yt-002",
            title="Tesla Full Self-Driving V13 Review",
            platform="youtube",
            url="https://youtube.com/watch?v=def456",
            duration="18:22",
            views="1.2M",
            likes="89K",
            relevance_note="Comprehensive FSD review and testing",
        ),
        Video(
            id="yt-003",
            title="iPhone 17 Pro Max First Look",
            platform="youtube",
            url="https://youtube.com/watch?v=ghi789",
            duration="15:45",
            views="3.1M",
            likes="210K",
            relevance_note="Exclusive first look at new iPhone",
        ),
    ],
    "tiktok": [
        Video(
            id="tt-001",
            title="#AI #trending #viral",
            platform="tiktok",
            url="https://tiktok.com/@user/video/123456",
            duration="0:45",
            views="5.2M",
            likes="890K",
            relevance_note="Trending AI content on TikTok",
        ),
        Video(
            id="tt-002",
            title="Dance challenge goes viral",
            platform="tiktok",
            url="https://tiktok.com/@user/video/234567",
            duration="0:30",
            views="12.1M",
            likes="2.1M",
            relevance_note="Top trending dance challenge",
        ),
    ],
    "instagram": [
        Video(
            id="ig-001",
            title="Reel: Amazing sunset timelapse",
            platform="instagram",
            url="https://instagram.com/reel/ABC123",
            duration="0:58",
            views="450K",
            likes="32K",
            relevance_note="Stunning nature footage",
        ),
        Video(
            id="ig-002",
            title="Reel: Tech review - Best gadgets 2024",
            platform="instagram",
            url="https://instagram.com/reel/DEF456",
            duration="1:30",
            views="280K",
            likes="18K",
            relevance_note="Tech gadgets overview",
        ),
    ],
    "twitter": [
        Video(
            id="tw-001",
            title="Breaking: Major announcement",
            platform="twitter",
            url="https://twitter.com/user/status/1234567890",
            duration="2:15",
            views="890K",
            likes="45K",
            relevance_note="Important news from verified account",
        ),
        Video(
            id="tw-002",
            title="Sports highlight clip",
            platform="twitter",
            url="https://twitter.com/user/status/0987654321",
            duration="0:47",
            views="1.5M",
            likes="120K",
            relevance_note="Viral sports moment",
        ),
    ],
}

CATEGORIES = {
    "music": ["youtube", "tiktok", "instagram"],
    "tech": ["youtube", "twitter"],
    "gaming": ["youtube", "tiktok"],
    "news": ["youtube", "twitter"],
    "entertainment": ["youtube", "tiktok", "instagram"],
    "sports": ["youtube", "twitter", "instagram"],
}


def get_mock_videos(platform: str = "all", limit: int = 10):
    """Get mock videos for a platform"""
    if platform == "all":
        all_videos = []
        for platform_videos in MOCK_VIDEOS.values():
            all_videos.extend(platform_videos)
        return all_videos[:limit]

    return MOCK_VIDEOS.get(platform, [])[:limit]


@app.get("/videos/search")
async def search_videos(
    q: str = Query(..., description="Search query"),
    platform: str = Query("all", description="Platform filter"),
    limit: int = Query(10, description="Max results"),
):
    """Search for videos"""
    platform_filter = platform if platform != "all" else None

    videos = get_mock_videos(platform_filter, limit)

    return {
        "query": q,
        "platform": platform,
        "videos": [v.dict() for v in videos],
        "total": len(videos),
    }


@app.get("/videos/trending")
async def get_trending(
    category: str = Query("all", description="Category filter"),
    region: str = Query("us", description="Region code"),
    limit: int = Query(10, description="Max results"),
):
    """Get trending videos"""
    platforms = CATEGORIES.get(category, list(MOCK_VIDEOS.keys()))

    videos = []
    for platform in platforms:
        platform_videos = MOCK_VIDEOS.get(platform, [])
        for v in platform_videos:
            v.trend_score = str(random.randint(80, 99))
            videos.append(v)

    videos = videos[:limit]

    return {
        "category": category,
        "region": region,
        "videos": [v.dict() for v in videos],
        "total": len(videos),
    }


@app.get("/videos/compare")
async def compare_videos(
    q: str = Query(..., description="Comparison query"),
    platforms: str = Query("youtube,tiktok,twitter", description="Comma-separated platforms"),
    limit: int = Query(3, description="Videos per platform"),
):
    """Compare videos across platforms"""
    platform_list = platforms.split(",")
    result_platforms = []

    for platform in platform_list:
        platform = platform.strip()
        videos = get_mock_videos(platform, limit)
        result_platforms.append({"platform": platform, "videos": [v.dict() for v in videos]})

    return {
        "query": q,
        "platforms": result_platforms,
        "summary": f"Found {sum(len(p['videos']) for p in result_platforms)} videos across {len(platform_list)} platforms for '{q}'.",
    }


@app.get("/videos/sourcing")
async def video_sourcing(
    query: str = Query(..., description="Sourcing query"),
    event_detail: str = Query("compact", description="compact or verbose"),
):
    """Video sourcing endpoint - simulates the video sourcing agent"""
    videos = get_mock_videos("all", 3)

    return {
        "event": "complete",
        "query": query,
        "videos": [v.dict() for v in videos],
        "summary": f"Found {len(videos)} relevant videos for '{query}'. Results show top trending content across platforms.",
        "tools_used": ["youtube_search", "tiktok_api", "twitter_api"],
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
