"""
LinkedIn Content Ideas Generator

This tool provides content ideas and strategies for LinkedIn posts.
"""

TOOL_SCHEMA = {
    "name": "linkedin_ideas",
    "description": "Generate content ideas for LinkedIn based on topics or trending themes. "
    "Provides high-engagement post formats, hashtag strategies, and content calendars.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "default": "general",
                "description": "Topic or industry for content ideas (e.g., 'tech', 'leadership', 'marketing')",
            }
        },
    },
}


def execute(topic: str = "general") -> str:
    """
    Generate content ideas and strategies for LinkedIn.

    Args:
        topic: Topic or industry for content ideas

    Returns:
        Content ideas, formats, and strategies
    """
    output = f"""## LinkedIn Content Ideas: {topic}

### Research Steps (via browser):

1. **Check trending topics**
   - URL: https://www.linkedin.com/news/
   - Extract top 5 trending stories in your industry

2. **Analyze competitor content**
   - Visit top creators in your niche
   - Note their most engaged posts (sort by reactions)
   - Identify patterns in hooks, formats, topics

3. **Check hashtag performance**
   - Search relevant hashtags (#{topic}, #leadership, #tech, etc.)
   - Note which posts get high engagement

---

## High-Engagement Post Formats

### 1. The Contrarian Take
> "Unpopular opinion: [controversial but defensible stance]"
- Drives comments and debate

### 2. The Story Arc
> "3 years ago, I [struggle]. Today, I [success]. Here's what changed:"
- Personal stories get 3x engagement

### 3. The List Post
> "10 [lessons/tips/tools] I wish I knew [timeframe] ago:"
- Easy to consume, high saves

### 4. The Before/After
> "Before: [old way]. After: [new way]. The difference? [insight]"
- Clear transformation narrative

### 5. The Question Hook
> "What's the one skill that changed your career?"
- Drives comments

### 6. Hot Take + Data
> "[Bold claim]. Here's the data: [stats]"
- Credibility + controversy

---

## Content Calendar Template

| Day | Format | Topic |
|-----|--------|-------|
| Mon | Story | Personal lesson |
| Wed | List | Industry tips |
| Fri | Engagement | Question/poll |

---

## Hashtag Strategy for {topic}

**Primary (high reach):** #{topic} #innovation #leadership
**Secondary (niche):** #startup #founder #growthmindset
**Branded:** #YourCompanyName

**Use 3-5 hashtags per post. Place at end.**

---

## Best Practices

- Write compelling hooks in first 2 lines (hook stops scroll)
- Add value before asking for engagement
- Use line breaks and bullet points for readability
- Include a clear call-to-action
- Post during peak times (Tue-Thu, 8-10am local time)

"""
    return output


if __name__ == "__main__":
    print(execute("tech"))
