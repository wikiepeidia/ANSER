
import subprocess
result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
print(result.stdout)

# Install vLLM (pre-built for CUDA 12.x — matches Colab L4 environment)
subprocess.run([
    "pip", "install", "vllm==0.6.6", "pyngrok", "huggingface_hub", "--quiet"
], check=True)
print("Dependencies installed.")

from pyngrok import ngrok

NGROK_AUTHTOKEN = "PASTE_YOUR_NGROK_TOKEN_HERE"  # Required — free account works
ngrok.set_auth_token(NGROK_AUTHTOKEN)
print("ngrok authenticated.")

import subprocess
import time
import os

MODEL_ID = "Qwen/Qwen2.5-14B-Instruct-AWQ"
VLLM_PORT = 8080
LOG_FILE = "/tmp/vllm.log"

vllm_cmd = [
    "python", "-m", "vllm.entrypoints.openai.api_server",
    "--model", MODEL_ID,
    "--port", str(VLLM_PORT),
    "--dtype", "half",
    "--quantization", "awq",
    "--max-model-len", "8192",
    "--gpu-memory-utilization", "0.88",
    "--served-model-name", MODEL_ID,
    "--trust-remote-code",
]

with open(LOG_FILE, "w") as log:
    vllm_process = subprocess.Popen(vllm_cmd, stdout=log, stderr=log)

print(f"vLLM PID: {vllm_process.pid}")
print("Loading model — this takes ~2-3 minutes on first run (downloading weights ~9GB)...")
print(f"Monitor logs: !tail -f {LOG_FILE}")


import requests
import time

def wait_for_server(port, timeout=300):
    url = f"http://localhost:{port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
        print(".", end="", flush=True)
    return False

print("Waiting for vLLM server...")
if wait_for_server(VLLM_PORT):
    print("\nServer ready!")
else:
    print("\nTimeout — check logs with: !tail -50 /tmp/vllm.log")
    raise RuntimeError("vLLM failed to start")

# Open public tunnel
tunnel = ngrok.connect(VLLM_PORT, "http")
PUBLIC_URL = tunnel.public_url

print("\n" + "="*60)
print(f"  PUBLIC vLLM URL : {PUBLIC_URL}/v1")
print(f"  Paste into .env : VLLM_BASE_URL={PUBLIC_URL}/v1")
print("="*60)
print("\nDO NOT close this Colab tab — tunnel stays alive while this runs.")

import json

SYSTEM_PROMPT = """You are an expert cybersecurity SOC analyst.
Analyze the provided log entry and respond ONLY with valid JSON in this exact schema:
{
  "threat_detected": <bool>,
  "severity": "<none|low|medium|high|critical>",
  "confidence": <0-100>,
  "attack_type": "<attack category or null>",
  "mitre_technique": "<ATT&CK technique ID or null>",
  "affected_assets": ["<list of IPs/users>"],
  "reason": "<one sentence explanation>",
  "recommended_action": "<block_ip|disable_account|escalate|monitor|none>"
}
Do not include markdown, code fences, or any text outside the JSON object."""

TEST_LOG = {
    "timestamp": "2026-05-19T08:23:11Z",
    "event_type": "authentication_failure",
    "source_ip": "192.168.1.105",
    "destination": "dc01.corp.local",
    "user": "administrator",
    "failure_count": 47,
    "protocol": "SMB",
    "raw": "Account lockout threshold reached — 47 failed logons in 120 seconds"
}

response = requests.post(
    f"http://localhost:{VLLM_PORT}/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this log:\n{json.dumps(TEST_LOG, indent=2)}"}
        ],
        "max_tokens": 512,
        "temperature": 0.05,  # Near-deterministic for structured output
        "response_format": {"type": "json_object"},
    },
    timeout=60
)

result = response.json()
parsed = json.loads(result["choices"][0]["message"]["content"])
print(json.dumps(parsed, indent=2))
print(f"\nLatency: {result['usage']}")

tunnels = ngrok.get_tunnels()
for t in tunnels:
    print(f"Active tunnel: {t.public_url} -> {t.config['addr']}")
