"""
LinkedIn Post Tool - Post content to LinkedIn

This tool provides browser automation instructions to post content to LinkedIn.
"""

TOOL_SCHEMA = {
    "name": "linkedin_post",
    "description": "Post content to LinkedIn. Use this tool to create and publish a new post on LinkedIn. "
    "The tool returns step-by-step browser instructions that the agent should execute using the browser tool.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The post content/text to publish on LinkedIn",
            },
            "image_path": {
                "type": "string",
                "description": "Optional: Path to an image file to attach to the post",
            },
        },
        "required": ["content"],
    },
}


def execute(content: str, image_path: str = None) -> str:
    """
    Generate browser automation instructions to post content to LinkedIn.

    Args:
        content: The post content to publish
        image_path: Optional path to an image to attach

    Returns:
        Step-by-step browser instructions for posting
    """
    fmt_image = f"**Image:** {image_path}" if image_path else ""
    add_image_step = (
        f"""**Add image (if provided)**
   - Click the image/media icon in the post composer
   - Upload the image: {image_path}
   - Wait for image preview to appear"""
        if image_path
        else "**No image to add**"
    )

    output = f"""## LinkedIn Post Workflow

### Content to Post:
---
{content}
---
{fmt_image}

### Browser Automation Steps:

1. **Navigate to LinkedIn Feed**
   - URL: https://www.linkedin.com/feed/
   - Wait for page to fully load

2. **Click "Start a post" button**
   - Selector: `button[class*="share-box-feed-entry__trigger"]`
   - Or look for button with text "Start a post" or "Create post"

3. **Enter post content**
   - In the modal that opens, find the post editor:
   - Selector: `div.ql-editor[data-placeholder]` or `div[contenteditable="true"]`
   - Type/paste the content: {content}

4. {add_image_step}

5. **Click "Post" button to publish**
   - Selector: `button.share-actions__primary-action`
   - Or button with text "Post"
   - Wait for post to appear in feed (confirmation)

### Rate Limit Warning:
- LinkedIn enforces limits: **max 2-3 posts per day**
- Stay under this limit to avoid account restrictions

### Verification:
- After posting, verify the post appears in your feed
- Check for any rate limit warnings

"""

    return output


if __name__ == "__main__":
    print(execute("Hello LinkedIn! This is a test post."))
