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
    company_vehicle = _pick(form_data, "company_vehicle")
    vehicles: list[dict[str, str]] = []
    if company_vehicle == "yes":
        try:
            vehicles = fetch_available_vehicles()
        except Exception:
            logger.exception("fetch_available_vehicles failed")
    return {"vehicles": vehicles}


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
        data = {"vehicles": []}

    logger.info(
        "flow response action=%s company_vehicle=%s vehicle_count=%s",
        action,
        _pick(form_data, "company_vehicle"),
        len(data.get("vehicles") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
