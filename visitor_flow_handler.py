"""Build WhatsApp Flow data-channel responses for the visitor form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

VISITOR_SCREEN = "VISITOR_FORM"


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    purpose = _pick(form_data, "purpose")
    return {"show_other_purpose": purpose == "other"}


def build_visitor_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or VISITOR_SCREEN).strip() or VISITOR_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    try:
        data = _screen_data(form_data)
    except Exception:
        logger.exception("visitor screen data failed action=%s data=%s", action, form_data)
        data = {"show_other_purpose": False}

    logger.info(
        "visitor flow response action=%s show_other_purpose=%s",
        action,
        data.get("show_other_purpose"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
