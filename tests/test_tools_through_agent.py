"""Every tool is exercised through the agent loop at least once (lesson D-021)."""

import json
from pathlib import Path


from steward.agent import TOOLS
from steward.llm import LLMTurn, ScriptedLLM, ToolCall
from tests.harness import Harness

DEVICE = (Path(__file__).parent / "fixtures" / "cookbook" / "device-hello-world-docker.yaml").read_text()


def call(name: str, /, **args) -> LLMTurn:
    return LLMTurn(text="", tool_calls=[ToolCall(f"c-{name}", name, args)])


def last_tool_result(llm: ScriptedLLM) -> dict:
    blocks = [b for m in llm.calls[-1] if isinstance(m["content"], list) for b in m["content"]
              if b.get("type") == "tool_result"]
    return json.loads(blocks[-1]["content"])


async def _run(files, turns, text="please do this in my workspace"):
    llm = ScriptedLLM(turns + [LLMTurn(text="ok")])
    h = Harness(files, llm=llm)
    turn = await h.say(text)
    errors = [r for r in h.sessions.get("u1").receipts if r["kind"] == "tool_error"]
    assert not errors, errors
    return h, llm, turn


async def test_search_docs():
    h, llm, _ = await _run({}, [call("search_docs", query="esp32 flash method")])
    result = last_tool_result(llm)
    assert result["status"] == "ok" and "devices" in result["passages"][0]["source"]


async def test_read_file():
    h, llm, _ = await _run({"a/b.yaml": DEVICE}, [call("read_file", path="b.yaml")])
    result = last_tool_result(llm)
    assert result["status"] == "resolved" and result["path"] == "a/b.yaml" and result["content"] == DEVICE


async def test_validate_file():
    h, llm, _ = await _run({"a/b.yaml": DEVICE}, [call("validate_file", path="a/b.yaml")])
    result = last_tool_result(llm)
    assert result["valid"] is True and result["runnability"]["verdict"] == "no_known_blocker"


async def test_write_file_creates_then_overwrite_of_foreign_file_needs_confirmation():
    h, llm, turn = await _run({"notes.md": "old"}, [call("write_file", path="docs/readme.md", content="# hi")])
    assert h.ws.files["docs/readme.md"] == "# hi"
    h2, llm2, turn2 = await _run({"notes.md": "old"}, [call("write_file", path="notes.md", content="new")])
    assert h2.ws.files["notes.md"] == "old" and "Reply yes or no" in turn2.text


async def test_create_folder_and_undo_tool():
    h, llm, turn = await _run({}, [call("create_folder", path="demo"), call("undo")])
    assert [a["action"] for a in turn.actions] == ["create_folder", "delete_folder"]


async def test_delete_folder_requires_confirmation_and_is_marked_irreversible():
    h, llm, turn = await _run({"demo/a.yaml": DEVICE}, [call("delete_folder", path="demo")])
    assert turn.actions == [] and "can't be undone" in turn.text
    confirm = await h.say("yes")
    assert confirm.actions == [{"action": "delete_folder", "path": "demo"}]
    undo = await h.say("undo")
    assert undo.actions == [] and "can't be undone" in undo.text


def test_every_tool_has_an_agent_level_test():
    source = "\n".join(p.read_text() for p in Path(__file__).parent.glob("test_*.py"))
    for spec in TOOLS:
        name = spec["name"]
        assert f'"{name}"' in source, f"no agent-level test references tool {name}"


async def test_edit_profile_changes_only_the_named_fields():
    native = (Path(__file__).parent / "fixtures" / "cookbook" / "native-hello-world.yaml").read_text()
    h, llm, turn = await _run({"cookbook/native.yaml": native}, [call(
        "edit_profile", path="cookbook/native.yaml",
        changes={"specs.runtime.containerImage.uri": "acme/hello-api", "specs.runtime.containerImage.tag": "1.0.0"})])
    result = last_tool_result(llm)
    assert result["status"] == "written_valid" and result["effect"] == "verified"
    assert "uri: acme/hello-api" in h.ws.files["cookbook/native.yaml"]
    assert result["runnability"]["verdict"] != "will_not_run"
