"""Time slot list for permission WhatsApp Flow dropdown."""

from __future__ import annotations


def _format_12h(hour24: int, minute: int) -> str:
    period = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return f"{hour12}:{minute:02d} {period}"


def permission_time_slot_options() -> list[dict[str, str]]:
    """12:00 AM – 11:30 PM every 30 minutes; id and title are the display value."""
    rows: list[dict[str, str]] = []
    for hour24 in range(24):
        for minute in (0, 30):
            label = _format_12h(hour24, minute)
            rows.append({"id": label, "title": label})
    return rows
