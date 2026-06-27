"""Build WhatsApp Flow data-channel responses for the Maintenance Request form."""

from __future__ import annotations

import json
import logging

from maintenance_data import (
    all_issue_category_options,
    default_machine_type,
    infer_machine_type,
    machine_no_options,
)
from users import get_user_by_phone, maintenance_user_context_from_token, phone_from_flow_token

logger = logging.getLogger(__name__)

MAINTENANCE_SCREEN = "MAINTENANCE_FORM"
_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if isinstance(val, dict):
        val = val.get("id") or val.get("title")
    if val is None:
        return ""
    return str(val).strip().lower()


def _expand_form_data(form_data: dict) -> dict:
    merged = dict(form_data or {})
    fad = merged.get("flow_action_data")
    if isinstance(fad, str) and fad.strip().startswith("{"):
        try:
            parsed = json.loads(fad)
            if isinstance(parsed, dict):
                merged.update(parsed)
        except json.JSONDecodeError:
            logger.warning("maintenance flow_action_data JSON parse failed")
    elif isinstance(fad, dict):
        merged.update(fad)
    return merged


def _normalize_route(route: str) -> str:
    r = (route or "").strip().upper()
    if r in ("JMD1", "UNIT_I", "UNIT1", "UNIT-1", "UNIT 1"):
        return "JMD1"
    if r in ("JMD2", "UNIT_II", "UNIT2", "UNIT-2", "UNIT 2"):
        return "JMD2"
    return r


def _user_context(flow_data: dict, form_data: dict) -> tuple[str, str, str]:
    expanded = _expand_form_data(form_data)
    token = str(flow_data.get("flow_token") or expanded.get("flow_token") or "")
    phone, token_dept, token_route = maintenance_user_context_from_token(token)
    if not phone:
        phone = phone_from_flow_token(token)

    dept = (expanded.get("employee_department") or expanded.get("department") or "").strip()
    route = _normalize_route(
        expanded.get("employee_jmd_route") or expanded.get("jmd_route") or ""
    )

    # Firestore is source of truth when the user is known (avoids stale flow_token dept).
    if phone:
        ud = get_user_by_phone(phone) or {}
        if ud.get("department"):
            dept = (ud.get("department") or "").strip()
        if ud.get("jmd_route"):
            route = _normalize_route(ud.get("jmd_route") or "")

    if not dept:
        dept = token_dept
    if not route:
        route = _normalize_route(token_route)

    return phone, dept.upper(), route.upper()


def _screen_data(form_data: dict, flow_data: dict, *, action: str = "") -> dict:
    expanded = _expand_form_data(form_data)
    phone, dept, route = _user_context(flow_data, expanded)
    dept_key = dept.upper() if dept else ""
    if dept_key == "FET":
        dept_key = "FETTLING"

    # Meta Flow Builder preview only — no user / token on publish health check.
    if not dept_key and not phone and action in _LOAD_ACTIONS:
        dept_key = "PDC"
        route = route or "JMD1"

    machine_no = _pick(expanded, "machine_no")
    machine_type = (
        _pick(expanded, "machine_type")
        or infer_machine_type(dept_key, machine_no)
        or default_machine_type(dept_key)
    )

    machine_opts = machine_no_options(dept_key, route) if dept_key else []
    issue_opts = all_issue_category_options(dept_key) if dept_key else []

    return {
        "employee_phone": phone,
        "employee_department": dept_key,
        "employee_jmd_route": route,
        "machine_no_options": machine_opts,
        "issue_category_options": issue_opts,
    }


def build_maintenance_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or MAINTENANCE_SCREEN).strip() or MAINTENANCE_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action not in _LOAD_ACTIONS:
        logger.warning("maintenance flow unexpected action=%s", action)

    try:
        data = _screen_data(form_data, flow_data, action=action)
    except Exception:
        logger.exception("maintenance screen data failed action=%s", action)
        data = {
            "employee_phone": "",
            "employee_department": "",
            "employee_jmd_route": "",
            "machine_no_options": [],
            "issue_category_options": [],
        }

    expanded = _expand_form_data(form_data)
    machine_no = _pick(expanded, "machine_no")
    dept_key = data.get("employee_department") or ""
    machine_type = (
        _pick(expanded, "machine_type")
        or infer_machine_type(dept_key, machine_no)
        or default_machine_type(dept_key)
        or "-"
    )
    logger.info(
        "maintenance flow action=%s dept=%s route=%s machine_type=%s machines=%s issues=%s",
        action,
        dept_key or "-",
        data.get("employee_jmd_route") or "-",
        machine_type,
        len(data.get("machine_no_options") or []),
        len(data.get("issue_category_options") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
