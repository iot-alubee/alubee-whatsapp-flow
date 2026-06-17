"""Build WhatsApp Flow data-channel responses for the visitor form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

VISITOR_SCREEN = "VISITOR_FORM"


def build_visitor_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or VISITOR_SCREEN).strip() or VISITOR_SCREEN

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    logger.info("visitor flow response action=%s", action)

    return {
        "version": "3.0",
        "screen": screen,
        "data": {},
    }
