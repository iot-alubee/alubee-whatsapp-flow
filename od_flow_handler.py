"""Build WhatsApp Flow data-channel responses for the OD form."""

from __future__ import annotations

import logging

from vehicles import fetch_available_vehicles

logger = logging.getLogger(__name__)

OD_SCREEN = "OD_FORM"

VISITING_TO_OPTIONS: list[dict[str, str]] = [
    {"id": "unit_i", "title": "Unit I"},
    {"id": "unit_ii", "title": "Unit II"},
    {"id": "hosur_town", "title": "Hosur Town"},
    {"id": "supplier_place", "title": "Supplier Place"},
    {"id": "bangalore", "title": "Bangalore"},
    {"id": "md_home", "title": "MD Home"},
]

TIME_REQUIRED_OPTIONS: list[dict[str, str]] = [
    {"id": "15_mins", "title": "15 mins"},
    {"id": "30_mins", "title": "30 mins"},
    {"id": "1_hour", "title": "1 Hour"},
    {"id": "2_hours", "title": "2 Hours"},
    {"id": "3_hours", "title": "3 Hours"},
    {"id": "over_3_hours", "title": "> 3 Hours"},
]


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    visiting_to = _pick(form_data, "visiting_to")
    show_purpose = bool(visiting_to) and visiting_to != "md_home"
    show_time_required = bool(visiting_to)
    show_company_vehicle = bool(visiting_to)

    company_vehicle = _pick(form_data, "company_vehicle")
    is_vehicle_visible = show_company_vehicle and company_vehicle == "yes"
    vehicles: list[dict[str, str]] = []
    if is_vehicle_visible:
        try:
            vehicles = fetch_available_vehicles()
        except Exception:
            logger.exception("fetch_available_vehicles failed")

    return {
        "visiting_to_options": VISITING_TO_OPTIONS,
        "time_required_options": TIME_REQUIRED_OPTIONS,
        "show_purpose": show_purpose,
        "show_time_required": show_time_required,
        "show_company_vehicle": show_company_vehicle,
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
            "visiting_to_options": VISITING_TO_OPTIONS,
            "time_required_options": TIME_REQUIRED_OPTIONS,
            "show_purpose": False,
            "show_time_required": False,
            "show_company_vehicle": False,
            "is_vehicle_visible": False,
            "vehicles": [],
        }

    logger.info(
        "flow response action=%s purpose=%s time=%s vehicle_visible=%s vehicle_count=%s",
        action,
        data.get("show_purpose"),
        data.get("show_time_required"),
        data.get("is_vehicle_visible"),
        len(data.get("vehicles") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
