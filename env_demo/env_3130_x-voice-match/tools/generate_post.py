"""
Generate Post Tool - 生成匹配声音特征的推文

根据已分析的声音画像，生成风格匹配的推文内容。
"""

import json
import random
from typing import Dict, Any, List, Optional

TOOL_SCHEMA = {
    "name": "generate_post",
    "description": "Generate X/Twitter posts that match a specific account's voice. "
    "Use after analyzing an account with analyze_voice. "
    "Takes a voice profile and topic, returns 3-5 style-matched posts with confidence scores. "
    "The posts will match the account's length, tone, humor style, and signature phrases.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Twitter username to match (with or without @)",
            },
            "topic": {"type": "string", "description": "Topic for the generated posts"},
            "post_count": {
                "type": "integer",
                "default": 3,
                "description": "Number of posts to generate (default 3, max 5)",
            },
            "post_type": {
                "type": "string",
                "description": "Type of post: hot-take, observation, meme, question, or any",
            },
        },
        "required": ["username", "topic"],
    },
}


def generate_voice_profile(username: str) -> Dict[str, Any]:
    """生成模拟的声音画像"""
    topics_pool = ["crypto", "ai", "memes", "trading", "tech"]

    return {
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


def generate_matching_posts(
    profile: Dict[str, Any], topic: str, count: int, post_type: str
) -> List[Dict[str, Any]]:
    """生成匹配声音的推文"""
    patterns = profile["patterns"]
    username = profile["account"]

    topics = patterns["topics"]
    phrases = patterns["signature_phrases"]
    tone = patterns["tone"]
    avg_length = patterns["avg_length"]

    post_templates = {
        "hot-take": [
            f"@{username}: hot take: {topic} is going to {random.choice(['moon', 'crash', 'change everything', 'be huge'])}. based and redpilled. fr fr",
            f"@{username}: unpopular opinion on {topic}... honestly i think most people are wrong. lmfao",
            f"@{username}: {topic} take: not enough people are paying attention. this is the way. gm",
        ],
        "observation": [
            f"@{username}: just realized something about {topic}... relatable?",
            f"@{username}: been thinking about {topic} a lot lately. no cap",
            f"@{username}: observation: {topic} is {random.choice(['overlooked', 'underrated', 'evolving', 'changing'])}. fren",
        ],
        "meme": [
            f"@{username}: {topic} lmfao this is too real",
            f"@{username}: me when {topic}: *existentially crisis* based",
            f"@{username}: {topic} be like: fr fr. literally can't even",
        ],
        "question": [
            f"@{username}: thoughts on {topic}? genuine question",
            f"@{username}: who else is bullish on {topic}? lfg",
            f"@{username}: question for the room: is {topic} actually worth it?",
        ],
        "any": [
            f"@{username}: been watching {topic} closely. my thesis is strengthening. gm",
            f"@{username}: update on {topic}: things are {random.choice(['getting interesting', 'evolving', 'heating up'])}",
            f"@{username}: {topic} update incoming. buckled up. ser",
            f"@{username}: quick thought on {topic}... honestly this might be big",
            f"@{username}: still thinking about {topic}. conviction remains. based",
        ],
    }

    selected_type = post_type if post_type in post_templates else "any"
    templates = post_templates[selected_type]

    posts = []
    used_templates = set()

    for i in range(min(count, 5)):
        available_templates = [t for t in templates if t not in used_templates]
        if not available_templates:
            available_templates = templates

        template = random.choice(available_templates)
        used_templates.add(template)

        confidence = round(random.uniform(0.75, 0.95), 2)

        reasoning = f"Matches {username}'s {patterns['engagement_type']} style, uses signature phrases like {', '.join(phrases[:2])}, average length {avg_length} chars"

        posts.append({"post": template, "confidence": confidence, "reasoning": reasoning})

    return posts


def execute(username: str, topic: str, post_count: int = 3, post_type: str = "any") -> str:
    """
    生成匹配账户声音的推文

    Args:
        username: 要匹配的 Twitter 用户名
        topic: 推文主题
        post_count: 生成数量
        post_type: 推文类型

    Returns:
        格式化的生成结果
    """
    if not username.startswith("@"):
        username = f"@{username}"

    profile = generate_voice_profile(username)
    posts = generate_matching_posts(profile, topic, post_count, post_type)

    output = f"# Generated Posts for {username}\n\n"
    output += f"**Topic:** {topic}\n"
    output += f"**Post Type:** {post_type}\n"
    output += f"**Voice Profile:** {profile['analyzed_tweets']} tweets analyzed\n\n"

    output += "## Voice Characteristics\n\n"
    patterns = profile["patterns"]
    output += f"- Avg Length: {patterns['avg_length']} chars\n"
    output += f"- Topics: {', '.join(patterns['topics'])}\n"
    output += f"- Signature: {', '.join(patterns['signature_phrases'][:3])}\n"
    output += f"- Style: {patterns['engagement_type']}\n\n"

    output += "## Generated Posts\n\n"
    for i, post in enumerate(posts, 1):
        output += f"### Option {i} (Confidence: {post['confidence'] * 100:.0f}%)\n\n"
        output += f"{post['post']}\n\n"
        output += f"*Reasoning: {post['reasoning']}*\n\n"
        output += "---\n\n"

    output += "**Note:** This is mock generation for demonstration. "
    output += "In production, this would use the actual voice profile from analyze_voice and an LLM for generation."

    return output


if __name__ == "__main__":
    print(execute("gravyxbt_", "AI agents taking over", 3, "hot-take"))
