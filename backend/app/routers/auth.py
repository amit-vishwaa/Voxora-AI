import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import db, security
from ..config import settings
from ..deps import current_user, load_user, public_user
from ..schemas import LoginIn, PasswordIn

router = APIRouter(prefix="/api/auth", tags=["auth"])
_failures = defaultdict(list)  # key -> timestamps of recent failed logins (in memory, per process)
_WINDOW, _LIMIT = 600, 6


def _locked(key: str) -> bool:
    now = time.time()
    _failures[key] = [t for t in _failures[key] if now - t < _WINDOW]
    return len(_failures[key]) >= _LIMIT


@router.post("/login")
def login(body: LoginIn, request: Request, conn=Depends(db.get_db)):
    email = body.email.strip().lower()
    key = f"{email}|{request.client.host if request.client else 'x'}"
    if _locked(key):
        raise HTTPException(429, "Too many failed attempts. Try again in 10 minutes.")
    user = db.row(conn, "SELECT * FROM users WHERE email = ?", (email,))
    if not user or not security.verify_password(body.password, user["password_hash"]):
        _failures[key].append(time.time())
        raise HTTPException(401, "Email or password is incorrect.")
    token = security.create_token({"sub": user["id"], "role": user["role"]}, settings.secret_key, settings.token_hours)
    try:
        full = load_user(conn, token)  # also checks active and suspended status
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    _failures.pop(key, None)
    return {"token": token, "user": public_user(full)}


@router.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)


@router.post("/change-password")
def change_password(body: PasswordIn, user=Depends(current_user), conn=Depends(db.get_db)):
    if not security.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect.")
    db.run(conn, "UPDATE users SET password_hash = ?, must_change = 0 WHERE id = ?", (security.hash_password(body.new_password), user["id"]))
    return {"ok": True}
