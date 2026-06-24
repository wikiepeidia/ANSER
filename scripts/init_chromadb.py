"""
Initialize ChromaDB knowledge base via RAG service.
Run once: python scripts/init_chromadb.py
"""
import json
import urllib.request
import urllib.error

RAG_URL = "http://localhost:8001"

SECURITY_DOCS = [
    "T1110 Brute Force: Adversaries attempt to gain access to accounts by systematically "
    "guessing credentials. Indicators: many failed logins from single IP, short time intervals, "
    "targeting admin accounts. Mitigation: account lockout, MFA, fail2ban.",

    "T1003 OS Credential Dumping: Adversaries dump credentials from LSASS, SAM, NTDS.dit. "
    "Tools: Mimikatz, ProcDump. Indicators: lsass.exe memory access, suspicious process "
    "injecting into lsass, privilege escalation events.",

    "T1021 Remote Services Lateral Movement: Adversaries use SMB, RDP, WinRM to move laterally. "
    "Indicators: new SMB connections from workstations, failed remote logons across subnets, "
    "use of PsExec or WMI for remote execution.",

    "T1071 Application Layer Protocol C2: Adversaries use HTTP/HTTPS/DNS for C2 channels. "
    "Indicators: beaconing traffic at regular intervals, unusual outbound connections to "
    "new external IPs, DNS queries for DGA domains.",

    "T1068 Exploitation for Privilege Escalation: Adversaries exploit vulnerabilities to "
    "elevate privileges. Indicators: processes running as SYSTEM unexpectedly, token "
    "impersonation, SeDebugPrivilege usage.",

    "T1048 Exfiltration Over Alternative Protocol: Data exfil via DNS, ICMP, or encrypted "
    "channels. Indicators: large DNS TXT record queries, high-volume outbound traffic to "
    "single IP, ICMP with unusual payload size.",

    "T1053 Scheduled Task/Job Persistence: Adversaries create scheduled tasks for persistence. "
    "Indicators: schtasks.exe creating new tasks, unusual task triggers, tasks pointing "
    "to temp directories or encoded PowerShell.",

    "T1070 Indicator Removal Defense Evasion: Adversaries clear event logs to cover tracks. "
    "Indicators: wevtutil.exe clearing Security log, event log service stopped unexpectedly, "
    "gaps in event log timestamps.",

    "Network Reconnaissance Port Scanning: Attacker probing network services. "
    "Indicators: single source IP connecting to many destination ports in short time, "
    "SYN packets with no established connection, IDS alerts for port sweep activity.",

    "Web Application Attack SQL Injection T1190: Adversary exploiting database via web app. "
    "Indicators: SQL keywords in HTTP parameters (SELECT, UNION, DROP), 500 errors from "
    "database backend, unusual query patterns in DB logs.",

    "T1486 Data Encrypted for Impact Ransomware: Malware encrypting files for extortion. "
    "Indicators: mass file rename events (.locked, .enc extensions), shadow copy deletion "
    "via vssadmin, high disk I/O on file server, ransom note creation.",

    "Insider Threat Unusual Data Access: Authorized user accessing sensitive data outside "
    "normal behavior. Indicators: access at unusual hours, bulk file downloads, accessing "
    "systems outside normal role, failed access to high-value resources.",
]

def post(url, body):
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, method="POST",
                                   headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read()), r.status
    except urllib.error.URLError:
        return {}, 0

def main():
    print("Checking RAG service health...")
    _, status = get(f"{RAG_URL}/health")
    if status != 200:
        print("ERROR: RAG service not reachable at http://localhost:8001")
        print("Run: docker compose up -d")
        print("Then wait ~60 seconds for rag-service to finish installing packages.")
        return

    print("RAG service is online. Loading security knowledge base...")
    doc_ids = [f"doc_{i:03d}" for i in range(len(SECURITY_DOCS))]

    resp, status = post(f"{RAG_URL}/init", {
        "collection": "security_context",
        "ids":        doc_ids,
        "documents":  SECURITY_DOCS
    })

    if status == 200 and resp.get("status") == "ok":
        print(f"Loaded {resp['count']} documents into ChromaDB.")
        print("RAG knowledge base is ready.")
    else:
        print(f"ERROR: {resp}")

if __name__ == "__main__":
    main()
