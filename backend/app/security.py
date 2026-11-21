"""Password hashing (scrypt) and signed tokens (HS256 JWT) using only the standard library."""
import base64
import hashlib
import hmac
import json
import os
import time

_N, _R, _P = 2 ** 14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                              n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(digest)))
        return hmac.compare_digest(calc, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(payload: dict, secret: str, hours: int = 12) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + hours * 3600
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    data = _b64(json.dumps(body, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), f"{head}.{data}".encode(), hashlib.sha256).digest())
    return f"{head}.{data}.{sig}"


def decode_token(token: str, secret: str) -> dict:
    """Return the payload or raise ValueError when the token is invalid or expired."""
    try:
        head, data, sig = token.split(".")
        expected = _b64(hmac.new(secret.encode(), f"{head}.{data}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        if json.loads(_unb64(head)).get("alg") != "HS256":
            raise ValueError("bad algorithm")
        payload = json.loads(_unb64(data))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid token") from exc
    if payload.get("exp", 0) < time.time():
        raise ValueError("token expired")
    return payload
