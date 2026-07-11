"""
Send sample logs to the n8n webhook for testing.
Usage:  python scripts/test_log.py [normal|attack|all]
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

WEBHOOK_URL = "http://localhost:5678/webhook/analyze-log"
# SEC-3: token chia sẻ — phải khớp ANSER_WEBHOOK_TOKEN đã cấu hình cho n8n
WEBHOOK_TOKEN = os.environ.get("ANSER_WEBHOOK_TOKEN", "")

ATTACK_LOGS = [
    {
        "_label": "Brute Force SSH",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "authentication_failure",
        "source_ip": "45.33.32.156",
        "destination": "web-server-01.corp",
        "user": "root",
        "failure_count": 87,
        "protocol": "SSH",
        "port": 22,
        "message": "Failed password for root from 45.33.32.156 — 87 attempts in 60 seconds"
    },
    {
        "_label": "SMB Lateral Movement",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "lateral_movement",
        "source_ip": "192.168.1.45",
        "destination": "dc01.corp.local",
        "user": "CORP\\jsmith",
        "protocol": "SMB",
        "port": 445,
        "message": "PsExec service created on dc01 from workstation 192.168.1.45 using domain admin credentials"
    },
    {
        "_label": "Ransomware File Activity",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "file_system_anomaly",
        "source_ip": "192.168.1.102",
        "destination": "fileserver-01",
        "user": "CORP\\mwilson",
        "message": "Mass file rename detected: 4,312 files renamed with .locked extension in 45 seconds. vssadmin shadow copy deletion observed."
    },
]

NORMAL_LOGS = [
    {
        "_label": "Normal Web Request",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "http_request",
        "source_ip": "10.0.0.23",
        "destination": "intranet.corp.local",
        "user": "bpham",
        "protocol": "HTTPS",
        "port": 443,
        "message": "GET /internal/dashboard HTTP/1.1 200 OK — routine intranet access"
    },
    {
        "_label": "Normal VPN Login",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "authentication_success",
        "source_ip": "171.240.15.88",
        "destination": "vpn.corp.com",
        "user": "atran",
        "protocol": "IKEv2",
        "message": "User atran authenticated successfully via MFA from known home IP"
    },
]

def send_log(log: dict) -> dict:
    label = log.pop("_label", "Unknown")
    data  = json.dumps(log).encode()
    headers = {"Content-Type": "application/json"}
    if WEBHOOK_TOKEN:
        headers["x-anser-token"] = WEBHOOK_TOKEN
    req   = urllib.request.Request(
        WEBHOOK_URL, data=data, method="POST", headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            result = json.loads(r.read())
            print(f"\n[{label}]")
            print(f"  threat_detected : {result.get('threat_detected')}")
            print(f"  severity        : {result.get('severity')}")
            print(f"  confidence      : {result.get('confidence')}%")
            print(f"  attack_type     : {result.get('attack_type')}")
            print(f"  mitre           : {result.get('mitre_technique')}")
            print(f"  action          : {result.get('recommended_action')}")
            print(f"  reason          : {result.get('reason')}")
            return result
    except urllib.error.URLError as e:
        print(f"[{label}] ERROR: {e.reason}")
        return {}

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    logs = []
    if mode in ("attack", "all"):
        logs += ATTACK_LOGS
    if mode in ("normal", "all"):
        logs += NORMAL_LOGS

    print(f"Sending {len(logs)} log(s) to {WEBHOOK_URL}")
    print("=" * 60)

    results = [send_log(log) for log in logs]

    threats = sum(1 for r in results if r.get("threat_detected"))
    print(f"\n{'='*60}")
    print(f"Summary: {threats}/{len(results)} threats detected")

if __name__ == "__main__":
    main()
