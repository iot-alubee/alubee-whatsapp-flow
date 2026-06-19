"""Firestore user lookup for WhatsApp Flow (permission supervisor routing)."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

_db = None


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw or "")


def _get_db():
    global _db
    if _db is not None:
        return _db
    project = (os.getenv("FIREBASE_PROJECT_ID") or "whatsapp-approval-system").strip()
    try:
        from google.cloud import firestore

        _db = firestore.Client(project=project)
        return _db
    except Exception:
        logger.exception("Firestore client init failed project=%s", project)
        return None


def phone_to_10(phone: str) -> str:
    d = _digits(phone)
    if len(d) >= 10:
        return d[-10:]
    return d


def wa_id_from_phone(phone: str) -> str:
    d = phone_to_10(phone)
    if len(d) == 10:
        return f"whatsapp:+91{d}"
    return ""


def phone_from_flow_token(token: str) -> str:
    t = (token or "").strip()
    if t.lower().startswith("it_"):
        first = t[3:].split("_", 1)[0]
        d = _digits(first)
        if len(d) == 10:
            return d
    for prefix in ("perm_", "leave_", "visitor_", "od_", "it_"):
        if t.lower().startswith(prefix):
            d = _digits(t[len(prefix) :])
            if len(d) == 10:
                return d
    d = _digits(t)
    if len(d) == 10:
        return d
    if len(d) >= 12 and d.startswith("91"):
        return d[-10:]
    return ""


def it_user_context_from_token(token: str) -> tuple[str, str, str]:
    """Parse it_{phone} or it_{phone}_{dept}_{route} flow tokens."""
    t = (token or "").strip()
    if not t.lower().startswith("it_"):
        return "", "", ""
    parts = [p for p in t[3:].split("_") if p]
    if not parts:
        return "", "", ""
    phone = _digits(parts[0])
    if len(phone) != 10:
        return "", "", ""
    if len(parts) < 3:
        return phone, "", ""
    dept = parts[1].strip().upper()
    if dept == "FET":
        dept = "FETTLING"
    route = parts[2].strip().upper()
    return phone, dept, route


def get_user_by_phone(phone: str) -> dict | None:
    wa_id = wa_id_from_phone(phone)
    if not wa_id:
        return None
    db = _get_db()
    if not db:
        return None
    try:
        snap = db.collection("users").document(wa_id).get()
        if snap.exists:
            return snap.to_dict() or {}
    except Exception:
        logger.exception("users read failed wa_id=%s", wa_id)
    return None


def is_supervisor_for_phone(phone: str) -> bool:
    ud = get_user_by_phone(phone)
    return bool(ud and ud.get("is_supervisor"))


def is_rotational_shift_for_phone(phone: str) -> bool:
    ud = get_user_by_phone(phone)
    return (ud or {}).get("shift_type", "").strip().upper() == "RS"
