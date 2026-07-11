"""anser/discord-mock — nhận Discord webhook trong dev/test.

- POST bất kỳ path: log payload, trả 204 (giống Discord thật).
- GET /_captured: trả JSON các payload đã nhận (để test assert nội dung embed).
- GET /health: 200.
Không phụ thuộc thư viện ngoài (stdlib) → build nhanh.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

CAPTURED = []  # lưu tối đa 200 payload gần nhất


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"status": "ok"})
        if self.path.startswith("/_captured"):
            return self._json(200, {"count": len(CAPTURED), "items": CAPTURED[-50:]})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n).decode("utf-8", "ignore") if n else ""
        try:
            data = json.loads(raw)
            title = (data.get("embeds") or [{}])[0].get("title", "<no title>")
        except Exception:
            data, title = {"_raw": raw}, "<invalid json>"
        CAPTURED.append({"path": self.path, "title": title, "payload": data})
        print(f"[DISCORD-MOCK] {self.path} | embed: {title} | {len(raw)} bytes", flush=True)
        self.send_response(204)  # Discord trả 204 No Content
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("[DISCORD-MOCK] listening on :9099", flush=True)
    HTTPServer(("0.0.0.0", 9099), H).serve_forever()
