"""Available company vehicles for OD WhatsApp Flow dropdown."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_db = None


def _ist_tzinfo():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Kolkata")
    except ImportError:
        return timezone(timedelta(hours=5, minutes=30))


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


def fetch_available_vehicles() -> list[dict[str, str]]:
    """
    Dropdown items for WhatsApp Flow: ``{"id": vehicle_id, "title": label}``.

    Every active vehicle is listed, including ones already out on another OD.
    Falls back to demo vehicles when Firestore is unavailable.
    """
    db = _get_db()
    if not db:
        return _demo_vehicles()

    available: list[dict[str, str]] = []
    try:
        for snap in db.collection("vehicles").stream():
            d = snap.to_dict() or {}
            if d.get("active") is False:
                continue
            vid = (d.get("vehicle_id") or snap.id or "").strip().upper()
            if not vid:
                continue
            desc = (d.get("description") or d.get("vehicle") or vid).strip()
            title = f"{desc} ({vid})" if desc != vid else vid
            available.append({"id": vid, "title": title[:80]})
    except Exception:
        logger.exception("vehicles collection read failed")
        return _demo_vehicles()

    available.sort(key=lambda v: v.get("title") or v.get("id") or "")
    return available or _demo_vehicles()


def _demo_vehicles() -> list[dict[str, str]]:
    """Used when Firestore is not configured (local Flow endpoint testing)."""
    return [
        {"id": "TN01AB1234", "title": "Demo vehicle TN01AB1234"},
        {"id": "TN01CD5678", "title": "Demo vehicle TN01CD5678"},
    ]
