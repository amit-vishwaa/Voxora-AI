"""Super Admin only: every company, plan and client login."""
from fastapi import APIRouter, Depends, HTTPException

from .. import db, packs, security
from ..config import PLANS
from ..deps import require_admin
from ..schemas import CompanyIn, CompanyPatch, UserIn, UserPatch
from ..services import analytics

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _check_company_fields(industry, plan):
    if industry is not None and packs.get(industry) is None:
        raise HTTPException(422, "Unknown industry pack.")
    if plan is not None and plan not in PLANS:
        raise HTTPException(422, "Unknown plan.")


@router.get("/overview")
def overview(conn=Depends(db.get_db)):
    return analytics.platform_overview(conn)


@router.get("/companies")
def companies(conn=Depends(db.get_db)):
    return analytics.companies_table(conn)


@router.post("/companies", status_code=201)
def create_company(body: CompanyIn, conn=Depends(db.get_db)):
    _check_company_fields(body.industry, body.plan)
    email = body.admin_email.strip().lower()
    if db.row(conn, "SELECT id FROM users WHERE email = ?", (email,)):
        raise HTTPException(409, "That login email is already in use.")
    now = db.now_iso()
    with conn:
        cid = conn.execute("INSERT INTO companies(name, industry, plan, contact_email, created_at) VALUES (?,?,?,?,?)",
                           (body.name.strip(), body.industry, body.plan, body.contact_email.strip(), now)).lastrowid
        conn.execute("INSERT INTO users(company_id, name, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                     (cid, body.admin_name.strip(), email, security.hash_password(body.admin_password), "client_admin", now))
        conn.execute("INSERT INTO agents(company_id, name, pack_key, language, voice, created_at) VALUES (?,?,?,?,?,?)",
                     (cid, "Assistant", body.industry, "en", "anushka", now))
    return db.row(conn, "SELECT * FROM companies WHERE id = ?", (cid,))


@router.patch("/companies/{company_id}")
def update_company(company_id: int, body: CompanyPatch, conn=Depends(db.get_db)):
    if not db.row(conn, "SELECT id FROM companies WHERE id = ?", (company_id,)):
        raise HTTPException(404, "Company not found.")
    changes = body.model_dump(exclude_none=True)
    _check_company_fields(changes.get("industry"), changes.get("plan"))
    if changes:
        sets = ", ".join(f"{k} = ?" for k in changes)  # keys come from the pydantic model, never from the request
        db.run(conn, f"UPDATE companies SET {sets} WHERE id = ?", (*changes.values(), company_id))
    return db.row(conn, "SELECT * FROM companies WHERE id = ?", (company_id,))


@router.get("/companies/{company_id}/users")
def company_users(company_id: int, conn=Depends(db.get_db)):
    return db.rows(conn, "SELECT id, name, email, role, active, created_at FROM users WHERE company_id = ? ORDER BY id", (company_id,))


@router.post("/companies/{company_id}/users", status_code=201)
def add_user(company_id: int, body: UserIn, conn=Depends(db.get_db)):
    if not db.row(conn, "SELECT id FROM companies WHERE id = ?", (company_id,)):
        raise HTTPException(404, "Company not found.")
    email = body.email.strip().lower()
    if db.row(conn, "SELECT id FROM users WHERE email = ?", (email,)):
        raise HTTPException(409, "That login email is already in use.")
    uid = db.run(conn, "INSERT INTO users(company_id, name, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                 (company_id, body.name.strip(), email, security.hash_password(body.password), body.role, db.now_iso()))
    return db.row(conn, "SELECT id, name, email, role, active FROM users WHERE id = ?", (uid,))


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, admin=Depends(require_admin), conn=Depends(db.get_db)):
    user = db.row(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(404, "User not found.")
    if user["id"] == admin["id"] and body.active is False:
        raise HTTPException(400, "You cannot disable your own account.")
    if body.name is not None:
        db.run(conn, "UPDATE users SET name = ? WHERE id = ?", (body.name.strip(), user_id))
    if body.active is not None:
        db.run(conn, "UPDATE users SET active = ? WHERE id = ?", (1 if body.active else 0, user_id))
    if body.password is not None:
        db.run(conn, "UPDATE users SET password_hash = ?, must_change = 1 WHERE id = ?", (security.hash_password(body.password), user_id))
    return db.row(conn, "SELECT id, name, email, role, active FROM users WHERE id = ?", (user_id,))
