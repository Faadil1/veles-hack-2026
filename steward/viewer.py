"""Read-only receipts viewer: one session's timeline of lookups, guard decisions, actions, validator calls and
model calls. Server-rendered HTML, no scripts, so it works anywhere the service is reachable."""

from __future__ import annotations

import html
from typing import Any

from .engine import Session

_LABELS = {
    "user": "You", "route": "Request", "read_file": "Lookup", "validate_file": "IDE validator", "guard": "Guard",
    "action": "Action", "rollback": "Rollback", "undo": "Undo", "confirmation": "Confirmation", "llm": "Model",
    "local_check": "Local check", "runnability": "Runnability", "search_docs": "Docs", "docs_prefetch": "Docs",
    "create_profile": "Builder", "degraded_mode": "Degraded", "llm_error": "Model error", "tool_error": "Error",
    "turn_done": "Turn done", "turn_error": "Error", "guardrail": "Scope",
}
_TONE = {"guard": "warn", "rollback": "warn", "undo": "info", "confirmation": "info", "tool_error": "bad",
         "turn_error": "bad", "llm_error": "bad", "degraded_mode": "warn", "action": "act"}


def _summary(r: dict[str, Any]) -> str:
    k = r["kind"]
    if k == "user":
        return r.get("text", "")
    if k == "read_file":
        extra = f" → {', '.join(r['matches'])}" if r.get("matches") else (f" → {r['path']}" if r.get("path") else "")
        return f"{r.get('target')} : {r.get('outcome')}{extra}"
    if k == "guard":
        tail = f" ({', '.join(r['matches'])})" if r.get("matches") else (f" {r['path']}" if r.get("path") else "")
        return f"{r.get('rule')} {r.get('decision')}{tail}"
    if k == "action":
        return f"{r.get('action')} {r.get('path')}" + ("" if r.get("reversible", True) else " (not reversible)")
    if k == "validate_file":
        errs = "; ".join(f"{e.get('field')}: {e.get('message')}" for e in (r.get("errors") or [])[:3])
        return f"{r.get('path')} : {r.get('outcome')} valid={r.get('valid')}" + (f" · {errs}" if errs else "")
    if k == "runnability":
        return f"{r.get('path')} : {r.get('verdict')}" + "".join(f" · {f['message']}" for f in r.get("findings", [])[:2])
    if k == "llm":
        tools = ", ".join(r.get("tools") or []) or "text"
        return f"{r.get('model')} · {r.get('input_tokens')}→{r.get('output_tokens')} tokens · {r.get('latency_ms')} ms · {tools}"
    if k in ("rollback", "undo", "confirmation"):
        return " ".join(f"{key}={val}" for key, val in r.items() if key not in ("seq", "at", "kind"))
    if k in ("docs_prefetch", "search_docs"):
        return "; ".join(r.get("hits") or []) or "no matching passage"
    if k == "turn_done":
        return f"{r.get('latency_ms')} ms"
    return " ".join(f"{key}={val}" for key, val in r.items() if key not in ("seq", "at", "kind"))[:300]


def render(session: Session | None, user_id: str) -> str:
    rows = []
    for r in (session.receipts if session else []):
        tone = _TONE.get(r["kind"], "")
        rows.append(
            f'<li class="{tone}"><time>{html.escape(r["at"][11:23])}</time>'
            f'<b>{html.escape(_LABELS.get(r["kind"], r["kind"]))}</b>'
            f'<span>{html.escape(_summary(r))}</span></li>')
    journal = []
    for e in (session.journal if session else []):
        state = "undone" if e.undone else ("not reversible" if not e.reversible else "reversible")
        journal.append(f"<li><b>#{e.entry_id}</b> {html.escape(e.action)} <code>{html.escape(e.path)}</code>"
                       f" <em>{state}</em></li>")
    pending = html.escape(session.pending.summary) if session and session.pending else "none"
    body_rows = "\n".join(rows) or "<li><span>No activity yet for this user.</span></li>"
    body_journal = "\n".join(journal) or "<li>Nothing changed yet.</li>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Steward receipts</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1c1a;--muted:#6b6862;--line:#e6e2da;--warn:#9a5b00;--bad:#a1271b;--info:#285e8c;--act:#2d6a3e}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151513;--fg:#ecebe7;--muted:#9c9a94;--line:#2c2b28;--warn:#e0a54a;--bad:#ef7a6c;--info:#8cb8e0;--act:#7cc28e}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,sans-serif}}
main{{max-width:60rem;margin:0 auto;padding:2rem 1rem 4rem}}
h1{{font-size:1.25rem;margin:0 0 .25rem}} p{{color:var(--muted);margin:0 0 1.5rem}}
h2{{font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:2rem 0 .5rem}}
ol,ul{{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}}
li{{display:grid;grid-template-columns:7.5rem 7.5rem 1fr;gap:.75rem;padding:.45rem 0;border-bottom:1px solid var(--line)}}
ul li{{display:block}} time{{color:var(--muted);font:12px ui-monospace,monospace;padding-top:.15rem}}
b{{font-weight:600}} span{{overflow-wrap:anywhere}} code{{font:13px ui-monospace,monospace}} em{{color:var(--muted)}}
.warn b{{color:var(--warn)}} .bad b{{color:var(--bad)}} .info b{{color:var(--info)}} .act b{{color:var(--act)}}
@media (max-width:40rem){{li{{grid-template-columns:1fr}} time{{padding:0}}}}
</style></head><body><main>
<h1>Steward receipts</h1>
<p>Session <code>{html.escape(user_id)}</code> · waiting for confirmation: {pending}</p>
<h2>Timeline</h2><ol>{body_rows}</ol>
<h2>Restore points</h2><ul>{body_journal}</ul>
</main></body></html>"""
