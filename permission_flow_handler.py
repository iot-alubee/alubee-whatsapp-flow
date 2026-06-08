"""Build WhatsApp Flow data-channel responses for the permission form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PERMISSION_SCREEN = "PERMISSION_FORM"


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    permission_for = _pick(form_data, "permission_for")
    is_cl = permission_for == "cl"
    return {
        "show_cl_name": is_cl,
        "show_shift": True,
        "show_type": not is_cl,
    }


def build_permission_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or PERMISSION_SCREEN).strip() or PERMISSION_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    try:
        data = _screen_data(form_data)
    except Exception:
        logger.exception("permission screen data failed action=%s data=%s", action, form_data)
        data = {"show_cl_name": False, "show_shift": True, "show_type": True}

    logger.info(
        "permission flow response action=%s show_cl=%s show_type=%s",
        action,
        data.get("show_cl_name"),
        data.get("show_type"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
