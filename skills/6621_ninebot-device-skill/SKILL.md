---
name: ninebot-device-skill
description: Query Ninebot electric vehicle status via API login + device list + device detail flow. Use when users ask about remaining battery, vehicle status, or location of their Ninebot scooters/bikes, or when an agent needs to authenticate and select a device from a user account.
---

# Ninebot Vehicle Query

## Overview
Provide a reliable workflow to authenticate a Ninebot user, list their devices, select a device, and fetch key status fields (battery, status, location). Includes a ready-to-run script with a configurable API mapping.

## Workflow (Login → Device List → Device Info)

### 1) Gather required inputs
- User credentials (username + password)
- Login requires only username + password (no signature for now)
- Optional: preferred device name or SN
- Optional: a config file that maps the real API fields/paths

### 2) Run the query script
Use the bundled script to execute the flow end-to-end:

```bash
python3 scripts/ninebot_query.py \
  --username "USER" \
  --password "PASS" \
  --lang "zh" \
  --device-name "小九"
```

If the account has multiple devices and no selection was provided, the script returns a list for the user to choose:

```json
{"choose_device": [{"sn":"SN123","name":"小九"},{"sn":"SN456","name":"小白"}]}
```

Then re-run with `--device-name` or `--device-sn`.

### 3) Output interpretation
The script outputs JSON:

```json
{
  "device_name": "九号电动E200P",
  "sn": "************",
  "battery": 57,
  "status": 1,
  "location": "北京市海淀区东升(地区)镇后屯东路",
  "estimateMileage": 50.4,
  "chargingState": 0,
  "pwr": 1,
  "gsm": 19
}
```

### 4) API wiring (when real endpoints are ready)
Update API mapping in one of two ways:
- **Edit the config JSON** and pass it via `--config`
- **Edit references/api-spec.md** and mirror those changes into a config JSON

Config schema is documented in `references/api-spec.md`.

## Guidance for Real APIs
- If the auth header or token path is different, update `auth_header`, `auth_prefix`, and `token_path`.
- If device list or device info fields differ, update `list_path`, `sn_field`, `name_field`, and the `battery/status/location` paths.
- Keep the script output stable for downstream integrations.

## Resources

### scripts/
- `ninebot_query.py` — end-to-end login → list → info workflow (supports `--mock` for placeholder data).

### references/
- `api-spec.md` — placeholder API spec + config mapping template.
