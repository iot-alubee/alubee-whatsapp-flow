"""Route decrypted WhatsApp Flow requests to OD or visitor handlers."""

from __future__ import annotations

from od_flow_handler import build_od_flow_response
from visitor_flow_handler import build_visitor_flow_response


def build_flow_response(flow_data: dict) -> dict:
    screen = (flow_data.get("screen") or "").strip().upper()
    if screen.startswith("VISITOR"):
        return build_visitor_flow_response(flow_data)
    return build_od_flow_response(flow_data)
