"""Build WhatsApp Flow data-channel responses for the permission form."""

from __future__ import annotations

import json
import logging

from users import (
    is_rotational_shift_for_phone,
    is_supervisor_for_phone,
    phone_from_flow_token,
    phone_to_10,
)

logger = logging.getLogger(__name__)

PERMISSION_SCREEN = "PERMISSION_FORM"

_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _is_supervisor_flag(data: dict) -> bool:
    val = data.get("is_supervisor")
    if val is True:
        return True
    if val is False:
        return False
    return str(val).strip().lower() in ("1", "true", "yes", "on")


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
            logger.warning("permission flow_action_data JSON parse failed")
    elif isinstance(fad, dict):
        merged.update(fad)
    return merged


def _phone_from_context(flow_data: dict, form_data: dict) -> str:
    for source in (flow_data, form_data):
        if not isinstance(source, dict):
            continue
        phone = phone_from_flow_token(str(source.get("flow_token") or ""))
        if phone:
            return phone
    for key in ("phone", "phone_number", "employee_mobile"):
        raw = phone_to_10(str(form_data.get(key) or ""))
        if len(raw) == 10:
            return raw
    return ""


def _resolve_is_supervisor(flow_data: dict, form_data: dict) -> tuple[bool, str]:
    phone = _phone_from_context(flow_data, form_data)
    if phone:
        try:
            return is_supervisor_for_phone(phone), phone
        except Exception:
            logger.exception("permission supervisor lookup failed phone=%s", phone)
    return _is_supervisor_flag(form_data), phone


def _needs_shift(phone: str, permission_for: str) -> bool:
    if permission_for == "cl":
        return True
    if not phone:
        return True
    try:
        return is_rotational_shift_for_phone(phone)
    except Exception:
        logger.exception("permission shift lookup failed phone=%s", phone)
        return True


def _screen_data(flow_data: dict, form_data: dict) -> dict:
    expanded = _expand_form_data(form_data)
    is_supervisor, phone = _resolve_is_supervisor(flow_data, expanded)
    permission_for = _pick(expanded, "permission_for")
    if not permission_for and not is_supervisor:
        permission_for = "myself"
    is_cl = permission_for == "cl"
    show_shift = _needs_shift(phone, permission_for)
    return {
        "show_permission_for": is_supervisor,
        "show_cl_name": is_cl,
        "show_shift": show_shift,
        "show_type": not is_cl,
    }


def build_permission_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or "").strip() or PERMISSION_SCREEN
    if action in ("init", "navigate"):
        screen = PERMISSION_SCREEN
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action not in _LOAD_ACTIONS:
        logger.warning("permission flow unexpected action=%s", action)

    try:
        data = _screen_data(flow_data, form_data)
    except Exception:
        logger.exception(
            "permission screen data failed action=%s token=%s data=%s",
            action,
            flow_data.get("flow_token"),
            form_data,
        )
        data = {
            "show_permission_for": False,
            "show_cl_name": False,
            "show_shift": True,
            "show_type": True,
        }

    is_supervisor, phone = _resolve_is_supervisor(flow_data, _expand_form_data(form_data))
    logger.info(
        "permission flow response action=%s token=%s phone=%s supervisor=%s "
        "show_for=%s show_shift=%s show_cl=%s show_type=%s",
        action,
        flow_data.get("flow_token"),
        phone,
        is_supervisor,
        data.get("show_permission_for"),
        data.get("show_shift"),
        data.get("show_cl_name"),
        data.get("show_type"),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
