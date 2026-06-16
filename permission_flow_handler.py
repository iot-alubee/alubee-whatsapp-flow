"""Build WhatsApp Flow data-channel responses for the permission form."""

from __future__ import annotations

import json
import logging

from permission_times import (
    build_permission_time_slots,
    permission_types_for_user,
)
from users import (
    get_user_by_phone,
    is_rotational_shift_for_phone,
    is_supervisor_for_phone,
    phone_from_flow_token,
    phone_to_10,
)

logger = logging.getLogger(__name__)

SCREEN_FORM = "PERMISSION_FORM"
SCREEN_NO_ACCESS = "PERMISSION_NO_ACCESS"

_LOAD_ACTIONS = frozenset({"init", "navigate", "data_exchange"})

_EMPTY_SLOTS: list[dict[str, str]] = []

_HIDDEN = {
    "show_cl_name": False,
    "show_shift": False,
    "show_type": False,
    "show_expected_out": False,
    "show_expected_in": False,
    "show_reason": False,
    "permission_types": _EMPTY_SLOTS,
    "out_time_slots": _EMPTY_SLOTS,
    "in_time_slots": _EMPTY_SLOTS,
}


def _pick(data: dict, key: str) -> str:
    val = data.get(key)
    if val is None:
        return ""
    return str(val).strip().lower()


def _normalize_shift(raw: str) -> str:
    r = (raw or "").strip().lower().replace(" ", "_")
    if r in ("shift_ii", "shift2", "ii", "2"):
        return "II"
    if r in ("shift_i", "shift1", "i", "1"):
        return "I"
    return ""


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


def _cl_form_data() -> dict:
    return {
        "show_cl_name": True,
        "show_shift": True,
        "show_type": False,
        "show_expected_out": False,
        "show_expected_in": False,
        "show_reason": True,
        "permission_types": _EMPTY_SLOTS,
        "out_time_slots": _EMPTY_SLOTS,
        "in_time_slots": _EMPTY_SLOTS,
    }


def _myself_form_data(phone: str, expanded: dict) -> dict:
    ud = get_user_by_phone(phone) if phone else None
    show_shift = _needs_shift(phone, "myself")
    shift = _normalize_shift(_pick(expanded, "permission_shift"))
    permission_type = _pick(expanded, "permission_type")
    expected_out = str(expanded.get("expected_out") or "").strip()

    data = {
        "show_cl_name": False,
        "show_shift": show_shift,
        "show_type": False,
        "show_expected_out": False,
        "show_expected_in": False,
        "show_reason": False,
        "permission_types": _EMPTY_SLOTS,
        "out_time_slots": _EMPTY_SLOTS,
        "in_time_slots": _EMPTY_SLOTS,
    }

    if show_shift and not shift:
        return data

    shift_key = shift or "I"
    data["permission_types"] = permission_types_for_user(ud, shift_key)
    data["show_type"] = bool(data["permission_types"])

    if not permission_type:
        return data

    out_slots, in_slots = build_permission_time_slots(
        ud,
        permission_shift=shift_key,
        permission_type=permission_type,
        expected_out=expected_out,
    )
    data["out_time_slots"] = out_slots
    data["in_time_slots"] = in_slots
    data["show_expected_out"] = bool(out_slots)
    data["show_expected_in"] = bool(in_slots)
    data["show_reason"] = True
    return data


def build_permission_flow_response(flow_data: dict) -> dict:
    action = (flow_data.get("action") or "").strip().lower()
    screen = (flow_data.get("screen") or "").strip().upper()
    form_data = flow_data.get("data") if isinstance(flow_data.get("data"), dict) else {}
    expanded = _expand_form_data(form_data)

    if action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    if action not in _LOAD_ACTIONS:
        logger.warning("permission flow unexpected action=%s", action)

    phone = _phone_from_context(flow_data, expanded)
    try:
        is_supervisor = is_supervisor_for_phone(phone) if phone else False
    except Exception:
        logger.exception("permission supervisor lookup failed phone=%s", phone)
        is_supervisor = False

    permission_for = _pick(expanded, "permission_for")

    try:
        if action in ("init", "navigate"):
            screen = SCREEN_FORM
            data = dict(_HIDDEN)
        elif permission_for == "cl" and not is_supervisor:
            screen = SCREEN_NO_ACCESS
            data = {}
        elif permission_for == "cl":
            screen = SCREEN_FORM
            data = _cl_form_data()
        elif permission_for == "myself":
            screen = SCREEN_FORM
            data = _myself_form_data(phone, expanded)
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
        "for=%s shift=%s type=%s screen=%s show_type=%s types=%s",
        action,
        flow_data.get("flow_token"),
        phone,
        is_supervisor,
        permission_for or "-",
        _normalize_shift(_pick(expanded, "permission_shift")) or "-",
        _pick(expanded, "permission_type") or "-",
        screen,
        data.get("show_type"),
        len(data.get("permission_types") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
