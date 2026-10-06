"""Behaviour tests for Steward's safety invariants, against the LOCAL_STUB IDE."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from steward.llm import LLMError, LLMTurn, ScriptedLLM, ToolCall
from tests.harness import Harness

FIX = Path(__file__).parent / "fixtures" / "cookbook"
NATIVE_BROKEN = (FIX / "native-hello-world.yaml").read_text()
DEVICE_OK = (FIX / "device-hello-world-docker.yaml").read_text()
APP_A = "apiVersion: hyper.ai/v1\nkind: Application\nmetadata:\n  name: a\n"
APP_B = "apiVersion: hyper.ai/v1\nkind: Application\nmetadata:\n  name: b\n"


def tool(name: str, **args) -> LLMTurn:
    return LLMTurn(text="", tool_calls=[ToolCall(f"t-{name}", name, args)])


def say(text: str) -> LLMTurn:
    return LLMTurn(text=text)


pytestmark = pytest.mark.asyncio


# I1 — ambiguity guard -------------------------------------------------------------------------------

async def test_ambiguous_delete_emits_no_action_and_lists_matches():
    h = Harness({"edge/app.yaml": APP_A, "cloud/app.yaml": APP_B},
                llm=ScriptedLLM([tool("delete_file", path="app.yaml"), say("Which one: edge/app.yaml or cloud/app.yaml?")]))
    turn = await h.say("delete app.yaml")
    assert turn.actions == []
    assert set(h.ws.files) == {"edge/app.yaml", "cloud/app.yaml"}
    receipts = h.sessions.get("u1").receipts
    assert any(r["kind"] == "guard" and r.get("decision") == "blocked_first_match" for r in receipts)


async def test_check_command_on_ambiguous_name_lists_both_paths_without_model():
    h = Harness({"edge/app.yaml": APP_A, "cloud/app.yaml": APP_B}, llm=None)
    turn = await h.say("check app.yaml")
    assert "edge/app.yaml" in turn.text and "cloud/app.yaml" in turn.text
    assert turn.actions == []


# I2 + I4 — confirmation, restore point, undo --------------------------------------------------------

async def test_delete_requires_confirmation_then_undo_restores_exact_content():
    h = Harness({"demo/app.yaml": DEVICE_OK},
                llm=ScriptedLLM([tool("delete_file", path="app.yaml"), say("Delete demo/app.yaml? (yes/no)")]))
    first = await h.say("remove app.yaml")
    assert first.actions == [] and "demo/app.yaml" in h.ws.files

    confirm = await h.say("yes")
    assert confirm.actions == [{"action": "delete_file", "path": "demo/app.yaml"}]
    assert "demo/app.yaml" not in h.ws.files

    undo = await h.say("undo")
    assert undo.actions[0]["action"] == "create_file"
    assert h.ws.files["demo/app.yaml"] == DEVICE_OK


async def test_declining_confirmation_changes_nothing():
    h = Harness({"demo/app.yaml": DEVICE_OK}, llm=ScriptedLLM([tool("delete_file", path="demo/app.yaml"), say("Sure?")]))
    await h.say("delete demo/app.yaml")
    turn = await h.say("no")
    assert turn.actions == [] and h.ws.files["demo/app.yaml"] == DEVICE_OK


async def test_delete_uses_full_path_even_when_user_gave_a_bare_name():
    h = Harness({"deep/nested/only.yaml": DEVICE_OK}, llm=ScriptedLLM([tool("delete_file", path="only.yaml"), say("ok?")]))
    await h.say("delete only.yaml")
    turn = await h.say("yes")
    assert turn.actions == [{"action": "delete_file", "path": "deep/nested/only.yaml"}]


# I3 — validator loop and rollback ------------------------------------------------------------------

async def test_new_valid_profile_is_written_and_validated():
    h = Harness({}, llm=ScriptedLLM([tool("write_profile", path="demo/hello.yaml", yaml=DEVICE_OK), say("Saved.")]))
    turn = await h.say("create a hello world device app in demo/hello.yaml")
    assert turn.actions[0]["action"] == "create_file"
    assert h.ws.files["demo/hello.yaml"] == DEVICE_OK
    kinds = [r["kind"] for r in h.sessions.get("u1").receipts]
    assert "validate_file" in kinds


async def test_locally_invalid_profile_never_reaches_workspace():
    bad = DEVICE_OK.replace("kind: DockerImage", "kind: Kubernetes")
    h = Harness({}, llm=ScriptedLLM([tool("write_profile", path="demo/x.yaml", yaml=bad), say("It failed checks.")]))
    turn = await h.say("make it")
    assert turn.actions == [] and h.ws.files == {}


async def test_validator_rejection_rolls_back_overwrite_to_original():
    original = DEVICE_OK
    changed = DEVICE_OK.replace("name: hello-world\n  annotations", "name: hello-world-2\n  annotations")
    h = Harness({"demo/app.yaml": original},
                llm=ScriptedLLM([tool("write_profile", path="demo/app.yaml", yaml=changed), say("Overwrite?")]))
    h.ws.forced_invalid["demo/app.yaml"] = "rejected by backend"
    await h.say("rename the app")
    assert h.sessions.get("u1").pending is not None  # not created by Steward → confirmation first
    turn = await h.say("yes")
    assert [a["action"] for a in turn.actions] == ["edit_file", "edit_file"]
    assert h.ws.files["demo/app.yaml"] == original
    assert any(r["kind"] == "rollback" for r in h.sessions.get("u1").receipts)


async def test_validator_rejection_of_new_file_deletes_it():
    h = Harness({}, llm=ScriptedLLM([tool("write_profile", path="demo/new.yaml", yaml=DEVICE_OK), say("Rejected.")]))
    h.ws.forced_invalid["demo/new.yaml"] = "rejected by backend"
    turn = await h.say("create it")
    assert [a["action"] for a in turn.actions] == ["create_file", "delete_file"]
    assert "demo/new.yaml" not in h.ws.files


# I5 — failure behaviour ----------------------------------------------------------------------------

async def test_backend_down_means_no_action():
    h = Harness({}, llm=ScriptedLLM([tool("write_profile", path="demo/a.yaml", yaml=DEVICE_OK), say("Backend down.")]),
                backend_up=False)
    turn = await h.say("create it")
    assert turn.actions == []
    assert any(r["kind"] == "read_file" and r["outcome"] == "unreachable" for r in h.sessions.get("u1").receipts)


async def test_model_failure_degrades_without_writing():
    class Boom(ScriptedLLM):
        async def step(self, *a, **k):
            raise LLMError("overloaded")

    h = Harness({}, llm=Boom([]))
    turn = await h.say("how do I deploy a workflow?")
    assert turn.actions == []
    assert "Deploy" in turn.text and "unavailable" in turn.text


async def test_path_traversal_is_rejected():
    h = Harness({}, llm=ScriptedLLM([tool("write_profile", path="../etc/x.yaml", yaml=DEVICE_OK), say("Refused.")]))
    turn = await h.say("write outside")
    assert turn.actions == []


# runnability through the check command ----------------------------------------------------------------

async def test_check_flags_official_cookbook_example_as_not_runnable():
    h = Harness({"cookbook/native.yaml": NATIVE_BROKEN}, llm=None)
    turn = await h.say("check native.yaml")
    assert "will not run" in turn.text
    assert "uvicorn" in turn.text and "nginx" in turn.text


async def test_undo_with_nothing_to_undo():
    h = Harness({}, llm=None)
    turn = await h.say("undo")
    assert "nothing" in turn.text.lower() and turn.actions == []


async def test_sessions_are_isolated_per_user():
    h = Harness({}, llm=ScriptedLLM([tool("write_profile", path="u1.yaml", yaml=DEVICE_OK), say("ok")]))
    await h.say("create", user_id="alice")
    turn = await h.say("undo", user_id="bob")
    assert turn.actions == [] and "u1.yaml" in h.ws.files


async def test_guard_question_is_said_even_if_model_stays_silent():
    h = Harness({"edge/app.yaml": APP_A, "cloud/app.yaml": APP_B},
                llm=ScriptedLLM([tool("delete_file", path="app.yaml")]))  # model says nothing afterwards
    turn = await h.say("delete app.yaml")
    assert "edge/app.yaml" in turn.text and "cloud/app.yaml" in turn.text and turn.actions == []


async def test_confirmation_question_is_deterministic_and_ends_turn():
    h = Harness({"demo/app.yaml": DEVICE_OK}, llm=ScriptedLLM([tool("delete_file", path="demo/app.yaml")]))
    turn = await h.say("delete demo/app.yaml")
    assert "Reply **yes** or **no**" in turn.text and turn.actions == []


async def test_check_profile_accepts_a_path():
    h = Harness({"cookbook/native.yaml": NATIVE_BROKEN},
                llm=ScriptedLLM([tool("check_profile", yaml="cookbook/native.yaml"), say("It won't run.")]))
    await h.say("will it run?")
    messages = h.steward.llm.calls[-1]
    results = [b for m in messages if isinstance(m["content"], list) for b in m["content"]
               if b.get("type") == "tool_result"]
    result = json.loads(results[0]["content"])
    assert result["runnability"]["verdict"] == "will_not_run"
