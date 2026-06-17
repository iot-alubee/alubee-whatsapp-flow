"""Build WhatsApp Flow data-channel responses for the visitor form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

VISITOR_SCREEN = "VISITOR_FORM"

VISITOR_TYPE_OPTIONS: list[dict[str, str]] = [
    {"id": "supplier", "title": "Supplier"},
    {"id": "customer", "title": "Customer"},
    {"id": "interview", "title": "Interview"},
    {"id": "govt_officials", "title": "Govt Officials"},
    {"id": "consultant", "title": "Consultant"},
    {"id": "contractor", "title": "Contractor"},
    {"id": "service_provider", "title": "Service Provider"},
    {"id": "guest", "title": "Guest"},
]


def build_visitor_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or VISITOR_SCREEN).strip() or VISITOR_SCREEN

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    logger.info("visitor flow response action=%s", action)

    return {
        "version": "3.0",
        "screen": screen,
        "data": {
            "visitor_type_options": VISITOR_TYPE_OPTIONS,
        },
    }
