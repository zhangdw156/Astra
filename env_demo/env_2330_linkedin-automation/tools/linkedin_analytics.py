"""
LinkedIn Analytics Tool - Get engagement statistics

This tool provides browser automation instructions to fetch LinkedIn analytics data.
"""

TOOL_SCHEMA = {
    "name": "linkedin_analytics",
    "description": "Get LinkedIn analytics for your profile and posts. "
    "Extracts impressions, engagement rates, profile views, and follower growth.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "default": 7,
                "description": "Number of days to analyze (default: 7)",
            }
        },
    },
}


def execute(days: int = 7) -> str:
    """
    Generate browser automation instructions to get LinkedIn analytics.

    Args:
        days: Number of days to analyze

    Returns:
        Step-by-step browser instructions for fetching analytics
    """
    output = f"""## LinkedIn Analytics Workflow

### Parameters:
- Analysis period: Last {days} days

### Browser Automation Steps:

1. **Navigate to LinkedIn Analytics**
   - URL: https://www.linkedin.com/analytics/creator/
   - Wait for dashboard to load

2. **Extract Dashboard Metrics:**
   - **Impressions**: Total views of your content
   - **Engagements**: Total likes + comments + shares
   - **Profile views**: Number of profile visitors
   - **Follower count**: Current total followers
   - **Search appearances**: How often you appear in searches

3. **Navigate to Posts Section**
   - URL: https://www.linkedin.com/in/me/recent-activity/all/
   - Extract metrics for each post:
     - Post date
     - Impressions
     - Reactions count
     - Comments count
     - Reposts/shares count

4. **Calculate Metrics:**
   - Engagement rate = (reactions + comments + reposts) / impressions * 100
   - Average engagement per post
   - Best performing post (highest engagement rate)
   - Best posting time (based on top performers)

5. **Return Structured Data:**
```json
{{
  "period": "{days} days",
  "totalImpressions": <number>,
  "totalEngagements": <number>,
  "engagementRate": "<percentage>",
  "followerChange": "<+/- number>",
  "profileViews": <number>,
  "topPost": {{
    "content": "<preview>",
    "impressions": <number>,
    "engagementRate": "<percentage>"
  }},
  "posts": [...]
}}
```

### Tips:
- Run weekly to track trends
- Compare different time periods
- Identify content that performs best

"""
    return output


if __name__ == "__main__":
    print(execute(7))
