"""Build WhatsApp Flow data-channel responses for the IT request form."""

from __future__ import annotations

import json
import logging

from users import (
    get_user_by_phone,
    it_user_context_from_token,
    phone_from_flow_token,
    phone_to_10,
)

logger = logging.getLogger(__name__)

IT_SCREEN = "IT_FORM"
_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})

CATEGORY_OPTIONS: list[dict[str, str]] = [
    {"id": "printer", "title": "Printer"},
    {"id": "computer_laptop", "title": "Computer/Laptop"},
    {"id": "network", "title": "Network"},
    {"id": "iot", "title": "IoT"},
    {"id": "alubee_app", "title": "Alubee App"},
]

# Unit I shop-floor machines (from shop floor list).
PDC_UNIT_I_MACHINE_OPTIONS: list[dict[str, str]] = [
    {"id": "125t_1", "title": "125T-1"},
    {"id": "125t_2", "title": "125T-2"},
    {"id": "125t_3", "title": "125T-3"},
    {"id": "125t_4", "title": "125T-4"},
    {"id": "125t_5", "title": "125T-5"},
    {"id": "125t_6", "title": "125T-6"},
    {"id": "125t_7", "title": "125T-7"},
    {"id": "250t_1", "title": "250T-1"},
    {"id": "350t_1", "title": "350T-1"},
    {"id": "350t_2", "title": "350T-2"},
    {"id": "350t_3", "title": "350T-3"},
    {"id": "350t_4", "title": "350T-4"},
]

CNC_UNIT_I_MACHINE_OPTIONS: list[dict[str, str]] = [
    *[{"id": f"cnc_{i}", "title": f"CNC-{i}"} for i in range(1, 10)],
    *[{"id": f"vmc_{i}", "title": f"VMC-{i}"} for i in range(1, 9)],
]

FETTLING_UNIT_I_MACHINE_OPTIONS: list[dict[str, str]] = [
    *[{"id": f"fet_{i}", "title": f"FET-{i}"} for i in range(1, 16)],
    {"id": "fet_17", "title": "FET-17"},
    {"id": "fet_18", "title": "FET-18"},
    {"id": "fet_19", "title": "FET-19"},
]

IOT_MACHINE_DEPARTMENTS = frozenset({"PDC", "CNC", "FETTLING"})

UNIT_I_MACHINES_BY_DEPT: dict[str, list[dict[str, str]]] = {
    "PDC": PDC_UNIT_I_MACHINE_OPTIONS,
    "CNC": CNC_UNIT_I_MACHINE_OPTIONS,
    "FETTLING": FETTLING_UNIT_I_MACHINE_OPTIONS,
}

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
    if isinstance(val, dict):
        val = val.get("id") or val.get("title")
    if val is None:
        return ""
    return str(val).strip().lower()


def _expand_form_data(form_data: dict) -> dict:
    merged = {
        k: v
        for k, v in (form_data or {}).items()
        if k not in ("error", "error_message")
    }
    fad = merged.get("flow_action_data")
    if isinstance(fad, str) and fad.strip().startswith("{"):
        try:
            parsed = json.loads(fad)
            if isinstance(parsed, dict):
                merged.update(parsed)
        except json.JSONDecodeError:
            logger.warning("it flow_action_data JSON parse failed")
    elif isinstance(fad, dict):
        merged.update(fad)
    return merged


def _phone_from_context(flow_data: dict, form_data: dict) -> str:
    for token_raw in (flow_data.get("flow_token"), form_data.get("flow_token")):
        phone = phone_from_flow_token(str(token_raw or ""))
        if phone:
            return phone
    for source in (flow_data, form_data):
        if not isinstance(source, dict):
            continue
        phone = phone_from_flow_token(str(source.get("flow_token") or ""))
        if phone:
            return phone
    for key in ("employee_phone", "phone", "phone_number", "employee_mobile"):
        raw = phone_to_10(str(form_data.get(key) or ""))
        if len(raw) == 10:
            return raw
    return ""


def _user_context(flow_data: dict, form_data: dict) -> tuple[str, str, str]:
    expanded = _expand_form_data(form_data)
    token = str(flow_data.get("flow_token") or expanded.get("flow_token") or "")
    phone, dept, route = it_user_context_from_token(token)
    if not phone:
        phone = _phone_from_context(flow_data, expanded)
    if not dept:
        dept = (expanded.get("employee_department") or expanded.get("department") or "").strip()
    if not route:
        route = (expanded.get("employee_jmd_route") or expanded.get("jmd_route") or "").strip().upper()
    if phone and (not dept or not route):
        ud = get_user_by_phone(phone) or {}
        if not dept:
            dept = (ud.get("department") or "").strip()
        if not route:
            route = (ud.get("jmd_route") or "").strip().upper()
    return phone, dept, route


def _normalize_iot_dept(dept: str) -> str:
    d = (dept or "").strip().upper()
    if d == "FET":
        return "FETTLING"
    if d in IOT_MACHINE_DEPARTMENTS:
        return d
    return ""


def _iot_machine_options(dept: str, route: str) -> list[dict[str, str]]:
    """Machine No list only for IoT + PDC/CNC/FETTLING on Unit I (JMD1)."""
    dept_key = _normalize_iot_dept(dept)
    if not dept_key or (route or "").strip().upper() != "JMD1":
        return []
    return list(UNIT_I_MACHINES_BY_DEPT.get(dept_key, []))


def _screen_data(form_data: dict, flow_data: dict) -> dict:
    expanded = _expand_form_data(form_data)
    category = _pick(expanded, "it_category")
    phone, dept, route = _user_context(flow_data, expanded)
    show_issue_type = bool(category)
    issue_options = ISSUE_TYPES_BY_CATEGORY.get(category, []) if show_issue_type else []
    # Machine No: IoT only, and only for PDC / CNC / FETTLING (Unit I).
    machine_options = _iot_machine_options(dept, route) if category == "iot" else []
    show_machine_no = category == "iot" and bool(machine_options)
    return {
        "category_options": CATEGORY_OPTIONS,
        "employee_phone": phone,
        "employee_department": dept,
        "employee_jmd_route": route,
        "machine_no_options": machine_options,
        "issue_type_options": issue_options,
        "show_machine_no": show_machine_no,
        "show_issue_type": show_issue_type,
    }


def build_it_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or IT_SCREEN).strip() or IT_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action not in _LOAD_ACTIONS:
        logger.warning("it flow unexpected action=%s", action)

    try:
        data = _screen_data(form_data, flow_data)
    except Exception:
        logger.exception("it screen data failed action=%s data=%s", action, form_data)
        data = {
            "category_options": CATEGORY_OPTIONS,
            "employee_phone": "",
            "employee_department": "",
            "employee_jmd_route": "",
            "machine_no_options": [],
            "issue_type_options": [],
            "show_machine_no": False,
            "show_issue_type": False,
        }

    logger.info(
        "it flow response action=%s category=%s phone=%s dept=%s route=%s "
        "machine_count=%s show_machine=%s",
        action,
        _pick(_expand_form_data(form_data), "it_category") or "-",
        data.get("employee_phone") or "-",
        data.get("employee_department") or "-",
        data.get("employee_jmd_route") or "-",
        len(data.get("machine_no_options") or []),
        data.get("show_machine_no"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
