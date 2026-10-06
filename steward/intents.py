"""Deterministic intent fallback for when no language model is reachable.

How the evaluation container gets its model key is not documented (UNKNOWN). If the model is missing or down, the
canonical requests must still work: creating a profile for an image, deleting a path, creating a folder. These
patterns cover them; anything else falls back to cited documentation passages. Every action still goes through
SafeOps (lookup, confirmation, validator, read-back), exactly like the model path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .templates import slug

_CREATE = re.compile(r"\b(create|make|generate|write|build|add|set up|new)\b", re.I)
_PROFILE_NOUN = re.compile(r"\b(ya?ml|profile|app|application|deployment|service|manifest)\b", re.I)
_DELETE = re.compile(r"^\s*(please\s+)?(delete|remove)\s+(the\s+)?(file\s+|folder\s+)?(?P<target>[\w./-]+)\s*[.!?]*\s*$",
                     re.I)
_FOLDER = re.compile(r"^\s*(please\s+)?(create|make|add)\s+(a\s+|the\s+)?(new\s+)?(folder|directory)\s+"
                     r"(called\s+|named\s+)?(?P<path>[\w./-]+)\s*[.!?]*\s*$", re.I)
_PATH = re.compile(r"(?P<path>[\w.-]+(?:/[\w.-]+)*\.ya?ml)\b")
_IMAGE_PATTERNS = [
    re.compile(r"\bimage\s+[\"'`]?(?P<img>[a-z0-9][\w./:@-]*)", re.I),
    re.compile(r"\b(?:using|with|runs?|running|for|from)\s+(?:the\s+|an?\s+)?[\"'`]?(?P<img>[a-z0-9][\w./:@-]*)[\"'`]?"
               r"\s+(?:docker\s+|container\s+)?image\b", re.I),
    re.compile(r"\b(?:using|with|runs?|running|for)\s+(?:the\s+)?[\"'`]?(?P<img>[a-z0-9][\w.-]*/[\w./:@-]+)", re.I),
    re.compile(r"\b(?:for|of)\s+(?:an?\s+)?(?P<img>nginx|redis|postgres|mysql|mongo|httpd|traefik|grafana|"
               r"prometheus|mosquitto|kafka|rabbitmq|hello-world|busybox|alpine)\b", re.I),
]
_NAME = re.compile(r"\b(?:called|named)\s+[\"'`]?(?P<name>[\w-]+)", re.I)
_PORT = re.compile(r"\bports?\s+(?P<port>\d{2,5})\b", re.I)
_ARCH = re.compile(r"\b(arm64|amd64|x86_64|armv7)\b", re.I)
_LATENCY = re.compile(r"\b(?P<ms>\d+)\s*ms\b", re.I)
_WELL_KNOWN_PORTS = {"nginx": 80, "httpd": 80, "traefik": 80, "grafana": 3000, "prometheus": 9090, "redis": 6379,
                     "postgres": 5432, "mysql": 3306, "mongo": 27017, "mosquitto": 1883, "rabbitmq": 5672,
                     "kafka": 9092}
_STOP = {"a", "an", "the", "my", "this", "that", "docker", "container", "service", "app", "it"}


@dataclass
class Intent:
    kind: str  # create_profile | delete | create_folder
    args: dict[str, Any] = field(default_factory=dict)


def parse(text: str) -> Intent | None:
    m = _FOLDER.match(text)
    if m:
        return Intent("create_folder", {"path": m.group("path")})
    m = _DELETE.match(text)
    if m:
        return Intent("delete", {"path": m.group("target")})
    if _CREATE.search(text) and _PROFILE_NOUN.search(text):
        image = _image(text)
        if not image:
            return None
        base = image.split("@")[0].rsplit("/", 1)[-1].split(":")[0]
        name_m = _NAME.search(text)
        name = slug(name_m.group("name") if name_m else base)
        path_m = _PATH.search(text)
        args: dict[str, Any] = {"kind": "native" if re.search(r"\bnative\b", text, re.I) else "device",
                                "name": name, "image": image, "path": path_m.group("path") if path_m else f"{name}.yaml"}
        port_m = _PORT.search(text)
        port = int(port_m.group("port")) if port_m else _WELL_KNOWN_PORTS.get(base)
        if port:
            args["ports"] = [port]
        archs = sorted({a.lower() for a in _ARCH.findall(text)})
        if archs:
            args["architectures"] = archs
        lat = _LATENCY.search(text)
        if lat:
            args["latency_ms"] = float(lat.group("ms"))
        return Intent("create_profile", args)
    return None


def _image(text: str) -> str | None:
    for rx in _IMAGE_PATTERNS:
        for m in rx.finditer(text):
            img = m.group("img").strip("\"'`.,")
            if img.lower() not in _STOP:
                return img
    return None
