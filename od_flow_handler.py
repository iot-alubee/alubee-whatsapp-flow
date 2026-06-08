"""Build WhatsApp Flow data-channel responses for the OD form."""

from __future__ import annotations

import logging

from vehicles import fetch_available_vehicles

logger = logging.getLogger(__name__)

OD_ENTRY_SCREEN = "OD_FORM"
OD_SIMPLE_SCREEN = "OD_SIMPLE"
OD_OTHER_SCREEN = "OD_OTHER"
OD_VEHICLE_SCREEN = "OD_VEHICLE"
OD_BOTH_SCREEN = "OD_OTHER_VEHICLE"

OD_DEFAULT_FORM = {"od_reason": "unit_i", "company_vehicle": "no"}


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _fetch_vehicles() -> list[dict[str, str]]:
    try:
        return fetch_available_vehicles()
    except Exception:
        logger.exception("fetch_available_vehicles failed")
        return []


def _route_screen(form_data: dict) -> tuple[str, dict]:
    """Pick the submit screen; extra fields live only on screens that need them."""
    od_reason = _pick(form_data, "od_reason") or OD_DEFAULT_FORM["od_reason"]
    company_vehicle = _pick(form_data, "company_vehicle") or OD_DEFAULT_FORM["company_vehicle"]
    needs_other = od_reason == "other"
    needs_vehicle = company_vehicle == "yes"

    data: dict = {
        "od_reason": od_reason,
        "company_vehicle": company_vehicle,
    }

    if needs_other and needs_vehicle:
        screen = OD_BOTH_SCREEN
    elif needs_other:
        screen = OD_OTHER_SCREEN
    elif needs_vehicle:
        screen = OD_VEHICLE_SCREEN
    else:
        screen = OD_SIMPLE_SCREEN

    if needs_vehicle:
        data["vehicles"] = _fetch_vehicles()

    return screen, data


def build_od_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or OD_ENTRY_SCREEN).strip() or OD_ENTRY_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action == "init":
        next_screen = OD_ENTRY_SCREEN
        data: dict = {}
    elif screen == OD_ENTRY_SCREEN:
        try:
            next_screen, data = _route_screen(form_data)
        except Exception:
            logger.exception("route failed action=%s data=%s", action, form_data)
            next_screen, data = _route_screen(OD_DEFAULT_FORM)
    else:
        next_screen = screen
        data = dict(form_data)

    logger.info(
        "flow response action=%s screen=%s next=%s od_reason=%s company_vehicle=%s vehicle_count=%s",
        action,
        screen,
        next_screen,
        data.get("od_reason"),
        data.get("company_vehicle"),
        len(data.get("vehicles") or []),
    )

    return {
        "version": "3.0",
        "screen": next_screen,
        "data": data,
    }
