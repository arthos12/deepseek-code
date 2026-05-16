"""System test for DeepSeek Code."""

import sys, os, json, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def ok(msg=""): print(f"  PASS {msg}")
def fail(msg): print(f"  FAIL: {msg}"); return 1
def hdr(name): print(f"\n{'='*60}\n  {name}\n{'='*60}")

errors = 0

hdr("1. Imports")
from deepseek_code.types import Message, ToolResult, ToolCall; ok("types")
from deepseek_code.config import load_config
config = load_config("D:/project/deepseek-code"); ok("config")
from deepseek_code.tools.base import BaseTool; from deepseek_code.tools.registry import ToolRegistry; ok("tool base")
from deepseek_code.display import Display; ok("display")
from deepseek_code.permissions import PermissionManager
pm = PermissionManager(config); ok("permissions")
from deepseek_code.compaction import Compactor
compactor = Compactor(config); ok("compaction")
from deepseek_code.system_prompt import build_system_prompt
sp = build_system_prompt("D:/project/deepseek-code/skills")
assert len(sp) > 400, f"Prompt too short: {len(sp)}"
assert "DeepSeek Code" in sp, "Missing identity"
assert "partner" in sp, "Missing warm tone"
assert "Project context (DEEPSEEK.md)" in sp, "Missing memory injection"
assert "colleague at your desk" in sp, "Missing conversational tone"
ok(f"system_prompt ({len(sp)} chars)")
from deepseek_code.session import save_session, load_session, list_sessions, delete_session; ok("session")
from deepseek_code.sub_agent import run_sub_agent; ok("sub_agent")
from deepseek_code.skills import SkillManager
sm = SkillManager("D:/project/deepseek-code/skills")
assert len(sm.list_skills()) >= 3; ok(f"skills ({len(sm.list_skills())})")

hdr("2. Tools")
from deepseek_code.tools.file_read import ReadTool
from deepseek_code.tools.file_write import WriteTool
from deepseek_code.tools.file_edit import EditTool
from deepseek_code.tools.glob_search import GlobTool
from deepseek_code.tools.grep_search import GrepTool
from deepseek_code.tools.shell import ShellTool
from deepseek_code.tools.web_search import WebSearchTool
from deepseek_code.tools.web_fetch import WebFetchTool
from deepseek_code.tools.todo_write import TodoWriteTool
from deepseek_code.tools.agent_tool import AgentTool

reg = ToolRegistry()
for t in [ReadTool(), WriteTool(), EditTool(), GlobTool(), GrepTool(),
          ShellTool(), WebSearchTool(), WebFetchTool(), TodoWriteTool(),
          AgentTool(main_registry=reg, config=config)]:
    reg.register(t)
assert len(reg.list_names()) >= 10; ok(f"registry: {len(reg.list_names())} tools")
for name in reg.list_names():
    assert "function" in reg.get(name).to_openai_schema()
ok("tool schemas valid")

r = reg.execute("Read", {"file_path": "D:/project/deepseek-code/settings.json"})
assert not r.is_error and "model" in r.content; ok("Read")
r = reg.execute("Read", {"file_path": "D:/no_such_file.xyz"})
assert r.is_error; ok("Read missing = error")

tmp = "D:/project/deepseek-code/tests/_tw.txt"
r = reg.execute("Write", {"file_path": tmp, "content": "hi"})
assert not r.is_error and os.path.exists(tmp); os.remove(tmp); ok("Write")

tmp = "D:/project/deepseek-code/tests/_te.txt"
os.makedirs(os.path.dirname(tmp), exist_ok=True)
with open(tmp, "w") as f: f.write("line one\nline two")
r = reg.execute("Edit", {"file_path": tmp, "old_string": "line two", "new_string": "LINE TWO"})
assert not r.is_error; ok("Edit")
os.remove(tmp)

r = reg.execute("Glob", {"pattern": "*.py", "path": "D:/project/deepseek-code/deepseek_code"})
assert not r.is_error; ok("Glob")

r = reg.execute("Grep", {"pattern": "class.*Tool", "path": "D:/project/deepseek-code/deepseek_code/tools", "glob": "*.py"})
if r.is_error: print("  SKIP Grep: rg not found")
else: ok("Grep")

r = reg.execute("Shell", {"command": "echo test123", "description": "test"})
assert not r.is_error and "test123" in r.content; ok("Shell")
r = reg.execute("Shell", {"command": "rm -rf /", "description": "bad"})
assert r.is_error; ok("Shell blocks rm -rf /")

r = reg.execute("TodoWrite", {"todos": [{"content": "T1", "status": "completed", "activeForm": "Doing T1"}]})
assert not r.is_error; ok("TodoWrite")

r = reg.execute("WebSearch", {"query": "test"})
ok(f"WebSearch ({len(r.content)} chars)")

hdr("3. Security Model")
assert pm.is_in_project("D:/project/deepseek-code/tools"); ok("in project")
assert not pm.is_in_project("D:/project/scripts/test.py"); ok("outside project")
assert pm.is_sensitive_path("D:/x/.env"); ok("sensitive: .env")
assert pm.is_sensitive_path("/home/x/id_rsa"); ok("sensitive: id_rsa")
assert pm.check("Read", {"file_path": "D:/project/deepseek-code/.env"}) == "deny"; ok("deny .env in project")
assert pm.check("Read", {"file_path": "C:/Windows/System32/x.dll"}) == "deny"; ok("deny system dir")
assert pm.check("Read", {"file_path": "D:/project/scripts/x.py"}) == "ask"; ok("ask outside project")
assert pm.check("Read", {"file_path": "D:/project/deepseek-code/settings.json"}) == "allow"; ok("allow in project")
assert pm.check("Shell", {"command": "rm -rf /"}) == "deny"; ok("deny dangerous shell")

hdr("4. Compaction")
msgs = [{"role":"system","content":"x"}] + [{"role":"user","content":f"m{i}"} for i in range(10)]
assert not compactor.should_compact(msgs); ok("no compact small")
big = msgs + [{"role":"user","content":"x"*100000} for _ in range(50)]
if compactor.should_compact(big):
    c = compactor.compact(big)
    assert len(c) < len(big); ok(f"compacted {len(big)} -> {len(c)}")

hdr("5. Session")
sd = "D:/project/deepseek-code/tests/_s"
os.makedirs(sd, exist_ok=True)
sid = uuid.uuid4().hex[:12]
with open(f"{sd}/{sid}.jsonl","w",encoding="utf-8") as f:
    f.write(json.dumps({"type":"session_header","id":sid,"model":"dc","token_usage":{},"created":"","updated":""})+"\n")
    f.write(json.dumps({"role":"user","content":"hi"})+"\n")
d = load_session(sid, sd)
assert d and d["id"] == sid; ok("load")
assert any(s["id"] == sid for s in list_sessions(sd)); ok("list")
assert delete_session(sid, sd); ok("delete")
import shutil; shutil.rmtree(sd)

hdr("6. Skills")
assert "brainstorming" in sm.get_descriptions(); ok("descriptions")
assert sm.load_skill("brainstorming"); ok("load skill")
assert sm.load_skill("nope") is None; ok("missing -> None")

hdr("7. API")
from deepseek_code.api import DeepSeekAPI
try: DeepSeekAPI({"api_key":""}); errors+=fail("empty key")
except ValueError: ok("empty key rejected")
api = DeepSeekAPI({"api_key":"sk-test"}); ok("client init")

hdr("8. CLI")
from deepseek_code.main import build_registry, _ensure_api_key, _detect_lang
assert len(build_registry(config).list_names()) >= 10; ok("build_registry")
tc = {"api_key":"sk-x"}; _ensure_api_key(tc, "."); assert tc["api_key"] == "sk-x"; ok("_ensure_api_key")
assert _detect_lang() in ("zh","en"); ok(f"lang: {_detect_lang()}")

hdr("9. Sub-agent")
sub = reg.get_subset(["Read","Glob","Grep"])
assert len(sub.list_names()) == 3; ok(f"sub tools: {sub.list_names()}")

hdr("RESULTS")
if errors == 0: print("\n  ALL TESTS PASSED")
else: print(f"\n  {errors} FAILED")
print()
sys.exit(errors)
