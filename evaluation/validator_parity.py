"""Differential test: the real HYPER-AI backend validator (JavaScript) versus Steward's Python port.

Builds a corpus from the official cookbook examples, Steward's template outputs, and systematic mutations of each
(every field removed, retyped, set to an out-of-range or wrong-enum value, unknown keys added, YAML 1.1/1.2 edge
cases such as yes/no, unquoted timestamps and versions, duplicate keys). Each document is validated by both
implementations and the (field, message) sets are compared for errors and the field sets for warnings.

The JavaScript side is the backend's own validation/ folder (copied from donmichael/ide-backend:latest by the
ide-recon workflow) run with Node and the `yaml` package. Evidence class: BEHAVIOR, real validator source.

Run: python -m evaluation.validator_parity --validator-dir <dir containing validation/ and node_modules/>
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

from steward import hyperai_schema, templates

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "cookbook"

RUNNER = """
import { validateProfile } from "./validation/index.js";
import fs from "fs";
const files = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
for (const [name, text] of Object.entries(files)) {
  const r = validateProfile(text);
  out[name] = { type: r.type, valid: r.valid,
    errors: r.errors.map((e) => [e.field, e.message]), warnings: r.warnings.map((w) => w.field) };
}
fs.writeFileSync(process.argv[3], JSON.stringify(out));
"""


def _leaves(node: Any, path: tuple = ()) -> list[tuple]:
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.append(path + (k,))
            out.extend(_leaves(v, path + (k,)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.append(path + (i,))
            out.extend(_leaves(v, path + (i,)))
    return out


def _get_parent(doc: Any, path: tuple) -> tuple[Any, Any]:
    node = doc
    for p in path[:-1]:
        node = node[p]
    return node, path[-1]


def _dump(doc: Any) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def _mutations(name: str, text: str) -> dict[str, str]:
    base = hyperai_schema.load_yaml(text)
    out = {name: text}
    replacements: list[Any] = [None, 7, 2.5, -1, 0, 70000, True, "x", "", [], ["a"], [1], {}, {"k": 1}, "2026-01-01"]
    for path in _leaves(base):
        tag = ".".join(map(str, path))
        doc = copy.deepcopy(base)
        parent, key = _get_parent(doc, path)
        if isinstance(parent, dict):
            del parent[key]
            out[f"{name}::del::{tag}"] = _dump(doc)
            doc = copy.deepcopy(base)
            parent, key = _get_parent(doc, path)
            parent[f"{key}Extra"] = 1
            out[f"{name}::unknown::{tag}"] = _dump(doc)
        for i, rep in enumerate(replacements):
            doc = copy.deepcopy(base)
            parent, key = _get_parent(doc, path)
            parent[key] = rep
            out[f"{name}::set{i}::{tag}"] = _dump(doc)
    # Raw-text edge cases the dumper would never produce.
    edge = {
        "yes_no": text.replace("isHighlyAvailable: false", "isHighlyAvailable: no"),
        "unquoted_version": re.sub(r"schemaVersion: .*", "schemaVersion: 1.1", text),
        "unquoted_semver": re.sub(r"schemaVersion: .*", "schemaVersion: 1.1.0", text),
        "unquoted_ts": re.sub(r"(\n(\s*)name: .*)", r"\1\n\2createdAt: 2026-06-04T12:00:00Z", text, count=1),
        "on_off": text.replace("false", "off").replace("true", "on"),
        "dup_key": text.replace("metadata:", "metadata:\n  name: dup\n  name: dup2", 1),
        "tabs_broken": text.replace("\n  ", "\n\t", 1),
        "empty": "",
        "scalar": "hello",
        "list_root": "- a\n- b\n",
        "only_kind": "kind: Application\n",
        "native_null": "applicationProfile:\n",
        "native_extra_root": "foo: 1\n" + text if "applicationProfile" in text else text,
        "octal_hex": re.sub(r"(schedulingPriority|port): \d+", r"\1: 0x10", text),
        "octal_o": re.sub(r"(schedulingPriority|port): \d+", r"\1: 0o17", text),
        "float_int": re.sub(r"(schedulingPriority|port): \d+", r"\1: 80.0", text),
        "inf": re.sub(r"(schedulingPriority|port): \d+", r"\1: .inf", text),
        "null_tilde": re.sub(r"owner: .*", "owner: ~", text),
    }
    for k, v in edge.items():
        out[f"{name}::edge::{k}"] = v
    return out


def corpus() -> dict[str, str]:
    docs: dict[str, str] = {}
    sources = {p.name: p.read_text() for p in sorted(FIX.glob("*.yaml"))}
    sources["tpl-device-docker.yaml"] = templates.build_device_profile("nginx-web", image="nginx:1.27", ports=[80])
    sources["tpl-device-apk.yaml"] = templates.build_device_profile(
        "cam", workload="AndroidApk", apk_url="https://example.com/a.apk", package_name="com.ex.cam",
        device_name="pixel-7")
    sources["tpl-device-esp32.yaml"] = templates.build_device_profile(
        "temp", workload="esp32Binary", binary_url="https://example.com/fw.bin", chip="esp32s3")
    sources["tpl-native.yaml"] = templates.build_native_profile(
        "hello-api", image="acme/hello-api", tag="1.0.0", entry_point="uvicorn", args=["app:app"], ports=[8000])
    for name, text in sources.items():
        docs.update(_mutations(name, text))
    return docs


def run_js(validator_dir: Path, docs: dict[str, str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(validator_dir) / "parity-runner.mjs"
        runner.write_text(RUNNER)
        src, dst = Path(tmp) / "in.json", Path(tmp) / "out.json"
        src.write_text(json.dumps(docs))
        subprocess.run(["node", str(runner), str(src), str(dst)], check=True, cwd=validator_dir)
        return json.loads(dst.read_text())


def run_py(docs: dict[str, str]) -> dict[str, Any]:
    out = {}
    for name, text in docs.items():
        r = hyperai_schema.validate_profile(text)
        out[name] = {"type": r.type, "valid": r.valid,
                     "errors": [[e.path, e.message] for e in r.errors], "warnings": [w.path for w in r.warnings]}
    return out


def compare(js: dict[str, Any], py: dict[str, Any]) -> list[dict[str, Any]]:
    diffs = []
    for name in js:
        a, b = js[name], py[name]
        if a["type"] != b["type"] or a["valid"] != b["valid"]:
            diffs.append({"doc": name, "what": "type/valid", "js": [a["type"], a["valid"]], "py": [b["type"], b["valid"]]})
            continue
        if a["errors"] and a["errors"][0][1].startswith("Invalid YAML"):
            continue  # both reject the document as YAML; parser wording differs by design
        ja, pa = {tuple(e) for e in a["errors"]}, {tuple(e) for e in b["errors"]}
        if ja != pa:
            diffs.append({"doc": name, "what": "errors", "only_js": sorted(ja - pa), "only_py": sorted(pa - ja)})
        if set(a["warnings"]) != set(b["warnings"]):
            diffs.append({"doc": name, "what": "warnings", "only_js": sorted(set(a["warnings"]) - set(b["warnings"])),
                          "only_py": sorted(set(b["warnings"]) - set(a["warnings"]))})
    return diffs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validator-dir", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    docs = corpus()
    js, py = run_js(Path(args.validator_dir), docs), run_py(docs)
    diffs = compare(js, py)
    report = {"evidence_class": "BEHAVIOR / real backend validator source vs Python port",
              "documents": len(docs), "js_invalid": sum(not r["valid"] for r in js.values()),
              "disagreements": len(diffs), "diffs": diffs[:200]}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ("documents", "js_invalid", "disagreements")}))
    for d in diffs[:15]:
        print(json.dumps(d, ensure_ascii=False)[:400])
    raise SystemExit(1 if diffs else 0)


if __name__ == "__main__":
    main()
