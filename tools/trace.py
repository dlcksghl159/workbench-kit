#!/usr/bin/env python3
"""Summarize this workspace's Codex sessions: your prompts, delegations, token use.

Reads $CODEX_HOME/sessions/**/rollout-*.jsonl (default ~/.codex), keeps the
sessions whose working directory is this workspace, and prints a compact trace.
Useful for self-review, for the mock grader, and for answering "how did you use AI?".
Standard library only; Python 3.8+.

Usage:
  python3 .kit/tools/trace.py [workspace] [--since-install] [--full] [--out FILE]
"""
import argparse
import datetime
import glob
import json
import os
import sys

INJECTED = ("# AGENTS.md instructions", "<environment_context>", "<user_instructions>", "<permissions",
            "<skills_instructions>", "<collaboration_mode>", "<turn_aborted>", "<user_shell_command>")
TASK_KEYS = ("message", "task", "prompt", "instructions", "input", "items")


def load(path):
    entries = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def text_of(content):
    if isinstance(content, str):
        return content.strip()
    parts = []
    for item in content or []:
        if isinstance(item, dict) and item.get("type") in ("input_text", "text", "output_text"):
            parts.append(item.get("text", ""))
    return "\n".join(parts).strip()


def clock(ts):
    if not ts:
        return "--:--"
    try:
        moment = datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        return moment.astimezone().strftime("%H:%M")
    except ValueError:
        return ts[11:16]


def clip(text, full, width=300):
    text = " ".join(text.split())
    return text if full or len(text) <= width else text[: width - 1] + "…"


def summarize(path, entries, full):
    meta = next((e.get("payload", {}) for e in entries if e.get("type") == "session_meta"), {})
    sub = meta.get("thread_source") == "subagent" or "subagent" in json.dumps(meta.get("source", ""))
    role = meta.get("agent_role") or ("sub-agent" if sub else "main")
    out = {"file": os.path.basename(path), "start": meta.get("timestamp"), "sub": sub, "role": role,
           "nick": meta.get("agent_nickname") or "", "prompts": [], "spawns": [], "tools": 0, "tokens": None}
    for e in entries:
        payload = e.get("payload") or {}
        if e.get("type") == "response_item":
            kind = payload.get("type")
            if kind == "message" and payload.get("role") == "user":
                text = text_of(payload.get("content"))
                if text and not text.startswith(INJECTED):
                    out["prompts"].append((clock(e.get("timestamp")), clip(text, full)))
            elif kind in ("function_call", "custom_tool_call"):
                out["tools"] += 1
                if payload.get("name") == "spawn_agent":
                    try:
                        args = json.loads(payload.get("arguments") or "{}")
                    except ValueError:
                        args = {}
                    detail = {k: args[k] for k in ("agent_type", "task_name", "fork_turns", "model", "reasoning_effort") if k in args}
                    task = next((args[k] for k in TASK_KEYS if isinstance(args.get(k), str)), "")
                    out["spawns"].append((clock(e.get("timestamp")), detail, clip(task, full, 160)))
        elif e.get("type") == "event_msg" and payload.get("type") == "token_count":
            usage = (payload.get("info") or {}).get("total_token_usage")
            if usage:
                out["tokens"] = usage
    return out


def fmt_tokens(t):
    if not t:
        return "tokens: (none recorded)"
    return "tokens: input %s (cached %s), output %s (reasoning %s)" % (
        format(t.get("input_tokens", 0), ","), format(t.get("cached_input_tokens", 0), ","),
        format(t.get("output_tokens", 0), ","), format(t.get("reasoning_output_tokens", 0), ","))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workspace", nargs="?", default=".")
    parser.add_argument("--since-install", action="store_true", help="only sessions started after install")
    parser.add_argument("--full", action="store_true", help="print prompts in full")
    parser.add_argument("--out", help="also write the trace to this file")
    args = parser.parse_args()

    ws = os.path.realpath(args.workspace)
    home = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
    since = 0.0
    marker = os.path.join(ws, ".kit", "runtime", "BASE_HEAD")
    if args.since_install and os.path.exists(marker):
        since = os.path.getmtime(marker)

    sessions = []
    for path in sorted(glob.glob(os.path.join(home, "sessions", "**", "rollout-*.jsonl"), recursive=True)):
        if since and os.path.getmtime(path) < since:
            continue
        entries = load(path)
        meta = next((e.get("payload", {}) for e in entries if e.get("type") == "session_meta"), {})
        cwd = os.path.realpath(meta.get("cwd") or "/nonexistent")
        if cwd == ws or cwd.startswith(ws + os.sep):
            sessions.append(summarize(path, entries, args.full))

    lines = ["# Codex trace — %s" % ws]
    if not sessions:
        lines.append("no Codex sessions found for this workspace under %s/sessions" % home)
    else:
        mains = [s for s in sessions if not s["sub"]]
        totals = {}
        for s in sessions:
            for k, v in (s["tokens"] or {}).items():
                if isinstance(v, int):
                    totals[k] = totals.get(k, 0) + v
        lines.append("sessions: %d (main %d, sub-agents %d) | human prompts: %d | delegations: %d" % (
            len(sessions), len(mains), len(sessions) - len(mains),
            sum(len(s["prompts"]) for s in mains), sum(len(s["spawns"]) for s in sessions)))
        lines.append("all sessions " + fmt_tokens(totals))
        for s in sessions:
            head = "main" if not s["sub"] else "sub-agent %s %s" % (s["role"], s["nick"])
            lines.append("")
            lines.append("## %s · %s · %s" % (head, clock(s["start"]), s["file"]))
            lines.append(fmt_tokens(s["tokens"]) + " | tool calls: %d" % s["tools"])
            label = "task" if s["sub"] else "prompt"
            for i, (when, text) in enumerate(s["prompts"], 1):
                lines.append("%s %d [%s] %s" % (label, i, when, text))
            for when, detail, task in s["spawns"]:
                lines.append("spawn [%s] %s %s" % (when, json.dumps(detail, ensure_ascii=False), task))
    report = "\n".join(lines)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")


if __name__ == "__main__":
    sys.exit(main())
