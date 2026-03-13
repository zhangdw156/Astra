#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ninebot vehicle query (placeholder workflow).
- Login -> get token
- List devices -> pick device by name or sn
- Query device info -> battery/status/location

Config is overridable via --config (JSON). See references/api-spec.md.
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
from typing import Any, Dict

DEFAULT_CONFIG = {
    "base_url": "https://api-passport-bj.ninebot.com",
    "login": {
        "base_url": "https://api-passport-bj.ninebot.com",
        "method": "POST",
        "path": "/v3/openClaw/user/login",
        "payload": {"username": "{username}", "password": "{password}"},
        "token_path": "data.access_token",
    },
    "devices": {
        "base_url": "https://cn-cbu-gateway.ninebot.com",
        "method": "POST",
        "path": "/app-api/inner/device/ai/get-device-list",
        "payload": {"access_token": "{token}", "lang": "{lang}"},
        "list_path": "data",
        "sn_field": "sn",
        "name_field": "deviceName",
    },
    "device_info": {
        "base_url": "https://cn-cbu-gateway.ninebot.com",
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
            "gsm": "data.gsm",
        },
    },
}

MOCK_DATA = {
    "token": "MOCK_TOKEN",
    "devices": [
        {"sn": "SN123", "name": "小九"},
        {"sn": "SN456", "name": "小白"},
    ],
    "device_info": {
        "battery": 78,
        "status": "LOCKED",
        "location": {"lat": 31.2304, "lng": 121.4737, "address": "上海市黄浦区"},
    },
}


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def deep_get(data: Dict[str, Any], path: str) -> Any:
    """Get value by dot path (e.g., data.token)."""
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def get_base_url(cfg: Dict[str, Any], section: str) -> str:
    section_url = (cfg.get(section) or {}).get("base_url")
    if section_url:
        return section_url
    return cfg.get("base_url", "")


def http_request(
    method: str,
    url: str,
    headers: Dict[str, str] = None,
    payload: Dict[str, Any] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    headers = headers or {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if debug:
            try:
                body = err.read().decode("utf-8")
            except Exception:
                body = None
            print(
                json.dumps(
                    {"http_error": {"url": url, "status": err.code, "body": body, "headers": headers, "payload": payload}},
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
        raise


def login(cfg: Dict[str, Any], username: str, password: str, mock: bool, debug: bool) -> str:
    if mock:
        return MOCK_DATA["token"]
    payload_template = cfg["login"]["payload"]
    payload = {
        k: (v.format(username=username, password=password) if isinstance(v, str) else v)
        for k, v in payload_template.items()
    }
    url = get_base_url(cfg, "login").rstrip("/") + cfg["login"]["path"]
    headers = {
        "clientId": "open_claw_client",
        "timestamp": str(int(time.time() * 1000)),
        "Content-Type": "application/json",
    }
    res = http_request(cfg["login"]["method"], url, headers=headers, payload=payload, debug=debug)
    token = deep_get(res, cfg["login"]["token_path"])
    if not token:
        if debug:
            print(json.dumps({"login_response": res}, ensure_ascii=False), file=sys.stderr)
        if isinstance(res, dict):
            result_code = res.get("resultCode") or res.get("code")
            result_desc = res.get("resultDesc") or res.get("desc")
            if result_code or result_desc:
                raise RuntimeError(f"Token not found in login response (code={result_code}, desc={result_desc})")
        raise RuntimeError("Token not found in login response")

    #print(json.dumps({"token": token}, ensure_ascii=False), file=sys.stderr)
    return token


def list_devices(cfg: Dict[str, Any], token: str, lang: str, mock: bool, debug: bool):
    if mock:
        return MOCK_DATA["devices"]
    url = get_base_url(cfg, "devices").rstrip("/") + cfg["devices"]["path"]
    payload_tpl = cfg["devices"].get("payload") or {}
    payload = {
        k: (v.format(token=token, lang=lang) if isinstance(v, str) else v)
        for k, v in payload_tpl.items()
    }
    headers = {
        #"clientId": "open_claw_client",
        #"timestamp": str(int(time.time() * 1000)),
        #"Content-Type": "application/json",
        #"clientParam": "a23HXtRwKLGk7nVA",
    }
    res = http_request(cfg["devices"]["method"], url, headers=headers, payload=payload, debug=debug)
    print(json.dumps({"list_devices_response": res}, ensure_ascii=False), file=sys.stderr)
    devices = deep_get(res, cfg["devices"]["list_path"]) or []
    return devices


def get_device_info(cfg: Dict[str, Any], token: str, sn: str, mock: bool, debug: bool):
    if mock:
        return MOCK_DATA["device_info"]
    path = cfg["device_info"]["path"].replace("{sn}", urllib.parse.quote(sn))
    url = get_base_url(cfg, "device_info").rstrip("/") + path
    payload_tpl = cfg["device_info"].get("payload") or {}
    payload = {
        k: (v.format(token=token, sn=sn) if isinstance(v, str) else v)
        for k, v in payload_tpl.items()
    }
    headers = {
        #"clientId": "open_claw_client",
        #"timestamp": str(int(time.time() * 1000)),
        #"Content-Type": "application/json",
        #"clientParam": "a23HXtRwKLGk7nVA",
    }
    res = http_request(cfg["device_info"]["method"], url, headers=headers, payload=payload, debug=debug)
    out = {
        "battery": deep_get(res, cfg["device_info"]["battery_path"]),
        "status": deep_get(res, cfg["device_info"]["status_path"]),
        "location": deep_get(res, cfg["device_info"]["location_path"]),
    }
    extra = cfg["device_info"].get("extra_fields") or {}
    for k, path in extra.items():
        out[k] = deep_get(res, path)
    return out


def main():
    parser = argparse.ArgumentParser(description="Ninebot vehicle query (placeholder).")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--device-name", default=None, help="Device name to select")
    parser.add_argument("--device-sn", default=None, help="Device SN to select")
    parser.add_argument("--config", default=None, help="Path to JSON config")
    parser.add_argument("--lang", default="zh", help="Language: zh | zh-hant | en")
    parser.add_argument("--mock", action="store_true", help="Use mock data")
    parser.add_argument("--debug", action="store_true", help="Print API responses on error")
    args = parser.parse_args()

    cfg = DEFAULT_CONFIG
    if args.config:
        cfg = load_config(args.config)

    token = login(cfg, args.username, args.password, args.mock, args.debug)
    devices = list_devices(cfg, token, args.lang, args.mock, args.debug)

    if not devices:
        print(json.dumps({"error": "No devices found"}, ensure_ascii=False))
        sys.exit(2)

    selected = None
    if args.device_sn:
        for d in devices:
            if str(d.get(cfg["devices"]["sn_field"])) == args.device_sn:
                selected = d
                break
    elif args.device_name:
        for d in devices:
            if str(d.get(cfg["devices"]["name_field"])) == args.device_name:
                selected = d
                break
    else:
        # If multiple devices, return list for caller to decide
        if len(devices) > 1:
            print(json.dumps({"choose_device": devices}, ensure_ascii=False))
            sys.exit(3)
        selected = devices[0]

    if not selected:
        print(json.dumps({"error": "Device not found", "devices": devices}, ensure_ascii=False))
        sys.exit(4)

    sn = str(selected.get(cfg["devices"]["sn_field"]))
    name = selected.get(cfg["devices"]["name_field"]) or ""
    info = get_device_info(cfg, token, sn, args.mock, args.debug)

    output = {
        "device_name": name,
        "sn": sn,
        "battery": info.get("battery"),
        "status": info.get("status"),
        "location": info.get("location"),
        "estimateMileage": info.get("estimateMileage"),
        "chargingState": info.get("chargingState"),
        "pwr": info.get("pwr"),
        "gsm": info.get("gsm"),
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
