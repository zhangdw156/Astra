"""
Quick Match Tool - 一站式分析并生成匹配推文

一步完成账户分析和推文生成，无需分步操作。
"""

import json
import random
from typing import Dict, Any, List

TOOL_SCHEMA = {
    "name": "quick_match",
    "description": "One-step voice matching: analyze an account and generate matching posts in one call. "
    "Use this when you want to quickly generate posts that sound like a specific account "
    "without manually running analyze_voice first. Returns both the voice profile and generated posts.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Twitter username to analyze and match"},
            "topic": {"type": "string", "description": "Topic for the generated posts"},
            "post_count": {
                "type": "integer",
                "default": 3,
                "description": "Number of posts to generate",
            },
        },
        "required": ["username", "topic"],
    },
}


def generate_mock_profile_and_posts(username: str, topic: str, count: int) -> Dict[str, Any]:
    """生成模拟画像和推文"""
    topics_pool = ["crypto", "ai", "memes", "trading", "tech"]

    profile = {
        "account": username if username.startswith("@") else f"@{username}",
        "analyzed_tweets": 50,
        "patterns": {
            "avg_length": random.randint(60, 120),
            "distribution": {"short": 0.5, "medium": 0.4, "long": 0.1},
            "uses_threads": False,
            "tone": {
                "humor_level": random.choice(["high", "medium", "low"]),
                "self_deprecating": True,
                "sarcastic": random.choice([True, False]),
                "edgy": random.choice([True, False]),
            },
            "topics": random.sample(topics_pool, 3),
            "engagement_type": random.choice(["original content focused", "mixed original and QT"]),
            "signature_phrases": ["lmao", "fr", "based", "honestly", "gm"],
            "style": {
                "emoji_usage": "minimal",
                "capitalization": "mostly lowercase",
                "punctuation": "casual",
            },
        },
        "sample_tweets": [
            f"@{username}: just stacked more. lfg",
            f"@{username}: hot take: agents are the future. based",
            f"@{username}: my portfolio is down but my conviction is up. gm",
        ],
    }

    phrases = profile["patterns"]["signature_phrases"]
    avg_length = profile["patterns"]["avg_length"]
    engagement = profile["patterns"]["engagement_type"]

    templates = [
        f"@{username}: {topic} update: things are getting interesting. gm",
        f"@{username}: been thinking about {topic}... honestly this might be huge. fr",
        f"@{username}: hot take on {topic}. based and redpilled. lmfao",
        f"@{username}: {topic} be like: can't even. ser",
        f"@{username}: quick thought on {topic}. conviction remains. fren",
    ]

    posts = []
    for i in range(min(count, 5)):
        confidence = round(random.uniform(0.75, 0.95), 2)
        posts.append(
            {
                "post": random.choice(templates),
                "confidence": confidence,
                "reasoning": f"Matches {engagement} style, uses {', '.join(phrases[:2])}, ~{avg_length} chars",
            }
        )

    return {"profile": profile, "posts": posts}


def execute(username: str, topic: str, post_count: int = 3) -> str:
    """
    一站式分析账户并生成匹配推文

    Args:
        username: 要分析的 Twitter 用户名
        topic: 推文主题
        post_count: 生成数量

    Returns:
        格式化的分析+生成结果
    """
    if not username.startswith("@"):
        username = f"@{username}"

    result = generate_mock_profile_and_posts(username, topic, post_count)
    profile = result["profile"]
    posts = result["posts"]

    output = f"# Quick Match: {username}\n\n"
    output += f"**Topic:** {topic}\n"
    output += f"**Posts Generated:** {len(posts)}\n\n"

    output += "## Voice Profile\n\n"
    patterns = profile["patterns"]
    output += f"- **Avg Length:** {patterns['avg_length']} chars\n"
    output += f"- **Topics:** {', '.join(patterns['topics'])}\n"
    output += f"- **Signature Phrases:** {', '.join(patterns['signature_phrases'][:3])}\n"
    output += f"- **Style:** {patterns['engagement_type']}\n"
    output += f"- **Humor:** {patterns['tone']['humor_level']}\n"
    output += f"- **Self-Deprecating:** {patterns['tone']['self_deprecating']}\n\n"

    output += "## Generated Posts\n\n"
    for i, post in enumerate(posts, 1):
        output += f"### Option {i} (Confidence: {post['confidence'] * 100:.0f}%)\n\n"
        output += f"{post['post']}\n\n"
        output += f"*{post['reasoning']}*\n\n"
        output += "---\n\n"

    output += "**Workflow:** This tool combines analyze_voice + generate_post in one call.\n"
    output += "For more accurate results, use them separately with real tweet analysis."

    return output


if __name__ == "__main__":
    print(execute("gravyxbt_", "AI agents taking over", 3))
