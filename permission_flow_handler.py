"""Build WhatsApp Flow data-channel responses for the permission form."""

from __future__ import annotations

import json
import logging

from permission_times import permission_time_slot_options
from users import (
    is_rotational_shift_for_phone,
    is_supervisor_for_phone,
    phone_from_flow_token,
    phone_to_10,
)

logger = logging.getLogger(__name__)

SCREEN_FORM = "PERMISSION_FORM"
SCREEN_NO_ACCESS = "PERMISSION_NO_ACCESS"

_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})

_TIME_SLOTS = permission_time_slot_options()

# Before user picks For Myself / For CL — only the radio is shown.
_HIDDEN = {
    "show_cl_name": False,
    "show_shift": False,
    "show_type": False,
    "show_reason": False,
    "show_expected_in": False,
    "show_expected_out": False,
    "time_slots": _TIME_SLOTS,
}


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _normalize_permission_type(raw: str) -> str:
    s = (raw or "").strip().lower().replace(" ", "_")
    if s in ("late_in", "latein", "late"):
        return "late_in"
    if s in ("early_out", "earlyout", "early"):
        return "early_out"
    if s == "other":
        return "other"
    return ""


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


def _myself_form_data(phone: str, permission_type: str = "") -> dict:
    show_shift = _needs_shift(phone, "myself")
    pt = _normalize_permission_type(permission_type)
    return {
        "show_cl_name": False,
        "show_shift": show_shift,
        "show_type": True,
        "show_reason": bool(pt),
        "show_expected_in": pt in ("late_in", "other"),
        "show_expected_out": pt in ("early_out", "other"),
        "time_slots": _TIME_SLOTS,
    }


def _cl_form_data(phone: str) -> dict:
    return {
        "show_cl_name": True,
        "show_shift": True,
        "show_type": False,
        "show_reason": True,
        "show_expected_in": False,
        "show_expected_out": True,
        "time_slots": _TIME_SLOTS,
    }


def build_permission_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or "").strip().upper()
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}
    expanded = _expand_form_data(form_data)

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action not in _LOAD_ACTIONS:
        logger.warning("permission flow unexpected action=%s", action)

    is_supervisor, phone = _resolve_is_supervisor(flow_data, expanded)
    permission_for = _pick(expanded, "permission_for")
    permission_type = _pick(expanded, "permission_type")

    try:
        if action in ("init", "navigate"):
            screen = SCREEN_FORM
            data = dict(_HIDDEN)
        elif permission_for == "cl" and not is_supervisor:
            screen = SCREEN_NO_ACCESS
            data = {}
        elif permission_for == "cl":
            screen = SCREEN_FORM
            data = _cl_form_data(phone)
        elif permission_for == "myself":
            screen = SCREEN_FORM
            data = _myself_form_data(phone, permission_type)
        elif screen == SCREEN_NO_ACCESS:
            data = {}
        else:
            screen = SCREEN_FORM
            data = dict(_HIDDEN)
    except Exception:
        logger.exception(
            "permission screen data failed action=%s token=%s data=%s",
            action,
            flow_data.get("flow_token"),
            form_data,
        )
        screen = SCREEN_FORM
        data = dict(_HIDDEN)

    logger.info(
        "permission flow response action=%s token=%s phone=%s supervisor=%s "
        "for=%s type=%s screen=%s data=%s",
        action,
        flow_data.get("flow_token"),
        phone,
        is_supervisor,
        permission_for or "-",
        permission_type or "-",
        screen,
        data,
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
