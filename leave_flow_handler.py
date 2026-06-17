"""Build WhatsApp Flow data-channel responses for the leave form."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]

from leave_counts import get_leave_counts_for_phone
from users import get_user_by_phone, phone_from_flow_token, phone_to_10

logger = logging.getLogger(__name__)

LEAVE_SCREEN = "LEAVE_FORM"
_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})

DATE_TODAY_ERROR = "Leave cannot be raised for today's date. Please choose tomorrow or a later date."
DATE_TO_BEFORE_FROM_ERROR = "To date must be on or after From date."


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _today_ist() -> date:
    if ZoneInfo:
        return datetime.now(ZoneInfo("Asia/Kolkata")).date()
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def _parse_flow_date(raw: str) -> date | None:
    s = (raw or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


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


def _leave_count_lines(phone: str) -> tuple[str, str]:
    leaves_last = "0"
    leaves_curr = "0"
    if phone and get_user_by_phone(phone):
        last, curr = get_leave_counts_for_phone(phone)
        leaves_last = _format_leave_count(last)
        leaves_curr = _format_leave_count(curr)
    current_line = f"Leaves in Current Month: {leaves_curr}"
    last_line = f"Leaves in Last Month: {leaves_last}"
    return current_line, last_line


def _tomorrow_ist() -> date:
    return _today_ist() + timedelta(days=1)


def _min_date_iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _min_dates_for_other(form_data: dict) -> tuple[str, str]:
    """Earliest selectable From/To dates (tomorrow IST; To >= From)."""
    tomorrow = _tomorrow_ist()
    min_from = _min_date_iso(tomorrow)
    from_dt = _parse_flow_date(str(form_data.get("from_date") or ""))
    if from_dt and from_dt >= tomorrow:
        min_to = _min_date_iso(from_dt)
    else:
        min_to = min_from
    return min_from, min_to


def _other_dates_invalid(form_data: dict) -> str:
    """Return error text if Other-date range is invalid; else empty string."""
    if _pick(form_data, "leave_when") != "other":
        return ""
    from_raw = str(form_data.get("from_date") or "").strip()
    to_raw = str(form_data.get("to_date") or "").strip()
    if not from_raw and not to_raw:
        return ""

    from_dt = _parse_flow_date(from_raw)
    to_dt = _parse_flow_date(to_raw) if to_raw else None
    tomorrow = _tomorrow_ist()

    if from_raw and not from_dt:
        return "Please enter valid From and To dates."
    if to_raw and not to_dt:
        return "Please enter valid From and To dates."
    if from_dt and from_dt < tomorrow:
        return DATE_TODAY_ERROR
    if to_dt and to_dt < tomorrow:
        return DATE_TODAY_ERROR
    if from_dt and to_dt and to_dt < from_dt:
        return DATE_TO_BEFORE_FROM_ERROR
    return ""


def _can_submit(form_data: dict) -> bool:
    if _pick(form_data, "leave_when") == "other" and _other_dates_invalid(form_data):
        return False
    return True


def _screen_data(form_data: dict, phone: str) -> dict:
    leave_when = _pick(form_data, "leave_when")
    show_date_range = leave_when == "other"
    show_duration = leave_when == "tomorrow"
    current_line, last_line = _leave_count_lines(phone)
    date_error = _other_dates_invalid(form_data)
    from_min_date, to_min_date = _min_dates_for_other(form_data)

    return {
        "show_date_range": show_date_range,
        "show_duration": show_duration,
        "show_leave_counts": True,
        "show_date_error": bool(date_error),
        "date_error_line": date_error,
        "can_submit": _can_submit(form_data),
        "from_min_date": from_min_date,
        "to_min_date": to_min_date,
        "leaves_current_month": current_line,
        "leaves_last_month": last_line,
        "leaves_current_month_line": current_line,
        "leaves_last_month_line": last_line,
    }


def _apply_error(data: dict, message: str) -> dict:
    data = dict(data)
    data["show_date_error"] = True
    data["date_error_line"] = message
    data["error_message"] = message
    return data


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
            "show_date_error": False,
            "date_error_line": "",
            "can_submit": True,
            "from_min_date": _min_date_iso(_tomorrow_ist()),
            "to_min_date": _min_date_iso(_tomorrow_ist()),
            "leaves_current_month": "Leaves in Current Month: 0",
            "leaves_last_month": "Leaves in Last Month: 0",
            "leaves_current_month_line": "Leaves in Current Month: 0",
            "leaves_last_month_line": "Leaves in Last Month: 0",
        }

    if data.get("date_error_line"):
        data = _apply_error(data, data["date_error_line"])

    logger.info(
        "leave flow response action=%s token=%s phone=%s when=%s date_error=%s",
        action,
        flow_data.get("flow_token"),
        phone or "-",
        _pick(form_data, "leave_when") or "-",
        data.get("date_error_line") or "-",
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
