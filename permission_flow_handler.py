"""Build WhatsApp Flow data-channel responses for the permission form."""

from __future__ import annotations

import json
import logging

from permission_times import (
    build_permission_time_slots,
    normalize_permission_time_label,
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

_DEFAULT_PERMISSION_TYPES = [
    {"id": "late_in", "title": "Late IN"},
    {"id": "early_out", "title": "Early OUT"},
    {"id": "other", "title": "Other"},
]

# Before user picks For Myself / For CL — only the radio is shown.
_HIDDEN = {
    "show_cl_name": False,
    "show_shift": False,
    "show_type": False,
    "show_reason": False,
    "show_expected_in": False,
    "show_expected_out": False,
    "permission_types": _DEFAULT_PERMISSION_TYPES,
    "out_time_slots": [],
    "in_time_slots": [],
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


def _normalize_shift(raw: str) -> str:
    s = (raw or "").strip().lower().replace(" ", "_")
    if s in ("shift_ii", "shift2", "ii", "2"):
        return "II"
    if s in ("shift_i", "shift1", "i", "1"):
        return "I"
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


def _effective_shift(
    phone: str, permission_for: str, permission_shift: str, ud: dict | None
) -> str:
    shift = _normalize_shift(permission_shift)
    if permission_for == "cl":
        return shift or "I"
    if ud and (ud.get("shift_type") or "GS").strip().upper() == "GS":
        return "I"
    return shift or "I"


def _time_slot_fields(
    ud: dict | None,
    *,
    permission_shift: str,
    permission_type: str,
    expected_out: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not ud:
        return [], []
    if (
        (ud.get("shift_type") or "GS").strip().upper() == "RS"
        and permission_shift not in ("I", "II")
    ):
        return [], []
    return build_permission_time_slots(
        ud,
        permission_shift=permission_shift,
        permission_type=permission_type,
        expected_out=expected_out,
    )


def _myself_form_data(
    phone: str,
    *,
    permission_type: str = "",
    permission_shift: str = "",
    expected_out: str = "",
) -> dict:
    ud = get_user_by_phone(phone) if phone else None
    show_shift = _needs_shift(phone, "myself")
    shift = _effective_shift(phone, "myself", permission_shift, ud)
    pt = _normalize_permission_type(permission_type)
    perm_types = permission_types_for_user(ud, shift)

    if pt == "other" and shift == "II" and (ud or {}).get("shift_type", "").strip().upper() == "RS":
        pt = ""

    out_slots, in_slots = (
        _time_slot_fields(ud, permission_shift=shift, permission_type=pt, expected_out=expected_out)
        if pt
        else ([], [])
    )

    expected_out_label = normalize_permission_time_label(expected_out)
    show_out = pt in ("early_out", "other")
    show_in = pt == "late_in" or (pt == "other" and bool(expected_out_label))
    show_reason = bool(pt) and (pt != "other" or bool(expected_out_label))

    return {
        "show_cl_name": False,
        "show_shift": show_shift,
        "show_type": True,
        "show_reason": show_reason,
        "show_expected_out": show_out,
        "show_expected_in": show_in,
        "permission_types": perm_types,
        "out_time_slots": out_slots,
        "in_time_slots": in_slots,
    }


def _cl_form_data(phone: str, *, permission_shift: str = "") -> dict:
    ud = get_user_by_phone(phone) if phone else None
    # CL permission is Unit I / Shift I only.
    shift = "I"
    out_slots, _ = _time_slot_fields(
        ud,
        permission_shift=shift,
        permission_type="early_out",
        expected_out="",
    )
    return {
        "show_cl_name": True,
        "show_shift": False,
        "show_type": False,
        "show_reason": True,
        "show_expected_in": False,
        "show_expected_out": True,
        "permission_types": _DEFAULT_PERMISSION_TYPES,
        "out_time_slots": out_slots,
        "in_time_slots": [],
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
    permission_shift = _pick(expanded, "permission_shift")
    expected_out = str(expanded.get("expected_out_time") or "").strip()

    try:
        if action in ("init", "navigate"):
            screen = SCREEN_FORM
            data = dict(_HIDDEN)
        elif permission_for == "cl" and not is_supervisor:
            screen = SCREEN_NO_ACCESS
            data = {}
        elif permission_for == "cl":
            screen = SCREEN_FORM
            data = _cl_form_data(phone, permission_shift=permission_shift)
        elif permission_for == "myself":
            screen = SCREEN_FORM
            data = _myself_form_data(
                phone,
                permission_type=permission_type,
                permission_shift=permission_shift,
                expected_out=expected_out,
            )
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
        "for=%s type=%s shift=%s out_slots=%s in_slots=%s",
        action,
        flow_data.get("flow_token"),
        phone,
        is_supervisor,
        permission_for or "-",
        permission_type or "-",
        permission_shift or "-",
        len(data.get("out_time_slots") or []),
        len(data.get("in_time_slots") or []),
    )

    return {
        "version": "3.0",
        "screen": screen,
        "data": data,
    }
