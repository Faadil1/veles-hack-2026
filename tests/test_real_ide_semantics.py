"""Behaviour of the shipped IDE (GUI bundle + backend source, read by CI recon) and Steward's answers to it.

OBSERVED in donmichael/ide-gui:latest: streamed actions are fire-and-forget, the agent never learns the outcome,
ambiguous names are a silent no-op (WARN in the status log), create_file on an existing path fails.
"""

from pathlib import Path

from steward.llm import LLMTurn, ScriptedLLM
from stub_ide.app import Workspace
from tests.harness import Harness
from tests.test_tools_through_agent import call, last_tool_result

DEVICE = (Path(__file__).parent / "fixtures" / "cookbook" / "device-hello-world-docker.yaml").read_text()


def test_gui_refuses_ambiguous_bare_names_instead_of_first_match():
    ws = Workspace()
    ws.seed({"edge/app.yaml": "a", "cloud/app.yaml": "b"})
    out = ws.apply({"action": "delete_file", "path": "app.yaml"})
    assert out["applied"] is False and len(ws.files) == 2 and "matches 2 files" in ws.status_log[-1]


def test_gui_resolves_a_unique_suffix_and_fails_create_on_existing():
    ws = Workspace()
    ws.seed({"edge/app.yaml": "a"})
    assert ws.apply({"action": "edit_file", "path": "app.yaml", "content": "b"})["resolved"] == "edge/app.yaml"
    assert ws.apply({"action": "create_file", "path": "edge/app.yaml", "content": "c"})["applied"] is False
    assert ws.files["edge/app.yaml"] == "b"


async def test_every_action_is_read_back_before_steward_claims_it():
    llm = ScriptedLLM([call("create_profile", path="demo/web.yaml", kind="device", name="web", image="nginx:1.27"),
                       LLMTurn(text="ok")])
    h = Harness({}, llm=llm)
    await h.say("go ahead with the web server we discussed")
    result = last_tool_result(llm)
    assert result["status"] == "written_valid" and result["effect"] == "verified"
    kinds = [r["kind"] for r in h.sessions.get("u1").receipts]
    assert kinds.index("effect") < kinds.index("validate_file")  # never validates a file it has not seen land


async def test_when_the_ide_does_not_apply_actions_steward_does_not_claim_success():
    llm = ScriptedLLM([call("create_profile", path="demo/web.yaml", kind="device", name="web", image="nginx:1.27"),
                       LLMTurn(text="ok")])
    h = Harness({}, llm=llm)
    h.ws.drop_actions = True  # the IDE page is closed: nothing executes the streamed actions
    await h.say("go ahead with the web server we discussed")
    result = last_tool_result(llm)
    assert result["status"] == "sent_unverified" and result["effect"] == "not_seen"
    assert result["validator"]["outcome"] == "skipped"
    assert not any(r["kind"] == "validate_file" for r in h.sessions.get("u1").receipts)


async def test_confirmed_delete_that_never_lands_is_reported_as_unconfirmed():
    h = Harness({"demo/a.yaml": DEVICE}, llm=ScriptedLLM([call("delete_file", path="demo/a.yaml"), LLMTurn(text="")]))
    await h.say("delete demo/a.yaml")
    h.ws.drop_actions = True
    turn = await h.say("yes")
    assert "can't confirm" in turn.text and "Deleted" not in turn.text
    assert "demo/a.yaml" in h.ws.files


async def test_no_markdown_reaches_the_ide_panel():
    # The GUI renders agent text as is (OBSERVED): ** and backticks would show literally.
    h = Harness({"edge/app.yaml": DEVICE, "cloud/app.yaml": DEVICE})
    turn = await h.say("check app.yaml")
    assert "edge/app.yaml" in turn.text and "**" not in turn.text and "`" not in turn.text
