"""Permission form time slots — filtered by shift and type (max 4 hours)."""

from __future__ import annotations

import re

MAX_PERMISSION_MINUTES = 4 * 60
SLOT_STEP = 30

_TYPE_LATE_IN = "late_in"
_TYPE_EARLY_OUT = "early_out"
_TYPE_OTHER = "other"

_ALL_PERMISSION_TYPES = [
    {"id": "late_in", "title": "Late IN"},
    {"id": "early_out", "title": "Early OUT"},
    {"id": "other", "title": "Other"},
]
_SHIFT_II_PERMISSION_TYPES = [{"id": "late_in", "title": "Late IN"}]


def _format_12h(hour24: int, minute: int) -> str:
    period = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return f"{hour12}:{minute:02d} {period}"


def _parse_12h(text: str) -> tuple[int, int] | None:
    s = (text or "").strip().upper()
    m = re.match(r"^(\d{1,2})\s*:\s*(\d{2})\s*(AM|PM)$", s)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    period = m.group(3)
    if hour < 1 or hour > 12 or minute < 0 or minute > 59:
        return None
    if period == "AM":
        hour24 = 0 if hour == 12 else hour
    else:
        hour24 = 12 if hour == 12 else hour + 12
    return hour24, minute


def _parse_hhmm(text: str) -> tuple[int, int] | None:
    s = (text or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour, minute


def _minutes_of_day(hour24: int, minute: int) -> int:
    return hour24 * 60 + minute


def normalize_permission_time_label(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    parsed = _parse_12h(s)
    if parsed is None:
        return ""
    return _format_12h(parsed[0], parsed[1])


def resolve_shift_login_logout(
    ud: dict | None, permission_shift: str
) -> tuple[str, str] | None:
    if not ud:
        return None
    st = (ud.get("shift_type") or "GS").strip().upper()
    shift = (permission_shift or "I").strip().upper()
    if st == "GS":
        login = ud.get("shift_login")
        logout = ud.get("shift_logout")
    elif shift in ("II", "2"):
        login = ud.get("shift2_login")
        logout = ud.get("shift2_logout")
    else:
        login = ud.get("shift1_login")
        logout = ud.get("shift1_logout")
    if not login or not logout:
        return None
    return str(login).strip(), str(logout).strip()


def permission_types_for_user(ud: dict | None, permission_shift: str) -> list[dict[str, str]]:
    """RS Shift II: Late IN only."""
    if not ud:
        return list(_ALL_PERMISSION_TYPES)
    st = (ud.get("shift_type") or "GS").strip().upper()
    shift = (permission_shift or "I").strip().upper()
    if st == "RS" and shift in ("II", "2"):
        return list(_SHIFT_II_PERMISSION_TYPES)
    return list(_ALL_PERMISSION_TYPES)


def _slot_rows(minutes_start: int, minutes_end: int) -> list[dict[str, str]]:
    if minutes_end < minutes_start:
        return []
    rows: list[dict[str, str]] = []
    m = minutes_start
    while m <= minutes_end:
        hour24, minute = divmod(m, 60)
        if hour24 > 23:
            break
        label = _format_12h(hour24, minute)
        rows.append({"id": label, "title": label})
        m += SLOT_STEP
    return rows


def _late_in_slots(login_hhmm: str) -> list[dict[str, str]]:
    login = _parse_hhmm(login_hhmm)
    if not login:
        return []
    login_m = _minutes_of_day(login[0], login[1])
    start_m = login_m + SLOT_STEP
    end_m = login_m + MAX_PERMISSION_MINUTES
    return _slot_rows(start_m, end_m)


def _early_out_slots(logout_hhmm: str) -> list[dict[str, str]]:
    logout = _parse_hhmm(logout_hhmm)
    if not logout:
        return []
    logout_m = _minutes_of_day(logout[0], logout[1])
    start_m = logout_m - MAX_PERMISSION_MINUTES + SLOT_STEP
    end_m = logout_m - SLOT_STEP
    return _slot_rows(start_m, end_m)


def _other_out_slots(login_hhmm: str, logout_hhmm: str) -> list[dict[str, str]]:
    login = _parse_hhmm(login_hhmm)
    logout = _parse_hhmm(logout_hhmm)
    if not login or not logout:
        return []
    login_m = _minutes_of_day(login[0], login[1])
    logout_m = _minutes_of_day(logout[0], logout[1])
    if login_m % SLOT_STEP == 0:
        start_m = login_m
    else:
        start_m = ((login_m // SLOT_STEP) + 1) * SLOT_STEP
    end_m = logout_m - SLOT_STEP
    return _slot_rows(start_m, end_m)


def _other_in_slots(expected_out: str, logout_hhmm: str) -> list[dict[str, str]]:
    out_t = _parse_12h(normalize_permission_time_label(expected_out))
    logout = _parse_hhmm(logout_hhmm)
    if not out_t or not logout:
        return []
    out_m = _minutes_of_day(out_t[0], out_t[1])
    logout_m = _minutes_of_day(logout[0], logout[1])
    start_m = out_m + SLOT_STEP
    end_m = min(out_m + MAX_PERMISSION_MINUTES, logout_m)
    return _slot_rows(start_m, end_m)


def build_permission_time_slots(
    ud: dict | None,
    *,
    permission_shift: str,
    permission_type: str,
    expected_out: str = "",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Returns (out_time_slots, in_time_slots) for the permission form.
    """
    pt = (permission_type or "").strip().lower().replace(" ", "_")
    if pt in ("latein", "late"):
        pt = _TYPE_LATE_IN
    elif pt in ("earlyout", "early"):
        pt = _TYPE_EARLY_OUT

    bounds = resolve_shift_login_logout(ud, permission_shift)
    if not bounds:
        return [], []

    login_hhmm, logout_hhmm = bounds

    if pt == _TYPE_LATE_IN:
        return [], _late_in_slots(login_hhmm)
    if pt == _TYPE_EARLY_OUT:
        return _early_out_slots(logout_hhmm), []
    if pt == _TYPE_OTHER:
        out_slots = _other_out_slots(login_hhmm, logout_hhmm)
        in_slots = (
            _other_in_slots(expected_out, logout_hhmm) if expected_out.strip() else []
        )
        return out_slots, in_slots
    return [], []
