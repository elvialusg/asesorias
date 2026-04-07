"""Servicios de autenticación y seguridad para TesisFlow."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

from asesorias_app import config
from asesorias_app.core.utils import fix_text_encoding

USERS_FILE = config.DATA_DIR / "users.json"
PASSWORD_ITERATIONS = 390_000
RESET_TOKEN_TTL = 3600  # 1 hora
DEFAULT_PASSWORD = "TesisFlow2024!"
ADMIN_EMAIL = "biblio_data@umanizales.edu.co"

# Mapa básico de permisos por rol. Sirve para habilitar características específicas
# (register, consult, normalizacion, publicacion, dashboard, admin) sin reescribir
# el servicio cuando aparezcan nuevos módulos.
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


DEFAULT_USERS = [
    {
        "email": "dir_biblioteca@umanizales.edu.co",
        "name": "Diego Alejandro Soto Herrera",
        "role": "direccion",
    },
    {
        "email": "referencia@umanizales.edu.co",
        "name": "José Wilman Tangarife Cardona",
        "role": "normalizacion",
    },
    {
        "email": "prestamo1@umanizales.edu.co",
        "name": "Álvaro de Jesús Agudelo López",
        "role": "normalizacion",
    },
    {
        "email": "referencia2@umanizales.edu.co",
        "name": "Juan Manuel Ramírez Orozco",
        "role": "normalizacion",
    },
    {
        "email": "bibliobe@umanizales.edu.co",
        "name": "Harold García Álvarez",
        "role": "normalizacion",
    },
    {
        "email": "biblio_publicacion@umanizales.edu.co",
        "name": "Luz Andrea Sepúlveda Escobar",
        "role": "publicacion",
    },
    {
        "email": "biblio_servicios@umanizales.edu.co",
        "name": "María Eugenia Nieto Medina",
        "role": "servicios",
    },
    {
        "email": "formacion@umanizales.edu.co",
        "name": "Juan Pablo Charry Osorio",
        "role": "normalizacion",
    },
    {
        "email": "gescontenidos@umanizales.edu.co",
        "name": "Gloria Patricia Quintero Serna",
        "role": "publicacion",
    },
    {
        "email": "aux_gescontenidos@umanizales.edu.co",
        "name": "Diana Patricia Salazar Martinez",
        "role": "publicacion",
    },
    {
        "email": ADMIN_EMAIL,
        "name": "Elvia Lucia Sánchez García",
        "role": "administrador",
    },
]


def _normalize_email(email: str) -> str:
    return (fix_text_encoding(email, strip=True) or "").lower()


def _role_key(role: Optional[str]) -> str:
    if not role:
        return "colaborador"
    return fix_text_encoding(role, strip=True).lower()


DEFAULT_USER_EMAILS = {_normalize_email(user["email"]) for user in DEFAULT_USERS}
DEFAULT_USERS_MAP = {
    _normalize_email(user["email"]): {
        "email": _normalize_email(user["email"]),
        "name": fix_text_encoding(user["name"], strip=True),
        "role": _role_key(user.get("role")),
    }
    for user in DEFAULT_USERS
}


def is_authorized_user(email: str) -> bool:
    normalized = _normalize_email(email)
    if normalized in DEFAULT_USERS_MAP:
        return True
    store = _load_store()
    return normalized in store


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return base64.b64encode(salt).decode("utf-8") + ":" + base64.b64encode(derived).decode("utf-8")


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split(":")
        salt = base64.b64decode(salt_b64)
        stored_hash = base64.b64decode(hash_b64)
        new_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
        return secrets.compare_digest(stored_hash, new_hash)
    except Exception:
        return False


def _load_store() -> Dict[str, dict]:
    if not USERS_FILE.exists():
        ensure_default_users()
    if not USERS_FILE.exists():
        return {}
    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return {record["email"].lower(): record for record in data}


def _save_store(store: Dict[str, dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(list(store.values()), indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_default_users() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, dict] = {}
    if USERS_FILE.exists():
        try:
            current_data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current_data = []
        existing = {
            _normalize_email(record.get("email", "")): record
            for record in current_data
            if record.get("email")
        }
    updated = False
    for user in DEFAULT_USERS:
        key = _normalize_email(user["email"])
        name = fix_text_encoding(user["name"], strip=True)
        role = _role_key(user.get("role"))
        if key not in existing:
            existing[key] = {
                "email": key,
                "name": name,
                "role": role,
                "password_hash": _hash_password(DEFAULT_PASSWORD),
                "must_reset": True,
                "reset_token": None,
                "reset_token_expire": None,
            }
            updated = True
        else:
            current = existing[key]
            cleaned_name = fix_text_encoding(current.get("name") or name, strip=True)
            if cleaned_name != current.get("name"):
                current["name"] = cleaned_name
                updated = True
            if _role_key(current.get("role")) != role:
                current["role"] = role
                updated = True
    if not USERS_FILE.exists() or updated:
        USERS_FILE.write_text(json.dumps(list(existing.values()), indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_user_record(email: str) -> bool:
    normalized = _normalize_email(email)
    template = DEFAULT_USERS_MAP.get(normalized)
    if not template:
        return False
    store = _load_store()
    if normalized not in store:
        store[normalized] = {
            "email": normalized,
            "name": template["name"],
            "role": template["role"],
            "password_hash": _hash_password(DEFAULT_PASSWORD),
            "must_reset": True,
            "reset_token": None,
            "reset_token_expire": None,
        }
        _save_store(store)
    return True


def authenticate(email: str, password: str) -> Optional[AuthUser]:
    store = _load_store()
    user = store.get(_normalize_email(email))
    if not user or not _verify_password(password, user["password_hash"]):
        return None
    return AuthUser(
        email=user["email"],
        name=user["name"],
        role=_role_key(user.get("role")),
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
    if user.get("reset_token_expire") and int(time.time()) > user["reset_token_expire"]:
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
    return bool(user and user.get("must_reset"))


def set_initial_password(email: str, new_password: str, *, force: bool = False) -> bool:
    store = _load_store()
    key = _normalize_email(email)
    user = store.get(key)
    if not user:
        return False
    if not user.get("must_reset") and not force:
        return False
    if force and key not in DEFAULT_USER_EMAILS:
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_reset"] = False
    user["reset_token"] = None
    user["reset_token_expire"] = None
    _save_store(store)
    return True
