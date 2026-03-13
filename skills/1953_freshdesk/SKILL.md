---
name: freshdesk
description: "Freshdesk helpdesk — manage tickets, contacts, companies, and agents via REST API"
homepage: https://www.agxntsix.ai
license: MIT
compatibility: Python 3.10+ (stdlib only — no dependencies)
metadata: {"openclaw": {"emoji": "🆘", "requires": {"env": ["FRESHDESK_API_KEY", "FRESHDESK_DOMAIN"]}, "primaryEnv": "FRESHDESK_API_KEY", "homepage": "https://www.agxntsix.ai"}}
---

# 🆘 Freshdesk

Freshdesk helpdesk — manage tickets, contacts, companies, and agents via REST API

## Requirements

| Variable | Required | Description |
|----------|----------|-------------|
| `FRESHDESK_API_KEY` | ✅ | API key |
| `FRESHDESK_DOMAIN` | ✅ | Domain (yourcompany.freshdesk.com) |

## Quick Start

```bash
# List tickets
python3 {{baseDir}}/scripts/freshdesk.py tickets --filter <value> --email <value>

# Get ticket
python3 {{baseDir}}/scripts/freshdesk.py ticket-get id <value>

# Create ticket
python3 {{baseDir}}/scripts/freshdesk.py ticket-create --subject <value> --description <value> --email <value> --priority <value> --status <value>

# Update ticket
python3 {{baseDir}}/scripts/freshdesk.py ticket-update id <value> --status <value> --priority <value>

# Delete ticket
python3 {{baseDir}}/scripts/freshdesk.py ticket-delete id <value>

# Reply to ticket
python3 {{baseDir}}/scripts/freshdesk.py ticket-reply id <value> --body <value>

# Add note
python3 {{baseDir}}/scripts/freshdesk.py ticket-note id <value> --body <value>

# List conversations
python3 {{baseDir}}/scripts/freshdesk.py conversations id <value>
```

## All Commands

| Command | Description |
|---------|-------------|
| `tickets` | List tickets |
| `ticket-get` | Get ticket |
| `ticket-create` | Create ticket |
| `ticket-update` | Update ticket |
| `ticket-delete` | Delete ticket |
| `ticket-reply` | Reply to ticket |
| `ticket-note` | Add note |
| `conversations` | List conversations |
| `contacts` | List contacts |
| `contact-get` | Get contact |
| `contact-create` | Create contact |
| `companies` | List companies |
| `agents` | List agents |
| `groups` | List groups |
| `roles` | List roles |
| `products` | List products |
| `satisfaction-ratings` | List CSAT |
| `time-entries` | Ticket time entries |

## Output Format

All commands output JSON by default. Add `--human` for readable formatted output.

```bash
python3 {{baseDir}}/scripts/freshdesk.py <command> --human
```

## Script Reference

| Script | Description |
|--------|-------------|
| `{{baseDir}}/scripts/freshdesk.py` | Main CLI — all commands in one tool |

## Credits
Built by [M. Abidi](https://www.linkedin.com/in/mohammad-ali-abidi) | [agxntsix.ai](https://www.agxntsix.ai)
[YouTube](https://youtube.com/@aiwithabidi) | [GitHub](https://github.com/aiwithabidi)
Part of the **AgxntSix Skill Suite** for OpenClaw agents.

📅 **Need help setting up OpenClaw for your business?** [Book a free consultation](https://cal.com/agxntsix/abidi-openclaw)
