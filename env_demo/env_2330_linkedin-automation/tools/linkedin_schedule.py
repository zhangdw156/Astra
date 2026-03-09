"""
LinkedIn Schedule Tool - Schedule posts for later

This tool provides instructions to schedule LinkedIn posts using OpenClaw cron.
"""

TOOL_SCHEMA = {
    "name": "linkedin_schedule",
    "description": "Schedule a LinkedIn post for future publication. "
    "Use with OpenClaw cron to automate posting at optimal times.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The post content to schedule"},
            "schedule_time": {
                "type": "string",
                "description": "When to post (YYYY-MM-DD HH:MM format, UTC)",
            },
            "image_path": {"type": "string", "description": "Optional: Path to an image to attach"},
        },
        "required": ["content", "schedule_time"],
    },
}


def execute(content: str, schedule_time: str, image_path: str = None) -> str:
    """
    Generate instructions for scheduling a LinkedIn post.

    Args:
        content: The post content
        schedule_time: When to post (YYYY-MM-DD HH:MM UTC)
        image_path: Optional image path

    Returns:
        Instructions for scheduling
    """
    fmt_image = f"**Image:** {image_path}" if image_path else ""

    output = f"""## LinkedIn Scheduled Post

### Post Details:
- **Scheduled Time:** {schedule_time} (UTC)
- **Content:**
---
{content}
---
{fmt_image}

---

## How to Schedule in OpenClaw

Use the cron tool with an "at" schedule:

```json
{{
  "schedule": {{
    "kind": "at",
    "atMs": <timestamp_for_{schedule_time}>
  }},
  "payload": {{
    "kind": "systemEvent",
    "text": "Post to LinkedIn now: {content}"
  }},
  "sessionTarget": "main"
}}
```

### For Recurring Posts (cron expression):

- **Daily at 9am:** "0 9 * * *"
- **Weekdays at 9am:** "0 9 * * 1-5"
- **Mon/Wed/Fri at 2pm:** "0 14 * * 1,3,5"

---

## Convert Time to Unix Timestamp

```bash
date -d "{schedule_time}" +%s000
```

This gives milliseconds since epoch (required for OpenClaw cron).

---

## Alternative: Save for Manual Posting

Since LinkedIn doesn't have native scheduling, save the content and use the linkedin_post tool at the scheduled time.

### Quick Setup:
1. Store this content in your content calendar
2. Set a reminder for {schedule_time}
3. At scheduled time, use linkedin_post tool to publish

---

## Tips:
- Keep a content calendar and schedule a week at a time
- Schedule during peak engagement hours (Tue-Thu, 8-10am local time)
- Leave buffer time for review before posting

"""

    return output


if __name__ == "__main__":
    print(execute("Hello LinkedIn!", "2026-01-31 09:00"))
