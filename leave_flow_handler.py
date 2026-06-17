"""Build WhatsApp Flow data-channel responses for the leave form."""

from __future__ import annotations

import logging

from leave_counts import get_leave_counts_for_phone
from users import get_user_by_phone, phone_from_flow_token, phone_to_10

logger = logging.getLogger(__name__)

LEAVE_SCREEN = "LEAVE_FORM"
_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _phone_from_context(flow_data: dict, form_data: dict) -> str:
    for token_raw in (flow_data.get("flow_token"), form_data.get("flow_token")):
        phone = phone_from_flow_token(str(token_raw or ""))
        if phone:
            return phone
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


def _leave_count_lines(phone: str) -> tuple[str, str, str, str]:
    leaves_last = "0"
    leaves_curr = "0"
    if phone and get_user_by_phone(phone):
        last, curr = get_leave_counts_for_phone(phone)
        leaves_last = _format_leave_count(last)
        leaves_curr = _format_leave_count(curr)
    current_line = f"Leaves in Current Month: {leaves_curr}"
    last_line = f"Leaves in Last Month: {leaves_last}"
    return leaves_curr, leaves_last, current_line, last_line


def _screen_data(form_data: dict, phone: str) -> dict:
    leave_when = _pick(form_data, "leave_when")
    show_date_range = leave_when == "other"
    show_duration = leave_when == "tomorrow"
    _, _, current_line, last_line = _leave_count_lines(phone)

    return {
        "show_date_range": show_date_range,
        "show_duration": show_duration,
        "show_leave_counts": True,
        "leaves_current_month": current_line,
        "leaves_last_month": last_line,
        "leaves_current_month_line": current_line,
        "leaves_last_month_line": last_line,
    }


def build_leave_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or LEAVE_SCREEN).strip() or LEAVE_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action not in _LOAD_ACTIONS:
        logger.warning("leave flow unexpected action=%s", action)

    phone = _phone_from_context(flow_data, form_data)

    try:
        data = _screen_data(form_data, phone)
    except Exception:
        logger.exception("leave screen data failed action=%s data=%s", action, form_data)
        data = {
            "show_date_range": False,
            "show_duration": False,
            "show_leave_counts": True,
            "leaves_current_month": "Leaves in Current Month: 0",
            "leaves_last_month": "Leaves in Last Month: 0",
            "leaves_current_month_line": "Leaves in Current Month: 0",
            "leaves_last_month_line": "Leaves in Last Month: 0",
        }

    logger.info(
        "leave flow response action=%s token=%s phone=%s when=%s counts=%s | %s",
        action,
        flow_data.get("flow_token"),
        phone or "-",
        _pick(form_data, "leave_when") or "-",
        data.get("leaves_current_month_line"),
        data.get("leaves_last_month_line"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
