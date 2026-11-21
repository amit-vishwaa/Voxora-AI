"""Authentication and tenant isolation. The two rules that keep companies apart live here:
1) the user is reloaded from the database on every request, 2) client users can only ever
get their own company_id back from tenant()."""
from typing import Optional

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db, security
from .config import settings

bearer = HTTPBearer(auto_error=False)


def load_user(conn, token: str) -> dict:
    """Return the active user for a token or raise PermissionError with a readable message."""
    try:
        payload = security.decode_token(token, settings.secret_key)
    except ValueError:
        raise PermissionError("Your session has expired. Please sign in again.")
    user = db.row(conn, "SELECT u.*, c.name AS company_name, c.status AS company_status, c.plan AS company_plan, "
                        "c.industry AS company_industry FROM users u LEFT JOIN companies c ON c.id = u.company_id "
                        "WHERE u.id = ?", (payload.get("sub"),))
    if not user or not user["active"]:
        raise PermissionError("This account is disabled.")
    if user["role"] != "super_admin" and user["company_status"] != "active":
        raise PermissionError("Your company account is suspended. Please contact Voxora support.")
    return user


def public_user(user: dict) -> dict:
    keys = ("id", "name", "email", "role", "company_id", "company_name", "company_industry", "must_change")
    return {k: user.get(k) for k in keys}


def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer), conn=Depends(db.get_db)) -> dict:
    if creds is None:
        raise HTTPException(401, "Please sign in.")
    try:
        return load_user(conn, creds.credentials)
    except PermissionError as exc:
        raise HTTPException(401, str(exc))


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "super_admin":
        raise HTTPException(403, "This area is for the Voxora team only.")
    return user


def require_writer(user: dict = Depends(current_user)) -> dict:
    if user["role"] not in ("super_admin", "client_admin"):
        raise HTTPException(403, "Your role can view this data but not change it.")
    return user


def tenant(user: dict = Depends(current_user), company_id: Optional[int] = Query(default=None), conn=Depends(db.get_db)) -> int:
    """The company whose data this request may touch."""
    if user["role"] == "super_admin":
        if company_id is None:
            raise HTTPException(400, "Choose a company first.")
        if not db.row(conn, "SELECT id FROM companies WHERE id = ?", (company_id,)):
            raise HTTPException(404, "Company not found.")
        return company_id
    if company_id is not None and company_id != user["company_id"]:
        raise HTTPException(403, "You can only access your own company.")
    return user["company_id"]
