"""Checks a RUNNING server end to end (login, dashboards, and that companies cannot see each other).

Start the server first (run.bat), then in a second window:   python scripts/smoke_test.py
Needs the demo data (SEED_DEMO=true) and the original demo passwords."""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
failures = 0


def call(path, token=None, method="GET", body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name, ok, detail=""):
    global failures
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail and not ok else ""))
    failures += 0 if ok else 1


status, _ = call("/api/health")
check("server is up", status == 200, f"status {status}")
status, _ = call("/api/calls")
check("calls need a login (401)", status == 401, f"status {status}")
status, data = call("/api/auth/login", method="POST", body={"email": "demo.realty@voxora.local", "password": "wrong"})
check("wrong password is rejected (401)", status == 401, f"status {status}")

status, admin = call("/api/auth/login", method="POST", body={"email": "admin@voxora.local", "password": "ChangeMe@123"})
check("super admin can sign in", status == 200 and admin["user"]["role"] == "super_admin", f"status {status}")
status, realty = call("/api/auth/login", method="POST", body={"email": "demo.realty@voxora.local", "password": "Demo@12345"})
check("client can sign in", status == 200 and realty["user"]["role"] == "client_admin", f"status {status}")
if failures:
    sys.exit("Sign-in failed, so the remaining checks were skipped. Did you change the demo passwords?")

a, c = admin["token"], realty["token"]
my_company = realty["user"]["company_id"]
status, companies = call("/api/admin/companies", a)
other = next(x for x in companies if x["id"] != my_company)
status, mine = call("/api/calls?limit=5", c)
check("client sees own calls", status == 200 and mine["total"] > 0, f"status {status}")
status, _ = call(f"/api/calls?company_id={other['id']}", c)
check("client cannot read another company (403)", status == 403, f"status {status}")
status, _ = call("/api/admin/companies", c)
check("client cannot open the admin API (403)", status == 403, f"status {status}")
status, _ = call("/api/dashboard", a)
check("admin must choose a company first (400)", status == 400, f"status {status}")
status, dash = call(f"/api/dashboard?company_id={other['id']}", a)
check("admin can view any company", status == 200 and "kpis" in dash, f"status {status}")
status, other_calls = call(f"/api/calls?limit=1&company_id={other['id']}", a)
status2, _ = call(f"/api/calls/{other_calls['items'][0]['id']}", c)
check("client cannot open another company's call (404)", status2 == 404, f"status {status2}")
status, cfg = call("/api/meta/config", c)
check("provider status is reported", status == 200 and len(cfg["providers"]) == 4, f"status {status}")
print("\nAll checks passed." if not failures else f"\n{failures} check(s) failed.")
sys.exit(1 if failures else 0)
