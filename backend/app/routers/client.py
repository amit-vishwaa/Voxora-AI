"""Company-scoped endpoints. Every query filters by the company_id returned by tenant()."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db, packs
from ..config import PLANS, VOICES
from ..deps import current_user, require_writer, tenant
from ..schemas import AgentIn, AgentPatch, KnowledgeIn, RecordPatch
from ..services import analytics, scoring

router = APIRouter(prefix="/api", tags=["company"])


def _check_agent_fields(pack_key, voice):
    if pack_key is not None and packs.get(pack_key) is None:
        raise HTTPException(422, "Unknown industry pack.")
    if voice is not None and voice not in VOICES:
        raise HTTPException(422, "Unknown voice.")


@router.get("/company")
def company(cid: int = Depends(tenant), conn=Depends(db.get_db)):
    c = db.row(conn, "SELECT id, name, industry, plan, status, contact_email, created_at FROM companies WHERE id = ?", (cid,))
    c["plan_info"] = PLANS.get(c["plan"], PLANS["trial"])
    return c


@router.get("/dashboard")
def dashboard(days: int = Query(14, ge=7, le=90), cid: int = Depends(tenant), conn=Depends(db.get_db)):
    return analytics.dashboard(conn, cid, days)


# ---- agents ---------------------------------------------------------------------------------
@router.get("/agents")
def list_agents(cid: int = Depends(tenant), conn=Depends(db.get_db)):
    return db.rows(conn, "SELECT a.*, (SELECT COUNT(*) FROM calls c WHERE c.agent_id = a.id) AS calls FROM agents a "
                         "WHERE a.company_id = ? ORDER BY a.id", (cid,))


@router.post("/agents", status_code=201)
def create_agent(body: AgentIn, cid: int = Depends(tenant), _=Depends(require_writer), conn=Depends(db.get_db)):
    _check_agent_fields(body.pack_key, body.voice)
    aid = db.run(conn, "INSERT INTO agents(company_id, name, pack_key, language, voice, greeting, instructions, active, created_at)"
                       " VALUES (?,?,?,?,?,?,?,?,?)",
                 (cid, body.name.strip(), body.pack_key, body.language, body.voice, body.greeting.strip(),
                  body.instructions.strip(), 1 if body.active else 0, db.now_iso()))
    return db.row(conn, "SELECT * FROM agents WHERE id = ?", (aid,))


@router.patch("/agents/{agent_id}")
def update_agent(agent_id: int, body: AgentPatch, cid: int = Depends(tenant), _=Depends(require_writer), conn=Depends(db.get_db)):
    if not db.row(conn, "SELECT id FROM agents WHERE id = ? AND company_id = ?", (agent_id, cid)):
        raise HTTPException(404, "Agent not found.")
    changes = body.model_dump(exclude_none=True)
    _check_agent_fields(changes.get("pack_key"), changes.get("voice"))
    if "active" in changes:
        changes["active"] = 1 if changes["active"] else 0
    if changes:
        sets = ", ".join(f"{k} = ?" for k in changes)
        db.run(conn, f"UPDATE agents SET {sets} WHERE id = ? AND company_id = ?", (*changes.values(), agent_id, cid))
    return db.row(conn, "SELECT * FROM agents WHERE id = ? AND company_id = ?", (agent_id, cid))


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: int, cid: int = Depends(tenant), _=Depends(require_writer), conn=Depends(db.get_db)):
    if not db.row(conn, "SELECT id FROM agents WHERE id = ? AND company_id = ?", (agent_id, cid)):
        raise HTTPException(404, "Agent not found.")
    db.run(conn, "DELETE FROM agents WHERE id = ? AND company_id = ?", (agent_id, cid))


# ---- calls ----------------------------------------------------------------------------------
@router.get("/calls")
def list_calls(agent_id: Optional[int] = None, status: Optional[str] = None, sentiment: Optional[str] = None,
               q: Optional[str] = Query(default=None, max_length=80), limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
               cid: int = Depends(tenant), conn=Depends(db.get_db)):
    where, params = ["company_id = ?"], [cid]
    for col, val in (("agent_id", agent_id), ("status", status), ("sentiment", sentiment)):
        if val is not None:
            where.append(f"{col} = ?")
            params.append(val)
    if q:
        where.append("(summary LIKE ? OR collected_json LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    clause = " AND ".join(where)
    total = db.row(conn, f"SELECT COUNT(*) n FROM calls WHERE {clause}", params)["n"]
    items = db.rows(conn, f"SELECT id, agent_id, agent_name, language, started_at, duration_sec, status, sentiment, summary, score, collected_json "
                          f"FROM calls WHERE {clause} ORDER BY started_at DESC LIMIT ? OFFSET ?", (*params, limit, offset))
    for it in items:
        it["collected"] = json.loads(it.pop("collected_json") or "{}")
    return {"items": items, "total": total}


@router.get("/calls/{call_id}")
def get_call(call_id: int, cid: int = Depends(tenant), conn=Depends(db.get_db)):
    call = db.row(conn, "SELECT * FROM calls WHERE id = ? AND company_id = ?", (call_id, cid))
    if not call:
        raise HTTPException(404, "Call not found.")
    call["collected"] = json.loads(call.pop("collected_json") or "{}")
    call["turns"] = db.rows(conn, "SELECT idx, speaker, text, at FROM turns WHERE call_id = ? AND company_id = ? ORDER BY idx", (call_id, cid))
    call["record"] = db.row(conn, "SELECT id, type, title, status, score FROM records WHERE call_id = ? AND company_id = ?", (call_id, cid))
    return call


# ---- records (leads, appointments, tickets) -------------------------------------------------
@router.get("/records")
def list_records(type: Optional[str] = None, status: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 cid: int = Depends(tenant), conn=Depends(db.get_db)):
    where, params = ["company_id = ?"], [cid]
    for col, val in (("type", type), ("status", status)):
        if val is not None:
            where.append(f"{col} = ?")
            params.append(val)
    clause = " AND ".join(where)
    total = db.row(conn, f"SELECT COUNT(*) n FROM records WHERE {clause}", params)["n"]
    items = db.rows(conn, f"SELECT * FROM records WHERE {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?", (*params, limit, offset))
    for it in items:
        it["data"] = json.loads(it.pop("data_json") or "{}")
        it["label"] = scoring.label(it["score"])
    return {"items": items, "total": total}


@router.patch("/records/{record_id}")
def update_record(record_id: int, body: RecordPatch, cid: int = Depends(tenant), _=Depends(require_writer), conn=Depends(db.get_db)):
    if not db.row(conn, "SELECT id FROM records WHERE id = ? AND company_id = ?", (record_id, cid)):
        raise HTTPException(404, "Record not found.")
    db.run(conn, "UPDATE records SET status = ? WHERE id = ? AND company_id = ?", (body.status, record_id, cid))
    return {"id": record_id, "status": body.status}


# ---- knowledge base -------------------------------------------------------------------------
@router.get("/knowledge")
def list_knowledge(cid: int = Depends(tenant), conn=Depends(db.get_db)):
    return db.rows(conn, "SELECT k.*, a.name AS agent_name FROM knowledge k LEFT JOIN agents a ON a.id = k.agent_id "
                         "WHERE k.company_id = ? ORDER BY k.id DESC", (cid,))


@router.post("/knowledge", status_code=201)
def add_knowledge(body: KnowledgeIn, cid: int = Depends(tenant), _=Depends(require_writer), conn=Depends(db.get_db)):
    if body.agent_id is not None and not db.row(conn, "SELECT id FROM agents WHERE id = ? AND company_id = ?", (body.agent_id, cid)):
        raise HTTPException(404, "Agent not found.")
    kid = db.run(conn, "INSERT INTO knowledge(company_id, agent_id, title, content, created_at) VALUES (?,?,?,?,?)",
                 (cid, body.agent_id, body.title.strip(), body.content.strip(), db.now_iso()))
    return db.row(conn, "SELECT * FROM knowledge WHERE id = ?", (kid,))


@router.delete("/knowledge/{knowledge_id}", status_code=204)
def delete_knowledge(knowledge_id: int, cid: int = Depends(tenant), _=Depends(require_writer), conn=Depends(db.get_db)):
    if not db.row(conn, "SELECT id FROM knowledge WHERE id = ? AND company_id = ?", (knowledge_id, cid)):
        raise HTTPException(404, "Entry not found.")
    db.run(conn, "DELETE FROM knowledge WHERE id = ? AND company_id = ?", (knowledge_id, cid))


@router.get("/usage")
def usage(cid: int = Depends(tenant), conn=Depends(db.get_db)):
    return analytics.usage(conn, cid)
