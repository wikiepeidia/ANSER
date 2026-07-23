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
    for obj in reversed(cands):
        if isinstance(obj, dict) and "action" in obj:
            return obj
    # v2r-b: khong co "action" -> object NGOAI co the bi CAT hoac chua ky tu dieu
    # khien. Va lai tu dau "{" bang json_repair, thay vi roi xuong node con.
    i = text.find("{")
    if i != -1:
        try:
            from json_repair import repair_json as _rj2
            o = _rj2(text[i:], return_objects=True)
            if isinstance(o, list):
                for x in reversed(o):
                    if isinstance(x, dict) and "action" in x:
                        return x
                o = o[0] if o else None
            if isinstance(o, dict) and "action" in o:
                return o
        except Exception:
            pass
    if not cands:
        return None
    return cands[-1] if isinstance(cands[-1], dict) else None
'''


def patch_dependencies():
    p = "src/api/dependencies.py"
    s = rd(p)
    if "_rj2" in s and "def extract_action_json" in s:
        report.append("deps: extract_action_json da co, bo qua")
        return
    if "def extract_action_json" in s:
        # da co ban CU -> THAY THE (khong chen them, tranh trung ham)
        m = re.search(r"^def extract_action_json\(.*?(?=^def |\Z)", s, re.M | re.S)
        if m:
            s = s[:m.start()] + EXTRACT_FN.lstrip("\n").lstrip() + "\n\n" + s[m.end():]
            wr(p, s)
            report.append("deps: extract_action_json -> nang cap v2r")
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
        # Brevity dat o LUOT USER (khong dung vao system -> giu byte-match, van co <think>).
        # Can thiet vi max_seq_len=4096, prompt ~1400 token -> output chi con ~2048.
        # v2r: CHI bo do dai suy luan. TUYET DOI khong nhac JSON o day —
        # ban truoc ghi "xuat KET QUA/JSON" khien T5 (tinh thue) va T6 (redirect)
        # xuat JSON sai. Dinh dang output do PROTOCOL trong system prompt quyet dinh.
        parts.append("[LUU Y] Suy luan NGAN GON trong <think> (toi da 5 cau), "
                     "khong lap lai, roi tra loi theo dung PROTOCOL.")
        user = "\\n\\n".join(parts)
        return await self.generate_chat(system=system, user=user, max_new_tokens=2048)
'''


def patch_manager():
    p = "src/agents/manager.py"
    s = rd(p)
    if "system_prompt: str = None" in s and "v2r:" in s:
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
        # v2r-b: directive CHI bat khi that su co Y DINH TAO. Router hay xep nham
        # cau hoi ngoai domain ("giai thich thuat toan...") vao TECHNICAL; ep
        # create_workflow vo dieu kien se sinh workflow cho ca cau hoi do.
        _tao = any(k in low for k in (
            "tao quy trinh", "t\u1ea1o quy tr\u00ecnh", "tao workflow", "t\u1ea1o workflow",
            "workflow", "tu dong hoa", "t\u1ef1 \u0111\u1ed9ng h\u00f3a",
            "len lich", "l\u00ean l\u1ecbch", "t\u1ef1 \u0111\u1ed9ng g\u1eedi"))

        if any(k in low for k in ("hoa don", "h\u00f3a \u0111\u01a1n", "invoice", "qwen2-vl", "vlm")):
            # Ep NEU RO con so dung + trinh bay ngan, tranh dung bang markdown dai
            # roi cham tran token truoc khi kip ket luan.
            _inv = (
                "[KIEM TRA HOA DON] Trinh bay NGAN GON, KHONG lap bang dai. "
                "Voi moi dong sai, PHAI neu ro con so DUNG la bao nhieu "
                "(dang: 'dong N: amount dung phai la <so dung>, khong phai <so ghi tren hoa don>'). "
                "KHONG tu sua du lieu goc, chi bao loi. "
                "Du lieu: " + user_msg
            )
            resp = await runtime.manager.consult(
                _inv, system_prompt=Prompts.INVOICE_SYSTEM)

        elif _tao:
            _tech = (
                "[YEU CAU TAO WORKFLOW TU DONG HOA] BAT BUOC xuat JSON co "
                "action=create_workflow kem name va payload gom nodes, edges. "
                "TUYET DOI KHONG dung query_db, KHONG tra loi text thuan. "
                "Yeu cau cua nguoi dung: " + user_msg
            )
            resp = await runtime.manager.consult(
                _tech, system_prompt=Prompts.ACTION_SYSTEM)

        elif cat == "TECHNICAL":
            # TECHNICAL nhung khong co y dinh tao -> de PROTOCOL tu quyet,
            # ke ca rule 4 (ngoai ban le -> tra loi ngan roi huong ve ban le).
            resp = await runtime.manager.consult(
                user_msg, system_prompt=Prompts.ACTION_SYSTEM)

        elif cat == "DATA_INTERNAL":
            _sql = (
                "[YEU CAU TRUY VAN DU LIEU] BAT BUOC xuat JSON co "
                "action=query_db kem sql. KHONG tra loi text thuan, "
                "KHONG liet ke phan tich schema ra ngoai. "
                "Yeu cau cua nguoi dung: " + user_msg
            )
            resp = await runtime.manager.consult(
                _sql, system_prompt=Prompts.SQL_SYSTEM)

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
    for obj in reversed(cands):
        if isinstance(obj, dict) and "action" in obj:
            return obj
    i = text.find("{")          # v2r: va object ngoai bi cat / ky tu dieu khien
    if i != -1:
        try:
            from json_repair import repair_json as _rj2
            o = _rj2(text[i:], return_objects=True)
            if isinstance(o, list):
                for x in reversed(o):
                    if isinstance(x, dict) and "action" in x:
                        return x
                o = o[0] if o else None
            if isinstance(o, dict) and "action" in o:
                return o
        except Exception:
            pass
    if not cands:
        return None
    return cands[-1] if isinstance(cands[-1], dict) else None
'''


def patch_benchmark():
    p = "offline_training/benchmark_integration.py"
    if not os.path.exists(p):
        report.append("benchmark: khong thay file, bo qua")
        return
    s = rd(p)
    if "_rj2" in s and "for obj in reversed(cands)" in s:
        report.append("benchmark: da uu-tien-action, bo qua")
        return
    m = re.search(r"^def extract_json\(.*?(?=^def )", s, re.M | re.S)
    if m:
        wr(p, s[:m.start()] + BENCH_FN + "\n\n" + s[m.end():])
        report.append("benchmark: extract_json -> uu-tien-action")
    else:
        report.append("benchmark: KHONG thay extract_json — kiem tra tay")




# 5) engine.py : them _GEN_LOCK cap module de TUAN TU HOA vLLM
#    (fix "Forward context is not set" khi 2 request chong nhau)
def patch_engine_lock():
    p = "src/core/engine.py"
    s = rd(p)
    if "_GEN_LOCK" in s:
        report.append("engine: da co _GEN_LOCK, bo qua")
        return
    anchor = "TASK_REGISTRY = TaskRegistry(max_size=1000)"
    if anchor not in s:
        report.append("engine: KHONG thay TASK_REGISTRY - kiem tra tay")
        return
    s = s.replace(anchor,
                  anchor + "\n\n# vLLM LLM (offline API) KHONG thread-safe. run_in_executor dung ThreadPool\n"
                  "# nhieu thread -> 2 request chong nhau lam hong forward context\n"
                  "# (\"Forward context is not set\"). Lock nay tuan tu hoa moi lan generate.\n"
                  "_GEN_LOCK = threading.Lock()", 1)
    n = 0
    old1 = """        def _blocking_generate():
            outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()"""
    new1 = """        def _blocking_generate():
            with _GEN_LOCK:
                outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()"""
    if old1 in s:
        s = s.replace(old1, new1, 1); n += 1
    old2 = """        def _blocking_generate():
            tokenizer = self.llm.get_tokenizer()
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()"""
    new2 = """        def _blocking_generate():
            with _GEN_LOCK:
                tokenizer = self.llm.get_tokenizer()
                prompt = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()"""
    if old2 in s:
        s = s.replace(old2, new2, 1); n += 1
    old3 = """        def _blocking_vision():"""
    if old3 in s and "with _GEN_LOCK:" not in s.split(old3)[1][:200]:
        pass  # vision it dung, bo qua cho gon
    if n == 0:
        report.append("engine: KHONG thay _blocking_generate - kiem tra tay")
        return
    wr(p, s)
    report.append(f"engine: + _GEN_LOCK quanh llm.generate ({n} cho) - fix Forward context")




# 6) config.py : GIU max_model_len = 4096 (khong nang token).
#    8192 se di ra ngoai vung da SFT (max_seq_length=4096 luc train) va lam
#    latency tang. Neu lan chay truoc da doi thanh 8192 thi ham nay tra ve 4096.
def patch_config_revert():
    p = "src/core/config.py"
    s = rd(p)
    if '"max_model_len":          8192' in s:
        wr(p, s.replace('"max_model_len":          8192', '"max_model_len":          4096', 1))
        report.append("config: max_model_len 8192 -> 4096 (giu nguyen, khong nang token)")
    else:
        report.append("config: max_model_len giu 4096, bo qua")


for fn in (patch_dependencies, patch_manager, patch_chat, patch_benchmark,
           patch_engine_lock, patch_config_revert):
    try:
        fn()
    except Exception as e:
        report.append(f"{fn.__name__}: LOI {e}")

# kiem tra cu phap sau khi va
ok = True
for f in ("src/api/dependencies.py", "src/agents/manager.py", "src/core/engine.py",
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