"""Approved leave day counts for the leave WhatsApp Flow."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]

from users import _get_db, get_user_by_phone, wa_id_from_phone

logger = logging.getLogger(__name__)


def _ist_now() -> datetime:
    if ZoneInfo:
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def _leave_calendar_months(ref: datetime | None = None) -> tuple[tuple[int, int], tuple[int, int]]:
    ref = ref or _ist_now()
    y, m = ref.year, ref.month
    if m == 1:
        return (y - 1, 12), (y, m)
    return (y, m - 1), (y, m)


def _parse_ddmmy(text: str) -> date | None:
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    if len(raw) >= 10:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def _count_leave_days_in_month_from_doc(d: dict, year: int, month: int) -> float:
    duration = (d.get("leave_duration") or "").strip().lower()
    stored_days = d.get("leave_days")
    if duration == "half_day" or stored_days == 0.5:
        from_d = _parse_ddmmy(d.get("leave_from_date") or "")
        to_d = _parse_ddmmy(d.get("leave_to_date") or d.get("leave_from_date") or "")
        if from_d and from_d.year == year and from_d.month == month:
            if not to_d or from_d == to_d:
                return 0.5
    month_key = f"{year}-{month:02d}"
    if (d.get("source") or "").strip().lower() == "imported_history":
        hist = (d.get("history_month") or "").strip()
        if hist == month_key:
            return float(d.get("leave_days") or len(d.get("leave_dates") or []) or 0)
    dates = d.get("leave_dates") or []
    if dates:
        n = 0
        for ds in dates:
            parsed = _parse_ddmmy(str(ds))
            if parsed and parsed.year == year and parsed.month == month:
                n += 1
        return float(n)
    from_d = _parse_ddmmy(d.get("leave_from_date") or "")
    to_d = _parse_ddmmy(d.get("leave_to_date") or d.get("leave_from_date") or "")
    if not from_d:
        return 0.0
    if not to_d:
        to_d = from_d
    n = 0
    cur = from_d
    while cur <= to_d:
        if cur.year == year and cur.month == month:
            n += 1
        cur += timedelta(days=1)
    return float(n)


def _leave_days_in_month(d: dict, year: int, month: int) -> float:
    if (d.get("jmd_status") or "").strip().upper() != "APPROVED":
        return 0.0
    return _count_leave_days_in_month_from_doc(d, year, month)


def get_leave_counts_for_user(ud: dict | None, *, employee_wa: str = "") -> tuple[float, float]:
    if not ud:
        return 0.0, 0.0
    db = _get_db()
    if not db:
        return 0.0, 0.0
    eid = (ud.get("employee_id") or "").strip().upper()
    wa = (employee_wa or "").strip()
    (prev_y, prev_m), (curr_y, curr_m) = _leave_calendar_months()
    last_month = 0.0
    current_month = 0.0
    try:
        snaps = list(db.collection("requests").where("type", "==", "LEAVE").limit(500).stream())
    except Exception:
        logger.exception("leave count query failed employee_id=%s", eid)
        return 0.0, 0.0
    for snap in snaps:
        d = snap.to_dict() or {}
        match_id = eid and (d.get("employee_id") or "").strip().upper() == eid
        match_wa = wa and (d.get("employee") or "").strip() == wa
        if not (match_id or match_wa):
            continue
        last_month += _leave_days_in_month(d, prev_y, prev_m)
        current_month += _leave_days_in_month(d, curr_y, curr_m)
    return last_month, current_month


def get_leave_counts_for_phone(phone: str) -> tuple[float, float]:
    ud = get_user_by_phone(phone)
    return get_leave_counts_for_user(ud, employee_wa=wa_id_from_phone(phone))
