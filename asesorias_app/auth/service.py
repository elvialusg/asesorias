"""Servicios de autenticación y seguridad para controlTesis."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

from asesorias_app.core.utils import fix_text_encoding

from .user_sheet_repository import UserSheetRepository

PASSWORD_ITERATIONS = 390_000
RESET_TOKEN_TTL = 3600  # 1 hora

ROLE_FEATURES: Dict[str, Set[str]] = {
    "administrador": {"*"},
    "direccion": {"register", "consult", "normalizacion", "publicacion", "dashboard", "admin"},
    "normalizacion": {"register", "consult", "normalizacion", "dashboard"},
    "publicacion": {"register", "consult", "publicacion", "dashboard"},
    "servicios": {"register", "consult"},
    "colaborador": {"register", "consult"},
}


@dataclass
class AuthUser:
    email: str
    name: str
    role: str
    must_reset: bool

    @property
    def is_admin(self) -> bool:
        return self.role.strip().lower() == "administrador"


_user_repo = UserSheetRepository()


def _normalize_email(email: str) -> str:
    return (fix_text_encoding(email, strip=True) or "").lower()


def _role_key(role: Optional[str]) -> str:
    if not role:
        return "colaborador"
    return fix_text_encoding(role, strip=True).lower()


def _bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    text = (str(value).strip().lower()) if value is not None else ""
    if not text:
        return False
    return text in {"1", "true", "si", "sí", "yes"}


def _int_value(value) -> Optional[int]:
    if value in (None, "", "None"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return base64.b64encode(salt).decode("utf-8") + ":" + base64.b64encode(derived).decode("utf-8")


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split(":")
    except ValueError:
        return False
    try:
        salt = base64.b64decode(salt_b64)
        stored_hash = base64.b64decode(hash_b64)
    except Exception:
        return False
    new_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return secrets.compare_digest(stored_hash, new_hash)


def _load_store() -> Dict[str, dict]:
    rows = _user_repo.load_users()
    store: Dict[str, dict] = {}
    for row in rows:
        email = _normalize_email(row.get("email", ""))
        if not email:
            continue
        name = fix_text_encoding(row.get("name"), strip=True) or ""
        role = fix_text_encoding(row.get("role"), strip=True) or "colaborador"
        store[email] = {
            "email": email,
            "name": name,
            "role": role,
            "password_hash": row.get("password_hash") or "",
            "must_reset": _bool_value(row.get("must_reset")),
            "reset_token": row.get("reset_token") or None,
            "reset_token_expire": _int_value(row.get("reset_token_expire")),
        }
    return store


def _save_store(store: Dict[str, dict]) -> None:
    records = []
    for record in store.values():
        records.append(
            {
                "email": record["email"],
                "name": record.get("name", ""),
                "role": record.get("role", "colaborador"),
                "password_hash": record.get("password_hash", ""),
                "must_reset": record.get("must_reset", False),
                "reset_token": record.get("reset_token") or "",
                "reset_token_expire": record.get("reset_token_expire") or "",
            }
        )
    records.sort(key=lambda item: item["email"])
    _user_repo.save_users(records)


def ensure_user_record(email: str) -> bool:
    store = _load_store()
    return _normalize_email(email) in store


def authenticate(email: str, password: str) -> Optional[AuthUser]:
    store = _load_store()
    user = store.get(_normalize_email(email))
    if not user:
        return None
    stored_hash = user.get("password_hash") or ""
    updated = False
    if ":" not in stored_hash:
        if not secrets.compare_digest(stored_hash, password):
            return None
        user["password_hash"] = _hash_password(password)
        user["must_reset"] = False
        updated = True
    elif not _verify_password(password, stored_hash):
        if password == stored_hash:
            user["password_hash"] = _hash_password(password)
            user["must_reset"] = False
            updated = True
        else:
            return None
    if updated:
        _save_store(store)
    return AuthUser(
        email=user["email"],
        name=user["name"],
        role=user["role"],
        must_reset=bool(user.get("must_reset")),
    )


def change_password(email: str, current_password: str, new_password: str) -> bool:
    store = _load_store()
    key = _normalize_email(email)
    user = store.get(key)
    if not user or not _verify_password(current_password, user["password_hash"]):
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_reset"] = False
    _save_store(store)
    return True


def create_reset_token(email: str) -> Optional[str]:
    store = _load_store()
    key = _normalize_email(email)
    user = store.get(key)
    if not user:
        return None
    token = secrets.token_hex(3).upper()
    user["reset_token"] = token
    user["reset_token_expire"] = int(time.time()) + RESET_TOKEN_TTL
    _save_store(store)
    return token


def reset_password(email: str, token: str, new_password: str) -> bool:
    store = _load_store()
    key = _normalize_email(email)
    user = store.get(key)
    if not user or not token:
        return False
    if user.get("reset_token") != token.upper():
        return False
    expire = user.get("reset_token_expire")
    if expire and int(time.time()) > int(expire):
        return False
    user["password_hash"] = _hash_password(new_password)
    user["reset_token"] = None
    user["reset_token_expire"] = None
    user["must_reset"] = False
    _save_store(store)
    return True


def list_users() -> Dict[str, dict]:
    return _load_store()


def allowed_features(role: Optional[str]) -> Set[str]:
    normalized = _role_key(role)
    features = ROLE_FEATURES.get(normalized)
    if not features:
        return ROLE_FEATURES["colaborador"]
    return features


def can_access_feature(user: AuthUser, feature: str) -> bool:
    scope = allowed_features(user.role)
    return "*" in scope or feature in scope


def needs_password_setup(email: str) -> bool:
    store = _load_store()
    user = store.get(_normalize_email(email))
    if not user:
        return False
    if not user.get("password_hash"):
        return True
    return bool(user.get("must_reset"))


def set_initial_password(email: str, new_password: str, *, force: bool = False) -> bool:
    store = _load_store()
    key = _normalize_email(email)
    user = store.get(key)
    if not user:
        return False
    if not user.get("must_reset") and not force:
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_reset"] = False
    user["reset_token"] = None
    user["reset_token_expire"] = None
    _save_store(store)
    return True
