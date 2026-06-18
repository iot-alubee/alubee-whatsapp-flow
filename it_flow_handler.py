"""Build WhatsApp Flow data-channel responses for the IT request form."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

IT_SCREEN = "IT_FORM"

CATEGORY_OPTIONS: list[dict[str, str]] = [
    {"id": "printer", "title": "Printer"},
    {"id": "computer_laptop", "title": "Computer/Laptop"},
    {"id": "network", "title": "Network"},
    {"id": "iot", "title": "IoT"},
    {"id": "alubee_app", "title": "Alubee App"},
]

ISSUE_TYPES_BY_CATEGORY: dict[str, list[dict[str, str]]] = {
    "printer": [
        {"id": "printer_connection_error", "title": "Printer Connection Error"},
        {"id": "not_printing", "title": "Not Printing"},
        {"id": "printer_not_listed", "title": "Printer Not Listed"},
    ],
    "computer_laptop": [
        {"id": "os_reinstall", "title": "OS Reinstall"},
        {"id": "system_hanging_slow", "title": "System Hanging/Slow"},
        {"id": "excel_office_installation", "title": "Excel/Office Installation"},
        {"id": "third_party_software", "title": "Third-Party Software Requirements"},
        {"id": "hardware_issue", "title": "Monitor/Keyboard or Other Hardware Issue"},
    ],
    "network": [
        {"id": "server_not_accessible", "title": "Server Not Accessible"},
        {"id": "mac_whitelisting", "title": "MAC Whitelisting"},
        {"id": "internet_speed_issue", "title": "Internet Speed Issue"},
        {"id": "internet_connection_error", "title": "Internet Connection Error"},
    ],
    "iot": [
        {"id": "lcd_led_issue", "title": "LCD/LED Issue"},
        {"id": "button_issue", "title": "Button Issue"},
        {"id": "internet_not_connected", "title": "Internet Not Connected"},
        {"id": "device_freezed", "title": "Device Freezed"},
        {"id": "reset_issue", "title": "Reset Issue"},
        {"id": "data_issue", "title": "Data Issue"},
        {"id": "new_device_installation", "title": "New Device Installation"},
        {"id": "plan_updation_sheet_issue", "title": "Plan Updation Sheet Issue"},
        {"id": "data_request", "title": "Data Request"},
    ],
    "alubee_app": [
        {"id": "login_issue", "title": "Login Issue"},
        {"id": "app_not_loading", "title": "App Not Loading"},
        {"id": "in_out_button_issue", "title": "IN/OUT button issue"},
        {"id": "other_modification", "title": "Other Modification Requirement"},
    ],
}


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _screen_data(form_data: dict) -> dict:
    category = _pick(form_data, "it_category")
    show_issue_type = bool(category)
    issue_options = ISSUE_TYPES_BY_CATEGORY.get(category, []) if show_issue_type else []
    return {
        "category_options": CATEGORY_OPTIONS,
        "issue_type_options": issue_options,
        "show_issue_type": show_issue_type,
    }


def build_it_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or IT_SCREEN).strip() or IT_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    try:
        data = _screen_data(form_data)
    except Exception:
        logger.exception("it screen data failed action=%s data=%s", action, form_data)
        data = {
            "category_options": CATEGORY_OPTIONS,
            "issue_type_options": [],
            "show_issue_type": False,
        }

    logger.info(
        "it flow response action=%s category=%s issue_count=%s",
        action,
        _pick(form_data, "it_category") or "-",
        len(data.get("issue_type_options") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
