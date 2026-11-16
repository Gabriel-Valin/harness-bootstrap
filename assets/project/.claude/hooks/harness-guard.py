#!/usr/bin/env python3
"""harness-guard.py - PreToolUse hook that keeps feature-list state in the verifier's hands.

Blocks, for .harness/**/feature_list.json:
  - Edit / Write / MultiEdit that change status, evidence or history of any item
  - any change to an item that is already passing
  - removing items (use: feature.py remove ID --reason ...)
  - new items that do not start as not_started without evidence
  - Bash commands that write to the file directly (sed -i, redirection, tee, mv, cp)

Adding items and editing behavior / verification of non-passing items stays allowed.
Exit code 2 blocks the tool call and shows stderr to the agent.
"""

import json
import os
import re
import sys

GUARDED = ("status", "evidence", "history", "blocked_reason")
FIX = "use python3 scripts/harness/feature.py (start, verify, block, unblock, reopen, remove)."


def deny(reason):
    print("BLOCKED by harness guard: " + reason, file=sys.stderr)
    print("WHY:   item state must come from running its verification, not from an edit.", file=sys.stderr)
    print("FIX:   " + FIX, file=sys.stderr)
    sys.exit(2)


def is_feature_list(path):
    norm = path.replace("\\", "/")
    return norm.endswith("/feature_list.json") and "/.harness/" in "/" + norm.lstrip("/")


def check_bash(command):
    if "feature_list.json" not in command or "scripts/harness/feature.py" in command:
        return
    writes = (
        r"sed\s+(-[a-zA-Z]*\s+)*-i",
        r"perl\s+(-[a-zA-Z]*\s+)*-[a-zA-Z]*i",
        r">>?\s*['\"]?[^\s'\"]*feature_list\.json",
        r"\btee\b[^|;&]*feature_list\.json",
        r"\b(mv|cp)\b[^|;&]*feature_list\.json\s*($|[|;&])",
    )
    for pattern in writes:
        if re.search(pattern, command):
            deny("shell command writes to a feature_list.json")


def proposed_content(tool, tool_input, current):
    if tool == "Write":
        return tool_input.get("content", "")
    edits = []
    if tool == "Edit":
        edits = [tool_input]
    elif tool == "MultiEdit":
        edits = tool_input.get("edits", [])
    text = current
    for edit in edits:
        old, new = edit.get("old_string", ""), edit.get("new_string", "")
        if not old or old not in text:
            return None  # the tool itself will reject a non-matching edit
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text


def items_by_id(data):
    return {i.get("id"): i for i in data.get("items", []) if isinstance(i, dict)}


def compare(before, after):
    old_items, new_items = items_by_id(before), items_by_id(after)
    for item_id, old in old_items.items():
        new = new_items.get(item_id)
        if new is None:
            deny("item %s would be removed" % item_id)
        if old.get("status") == "passing" and new != old:
            deny("item %s is passing and cannot be edited" % item_id)
        for key in GUARDED:
            if old.get(key) != new.get(key):
                deny("item %s: '%s' would change by hand" % (item_id, key))
    for item_id, new in new_items.items():
        if item_id not in old_items:
            check_new_item(item_id, new)


def check_new_item(item_id, item):
    if item.get("status", "not_started") != "not_started":
        deny("new item %s must start as not_started" % item_id)
    if item.get("evidence") or item.get("history"):
        deny("new item %s cannot carry evidence or history" % item_id)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool == "Bash":
        check_bash(tool_input.get("command", ""))
        return
    if tool not in ("Edit", "Write", "MultiEdit"):
        return
    path = tool_input.get("file_path", "")
    if not path or not is_feature_list(path):
        return

    current = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            current = fh.read()
    proposed = proposed_content(tool, tool_input, current)
    if proposed is None:
        return
    try:
        after = json.loads(proposed)
    except json.JSONDecodeError as exc:
        deny("the result would not be valid JSON (%s)" % exc)

    if not current.strip():
        for item_id, item in items_by_id(after).items():
            check_new_item(item_id, item)
        return
    try:
        before = json.loads(current)
    except json.JSONDecodeError:
        return  # already broken; let the agent repair the syntax
    compare(before, after)


if __name__ == "__main__":
    main()
