import re
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# Only session tokens are accepted; tokens issued for any other purpose are rejected.
SESSION = "session"

PASSWORD_RULES = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a number and a special character."
)

_SPECIAL_CHARS = r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def validate_password(password: str) -> str:
    """Raises ValueError when the password doesn't meet the complexity rules."""
    if (
        len(password) < 8
        or not re.search(r"[A-Z]", password)
        or not re.search(r"\d", password)
        or not re.search(_SPECIAL_CHARS, password)
    ):
        raise ValueError(PASSWORD_RULES)
    return password


def create_token(subject: str, purpose: str = SESSION, expires_in: timedelta | None = None) -> str:
    if expires_in is None:
        expires_in = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "purpose": purpose,
        "exp": datetime.now(timezone.utc) + expires_in,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, purpose: str = SESSION) -> str | None:
    """Returns the subject, or None if the token is invalid, expired or the wrong purpose."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload.get("sub")


def generate_share_code() -> str:
    """Short human-readable code a customer gives their coach. Excludes lookalike characters."""
    alphabet = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1")
    return "".join(secrets.choice(alphabet) for _ in range(8))
