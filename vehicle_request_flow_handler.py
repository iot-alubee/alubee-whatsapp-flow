"""Build WhatsApp Flow data-channel responses for the Vehicle Request form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

VEHICLE_REQUEST_FORM_SCREEN = "VEHICLE_REQUEST_FORM"
VEHICLE_REQUEST_TIME_SCREEN = "VEHICLE_REQUEST_TIME"
VEHICLE_REQUEST_SCREEN = VEHICLE_REQUEST_FORM_SCREEN
_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})

SUPPLIER_DESTINATIONS: list[dict[str, str]] = [
    {"id": "neocol", "title": "Neocol"},
    {"id": "v_tech", "title": "V-Tech"},
    {"id": "chellam_transport", "title": "Chellam Transport"},
    {"id": "ayyappa_gas_shop", "title": "Ayyappa Gas Shop"},
    {"id": "ayyappa_gas_godown", "title": "Ayyappa Gas Godown"},
    {"id": "local_shipcot_area", "title": "Local Shipcot Area"},
    {"id": "local_hosur", "title": "Local Hosur"},
    {"id": "alloy_tech", "title": "Alloy Tech"},
    {"id": "arasanatti", "title": "Arasanatti"},
    {"id": "bagalur_road", "title": "Bagalur Road"},
    {"id": "seg_mould_inspection", "title": "SEG Mould Inspection"},
    {"id": "unit_1_to_unit_2", "title": "Unit-1 to Unit-2"},
]

SUB_CONTRACTOR_DESTINATIONS: list[dict[str, str]] = [
    {"id": "rajeshwari_layout", "title": "Rajeshwari Layout"},
    {"id": "kamal", "title": "Kamal"},
    {"id": "lakshmi_steels", "title": "Lakshmi Steels"},
    {"id": "kamaraj_nagar_supplier", "title": "Kamaraj Nagar Supplier"},
]

CUSTOMER_DESTINATIONS: list[dict[str, str]] = [
    {"id": "tvs", "title": "TVS"},
    {"id": "amara_raja", "title": "Amara Raja"},
]

DESTINATION_DISTANCE_KM: dict[str, int] = {
    "neocol": 6,
    "v_tech": 4,
    "chellam_transport": 24,
    "ayyappa_gas_shop": 6,
    "ayyappa_gas_godown": 15,
    "local_shipcot_area": 3,
    "local_hosur": 3,
    "alloy_tech": 17,
    "arasanatti": 5,
    "bagalur_road": 10,
    "seg_mould_inspection": 50,
    "unit_1_to_unit_2": 3,
    "rajeshwari_layout": 5,
    "kamal": 2,
    "lakshmi_steels": 6,
    "kamaraj_nagar_supplier": 4,
    "tvs": 20,
    "amara_raja": 420,
}

_MANUAL_CATEGORIES = frozenset({"purchase", "transport_office"})
_DROPDOWN_CATEGORIES = frozenset({"supplier", "sub_contractor", "customer"})


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if isinstance(val, dict):
        val = val.get("id") or val.get("title")
    if val is None:
        return ""
    return str(val).strip().lower()


def _destination_options(category: str) -> list[dict[str, str]]:
    if category == "supplier":
        return SUPPLIER_DESTINATIONS
    if category == "sub_contractor":
        return SUB_CONTRACTOR_DESTINATIONS
    if category == "customer":
        return CUSTOMER_DESTINATIONS
    return []


def _format_distance(km: int | None) -> str:
    if km is None:
        return "—"
    return f"{km} KM"


def _estimated_distance(category: str, destination: str) -> str:
    if category in _MANUAL_CATEGORIES:
        return "—"
    dest_id = _pick({"destination": destination}, "destination")
    if not dest_id:
        return ""
    return _format_distance(DESTINATION_DISTANCE_KM.get(dest_id))


def _screen_data(form_data: dict) -> dict:
    category = _pick(form_data, "destination_category")
    destination = _pick(form_data, "destination")
    vehicle_type = _pick(form_data, "vehicle_type")

    show_location = category in _MANUAL_CATEGORIES
    show_destination = category in _DROPDOWN_CATEGORIES
    show_vehicle_type = bool(category) and (show_location or bool(destination))
    show_hire_vehicle_type = show_vehicle_type and vehicle_type == "external_hire"
    show_load_size = bool(vehicle_type)
    show_distance = bool(category) and (show_location or bool(destination))
    estimated_distance = _estimated_distance(category, destination) if show_distance else ""

    return {
        "destination_options": _destination_options(category),
        "show_location_details": show_location,
        "show_destination": show_destination,
        "show_vehicle_type": show_vehicle_type,
        "show_hire_vehicle_type": show_hire_vehicle_type,
        "show_load_size": show_load_size,
        "show_distance": show_distance,
        "estimated_distance": estimated_distance,
    }


def build_vehicle_request_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (
        flow_data.get("screen") or VEHICLE_REQUEST_FORM_SCREEN
    ).strip() or VEHICLE_REQUEST_FORM_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if screen == VEHICLE_REQUEST_TIME_SCREEN:
        if action not in _LOAD_ACTIONS:
            logger.warning("vehicle request flow unexpected action=%s screen=%s", action, screen)
        return {"version": "3.0", "screen": VEHICLE_REQUEST_TIME_SCREEN, "data": {}}

    if action not in _LOAD_ACTIONS:
        logger.warning("vehicle request flow unexpected action=%s", action)

    try:
        data = _screen_data(form_data)
    except Exception:
        logger.exception(
            "vehicle request screen data failed action=%s data=%s", action, form_data
        )
        data = {
            "destination_options": [],
            "show_location_details": False,
            "show_destination": False,
            "show_vehicle_type": False,
            "show_hire_vehicle_type": False,
            "show_load_size": False,
            "show_distance": False,
            "estimated_distance": "",
        }

    logger.info(
        "vehicle request flow action=%s category=%s destination=%s distance=%s",
        action,
        _pick(form_data, "destination_category") or "-",
        _pick(form_data, "destination") or "-",
        data.get("estimated_distance") or "-",
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }


# Backward compat for older flow JSON / tokens during rollout.
build_logistics_flow_response = build_vehicle_request_flow_response
