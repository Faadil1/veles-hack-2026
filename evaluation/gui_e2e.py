"""End to end in the official HYPER-AI IDE GUI: a browser types into the Hyperion panel and Steward answers.

Stack: the GUI (donmichael/ide-gui:latest, served on :5000), the backend (donmichael/ide-backend:latest, :3001),
Steward on :8000 (the GUI hard-codes http://localhost:8000/chat). Playwright drives Chromium like a user. After
every message the workspace is read from the backend and a screenshot is saved.

`--suite deterministic` needs no model (guardrail, check, undo paths). `--suite model` needs Steward to have a model
(e.g. Ollama llama3.1:8b in CI, or the organisers' server).

Evidence class: LIVE GUI + LIVE backend in CI (official images); model as configured.
Run: python -m evaluation.gui_e2e --suite deterministic --out evidence/gui-e2e
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from playwright.async_api import Page, async_playwright

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "cookbook"
DEVICE = (FIX / "device-hello-world-docker.yaml").read_text()
NATIVE = (FIX / "native-hello-world.yaml").read_text()
EDGE = DEVICE.replace("name: hello-world\n  annotations", "name: edge-app\n  annotations")
CLOUD = DEVICE.replace("name: hello-world\n  annotations", "name: cloud-app\n  annotations")
SEED = {"cookbook/native.yaml": NATIVE, "edge/app.yaml": EDGE, "cloud/app.yaml": CLOUD}

Check = Callable[[str, dict[str, str], str], tuple[bool, str]]


@dataclass
class Step:
    sid: str
    text: str
    check: Check
    timeout_s: float = 60
    shot: str = ""


@dataclass
class Result:
    sid: str
    text: str
    passed: bool
    reason: str
    reply: str
    seconds: float
    files: list[str] = field(default_factory=list)
    status_log_tail: list[str] = field(default_factory=list)


def says(*words: str) -> Check:
    def check(reply: str, files: dict[str, str], log: str) -> tuple[bool, str]:
        missing = [w for w in words if w.lower() not in reply.lower()]
        return (not missing), ("ok" if not missing else f"reply missing {missing}")
    return check


def all_of(*checks: Check) -> Check:
    def check(reply: str, files: dict[str, str], log: str) -> tuple[bool, str]:
        for c in checks:
            ok, why = c(reply, files, log)
            if not ok:
                return ok, why
        return True, "ok"
    return check


def files_equal(expected: dict[str, str]) -> Check:
    def check(reply: str, files: dict[str, str], log: str) -> tuple[bool, str]:
        diff = [p for p in set(expected) | set(files) if expected.get(p) != files.get(p)]
        return (not diff), ("workspace as expected" if not diff else f"workspace differs at {sorted(diff)}")
    return check


def new_valid_profile() -> Check:
    def check(reply: str, files: dict[str, str], log: str) -> tuple[bool, str]:
        from steward import spec
        new = [p for p in files if p not in SEED and p.endswith((".yaml", ".yml"))]
        ok = [p for p in new if spec.check_profile(files[p]).ok]
        return bool(ok), f"new profiles {new}, valid {ok}"
    return check


def changed_and_valid(path: str) -> Check:
    def check(reply: str, files: dict[str, str], log: str) -> tuple[bool, str]:
        from steward import runnability, spec
        if files.get(path) in (None, SEED.get(path)):
            return False, f"{path} not changed"
        if not spec.check_profile(files[path]).ok:
            return False, f"{path} invalid"
        return True, f"fixed ({runnability.assess(files[path]).verdict.value})"
    return check


DETERMINISTIC = [
    Step("G1", "What's the weather in Valencia today?", says("HYPER-AI"), shot="off-topic"),
    Step("G2", "check cookbook/native.yaml", says("valid", "will not run"), shot="check-native"),
    Step("G3", "check app.yaml", all_of(says("edge/app.yaml", "cloud/app.yaml"), files_equal(SEED)), shot="ambiguous"),
    Step("G4", "undo", says("nothing"), shot="undo-empty"),
]

MODEL = [
    Step("M1", "What is HyperAI?", says("continuum"), timeout_s=600, shot="what-is-hyperai"),
    Step("M2", "Create a deployment YAML for a service using the nginx Docker image", new_valid_profile(),
         timeout_s=600, shot="create-nginx"),
    Step("M3", "delete app.yaml", all_of(says("edge/app.yaml", "cloud/app.yaml")), timeout_s=600, shot="delete-ambiguous"),
    Step("M4", "Fix cookbook/native.yaml so that it will actually run. My app image is acme/hello-api:1.0.0 and it "
               "starts with uvicorn on port 8000.", changed_and_valid("cookbook/native.yaml"), timeout_s=600,
         shot="fix-native"),
    Step("M5", "Which container image did you just put in that file?", says("acme/hello-api"), timeout_s=600,
         shot="memory"),
    Step("M6", "undo", lambda r, f, log: (f.get("cookbook/native.yaml") == NATIVE, "native restored"
                                          if f.get("cookbook/native.yaml") == NATIVE else "native not restored"),
         timeout_s=120, shot="undo"),
]


async def workspace(backend: str) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=10) as http:
        out: dict[str, str] = {}

        async def walk(path: str) -> None:
            for e in (await http.get(f"{backend}/files", params={"path": path})).json():
                if e["type"] == "folder":
                    await walk(e["path"])
                else:
                    r = await http.get(f"{backend}/file", params={"path": e["path"]})
                    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                    out[e["path"]] = body.get("content", r.text) if isinstance(body, dict) else r.text
        await walk("")
        return out


async def reset_workspace(backend: str) -> None:
    async with httpx.AsyncClient(timeout=10) as http:
        for e in (await http.get(f"{backend}/files", params={"path": ""})).json():
            await http.delete(f"{backend}/delete", params={"path": e["path"]})
        for path, content in SEED.items():
            await http.post(f"{backend}/file", json={"path": path, "content": content})


async def ask(page: Page, text: str, timeout_s: float) -> str:
    before = await page.locator(".agent-msg.agent").count()
    await page.fill(".agent-input-row textarea", text)
    await page.click(".agent-send-btn")
    await page.wait_for_function(
        f"document.querySelectorAll('.agent-msg.agent').length > {before} "
        "&& !document.querySelector('.agent-thinking') && !document.querySelector('.agent-send-btn').disabled",
        timeout=timeout_s * 1000, polling=500)
    await page.wait_for_timeout(1500)  # let fire-and-forget actions and the tree refresh settle
    return (await page.locator(".agent-msg.agent").last.inner_text()).strip()


async def status_log(page: Page) -> list[str]:
    box = page.locator("text=Workspace ready").locator("xpath=..")
    try:
        return [line for line in (await box.inner_text()).splitlines() if line.strip()][-6:]
    except Exception:  # noqa: BLE001 - diagnostic only
        return []


async def run(suite: str, gui: str, backend: str, out: Path, executable: str | None,
              video: bool = False) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    steps = DETERMINISTIC if suite == "deterministic" else DETERMINISTIC[:1] + MODEL
    await reset_workspace(backend)
    results: list[Result] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(**({"executable_path": executable} if executable else {}))
        context = await browser.new_context(viewport={"width": 1600, "height": 950},
                                            **({"record_video_dir": str(out / "video"),
                                                "record_video_size": {"width": 1600, "height": 950}} if video else {}))
        page = await context.new_page()
        await page.goto(gui)
        await page.click("button[title='Hyperion Agent']")
        await page.wait_for_selector(".agent-input-row textarea")
        await page.click("button[title='Refresh']")
        await page.screenshot(path=str(out / "00-start.png"))
        for i, step in enumerate(steps, 1):
            started = time.perf_counter()
            try:
                reply = await ask(page, step.text, step.timeout_s)
                files = await workspace(backend)
                log = await status_log(page)
                passed, reason = step.check(reply, files, "\n".join(log))
            except Exception as exc:  # noqa: BLE001 - recorded as a failure, never hidden
                reply, files, log, passed, reason = "", {}, [], False, f"{type(exc).__name__}: {str(exc)[:300]}"
            await page.screenshot(path=str(out / f"{i:02d}-{step.shot or step.sid}.png"))
            results.append(Result(step.sid, step.text, passed, reason, reply[:1200],
                                  round(time.perf_counter() - started, 1), sorted(files), log))
        await context.close()  # flushes the video file
        await browser.close()
    report = {"evidence_class": "LIVE GUI + backend (official images in CI) / browser-driven", "suite": suite,
              "passed": sum(r.passed for r in results), "total": len(results),
              "results": [r.__dict__ for r in results]}
    (out / f"gui-e2e-{suite}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["deterministic", "model"], default="deterministic")
    parser.add_argument("--gui", default="http://localhost:5000/")
    parser.add_argument("--backend", default="http://localhost:3001/api")
    parser.add_argument("--out", default="evidence/gui-e2e")
    parser.add_argument("--chromium", default="", help="executable path, when the bundled browser is absent")
    parser.add_argument("--video", action="store_true", help="record a video of the session (demo material)")
    args = parser.parse_args()
    report = asyncio.run(run(args.suite, args.gui, args.backend, Path(args.out), args.chromium or None,
                             args.video))
    print(json.dumps({k: report[k] for k in ("suite", "passed", "total")}))
    for r in report["results"]:
        print(f"{r['sid']} {'PASS' if r['passed'] else 'FAIL'} {r['seconds']}s {r['reason']} | {r['reply'][:160]!r}")
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
