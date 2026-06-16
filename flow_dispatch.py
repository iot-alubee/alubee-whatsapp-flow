"""Route decrypted WhatsApp Flow requests to the correct form handler."""

from __future__ import annotations

from leave_flow_handler import build_leave_flow_response
from od_flow_handler import build_od_flow_response
from permission_flow_handler import build_permission_flow_response
from visitor_flow_handler import build_visitor_flow_response


def _flow_token(flow_data: dict) -> str:
    return (flow_data.get("flow_token") or "").strip().lower()


def build_flow_response(flow_data: dict) -> dict:
    screen = (flow_data.get("screen") or "").strip().upper()
    token = _flow_token(flow_data)
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
