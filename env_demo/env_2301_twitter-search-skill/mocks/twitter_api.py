"""
Twitter API Mock - 模拟 TwitterAPI.io 的高级搜索接口

模拟 twitterapi.io 的 advanced_search 端点，返回预设的推文数据。
"""

import random
from datetime import datetime, timedelta
from fastapi import FastAPI, Query, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="Twitter API Mock")


class Author(BaseModel):
    id: str
    userName: str
    name: str
    url: str
    description: str
    location: str
    followers: int
    following: int
    statusesCount: int
    favouritesCount: int
    isBlueVerified: bool
    createdAt: str
    profilePicture: str


class Hashtag(BaseModel):
    text: str
    indices: List[int]


class Entities(BaseModel):
    hashtags: List[Hashtag]
    urls: List[Dict[str, Any]]
    user_mentions: List[Dict[str, Any]]


class Tweet(BaseModel):
    id: str
    url: str
    text: str
    createdAt: str
    lang: str
    source: str
    retweetCount: int
    replyCount: int
    likeCount: int
    quoteCount: int
    viewCount: int
    bookmarkCount: int
    isReply: bool
    inReplyToId: Optional[str] = None
    inReplyToUserId: Optional[str] = None
    inReplyToUsername: Optional[str] = None
    conversationId: str
    author: Author
    entities: Entities


def generate_mock_tweets(query: str, count: int = 20) -> List[Tweet]:
    """生成模拟的推文数据"""

    query_lower = query.lower()

    mock_authors = [
        {"userName": "elonmusk", "name": "Elon Musk", "followers": 150000000, "verified": True},
        {"userName": "sama", "name": "Sam Altman", "followers": 3000000, "verified": True},
        {"userName": "AndrewYNg", "name": "Andrew Ng", "followers": 2500000, "verified": True},
        {"userName": "JeffDean", "name": "Jeff Dean", "followers": 500000, "verified": True},
        {"userName": "ylecun", "name": "Yann LeCun", "followers": 1200000, "verified": True},
        {
            "userName": "hwchamberlain",
            "name": "Howard Wright",
            "followers": 80000,
            "verified": False,
        },
        {
            "userName": "FinanceGuru",
            "name": "Crypto Analyst",
            "followers": 150000,
            "verified": False,
        },
        {"userName": "TechNewsDaily", "name": "Tech News", "followers": 500000, "verified": True},
    ]

    templates = [
        "Just launched our new {topic} product! Incredible response from the community. {topic} is changing everything.",
        "The future of {topic} is incredibly bright. Exciting times ahead!",
        "Thinking about {topic} today. Here's my take: innovation wins.",
        "Big announcement coming soon about {topic}. Stay tuned!",
        "{topic} is the most important technology trend of 2026. Don't miss out.",
        "Our team has been working on {topic} for months. It's finally ready!",
        "Anyone else excited about {topic}? The developments are remarkable.",
        "The latest breakthroughs in {topic} are game-changing. Here's why...",
    ]

    if "ai" in query_lower or "chatgpt" in query_lower or "gpt" in query_lower:
        templates = [
            "GPT-5 is going to revolutionize how we work with AI. The capabilities are insane!",
            "Just finished reading the latest research on {topic}. Mind = blown.",
            "Our AI team achieved a major milestone today with {topic}. So proud!",
            "{topic} is advancing faster than anyone predicted. 2026 will be huge.",
            "The intersection of {topic} and coding is where the magic happens.",
        ]
    elif "bitcoin" in query_lower or "btc" in query_lower or "crypto" in query_lower:
        templates = [
            "Bitcoin to $200K by end of 2026. The fundamentals have never been stronger.",
            "Just bought more {topic}. DCA strategy working perfectly.",
            "{topic} adoption is accelerating. Major institutions are coming onboard.",
            "The {topic} bull run is just beginning. Not financial advice but...",
            "New {topic} analysis: key support levels and targets for Q2.",
        ]
    elif "apple" in query_lower or "iphone" in query_lower:
        templates = [
            "iPhone 18 Pro concept looks incredible. Apple innovation at its finest.",
            "Just upgraded to the latest {topic}. The features are amazing!",
            "{topic} event coming next month. Expectations are through the roof.",
            "Apple's {topic} strategy is brilliant. Here's my analysis...",
        ]

    hashtags_pool = ["AI", "Tech", "Innovation", "Crypto", "Bitcoin", "Startup", "Future", "Coding"]

    tweets = []
    base_time = datetime.now()

    for i in range(count):
        author = random.choice(mock_authors)
        template = random.choice(templates)

        topic_placeholder = query.split()[0] if query else "tech"
        text = template.format(topic=topic_placeholder)

        num_hashtags = random.randint(0, 3)
        selected_hashtags = random.sample(hashtags_pool, num_hashtags)

        entities_hashtags = []
        for j, tag in enumerate(selected_hashtags):
            idx = text.find(tag)
            if idx == -1:
                idx = random.randint(0, len(text))
            entities_hashtags.append(Hashtag(text=tag, indices=[idx, idx + len(tag)]))

        tweet = Tweet(
            id=f"190000000000000000{i}",
            url=f"https://x.com/{author['userName']}/status/190000000000000000{i}",
            text=text + " " + " ".join([f"#{h}" for h in selected_hashtags]),
            createdAt=(base_time - timedelta(hours=random.randint(1, 168))).strftime(
                "%a %b %d %H:%M:%S +0000 %Y"
            ),
            lang="en",
            source="Twitter for iPhone",
            retweetCount=random.randint(10, 50000),
            replyCount=random.randint(5, 5000),
            likeCount=random.randint(50, 100000),
            quoteCount=random.randint(0, 5000),
            viewCount=random.randint(1000, 2000000),
            bookmarkCount=random.randint(0, 1000),
            isReply=False,
            conversationId=f"190000000000000000{i}",
            author=Author(
                id=str(random.randint(100000000, 999999999)),
                userName=author["userName"],
                name=author["name"],
                url=f"https://x.com/{author['userName']}",
                description=f"Official account of {author['name']}",
                location="San Francisco, CA",
                followers=author["followers"],
                following=random.randint(100, 10000),
                statusesCount=random.randint(1000, 100000),
                favouritesCount=random.randint(100, 50000),
                isBlueVerified=author["verified"],
                createdAt="Mon Jan 01 00:00:00 +0000 2020",
                profilePicture="https://pbs.twimg.com/profile_images/placeholder.jpg",
            ),
            entities=Entities(hashtags=entities_hashtags, urls=[], user_mentions=[]),
        )
        tweets.append(tweet)

    return tweets


@app.get("/twitter/tweet/advanced_search")
async def advanced_search(
    query: str = Query(..., description="Search query"),
    queryType: str = Query("Top", description="Query type: Top or Latest"),
    max_results: int = Query(20, description="Max results"),
    cursor: str = Query("", description="Pagination cursor"),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """模拟 TwitterAPI.io 高级搜索接口"""

    if not x_api_key:
        return {"error": "API key required", "status_code": 401}

    if max_results > 100:
        max_results = 100

    tweets = generate_mock_tweets(query, max_results)

    has_next = random.choice([True, False])

    return {
        "tweets": [t.dict() for t in tweets],
        "has_next_page": has_next,
        "next_cursor": "mock_cursor_12345" if has_next else "",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
