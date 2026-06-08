"""Build WhatsApp Flow data-channel responses for the OD form."""

from __future__ import annotations

import logging

from vehicles import fetch_available_vehicles

logger = logging.getLogger(__name__)

OD_SCREEN = "OD_FORM"
OD_DEFAULT_FORM = {"od_reason": "unit_i", "company_vehicle": "no"}


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    od_reason = _pick(form_data, "od_reason")
    show_other_reason = od_reason == "other"

    company_vehicle = _pick(form_data, "company_vehicle")
    vehicles: list[dict[str, str]] = []
    is_vehicle_visible = False

    if company_vehicle == "yes":
        is_vehicle_visible = True
        try:
            vehicles = fetch_available_vehicles()
        except Exception:
            logger.exception("fetch_available_vehicles failed")
            vehicles = []

    return {
        "show_other_reason": show_other_reason,
        "is_vehicle_visible": is_vehicle_visible,
        "vehicles": vehicles,
    }


def _default_screen_data() -> dict:
    return _screen_data(OD_DEFAULT_FORM)


def build_od_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or OD_SCREEN).strip() or OD_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action == "init":
        data = _default_screen_data()
    else:
        try:
            data = _screen_data(form_data)
        except Exception:
            logger.exception("screen data build failed action=%s data=%s", action, form_data)
            data = _default_screen_data()

    logger.info(
        "flow response action=%s show_other=%s vehicle_visible=%s vehicle_count=%s",
        action,
        data.get("show_other_reason"),
        data.get("is_vehicle_visible"),
        len(data.get("vehicles") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
