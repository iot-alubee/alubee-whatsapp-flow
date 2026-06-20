"""Route decrypted WhatsApp Flow requests to the correct form handler."""

from __future__ import annotations

from it_flow_handler import build_it_flow_response
from leave_flow_handler import build_leave_flow_response
from vehicle_request_flow_handler import (
    build_logistics_flow_response,
    build_vehicle_request_flow_response,
)
from maintenance_flow_handler import build_maintenance_flow_response
from od_flow_handler import build_od_flow_response
from permission_flow_handler import build_permission_flow_response
from visitor_flow_handler import build_visitor_flow_response


def _flow_token(flow_data: dict) -> str:
    return (flow_data.get("flow_token") or "").strip().lower()


def build_flow_response(flow_data: dict) -> dict:
    screen = (flow_data.get("screen") or "").strip().upper()
    token = _flow_token(flow_data)
    if screen.startswith("IT") or token.startswith("it_"):
        return build_it_flow_response(flow_data)
    if screen.startswith("MAINTENANCE") or token.startswith("maintenance_"):
        return build_maintenance_flow_response(flow_data)
    if (
        screen.startswith("VEHICLE")
        or screen.startswith("LOGISTICS")
        or token.startswith("vehicle_request_")
        or token.startswith("logistics_")
    ):
        return build_vehicle_request_flow_response(flow_data)
    if screen.startswith("VISITOR") or token.startswith("visitor_"):
        return build_visitor_flow_response(flow_data)
    if screen.startswith("LEAVE") or token.startswith("leave_"):
        return build_leave_flow_response(flow_data)
    # Permission sends flow_token=perm_{phone}; INIT may arrive with empty screen.
    if screen.startswith("PERMISSION") or token.startswith("perm_"):
        return build_permission_flow_response(flow_data)
    if screen.startswith("OD") or token.startswith("od_"):
        return build_od_flow_response(flow_data)
    return build_od_flow_response(flow_data)
