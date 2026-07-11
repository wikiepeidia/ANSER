"""Import all workflow JSON files into n8n (n8n >= 1.0).

n8n >= 1.0 dùng User Management — Basic Auth cũ (N8N_BASIC_AUTH_*) đã bị gỡ bỏ.
Script hỗ trợ 2 cách xác thực (chọn 1):

  1. N8N_API_KEY        — khuyến nghị. Tạo trong n8n UI: Settings -> n8n API
  2. N8N_EMAIL + N8N_PASSWORD — tài khoản owner; script tự login lấy cookie

Usage:
    python scripts/import_workflows.py
    python scripts/import_workflows.py daily_sales_report.json
"""

import sys, os, json, glob
from urllib.request import Request, urlopen
from urllib.error import HTTPError

N8N_URL     = os.environ.get("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")
N8N_EMAIL   = os.environ.get("N8N_EMAIL", "")
N8N_PASS    = os.environ.get("N8N_PASSWORD", "")
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "..", "workflows")


def http(method, url, data=None, headers=None):
    """Gọi HTTP, trả (json_body, set_cookie_header)."""
    body = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=body, method=method,
                  headers={"Content-Type": "application/json", **(headers or {})})
    resp = urlopen(req, timeout=15)
    raw = resp.read()
    # get_all: server có thể set nhiều cookie — .get() chỉ lấy header đầu tiên
    cookie = "; ".join(resp.headers.get_all("Set-Cookie") or [])
    return (json.loads(raw) if raw else {}), cookie


def login_cookie():
    """Login owner account (n8n >= 1.0), trả về cookie 'n8n-auth=...'."""
    # payload key đổi tên giữa các version n8n — thử cả hai
    for payload in ({"emailOrLdapLoginId": N8N_EMAIL, "password": N8N_PASS},
                    {"email": N8N_EMAIL, "password": N8N_PASS}):
        try:
            _, cookies = http("POST", f"{N8N_URL}/rest/login", payload)
            for part in cookies.split("; "):
                if part.startswith("n8n-auth="):
                    return part.split(";")[0]
        except HTTPError:
            continue
    return None


def clean_payload(wf):
    """n8n chỉ chấp nhận các field này khi tạo workflow ('active'/'id' là read-only)."""
    return {
        "name": wf.get("name", ""),
        "nodes": wf.get("nodes", []),
        "connections": wf.get("connections", {}),
        "settings": wf.get("settings", {}),
    }


class PublicApiClient:
    """Dùng n8n Public API với X-N8N-API-KEY."""

    def __init__(self, api_key):
        self.headers = {"X-N8N-API-KEY": api_key}

    def list_names(self):
        data, _ = http("GET", f"{N8N_URL}/api/v1/workflows?limit=250", headers=self.headers)
        return {w["name"]: w["id"] for w in data.get("data", [])}

    def create(self, wf):
        data, _ = http("POST", f"{N8N_URL}/api/v1/workflows", clean_payload(wf),
                       headers=self.headers)
        return data.get("id") or data.get("data", {}).get("id")


class RestClient:
    """Dùng REST API nội bộ với cookie session (fallback khi không có API key)."""

    def __init__(self, cookie):
        self.headers = {"Cookie": cookie}

    def list_names(self):
        data, _ = http("GET", f"{N8N_URL}/rest/workflows", headers=self.headers)
        items = data.get("data", data) or []
        if isinstance(items, dict):
            items = items.get("data", [])
        return {w["name"]: w["id"] for w in items}

    def create(self, wf):
        data, _ = http("POST", f"{N8N_URL}/rest/workflows", clean_payload(wf),
                       headers=self.headers)
        inner = data.get("data", data) or {}
        return inner.get("id")


def make_client():
    if N8N_API_KEY:
        return PublicApiClient(N8N_API_KEY)
    if N8N_EMAIL and N8N_PASS:
        cookie = login_cookie()
        if cookie:
            return RestClient(cookie)
        print("Login THAT BAI — kiem tra N8N_EMAIL/N8N_PASSWORD (tai khoan owner).")
        sys.exit(1)
    print("Thieu thong tin xac thuc. Dat bien moi truong:")
    print("  N8N_API_KEY   (tao trong n8n UI: Settings -> n8n API)   — khuyen nghi")
    print("  hoac N8N_EMAIL + N8N_PASSWORD (tai khoan owner)")
    sys.exit(1)


def main():
    args = sys.argv[1:]
    if args:
        files = [os.path.join(WORKFLOWS_DIR, f) for f in args]
    else:
        # quét đệ quy workflows/{retail,manuf,shared}/*.json
        files = sorted(glob.glob(os.path.join(WORKFLOWS_DIR, "**", "*.json"), recursive=True))

    client = make_client()
    print(f"n8n: {N8N_URL}")
    print(f"Workflows: {len(files)} file(s)\n")

    try:
        existing = client.list_names()
    except HTTPError as e:
        print(f"Khong liet ke duoc workflows (HTTP {e.code}): {e.read().decode()[:200]}")
        sys.exit(1)

    for filepath in files:
        name = os.path.basename(filepath)
        if not os.path.exists(filepath):
            print(f"  File khong ton tai: {filepath}")
            continue
        with open(filepath, encoding="utf-8") as f:
            wf = json.load(f)
        wf_name = wf.get("name", name)

        if wf_name in existing:
            print(f"  [{name}] '{wf_name}' da ton tai (id={existing[wf_name]}), bo qua")
            continue
        try:
            wf_id = client.create(wf)
            print(f"  [{name}] Import thanh cong: '{wf_name}' (id={wf_id})")
        except HTTPError as e:
            print(f"  [{name}] Import THAT BAI — HTTP {e.code}: {e.read().decode()[:200]}")

    print("\nXong! Mo n8n de kiem tra: " + N8N_URL)


if __name__ == "__main__":
    main()
