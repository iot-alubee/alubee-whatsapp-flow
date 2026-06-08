"""Build WhatsApp Flow data-channel responses for the OD form."""

from __future__ import annotations

import logging

from vehicles import fetch_available_vehicles

logger = logging.getLogger(__name__)

OD_SCREEN = "OD_FORM"


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    od_reason = _pick(form_data, "od_reason")
    show_other_reason = od_reason == "other"

    company_vehicle = _pick(form_data, "company_vehicle")
    is_vehicle_visible = company_vehicle == "yes"
    vehicles: list[dict[str, str]] = []
    if is_vehicle_visible:
        try:
            vehicles = fetch_available_vehicles()
        except Exception:
            logger.exception("fetch_available_vehicles failed")

    return {
        "show_other_reason": show_other_reason,
        "is_vehicle_visible": is_vehicle_visible,
        "vehicles": vehicles,
    }


def build_od_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or OD_SCREEN).strip() or OD_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    try:
        data = _screen_data(form_data)
    except Exception:
        logger.exception("screen data build failed action=%s data=%s", action, form_data)
        data = {
            "show_other_reason": False,
            "is_vehicle_visible": False,
            "vehicles": [],
        }

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
