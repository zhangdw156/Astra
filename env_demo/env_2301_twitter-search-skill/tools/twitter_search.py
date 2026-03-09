"""
Twitter Search Tool - Search and analyze Twitter data

Searches Twitter using the TwitterAPI.io advanced search endpoint,
fetches tweets, and returns comprehensive analysis with statistics.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "twitter_search",
    "description": "Search Twitter for keywords using advanced search syntax and analyze results. "
    "Supports query parameters like 'from:user', 'since:date', 'lang:en', '#hashtag', etc. "
    "Returns tweets with engagement metrics, author info, hashtags, and statistical analysis. "
    "Use this when user requests social media search, tweet analysis, trend detection, "
    "influencer identification, or any Twitter/X data gathering task.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query using Twitter advanced search syntax (e.g., 'AI', 'from:elonmusk', '#AI lang:en', 'Bitcoin since:2024-01-01')",
            },
            "max_results": {
                "type": "integer",
                "default": 100,
                "description": "Maximum number of tweets to fetch (default: 100, max: 1000)",
            },
            "query_type": {
                "type": "string",
                "enum": ["Top", "Latest"],
                "default": "Top",
                "description": "Query type: 'Top' for most relevant, 'Latest' for most recent",
            },
        },
        "required": ["query"],
    },
}

TWITTER_API_BASE = os.environ.get("TWITTER_API_BASE", "http://localhost:8003")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "mock-api-key")


def execute(query: str, max_results: int = 100, query_type: str = "Top") -> str:
    """
    Search Twitter and return analysis results

    Args:
        query: Search query string with Twitter syntax
        max_results: Maximum number of tweets to fetch
        query_type: 'Top' or 'Latest'

    Returns:
        Formatted analysis report with tweets and statistics
    """
    if max_results > 1000:
        max_results = 1000
    if max_results < 1:
        max_results = 1

    output = f"## Twitter Search Results: {query}\n\n"

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{TWITTER_API_BASE}/twitter/tweet/advanced_search?query={encoded_query}&queryType={query_type}&max_results={max_results}"

        request = urllib.request.Request(url)
        request.add_header("X-API-Key", TWITTER_API_KEY)

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        tweets = data.get("tweets", [])

        if not tweets:
            output += "No tweets found for this query.\n"
            return output

        output += f"**Total tweets found:** {len(tweets)}\n\n"

        output += "### Key Metrics\n\n"

        total_likes = sum(t.get("likeCount", 0) for t in tweets)
        total_retweets = sum(t.get("retweetCount", 0) for t in tweets)
        total_replies = sum(t.get("replyCount", 0) for t in tweets)
        total_views = sum(t.get("viewCount", 0) for t in tweets)

        output += f"- **Total Likes:** {total_likes:,}\n"
        output += f"- **Total Retweets:** {total_retweets:,}\n"
        output += f"- **Total Replies:** {total_replies:,}\n"
        output += f"- **Total Views:** {total_views:,}\n"
        output += f"- **Avg Likes per Tweet:** {total_likes / len(tweets):.1f}\n"
        output += f"- **Avg Retweets per Tweet:** {total_retweets / len(tweets):.1f}\n\n"

        output += "### Top Tweets by Engagement\n\n"

        sorted_tweets = sorted(
            tweets, key=lambda t: t.get("likeCount", 0) + t.get("retweetCount", 0), reverse=True
        )

        for i, tweet in enumerate(sorted_tweets[:5], 1):
            author = tweet.get("author", {})
            text = tweet.get("text", "")[:200]
            if len(tweet.get("text", "")) > 200:
                text += "..."

            output += f"**{i}.** {text}\n"
            output += f"   - Likes: {tweet.get('likeCount', 0):,} | Retweets: {tweet.get('retweetCount', 0):,} | Replies: {tweet.get('replyCount', 0):,}\n"
            output += f"   - Author: @{author.get('userName', 'unknown')} ({author.get('followers', 0):,} followers)\n"
            output += f"   - [View Tweet]({tweet.get('url', '')})\n\n"

        all_hashtags = []
        for t in tweets:
            for h in t.get("entities", {}).get("hashtags", []):
                all_hashtags.append(h.get("text", ""))

        if all_hashtags:
            hashtag_counts = {}
            for tag in all_hashtags:
                hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1

            top_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            output += "### Top Hashtags\n\n"
            for tag, count in top_hashtags:
                output += f"- **#{tag}**: {count} tweets\n"
            output += "\n"

        authors = {}
        for t in tweets:
            username = t.get("author", {}).get("userName")
            if username:
                if username not in authors:
                    authors[username] = {
                        "name": t.get("author", {}).get("name"),
                        "followers": t.get("author", {}).get("followers", 0),
                        "tweet_count": 0,
                        "verified": t.get("author", {}).get("isBlueVerified", False),
                    }
                authors[username]["tweet_count"] += 1

        top_authors = sorted(authors.values(), key=lambda x: x["followers"], reverse=True)[:5]

        output += "### Top Authors by Followers\n\n"
        for author in top_authors:
            verified_badge = " [Verified]" if author.get("verified") else ""
            output += f"- **@{author.get('name', 'unknown')}**{verified_badge}: {author.get('followers', 0):,} followers, {author.get('tweet_count')} tweets\n"
        output += "\n"

        output += "### Analysis Summary\n\n"
        output += f"- Query: `{query}`\n"
        output += f"- Query Type: {query_type}\n"
        output += f"- Results: {len(tweets)} tweets analyzed\n"
        output += (
            f"- Total Engagement: {total_likes + total_retweets + total_replies:,} interactions\n"
        )

    except Exception as e:
        output += f"**Error searching Twitter:** {str(e)}\n"
        output += "\nMake sure the Twitter API mock is running or set TWITTER_API_BASE to the real API endpoint.\n"

    return output


if __name__ == "__main__":
    print(execute("AI", max_results=10))
