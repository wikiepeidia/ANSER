"""
apply_v2_fixes.py  —  Gộp 3 bản vá để chạy MỘT lần sau cell setup (bước 1-5).
Commit file này vào repo -> clone xong là có sẵn, không phải %%writefile mỗi phiên.

Vá (idempotent, sao lưu .bak):
  1. dependencies.py : + extract_action_json (uu tien object co "action", luon tra dict)
  2. chat.py         : ghi de tron khoi routing + imports + webhook
                       (invoice->INVOICE, TECHNICAL+tu khoa->ACTION+directive o user turn,
                        DATA->SQL, RETRIEVAL/GENERAL->ACTION)
  3. manager.py      : ghi de tron consult (system_prompt, ACTION_SYSTEM NGUYEN BAN,
                        KHONG .format/DB_SCHEMA, token 2048)
  4. benchmark_integration.py : extract_json uu-tien-action

Chay:  cd /content/ANSER_AI_FIX && python apply_v2_fixes.py
Chay TRUOC khi khoi dong server (bước 6). Neu da chay bước 6 roi thi chay lai bước 6.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
report = []


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def wr(p, s):
    shutil.copy2(p, p + ".bak")
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


# ──────────────────────────────────────────────────────────────────────────
# 1) dependencies.py : + extract_action_json
# ──────────────────────────────────────────────────────────────────────────
EXTRACT_FN = '''

def extract_action_json(text: str):
    """Uu tien object co key "action"; luon tra dict (khong tra list)."""
    import json as _json
    cands = []
    for m in re.finditer(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", text, re.DOTALL):
        try:
            cands.append(_json.loads(m.group(1)))
        except Exception:
            pass
    depth, start = 0, -1
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start != -1:
                blk = text[start:i + 1]
                try:
                    cands.append(_json.loads(blk))
                except Exception:
                    try:
                        from json_repair import repair_json as _rj
                        obj = _rj(blk, return_objects=True)
                        if isinstance(obj, dict):
                            cands.append(obj)
                    except Exception:
                        pass
                start = -1
    if not cands:
        return None
    for obj in reversed(cands):
        if isinstance(obj, dict) and "action" in obj:
            return obj
    return cands[-1] if isinstance(cands[-1], dict) else None
'''


def patch_dependencies():
    p = "src/api/dependencies.py"
    s = rd(p)
    if "def extract_action_json" in s:
        report.append("deps: extract_action_json da co, bo qua")
        return
    m = re.search(r"^def clean_output\(.*?(?=^def )", s, re.M | re.S)
    if m:
        s = s[:m.end()] + EXTRACT_FN.lstrip("\n") + "\n" + s[m.end():]
    else:
        s = s.rstrip() + "\n\n" + EXTRACT_FN.lstrip("\n")
    wr(p, s)
    report.append("deps: + extract_action_json")


# ──────────────────────────────────────────────────────────────────────────
# 2) manager.py : ghi de tron consult
# ──────────────────────────────────────────────────────────────────────────
NEW_CONSULT = '''    async def consult(self, task: str, context: str = "", history: str = "",
                      system_prompt: str = None):
        # system NGUYEN BAN (khong append gi -> giu byte-match, model van dung <think>).
        # KHONG .format, KHONG Prompts.DB_SCHEMA (khong ton tai o prompts tai sinh).
        system = system_prompt if system_prompt is not None else Prompts.ACTION_SYSTEM
        parts = []
        if context:
            parts.append(f"[CONTEXT]\\n{context}")
        if history:
            parts.append(history)
        parts.append(task)
        user = "\\n\\n".join(parts)
        return await self.generate_chat(system=system, user=user, max_new_tokens=2048)
'''


def patch_manager():
    p = "src/agents/manager.py"
    s = rd(p)
    if "system_prompt: str = None" in s and "max_new_tokens=2048" in s and "NGAN GON" not in s:
        report.append("manager.consult da dung, bo qua")
        return
    m = re.search(r"    async def consult\(self.*\Z", s, re.S)
    if not m:
        report.append("manager: KHONG thay consult — kiem tra tay")
        return
    wr(p, s[:m.start()] + NEW_CONSULT)
    report.append("manager: ghi de consult (system_prompt + ACTION_SYSTEM + token 2048)")


# ──────────────────────────────────────────────────────────────────────────
# 3) chat.py : imports + ghi de routing + webhook
# ──────────────────────────────────────────────────────────────────────────
NEW_ROUTING = '''        decision = await runtime.manager.analyze_task(user_msg)
        cat = decision.get("category", "GENERAL")
        logger.info("Route selected", extra={"request_id": request_id, "route": cat})

        resp = ""
        low = user_msg.lower()
        if any(k in low for k in ("hoa don", "h\u00f3a \u0111\u01a1n", "invoice", "qwen2-vl", "vlm")):
            resp = await runtime.manager.consult(
                user_msg, system_prompt=Prompts.INVOICE_SYSTEM)

        elif cat == "TECHNICAL" or any(k in low for k in (
                "tao quy trinh", "t\u1ea1o quy tr\u00ecnh", "t\u1ea1o workflow",
                "workflow", "tu dong", "t\u1ef1 \u0111\u1ed9ng", "len lich", "l\u00ean l\u1ecbch")):
            _tech = (
                "[YEU CAU TAO WORKFLOW TU DONG HOA] BAT BUOC xuat JSON co "
                "action=create_workflow kem name va payload gom nodes, edges. "
                "TUYET DOI KHONG dung query_db, KHONG tra loi text thuan. "
                "Yeu cau cua nguoi dung: " + user_msg
            )
            resp = await runtime.manager.consult(
                _tech, system_prompt=Prompts.ACTION_SYSTEM)

        elif cat == "DATA_INTERNAL":
            resp = await runtime.manager.consult(
                user_msg, system_prompt=Prompts.SQL_SYSTEM)

        elif cat == "RETRIEVAL":
            context_docs = ""
            found_internal = False
            if runtime.kb:
                results = runtime.kb.search(user_msg, top_k=2)
                if results:
                    context_docs = f"[INTERNAL DOCUMENTS]:\\n{results}"
                    found_internal = True
            if not found_internal:
                web_results = web_search_fallback(user_msg)
                context_docs = (f"[WEB SEARCH RESULTS]:\\n{web_results}"
                                if web_results else "")
            resp = await runtime.manager.consult(
                user_msg, context=context_docs, system_prompt=Prompts.ACTION_SYSTEM)

        else:
            resp = await runtime.manager.consult(
                user_msg, system_prompt=Prompts.ACTION_SYSTEM)

'''


def patch_chat():
    p = "src/api/routes/chat.py"
    s = rd(p)
    orig = s
    if "extract_action_json" not in s.split("async def")[0]:
        s = s.replace("clean_output, extract_user_content, web_search_fallback,",
                      "clean_output, extract_user_content, web_search_fallback,\n    extract_action_json,", 1)
    if "from src.core.prompts import Prompts" not in s:
        s = s.replace("from src.core.engine import TASK_REGISTRY",
                      "from src.core.engine import TASK_REGISTRY\nfrom src.core.prompts import Prompts", 1)
    m = re.search(r'        decision = await runtime\.manager\.analyze_task\(user_msg\).*?(?=        cleaned = clean_output\(resp\))', s, re.S)
    if not m:
        report.append("chat: KHONG thay khoi routing — kiem tra tay")
    else:
        s = s[:m.start()] + NEW_ROUTING + s[m.end():]
    block = ('                parsed_json = extract_action_json(cleaned)\n'
             '                if parsed_json is None:\n'
             '                    from json_repair import repair_json\n'
             '                    parsed_json = repair_json(cleaned, return_objects=True)\n')
    s = re.sub(r'( *(?:from json_repair import repair_json\n *)?parsed_json = (?:extract_action_json\(cleaned\)|repair_json\(cleaned, return_objects=True\))\n(?: *if parsed_json is None:\n(?: *from json_repair import repair_json\n)? *parsed_json = (?:extract_action_json\(cleaned\)|repair_json\(cleaned, return_objects=True\))\n)*)',
               block, s, count=1)
    if s != orig:
        wr(p, s)
        report.append("chat: routing + imports + webhook dong bo")
    else:
        report.append("chat: da dung, bo qua")


# ──────────────────────────────────────────────────────────────────────────
# 4) benchmark_integration.py : extract_json uu-tien-action
# ──────────────────────────────────────────────────────────────────────────
BENCH_FN = '''def extract_json(text: str):
    cands = []
    for m in re.finditer(r'```(?:json)?\\s*(\\{.*?\\})\\s*```', text, re.DOTALL):
        try:
            cands.append(json.loads(m.group(1)))
        except Exception:
            pass
    depth, start = 0, -1
    for i, c in enumerate(text):
        if c == '{':
            if depth == 0:
                start = i
            depth += 1
        elif c == '}' and depth > 0:
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    cands.append(json.loads(text[start:i + 1]))
                except Exception:
                    pass
                start = -1
    if not cands:
        return None
    for obj in reversed(cands):
        if isinstance(obj, dict) and "action" in obj:
            return obj
    return cands[-1] if isinstance(cands[-1], dict) else None
'''


def patch_benchmark():
    p = "offline_training/benchmark_integration.py"
    if not os.path.exists(p):
        report.append("benchmark: khong thay file, bo qua")
        return
    s = rd(p)
    if "for obj in reversed(cands)" in s:
        report.append("benchmark: da uu-tien-action, bo qua")
        return
    m = re.search(r"^def extract_json\(.*?(?=^def )", s, re.M | re.S)
    if m:
        wr(p, s[:m.start()] + BENCH_FN + "\n\n" + s[m.end():])
        report.append("benchmark: extract_json -> uu-tien-action")
    else:
        report.append("benchmark: KHONG thay extract_json — kiem tra tay")


for fn in (patch_dependencies, patch_manager, patch_chat, patch_benchmark):
    try:
        fn()
    except Exception as e:
        report.append(f"{fn.__name__}: LOI {e}")

# kiem tra cu phap sau khi va
ok = True
for f in ("src/api/dependencies.py", "src/agents/manager.py",
          "src/api/routes/chat.py", "offline_training/benchmark_integration.py"):
    if os.path.exists(f):
        try:
            import ast
            ast.parse(rd(f))
        except SyntaxError as e:
            ok = False
            report.append(f"SYNTAX LOI {f}: {e}")

print("=" * 60)
print("  APPLY V2 FIXES")
print("=" * 60)
for r in report:
    print("  -", r)
print("  " + ("=> OK, an toan khoi dong server" if ok else "=> CO LOI CU PHAP, xem tren"))
sys.exit(0 if ok else 1)
