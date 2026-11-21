"""Read-only numbers for the dashboards. Every company query filters by company_id."""
from datetime import datetime, timedelta, timezone

from .. import db
from ..config import PLANS


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _month_start() -> str:
    n = datetime.now(timezone.utc)
    return _iso(n.replace(day=1, hour=0, minute=0, second=0, microsecond=0))


def _daily(conn, cid: int, since: str, days: int) -> list:
    data = {r["d"]: r for r in db.rows(
        conn, "SELECT substr(started_at,1,10) d, COUNT(*) n, COALESCE(SUM(duration_sec),0) s FROM calls "
              "WHERE company_id=? AND started_at>=? GROUP BY d", (cid, since))}
    today = datetime.now(timezone.utc).date()
    out = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        out.append({"date": d, "calls": data.get(d, {}).get("n", 0), "minutes": round(data.get(d, {}).get("s", 0) / 60, 1)})
    return out


def dashboard(conn, cid: int, days: int = 14) -> dict:
    now = datetime.now(timezone.utc)
    since, prev_since = _iso(now - timedelta(days=days)), _iso(now - timedelta(days=days * 2))
    cur = db.row(conn, "SELECT COUNT(*) n, COALESCE(SUM(duration_sec),0) s, COALESCE(AVG(duration_sec),0) a,"
                       " COALESCE(SUM(status='completed'),0) c, COALESCE(SUM(sentiment='positive'),0) p FROM calls "
                       "WHERE company_id=? AND started_at>=?", (cid, since))
    prev = db.row(conn, "SELECT COUNT(*) n FROM calls WHERE company_id=? AND started_at>=? AND started_at<?", (cid, prev_since, since))
    recs = db.row(conn, "SELECT COUNT(*) n, COALESCE(AVG(score),0) a FROM records WHERE company_id=? AND created_at>=?", (cid, since))
    n = cur["n"]
    return {
        "days": days,
        "kpis": {"calls": n, "calls_prev": prev["n"], "minutes": round(cur["s"] / 60, 1), "avg_duration_sec": int(cur["a"]),
                 "completion_rate": round(100 * cur["c"] / n) if n else 0, "positive_rate": round(100 * cur["p"] / n) if n else 0,
                 "records": recs["n"], "avg_score": int(recs["a"])},
        "daily": _daily(conn, cid, since, days),
        "outcomes": db.rows(conn, "SELECT status k, COUNT(*) n FROM calls WHERE company_id=? AND started_at>=? GROUP BY status", (cid, since)),
        "sentiment": db.rows(conn, "SELECT sentiment k, COUNT(*) n FROM calls WHERE company_id=? AND started_at>=? GROUP BY sentiment", (cid, since)),
        "agents": db.rows(conn, "SELECT agent_name k, COUNT(*) n FROM calls WHERE company_id=? AND started_at>=? GROUP BY agent_name ORDER BY n DESC LIMIT 5", (cid, since)),
        "pipeline": db.rows(conn, "SELECT status k, COUNT(*) n FROM records WHERE company_id=? GROUP BY status", (cid,)),
        "recent": db.rows(conn, "SELECT id, agent_name, language, started_at, duration_sec, status, sentiment, summary, score "
                                "FROM calls WHERE company_id=? ORDER BY started_at DESC LIMIT 6", (cid,)),
    }


def minutes_used(conn, cid: int) -> float:
    r = db.row(conn, "SELECT COALESCE(SUM(duration_sec),0) s FROM calls WHERE company_id=? AND started_at>=?", (cid, _month_start()))
    return round(r["s"] / 60, 1)


def usage(conn, cid: int) -> dict:
    company = db.row(conn, "SELECT * FROM companies WHERE id=?", (cid,))
    plan = {**PLANS.get(company["plan"], PLANS["trial"]), "key": company["plan"]}
    used = minutes_used(conn, cid)
    return {"plan": plan, "plans": [{**v, "key": k} for k, v in PLANS.items()], "minutes_used": used,
            "minutes_limit": plan["minutes"], "percent": min(100, round(100 * used / plan["minutes"])) if plan["minutes"] else 0,
            "daily": _daily(conn, cid, _month_start(), max(1, datetime.now(timezone.utc).day)),
            "by_agent": db.rows(conn, "SELECT agent_name k, COUNT(*) calls, ROUND(COALESCE(SUM(duration_sec),0)/60.0,1) minutes FROM calls "
                                      "WHERE company_id=? AND started_at>=? GROUP BY agent_name ORDER BY minutes DESC", (cid, _month_start()))}


def companies_table(conn) -> list:
    since = _iso(datetime.now(timezone.utc) - timedelta(days=30))
    out = []
    for c in db.rows(conn, "SELECT * FROM companies ORDER BY id"):
        stats = db.row(conn, "SELECT COUNT(*) n FROM calls WHERE company_id=? AND started_at>=?", (c["id"], since))
        c["calls_30d"] = stats["n"]
        c["minutes_used"] = minutes_used(conn, c["id"])
        c["minutes_limit"] = PLANS.get(c["plan"], PLANS["trial"])["minutes"]
        c["agents"] = db.row(conn, "SELECT COUNT(*) n FROM agents WHERE company_id=?", (c["id"],))["n"]
        c["users"] = db.row(conn, "SELECT COUNT(*) n FROM users WHERE company_id=?", (c["id"],))["n"]
        out.append(c)
    return out


def platform_overview(conn) -> dict:
    companies = companies_table(conn)
    since = _iso(datetime.now(timezone.utc) - timedelta(days=14))
    daily = {r["d"]: r["n"] for r in db.rows(conn, "SELECT substr(started_at,1,10) d, COUNT(*) n FROM calls WHERE started_at>=? GROUP BY d", (since,))}
    today = datetime.now(timezone.utc).date()
    series = [{"date": (today - timedelta(days=i)).isoformat(), "calls": daily.get((today - timedelta(days=i)).isoformat(), 0)} for i in range(13, -1, -1)]
    return {"totals": {"companies": len(companies), "active": sum(1 for c in companies if c["status"] == "active"),
                       "calls_30d": sum(c["calls_30d"] for c in companies), "minutes_month": round(sum(c["minutes_used"] for c in companies), 1),
                       "agents": sum(c["agents"] for c in companies)},
            "daily": series, "companies": companies}
