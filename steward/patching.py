"""Field-level edits of an existing profile.

Small models are unreliable at re-emitting a whole profile (live run 07a7343: llama3.1 8B pasted an invented YAML
into the chat instead of editing the file). Setting a few dotted fields is a much smaller job: the model, or the
deterministic intent parser, names the fields and values; this module applies them to the real file content and the
result goes through the same SafeOps write path (local validator copy, read-back, IDE validator, rollback).
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from .hyperai_schema import load_yaml

_SEG = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


class PatchError(ValueError):
    pass


def _segments(path: str) -> list[str | int]:
    out: list[str | int] = []
    for name, index in _SEG.findall(path):
        out.append(int(index) if index else name)
    if not out:
        raise PatchError(f"empty field path {path!r}")
    return out


def normalise_path(doc: Any, path: str) -> str:
    """Accept native paths with or without the `applicationProfile.` prefix."""
    path = path.strip().strip(".")
    if isinstance(doc, dict) and "applicationProfile" in doc and not path.startswith("applicationProfile"):
        return f"applicationProfile.{path}"
    return path


def apply_changes(text: str, changes: dict[str, Any]) -> tuple[str, list[str]]:
    """Return the new YAML text and the list of fields actually changed."""
    doc = load_yaml(text)
    if not isinstance(doc, dict):
        raise PatchError("the file is not a YAML mapping")
    changed: list[str] = []
    for raw_path, value in changes.items():
        path = normalise_path(doc, raw_path)
        segs = _segments(path)
        node: Any = doc
        for i, seg in enumerate(segs[:-1]):
            nxt = segs[i + 1]
            if isinstance(seg, int):
                if not isinstance(node, list):
                    raise PatchError(f"{path}: {seg} is not a list index here")
                while len(node) <= seg:
                    node.append({} if not isinstance(nxt, int) else [])
                node = node[seg]
            else:
                if not isinstance(node, dict):
                    raise PatchError(f"{path}: cannot descend into {seg}")
                if node.get(seg) is None:
                    node[seg] = [] if isinstance(nxt, int) else {}
                node = node[seg]
        last = segs[-1]
        if isinstance(last, int):
            if not isinstance(node, list):
                raise PatchError(f"{path}: not a list")
            while len(node) <= last:
                node.append(None)
            old = node[last]
            node[last] = value
        else:
            if not isinstance(node, dict):
                raise PatchError(f"{path}: not a mapping")
            old = node.get(last)
            if value is None:
                node.pop(last, None)
            else:
                node[last] = value
        if old != value:
            changed.append(path)
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100), changed


def split_image(image: str) -> tuple[str, str]:
    """`acme/hello-api:1.0.0` -> (`acme/hello-api`, `1.0.0`); no tag -> `latest`."""
    ref = image.split("@")[0]
    if ":" in ref.rsplit("/", 1)[-1]:
        uri, tag = ref.rsplit(":", 1)
        return uri, tag
    return ref, "latest"
