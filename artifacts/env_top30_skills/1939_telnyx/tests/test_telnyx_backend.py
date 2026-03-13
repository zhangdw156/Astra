from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_telnyx_backend_updates_messages_calls_and_numbers() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    sent = loaded.backend.call(
        "send_message",
        {"from": "+14155550100", "to": "+14155550777", "text": "Dispatching now"},
    )
    assert sent["data"]["id"] == "msg_2"

    call = loaded.backend.call(
        "create_call",
        {"from": "+14155550100", "to": "+14155550666", "connection_id": "conn_1"},
    )
    assert call["data"]["id"] == "call_2"

    hangup = loaded.backend.call("hangup_call", {"id": "call_2"})
    assert hangup["data"]["status"] == "completed"

    order = loaded.backend.call("order_number", {"phone_numbers": "[\"+14155550199\"]"})
    assert order["data"][0]["phone_number"] == "+14155550199"

    faxes = loaded.backend.call(
        "send_fax",
        {
            "from": "+14155550100",
            "to": "+14155550555",
            "media_url": "https://example.com/invoice.pdf",
        },
    )
    assert faxes["data"]["id"] == "fax_1"


def test_telnyx_backend_lists_fixture_state() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    listed = loaded.backend.call("list_numbers", {"page_size": 5})
    assert listed["data"][0]["phone_number"] == "+14155550100"

    searched = loaded.backend.call("search_numbers", {"country_code": "US", "limit": 2})
    assert [item["phone_number"] for item in searched["data"]] == [
        "+14155550199",
        "+14155550200",
    ]

    balance = loaded.backend.call("get_balance", {})
    assert balance["balance"]["available_credit"] == 42.5
