"""Build WhatsApp Flow data-channel responses for the leave form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

LEAVE_SCREEN = "LEAVE_FORM"


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    leave_when = _pick(form_data, "leave_when")
    leave_reason = _pick(form_data, "leave_reason")
    return {
        "show_date_range": leave_when == "other",
        "show_other_reason": leave_reason == "other",
    }


def build_leave_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or LEAVE_SCREEN).strip() or LEAVE_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    try:
        data = _screen_data(form_data)
    except Exception:
        logger.exception("leave screen data failed action=%s data=%s", action, form_data)
        data = {"show_date_range": False, "show_other_reason": False}

    logger.info(
        "leave flow response action=%s show_date_range=%s show_other_reason=%s",
        action,
        data.get("show_date_range"),
        data.get("show_other_reason"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
