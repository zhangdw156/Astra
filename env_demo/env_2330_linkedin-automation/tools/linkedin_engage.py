"""
LinkedIn Engagement Tool - Engage with posts in feed

This tool provides browser automation instructions to like and comment on posts.
"""

TOOL_SCHEMA = {
    "name": "linkedin_engage",
    "description": "Engage with posts in your LinkedIn feed by liking and commenting. "
    "Use to build network engagement and grow your LinkedIn presence.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of posts to engage with (default: 10)",
            },
            "topic": {"type": "string", "description": "Optional: Filter posts by keyword/topic"},
        },
    },
}


def execute(limit: int = 10, topic: str = None) -> str:
    """
    Generate browser automation instructions for engagement.

    Args:
        limit: Number of posts to engage with
        topic: Optional topic filter

    Returns:
        Step-by-step browser instructions for engagement
    """
    topic_filter = f"- Containing keyword: {topic}" if topic else ""

    output = f"""## LinkedIn Engagement Workflow

### Parameters:
- Engage with up to {limit} posts
{topic_filter}

### Browser Automation Steps:

1. **Navigate to LinkedIn Feed**
   - URL: https://www.linkedin.com/feed/
   - Wait for feed to load

2. **Scroll through feed and identify high-quality posts:**
   - From people in your network
   - Related to your industry/interests
   {topic_filter}

3. **For each qualifying post (up to {limit}):**

   a) **Like the post** (always do this)
      - Click the Like button (thumbs up icon)
      - Or use reactions: Celebrate, Love, Insightful

   b) **Leave a thoughtful comment** (on best posts)
      - Add value, not just "Great post!"
      - Ask a question
      - Share your experience
      - Disagree respectfully (engagement gold)

4. **Track engagement:**
   - Note who you engaged with
   - They'll likely reciprocate
   - Builds algorithm favor for your content

---

## Comment Templates

### Adding perspective:
> "This resonates. In my experience, [related insight]. Have you found [question]?"

### Respectful disagreement:
> "Interesting take. I'd push back slightly on [point] because [reason]. What do you think about [alternative]?"

### Asking questions:
> "Love this. Curious - how did you handle [specific challenge] when [scenario]?"

### Sharing experience:
> "Went through something similar. The game-changer for me was [insight]. [Brief elaboration]."

---

## Best Practices

✅ Engage with posts 1-3 hours old (algorithm boost)
✅ Mix reactions (don't just Like everything)
✅ Comment on posts from people slightly ahead of you
✅ Reply to comments on your own posts within 1 hour
✅ Engage before AND after posting your own content

❌ Don't comment "Great post!" (looks like a bot)
❌ Don't mass-like 50 posts in 2 minutes
❌ Don't only engage with huge accounts
❌ Don't copy-paste the same comment

---

## Rate Limits:
- **Comments:** 20-30 per day max
- **Likes:** 100 per day max
- Space out engagement over several hours

"""
    return output


if __name__ == "__main__":
    print(execute(10, "tech"))
