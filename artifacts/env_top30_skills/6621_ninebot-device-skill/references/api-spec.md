# Ninebot Vehicle Query – API Assumptions (PLACEHOLDER)

> ⚠️ This file is a **placeholder** API spec for development. Replace with real endpoints/fields once available.

## Base URL

```
https://api.example.com
```

## Auth & Token

### 1) Login (openClaw)
- **Method:** POST
- **Path:** `/v3/openClaw/user/login`
- **Headers:**
  - `Content-Type: application/json`
- **Request JSON:**

```json
{
  "username": "<email/phone/username>",
  "password": "<password>"
}
```

- **Response JSON (example):**
```json
{
  "resultCode": "90000",
  "resultDesc": "success",
  "data": {
    "access_token": "TOKEN_VALUE",
    "refresh_token": "REFRESH_TOKEN"
  }
}
```

**Token path:** `data.access_token`

### 2) Device List (AI)
- **Method:** POST
- **Path:** `/app-api/inner/device/ai/get-device-list`
- **Params (JSON):**
  - `access_token` (user token)
  - `lang` (`zh` | `zh-hant` | `en`)
- **Response JSON (example):**
```json
{
  "code": 1,
  "desc": "成功",
  "data": [
    {"sn": "N4DEC2336J0022", "deviceName": "九号电动呢", "img": "..."},
    {"sn": "23DDB2521J0001", "deviceName": "M3 王者荣耀裴擒虎款", "img": "..."}
  ],
  "t": 1773140131339
}
```

**Devices path:** `data`  
**Device fields:** `sn`, `deviceName`

### 3) Device Dynamic Info (AI)
- **Method:** POST
- **Path:** `/app-api/inner/device/ai/get-device-dynamic-info`
- **Params (JSON):**
  - `access_token` (user token)
  - `sn` (device sn)
- **Response JSON (example):**
```json
{
  "code": 1,
  "desc": "Successfully",
  "data": {
    "gsm": 19,
    "gsmTime": 1773131197,
    "pwr": 1,
    "dumpEnergy": 57,
    "estimateMileage": 50.4,
    "locationInfo": {"locationDesc": "北京市海淀区东升(地区)镇后屯东路"},
    "chargingState": 0,
    "powerStatus": 1,
    "remainChargeTime": null,
    "wnumber": "4MDAZ2606J0012"
  },
  "t": 1773131267279
}
```

**Battery path:** `data.dumpEnergy`  
**Status path:** `data.powerStatus`  
**Location path:** `data.locationInfo.locationDesc`

---

## Config Mapping (for scripts/ninebot_query.py)

You can override any field via a JSON config file:

```json
{
  "base_url": "https://api.example.com",
  "login": {
    "method": "POST",
    "path": "/v3/openClaw/user/login",
    "payload": {"username": "{username}", "password": "{password}"},
    "token_path": "data.access_token"
  },
  "devices": {
    "method": "POST",
    "path": "/app-api/inner/device/ai/get-device-list",
    "payload": {"access_token": "{token}", "lang": "{lang}"},
    "list_path": "data",
    "sn_field": "sn",
    "name_field": "deviceName"
  },
  "device_info": {
    "method": "POST",
    "path": "/app-api/inner/device/ai/get-device-dynamic-info",
    "payload": {"access_token": "{token}", "sn": "{sn}"},
    "battery_path": "data.dumpEnergy",
    "status_path": "data.powerStatus",
    "location_path": "data.locationInfo.locationDesc",
    "extra_fields": {
      "estimateMileage": "data.estimateMileage",
      "chargingState": "data.chargingState",
      "pwr": "data.pwr",
      "gsm": "data.gsm"
    }
  }
}
```
