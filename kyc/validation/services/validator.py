from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class ValidationResult:
    document_valid: bool
    checks: List[Dict]
    confidence: float

def _mrz_checksum_ok(mrz: str) -> bool:
    # Mock: valide si longueur>30 et contient '<'
    return bool(mrz and len(mrz) > 30 and "<" in mrz)

def _date_iso_ok(date_str: str) -> bool:
    try:
        y,m,d = date_str.split("-")
        return len(y)==4 and 1<=int(m)<=12 and 1<=int(d)<=31
    except Exception:
        return False

def validate_document(*, detected: Dict, fields: Dict) -> ValidationResult:
    checks = []
    # MRZ checksum
    mrz_ok = _mrz_checksum_ok(fields.get("mrz",""))
    checks.append({"name":"mrz_checksum","status":"pass" if mrz_ok else "fail"})

    # expiry future
    expiry_ok = _date_iso_ok(fields.get("expiry_date",""))
    checks.append({"name":"expiry_future","status":"pass" if expiry_ok else "fail"})

    # dob past
    dob_ok = _date_iso_ok(fields.get("dob",""))
    checks.append({"name":"dob_past","status":"pass" if dob_ok else "fail"})

    ok = all(c["status"]=="pass" for c in checks)
    conf = 0.9 if ok else 0.6
    return ValidationResult(document_valid=ok, checks=checks, confidence=conf)
