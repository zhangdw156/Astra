"""
Analyze Voice Tool - 分析 Twitter/X 账户的声音特征

分析账户的推文风格，提取发布模式并生成声音画像。
"""

import json
import random
from typing import Dict, Any, List

TOOL_SCHEMA = {
    "name": "analyze_voice",
    "description": "Analyze a Twitter/X account's posting style and generate a voice profile. "
    "Extracts length patterns, tone markers, topics, engagement patterns, "
    "signature phrases, and writing style. Use this when you need to understand "
    "how an account tweets or prepare to generate matching content.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Twitter username to analyze (with or without @)",
            },
            "tweet_count": {
                "type": "integer",
                "default": 50,
                "description": "Number of tweets to analyze (default 50)",
            },
        },
        "required": ["username"],
    },
}


def generate_mock_tweets(username: str, count: int) -> List[Dict[str, Any]]:
    """生成模拟推文数据"""
    topics_pool = {
        "crypto": [
            "just bought the dip",
            "btc going to 100k",
            "my bags are heavy",
            "liquidity check",
        ],
        "ai": [
            "agent era is coming",
            "claude is cracked",
            "autonomous agents taking over",
            "llm ops",
        ],
        "tech": ["building in public", "shipped another feature", "dev life", "api integrations"],
        "memes": ["lmao fr fr", "based", "this is fine", "narrator: it was not fine"],
        "trading": ["entered at support", "stop loss triggered", "green day", "portfolio update"],
    }

    base_topics = random.choice(
        [
            ["crypto", "ai", "memes"],
            ["crypto", "trading", "memes"],
            ["ai", "tech", "trading"],
            ["crypto", "ai", "tech"],
        ]
    )

    sample_templates = {
        "crypto": [
            f"@{username}: just stacked more, avg down on btc. lfg 🚀",
            f"@{username}: eth looking strong, defi volume up. bulls incoming",
            f"@{username}: my portfolio is down but my conviction is up. ser",
            f"@{username}: unpopular opinion: alt season starts next month. based",
            f"@{username}: liquidated my bags. now i can finally sleep. gm",
        ],
        "ai": [
            f"@{username}: agents are the future. bookmark this. fr",
            f"@{username}: claude code is insane. built a whole app in 10 mins",
            f"@{username}: prompt engineering is dead. autonomous agents win",
            f"@{username}: hot take: ai won't replace devs, devs using ai will replace those who don't",
            f"@{username}: molt is cracked. this bot understands me better than i do",
        ],
        "tech": [
            f"@{username}: shipped v2.0. features: fewer bugs, more features",
            f"@{username}: api latency down 40%. optimization season",
            f"@{username}: refactored the whole backend. technical debt: paid",
            f"@{username}: documentation is code. change my mind",
            f"@{username}: stack: next.js + supabase + claude. unstoppable",
        ],
        "memes": [
            f"@{username}: lmfao this market. literally can't lose (except money)",
            f"@{username}: based and redpilled. fr fr",
            f"@{username}: narrator: it was not fine. narrator: actually it was",
            f"@{username}: my brain on crypto vs my brain on ai. different person",
            f"@{username}: this is the way. gm",
        ],
        "trading": [
            f"@{username}: entered at support. let's see how this plays out",
            f"@{username}: stop loss hit. on to the next one. gn",
            f"@{username}: green day. taking profits. honestly",
            f"@{username}: portfolio up 5%. treating myself to something",
            f"@{username}: risk management is everything. learned the hard way",
        ],
    }

    tweets = []
    for i in range(min(count, 50)):
        topic = random.choice(base_topics)
        templates = sample_templates[topic]
        text = random.choice(templates)
        is_qt = random.random() < 0.3
        tweets.append({"text": text, "is_qt": is_qt})

    return tweets


def analyze_length_patterns(tweets: List[Dict]) -> Dict[str, Any]:
    """分析推文长度分布"""
    lengths = [len(t["text"]) for t in tweets if "text" in t]

    if not lengths:
        return {"avg_length": 0, "distribution": {"short": 0, "medium": 0, "long": 0}}

    avg = sum(lengths) / len(lengths)
    short = sum(1 for l in lengths if l < 80) / len(lengths)
    medium = sum(1 for l in lengths if 80 <= l < 200) / len(lengths)
    long_term = sum(1 for l in lengths if l >= 200) / len(lengths)

    return {
        "avg_length": int(avg),
        "distribution": {
            "short": round(short, 2),
            "medium": round(medium, 2),
            "long": round(long_term, 2),
        },
    }


def analyze_tone(tweets: List[Dict]) -> Dict[str, Any]:
    """检测语气特征"""
    texts = [t["text"].lower() for t in tweets if "text" in t]
    all_text = " ".join(texts)

    humor_words = ["lmao", "lol", "lmfao", "fr", "bro", "man"]
    humor_count = sum(all_text.count(word) for word in humor_words)

    self_dep = ["bags", "down", "lost", "liquidated", "rug"]
    self_dep_count = sum(all_text.count(phrase) for phrase in self_dep)

    sarcasm = ["this is fine", "narrator:", "honestly", "unpopular"]
    sarcasm_count = sum(all_text.count(phrase) for phrase in sarcasm)

    edge_markers = ["based", "fr fr", "hot take"]
    edge_count = sum(all_text.count(phrase) for phrase in edge_markers)

    return {
        "humor_level": "high"
        if humor_count > len(tweets) * 0.3
        else "medium"
        if humor_count > 0.1
        else "low",
        "self_deprecating": self_dep_count > 0,
        "sarcastic": sarcasm_count > 0,
        "edgy": edge_count > 0,
    }


def extract_topics(tweets: List[Dict]) -> List[str]:
    """提取主要话题"""
    texts = [t["text"].lower() for t in tweets if "text" in t]
    all_text = " ".join(texts)

    topic_keywords = {
        "crypto": ["btc", "crypto", "eth", "bitcoin", "defi", "pump", "rug", "bags"],
        "ai": ["ai", "agent", "claude", "gpt", "llm", "molt", "autonomous"],
        "trading": ["trading", "portfolio", "buy", "sell", "entry", "stop loss"],
        "memes": ["lmao", "fr", "based", "meme", "gm"],
        "tech": ["dev", "code", "api", "shipped", "build"],
    }

    topics = []
    for topic, keywords in topic_keywords.items():
        if sum(all_text.count(kw) for kw in keywords) > len(tweets) * 0.1:
            topics.append(topic)

    return topics[:5]


def analyze_engagement_type(tweets: List[Dict]) -> str:
    """确定主要互动模式"""
    qt_count = sum(1 for t in tweets if t.get("is_qt", False))
    qt_ratio = qt_count / len(tweets) if tweets else 0

    if qt_ratio > 0.5:
        return "reactive QT heavy"
    elif qt_ratio > 0.2:
        return "mixed original and QT"
    else:
        return "original content focused"


def extract_signature_phrases(tweets: List[Dict]) -> List[str]:
    """查找重复短语"""
    texts = [t["text"].lower() for t in tweets if "text" in t]

    candidates = ["lmao", "fr", "bro", "based", "honestly", "gm", "gn", "ser", "fren"]

    found = []
    for phrase in candidates:
        count = sum(text.count(phrase) for text in texts)
        if count >= 2:
            found.append(phrase)

    return found[:10]


def analyze_style(tweets: List[Dict]) -> Dict[str, Any]:
    """分析写作风格"""
    texts = [t["text"] for t in tweets if "text" in t]

    lowercase_count = sum(1 for t in texts if t and t[0].islower())
    lowercase_ratio = lowercase_count / len(texts) if texts else 0

    return {
        "emoji_usage": "minimal",
        "capitalization": "mostly lowercase" if lowercase_ratio > 0.6 else "mixed",
        "punctuation": "casual",
    }


def create_voice_profile(username: str, tweets: List[Dict]) -> Dict[str, Any]:
    """创建综合声音画像"""

    length = analyze_length_patterns(tweets)
    tone = analyze_tone(tweets)
    topics = extract_topics(tweets)
    engagement = analyze_engagement_type(tweets)
    phrases = extract_signature_phrases(tweets)
    style = analyze_style(tweets)

    uses_threads = any(len(t.get("text", "")) > 240 for t in tweets)

    return {
        "account": username,
        "analyzed_tweets": len(tweets),
        "patterns": {
            **length,
            "uses_threads": uses_threads,
            "tone": tone,
            "topics": topics,
            "engagement_type": engagement,
            "signature_phrases": phrases,
            "style": style,
        },
        "sample_tweets": [t["text"] for t in tweets[:5] if "text" in t],
    }


def execute(username: str, tweet_count: int = 50) -> str:
    """
    分析 Twitter 账户的声音特征

    Args:
        username: 要分析的 Twitter 用户名
        tweet_count: 要分析的推文数量

    Returns:
        格式化的声音画像
    """
    if not username.startswith("@"):
        username = f"@{username}"

    tweets = generate_mock_tweets(username, tweet_count)
    profile = create_voice_profile(username, tweets)

    patterns = profile["patterns"]

    output = f"# Voice Profile: {username}\n\n"
    output += f"**Analyzed Tweets:** {profile['analyzed_tweets']}\n\n"

    output += "## Voice Characteristics\n\n"
    output += f"- **Average Length:** {patterns['avg_length']} characters\n"
    output += f"- **Length Distribution:** {patterns['distribution']}\n"
    output += f"- **Uses Threads:** {patterns['uses_threads']}\n"
    output += f"- **Engagement Type:** {patterns['engagement_type']}\n\n"

    output += "## Tone\n\n"
    tone = patterns["tone"]
    output += f"- Humor Level: {tone['humor_level']}\n"
    output += f"- Self-Deprecating: {tone['self_deprecating']}\n"
    output += f"- Sarcastic: {tone['sarcastic']}\n"
    output += f"- Edgy: {tone['edgy']}\n\n"

    output += "## Topics\n\n"
    output += f"{', '.join(patterns['topics'])}\n\n"

    output += "## Signature Phrases\n\n"
    output += f"{', '.join(patterns['signature_phrases'])}\n\n"

    output += "## Style\n\n"
    style = patterns["style"]
    output += f"- Capitalization: {style['capitalization']}\n"
    output += f"- Emoji Usage: {style['emoji_usage']}\n"
    output += f"- Punctuation: {style['punctuation']}\n\n"

    output += "## Sample Tweets\n\n"
    for i, tweet in enumerate(profile["sample_tweets"], 1):
        output += f"{i}. {tweet}\n"

    output += "\n---\n\n"
    output += "**Note:** This is a mock voice profile for demonstration. "
    output += (
        "In production, this would fetch real tweets via Bird CLI and perform actual analysis."
    )

    return output


if __name__ == "__main__":
    print(execute("gravyxbt_", 30))
