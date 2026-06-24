"""Import all workflow JSON files into n8n via REST API.

Usage:
    python scripts/import_workflows.py
    python scripts/import_workflows.py daily_sales_report.json
"""

import sys, os, json, glob
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from base64 import b64encode

N8N_URL  = os.environ.get("N8N_URL", "http://localhost:5678")
N8N_USER = os.environ.get("N8N_USER", "admin")
N8N_PASS = os.environ.get("N8N_PASSWORD", "changeme123")
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "..", "workflows")

auth = b64encode(f"{N8N_USER}:{N8N_PASS}".encode()).decode()

def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = Request(
        f"{N8N_URL}/rest/{path}",
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
    )
    try:
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read())
    except HTTPError as e:
        err = e.read().decode()
        print(f"  HTTP {e.code}: {err[:200]}")
        return None

def import_workflow(filepath):
    name = os.path.basename(filepath)
    with open(filepath, encoding="utf-8") as f:
        wf = json.load(f)

    wf_name = wf.get("name", name)

    # Check if already exists
    existing = api("GET", "workflows")
    if existing:
        for w in existing.get("data", []):
            if w.get("name") == wf_name:
                print(f"  [{name}] '{wf_name}' da ton tai (id={w['id']}), bo qua")
                return w["id"]

    result = api("POST", "workflows", wf)
    if result and "data" in result:
        wf_id = result["data"]["id"]
        print(f"  [{name}] Import thanh cong: '{wf_name}' (id={wf_id})")
        return wf_id
    else:
        print(f"  [{name}] Import THAT BAI")
        return None

def main():
    args = sys.argv[1:]
    if args:
        files = [os.path.join(WORKFLOWS_DIR, f) for f in args]
    else:
        files = sorted(glob.glob(os.path.join(WORKFLOWS_DIR, "*.json")))

    print(f"n8n: {N8N_URL}")
    print(f"Workflows: {len(files)} file(s)\n")

    for f in files:
        if not os.path.exists(f):
            print(f"  File khong ton tai: {f}")
            continue
        import_workflow(f)

    print("\nXong! Mo n8n de kiem tra: " + N8N_URL)

if __name__ == "__main__":
    main()
