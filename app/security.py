import json
import re
import secrets
import unicodedata
from html import escape as html_escape

import bcrypt
from starlette.requests import Request


def hash_password(password: str) -> str:
    data = password.encode("utf-8")[:72]
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        data = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(data, hashed.encode("utf-8"))
    except Exception:
        return False


def e(value) -> str:
    if value is None:
        return ""
    return html_escape(str(value), quote=True)


def clean_string(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"<[^>]+>", "", value).strip()


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text or f"item-{secrets.token_hex(4)}"


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf(request: Request, token: str | None) -> bool:
    expected = request.session.get("csrf_token")
    if not expected or not token:
        return False
    return secrets.compare_digest(str(expected), str(token))


def parse_features(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def money(value) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def money0(value) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "0"
