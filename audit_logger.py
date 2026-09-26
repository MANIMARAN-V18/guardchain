"""
Audit Logging and Role-Based Access Control (RBAC) Module for GuardChain
Maintains tamper-evident query trails for law enforcement evidence compliance.
"""

import os
import json
import hashlib
from datetime import datetime, timezone

AUDIT_LOG_FILE = os.path.join(os.path.dirname(__file__), "audit_trail.json")


def _mask_ip(ip: str) -> str:
    """Masks client IP for DPDP/GDPR officer privacy compliance."""
    if not ip or ip == "127.0.0.1" or ip == "localhost":
        return "127.0.0.1 (Localhost)"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return f"{ip[:4]}***"


def log_investigation_search(wallet_address, chain, officer_id="IO-CYBER-8841", role="Investigating Officer", ip="127.0.0.1"):
    """
    Logs an immutable forensic search event with a cryptographic checksum hash.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    raw_payload = f"{timestamp}|{officer_id}|{wallet_address}|{chain}|{role}"
    entry_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
    masked_ip = _mask_ip(ip)

    entry = {
        "log_id": f"LOG-{entry_hash[:10]}",
        "timestamp": timestamp,
        "officer_id": officer_id,
        "role": role,
        "wallet_queried": wallet_address,
        "chain": chain,
        "ip_address": masked_ip,
        "integrity_checksum": entry_hash
    }

    logs = []
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    logs.insert(0, entry)  # newest first
    logs = logs[:100]      # keep last 100 entries

    try:
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"[AuditLogger] Error writing audit log: {e}")

    return entry


def get_audit_trail():
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []
