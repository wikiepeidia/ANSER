# Plans

- we have api server. But since we test local, we will use local server
- The api endpoint server connect directly to the collab
- we connect our endpoint to the model instead. Kinda reversed
- have to do something with the api flask server to connect to the collab
- we check api .fast.flask.py (ai_service) having MOCK api/ID?
- neneefront end simple
-

# Implementation?

## Goal

Run the “Brain” (LLM) on Colab with Ngrok, call it from the Flask “Body”, and return a simple workflow JSON that the builder can render.

## Setup (Colab Brain)

1. Open Colab with GPU (L4/T4 is fine) and install deps:
 ```bash
 pip install fastapi uvicorn ngrok
 # if using hosted APIs only, you can skip heavy model downloads
 ```

2. Start a FastAPI server (ai_service) with endpoints:
 - `POST /plan` → input: `{ "prompt": "...", "context": {} }`, output simplified workflow JSON `{ nodes: [], edges: [], notes: "..." }`.
 - `GET /health` → returns `{status:"ok"}` for heartbeat.
3. Run Ngrok inside Colab:
 ```bash
 ngrok http 8000
 ```

	Grab the HTTPS forwarding URL (e.g., `https://abcd1234.ngrok-free.app`).
4. Add a simple shared secret (e.g., header `X-AI-KEY: <token>`) and keep it in env on both ends.

## Integration (Flask Body)

1. Add env/config `AI_SERVICE_URL` to store the Ngrok HTTPS URL; do **not** expose it in JS.
2. Create a proxy route `/api/ai/plan` in Flask:
 - Validate login.
 - Forward `{prompt}` to `AI_SERVICE_URL/plan` with the shared header.
 - Set timeout ~25–30s; handle errors gracefully.
 - Return the JSON as-is to the frontend.
3. (Optional) Add a small health check on app start to log if AI service is unreachable.

## Frontend (Workflow Builder)

1. Add a text input + “Generate” button.
2. On click, POST to `/api/ai/plan` with the prompt.
3. Take the returned `nodes/edges` and map into canvas:
 - For each node: assign position defaults, map `type` to your palette, set config fields.
 - For edges: connect `from` → `to` by node IDs.
4. Show errors clearly (toast) and keep the raw JSON in console for debug.

## Data Contract (keep it simple for the AI)

Ask the AI to return this shape:

```json
{
  "nodes": [
  {"id": "n1", "type": "google_sheet_read", "config": {"sheetId": "...", "range": "A1:C10"}},
  {"id": "n2", "type": "google_doc_write", "config": {"docId": "...", "template": "..."}}
  ],
  "edges": [ {"from": "n1", "to": "n2"} ],
  "notes": "Any explanation"
}
```

## Purpose / When to use

- Rapidly draft automations from natural language (“Read sheet, summarize, email manager”).
- Non-technical users can scaffold flows without dragging nodes manually.
- Works even if the Brain sleeps: show a clear “AI offline” message when Colab is down.

## If you want to avoid running models on Colab

- Use hosted LLM APIs (DeepSeek/Qwen/Mistral) inside the FastAPI instead of local GPU.
- You still expose only `/plan` via Ngrok; the rest stays the same.
