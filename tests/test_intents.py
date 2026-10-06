"""Deterministic fallback when no model is reachable (evaluation key provisioning is UNKNOWN)."""

from steward import intents
from tests.harness import Harness


def test_official_example_request_parses():
    i = intents.parse("Create a deployment YAML for a service using the nginx Docker image")
    assert i.kind == "create_profile" and i.args["image"] == "nginx" and i.args["ports"] == [80]
    assert i.args["path"] == "nginx.yaml" and i.args["kind"] == "device"


def test_named_image_path_and_constraints_parse():
    i = intents.parse("Create a device app called sensor-reader that runs the Docker image acme/sensor:1.2 on arm64 "
                      "edge devices with a 200 ms latency budget. Save it as edge/sensor-reader.yaml.")
    assert i.args == {"kind": "device", "name": "sensor-reader", "image": "acme/sensor:1.2",
                      "path": "edge/sensor-reader.yaml", "architectures": ["arm64"], "latency_ms": 200.0}


def test_delete_and_folder_parse_and_questions_do_not():
    assert intents.parse("delete app.yaml").args == {"path": "app.yaml"}
    assert intents.parse("create a folder called edge").args == {"path": "edge"}
    assert intents.parse("What is HyperAI?") is None
    assert intents.parse("How do I create a profile?") is None  # no image named: not an action


async def test_without_a_model_the_official_example_still_creates_a_valid_file():
    h = Harness({})
    turn = await h.say("Create a deployment YAML for a service using the nginx Docker image")
    assert [a["action"] for a in turn.actions] == ["create_file"] and "nginx.yaml" in h.ws.files
    assert "validator reports it valid" in turn.text


async def test_without_a_model_delete_still_asks_and_ambiguity_still_holds():
    h = Harness({"edge/app.yaml": "a: 1", "cloud/app.yaml": "a: 2"})
    turn = await h.say("delete app.yaml")
    assert turn.actions == [] and "edge/app.yaml" in turn.text
    h2 = Harness({"demo/a.yaml": "a: 1"})
    ask = await h2.say("delete demo/a.yaml")
    assert ask.actions == [] and "Reply yes or no" in ask.text
    done = await h2.say("yes")
    assert "demo/a.yaml" not in h2.ws.files and "Deleted" in done.text
