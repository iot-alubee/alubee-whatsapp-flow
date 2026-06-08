"""Build WhatsApp Flow data-channel responses for the permission form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PERMISSION_SCREEN = "PERMISSION_FORM"

_SUPERVISOR_OPTIONS = [
    {"id": "myself", "title": "For Myself"},
    {"id": "cl", "title": "For CL"},
]


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _is_supervisor_flag(data: dict) -> bool:
    val = data.get("is_supervisor")
    if val is True:
        return True
    if val is False:
        return False
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _screen_data(form_data: dict) -> dict:
    is_supervisor = _is_supervisor_flag(form_data)
    permission_for = _pick(form_data, "permission_for")
    if not permission_for and not is_supervisor:
        permission_for = "myself"
    is_cl = permission_for == "cl"
    return {
        "is_supervisor": is_supervisor,
        "show_permission_for": is_supervisor,
        "permission_for_options": _SUPERVISOR_OPTIONS if is_supervisor else [],
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
        data = {
            "is_supervisor": False,
            "show_permission_for": False,
            "permission_for_options": [],
            "show_cl_name": False,
            "show_shift": True,
            "show_type": True,
        }

    logger.info(
        "permission flow response action=%s supervisor=%s show_for=%s show_cl=%s show_type=%s",
        action,
        data.get("is_supervisor"),
        data.get("show_permission_for"),
        data.get("show_cl_name"),
        data.get("show_type"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
