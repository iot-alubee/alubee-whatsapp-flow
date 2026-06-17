"""Build WhatsApp Flow data-channel responses for the leave form."""

from __future__ import annotations

import logging

from leave_counts import get_leave_counts_for_phone
from users import get_user_by_phone, phone_from_flow_token, phone_to_10

logger = logging.getLogger(__name__)

LEAVE_SCREEN = "LEAVE_FORM"


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _phone_from_context(flow_data: dict, form_data: dict) -> str:
    for source in (flow_data, form_data):
        if not isinstance(source, dict):
            continue
        phone = phone_from_flow_token(str(source.get("flow_token") or ""))
        if phone:
            return phone
    for key in ("phone", "phone_number", "employee_mobile"):
        raw = phone_to_10(str(form_data.get(key) or ""))
        if len(raw) == 10:
            return raw
    return ""


def _format_leave_count(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)


def _screen_data(form_data: dict, phone: str) -> dict:
    leave_when = _pick(form_data, "leave_when")
    show_date_range = leave_when == "other"
    show_duration = leave_when == "tomorrow"

    leaves_last = "0"
    leaves_curr = "0"
    show_leave_counts = False
    if phone:
        ud = get_user_by_phone(phone)
        if ud:
            last, curr = get_leave_counts_for_phone(phone)
            leaves_last = _format_leave_count(last)
            leaves_curr = _format_leave_count(curr)
            show_leave_counts = True

    return {
        "show_date_range": show_date_range,
        "show_duration": show_duration,
        "show_leave_counts": show_leave_counts,
        "leaves_current_month": leaves_curr,
        "leaves_last_month": leaves_last,
    }


def build_leave_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or LEAVE_SCREEN).strip() or LEAVE_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    phone = _phone_from_context(flow_data, form_data)

    try:
        data = _screen_data(form_data, phone)
    except Exception:
        logger.exception("leave screen data failed action=%s data=%s", action, form_data)
        data = {
            "show_date_range": False,
            "show_duration": False,
            "show_leave_counts": False,
            "leaves_current_month": "0",
            "leaves_last_month": "0",
        }

    logger.info(
        "leave flow response action=%s when=%s show_date_range=%s show_duration=%s counts=%s/%s",
        action,
        _pick(form_data, "leave_when") or "-",
        data.get("show_date_range"),
        data.get("show_duration"),
        data.get("leaves_last_month"),
        data.get("leaves_current_month"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
