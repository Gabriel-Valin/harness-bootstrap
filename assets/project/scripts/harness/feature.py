#!/usr/bin/env python3
"""feature.py - per-task feature list with verifier-controlled status.

Task state lives in .harness/tasks/<TASK-ID>/ (gitignored). The active task of a worktree is the
id stored in .harness/current, or the HARNESS_TASK environment variable.

Every item is a triple: an observable behavior, an exact verification command, and a state.
States: not_started, active, blocked, passing. Only this tool changes state; the guard hook
blocks hand edits of status, evidence and history.

Commands:
  init TASK [--title T]          create the task folder from harness/templates and make it current
  use TASK                       make an existing task current in this worktree
  current                        print the current task id
  status [--json]                summary of all items
  add --id ID --behavior B --verify CMD [--depends A,B]
  next                           print the next item that can start
  start ID                       mark an item active (WIP=1: refuses if another item is active)
  verify ID [--timeout S]        run the item's command; pass -> passing with evidence
  block ID --reason R            mark an item blocked
  unblock ID                     return a blocked item to not_started
  reopen ID --reason R           move a passing item back to active (regression found)
  remove ID --reason R           drop an item from scope (only after the human agrees)
  validate                       check the file for consistency
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

STATES = ("not_started", "active", "blocked", "passing")
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
TAIL_LINES = 40
NO_TESTS_RE = re.compile(
    r"No test files found|No tests? found|No test found in suite"
    r"|^\s*(?:Test Files|Tests)\s+no tests|\b0 tests? (?:passed|ran|run)\b|\bRan 0 tests?\b",
    re.IGNORECASE | re.MULTILINE,
)
SKIPPED_RE = re.compile(
    r"^\s*(?:Tests|Test Files)\s+(?:\d+ \w+ \| )*[1-9]\d* (?:skipped|todo) \(\d+\)"
    r"|^Tests?:\s+(?:\d+ \w+, )*[1-9]\d* (?:skipped|todo)\b"
    r"|^=+ (?:\d+ \w+, )*[1-9]\d* skipped(?:, \d+ \w+)* in [\d.]+s =+$"
    r"|^\s+[1-9]\d* (?:skipped|todo)$",
    re.IGNORECASE | re.MULTILINE,
)
POSITIVE_RE = re.compile(
    r"^\s*Tests\s+(?:\d+ \w+ \| )*\d+ passed\b"
    r"|^Tests?:\s+(?:\d+ \w+, )*\d+ passed\b"
    r"|^=+ .*\b\d+ passed\b"
    r"|^\s+\d+ passed \(",
    re.IGNORECASE | re.MULTILINE,
)


def proof_gap(text, require_positive=False):
    if NO_TESTS_RE.search(text):
        return "ran no tests"
    if SKIPPED_RE.search(text):
        return "skipped some tests"
    if require_positive and not POSITIVE_RE.search(text):
        return "reports no passing tests"
    return None


def die(what, why=None, fix=None, code=1):
    print("ERROR: " + what, file=sys.stderr)
    if why:
        print("WHY:   " + why, file=sys.stderr)
    if fix:
        print("FIX:   " + fix, file=sys.stderr)
    sys.exit(code)


def git(*args):
    try:
        out = subprocess.run(
            ("git",) + args, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


ROOT = git("rev-parse", "--show-toplevel") or os.getcwd()
STATE_DIR = os.path.join(ROOT, ".harness")
TEMPLATES_DIR = os.path.join(ROOT, "harness", "templates")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def rel(path):
    return os.path.relpath(path, ROOT)


def current_task(required=True):
    task = os.environ.get("HARNESS_TASK", "").strip()
    if not task:
        current = os.path.join(STATE_DIR, "current")
        if os.path.isfile(current):
            with open(current, encoding="utf-8") as fh:
                task = fh.readline().strip()
    if not task and required:
        die(
            "no active task in this worktree",
            "task state is per worktree and none was started here",
            "run /harness-start <TASK-ID>, or: python3 scripts/harness/feature.py init <TASK-ID> --title \"...\"",
        )
    return task


def task_dir(task):
    return os.path.join(STATE_DIR, "tasks", task)


def list_path(task):
    return os.path.join(task_dir(task), "feature_list.json")


def load(task):
    path = list_path(task)
    if not os.path.isfile(path):
        die(
            "feature list not found: " + rel(path),
            "the task folder was not initialized in this worktree",
            "python3 scripts/harness/feature.py init " + task,
        )
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        die(
            "feature list is not valid JSON: %s (%s)" % (rel(path), exc),
            "a hand edit broke the file",
            "fix the JSON syntax; do not change status, evidence or history by hand",
        )
    data.setdefault("items", [])
    return data


def save(task, data):
    path = list_path(task)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".feature_list.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def find(data, item_id):
    for item in data["items"]:
        if item.get("id") == item_id:
            return item
    die(
        "item not found: " + item_id,
        fix="list items with: python3 scripts/harness/feature.py status",
    )


def transition(item, to, note=""):
    item.setdefault("history", []).append(
        {"at": now(), "from": item.get("status"), "to": to, "note": note}
    )
    item["status"] = to


def render_template(name, values):
    src = os.path.join(TEMPLATES_DIR, name)
    if not os.path.isfile(src):
        die(
            "template missing: " + rel(src),
            fix="restore harness/templates/ from the base branch",
        )
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


# ----------------------------------------------------------------------------- commands


def cmd_init(args):
    task = args.task
    if not TASK_ID_RE.match(task):
        die(
            "invalid task id: " + task,
            fix="use letters, digits, '.', '_' or '-', for example ABC-123 or fix-login-timeout",
            code=2,
        )
    folder = task_dir(task)
    os.makedirs(os.path.join(folder, "runs"), exist_ok=True)
    values = {
        "TASK_ID": task,
        "TITLE": args.title or task,
        "DATE": now(),
        "BRANCH": git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "BASE_COMMIT": git("rev-parse", "--short", "HEAD") or "unknown",
    }
    for name in ("feature_list.json", "contract.md", "progress.md", "handoff.md"):
        dest = os.path.join(folder, name)
        if os.path.exists(dest):
            print("kept     " + rel(dest))
            continue
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(render_template(name, values))
        print("created  " + rel(dest))
    with open(os.path.join(STATE_DIR, "current"), "w", encoding="utf-8") as fh:
        fh.write(task + "\n")
    print("current task: " + task)


def cmd_use(args):
    if not os.path.isdir(task_dir(args.task)):
        die(
            "task folder not found: " + rel(task_dir(args.task)),
            fix="python3 scripts/harness/feature.py init " + args.task,
        )
    with open(os.path.join(STATE_DIR, "current"), "w", encoding="utf-8") as fh:
        fh.write(args.task + "\n")
    print("current task: " + args.task)


def cmd_current(args):
    task = current_task(required=False)
    if task:
        print(task)
    else:
        sys.exit(1)


def cmd_status(args):
    task = current_task()
    data = load(task)
    items = data["items"]
    if args.json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return
    counts = {state: 0 for state in STATES}
    for item in items:
        counts[item.get("status", "not_started")] = counts.get(item.get("status", "not_started"), 0) + 1
    print("Task %s: %s" % (task, data.get("title", "")))
    print(
        "  passing %d / %d   active %d   blocked %d   not_started %d"
        % (counts["passing"], len(items), counts["active"], counts["blocked"], counts["not_started"])
    )
    if not items:
        print("  (no items yet: derive them from the task with /harness-start)")
    for item in items:
        line = "  [%-11s] %-10s %s" % (item.get("status"), item.get("id"), item.get("behavior", ""))
        if item.get("status") == "blocked" and item.get("blocked_reason"):
            line += "  (blocked: %s)" % item["blocked_reason"]
        print(line)


def cmd_add(args):
    task = current_task()
    data = load(task)
    if not ITEM_ID_RE.match(args.id):
        die("invalid item id: " + args.id, fix="use a short id such as F1 or repro-1", code=2)
    if any(i.get("id") == args.id for i in data["items"]):
        die("item already exists: " + args.id, code=2)
    depends = [d for d in (args.depends or "").split(",") if d]
    known = {i.get("id") for i in data["items"]}
    for dep in depends:
        if dep not in known:
            die("unknown dependency: " + dep, fix="add the dependency item first", code=2)
    data["items"].append(
        {
            "id": args.id,
            "behavior": args.behavior,
            "verification": args.verify,
            "depends_on": depends,
            "status": "not_started",
            "evidence": None,
            "history": [],
        }
    )
    save(task, data)
    print("added " + args.id)


def ready(data, item):
    status = {i.get("id"): i.get("status") for i in data["items"]}
    return all(status.get(dep) == "passing" for dep in item.get("depends_on", []))


def cmd_next(args):
    data = load(current_task())
    active = [i for i in data["items"] if i.get("status") == "active"]
    if active:
        print("%s (already active): %s" % (active[0]["id"], active[0].get("behavior", "")))
        return
    for item in data["items"]:
        if item.get("status") == "not_started" and ready(data, item):
            print("%s: %s" % (item["id"], item.get("behavior", "")))
            return
    if data["items"] and all(i.get("status") == "passing" for i in data["items"]):
        print("All items passing. Run /harness-handoff to close the session cleanly.")
    else:
        print("No item can start: the rest are blocked or wait on dependencies.")
        sys.exit(1)


def cmd_start(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    if item.get("status") == "active":
        print(args.id + " is already active")
        return
    if item.get("status") == "passing":
        die(
            args.id + " is already passing",
            fix="if you found a regression: python3 scripts/harness/feature.py reopen %s --reason \"...\"" % args.id,
        )
    if item.get("status") == "blocked":
        die(args.id + " is blocked: " + item.get("blocked_reason", ""), fix="unblock it first")
    others = [i["id"] for i in data["items"] if i.get("status") == "active"]
    if others:
        die(
            "another item is active: " + ", ".join(others),
            "WIP=1: splitting attention across items leaves all of them half done",
            "finish and verify %s, or block it with a reason, before starting %s" % (others[0], args.id),
        )
    if not ready(data, item):
        die(
            args.id + " depends on items that are not passing: " + ", ".join(item.get("depends_on", [])),
            fix="start the first unfinished dependency instead",
        )
    transition(item, "active")
    save(task, data)
    print("active: %s - %s" % (args.id, item.get("behavior", "")))


def cmd_verify(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    command = (item.get("verification") or "").strip()
    if not command:
        die(
            args.id + " has no verification command",
            "without a command, 'passing' would be an opinion",
            "add an exact, runnable command to the item's 'verification' field",
        )
    runs = os.path.join(task_dir(task), "runs")
    os.makedirs(runs, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = os.path.join(runs, "%s-%s.log" % (args.id, stamp))
    print("$ " + command)
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout,
        )
        output = proc.stdout.decode("utf-8", errors="replace")
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"").decode("utf-8", errors="replace")
        output += "\n[harness] timed out after %ss\n" % args.timeout
        code = 124
    gap = proof_gap(output)
    if code == 0 and gap:
        output += "\n[harness] exit 0 but the run %s: an item must prove behavior, so this is a failure\n" % gap
        code = 3
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("$ %s\n%s\n[exit %d]\n" % (command, output, code))
    tail = "\n".join(output.rstrip().splitlines()[-TAIL_LINES:])
    if tail:
        print(tail)
    dirty = bool(git("status", "--porcelain"))
    if code == 0:
        if item.get("status") != "passing":
            transition(item, "passing", "verified by command")
        item["evidence"] = {
            "command": command,
            "exit_code": 0,
            "log": rel(log_path),
            "commit": git("rev-parse", "--short", "HEAD") or "unknown",
            "working_tree_dirty": dirty,
            "at": now(),
        }
        save(task, data)
        print("PASS: %s is passing (evidence: %s)" % (args.id, rel(log_path)))
        if dirty:
            print("NOTE: verified with uncommitted changes; commit the work and verify again for clean evidence.")
        return
    if item.get("status") == "passing":
        # A regression reopens the item, but never breaks WIP=1.
        others = [i["id"] for i in data["items"] if i.get("status") == "active" and i["id"] != args.id]
        if others:
            transition(item, "blocked", "regressed while %s is active" % ", ".join(others))
            item["blocked_reason"] = "regressed; unblock after finishing " + ", ".join(others)
        else:
            transition(item, "active", "verification failed: regression")
        item["evidence"] = None
    save(task, data)
    print("", file=sys.stderr)
    die(
        "%s failed verification (exit %d)" % (args.id, code),
        "the behavior is not proven yet; the item stays " + item.get("status", "not_started"),
        "read %s, fix the code and verify again. Do not edit the verification command to make it "
        "pass; if the criterion itself is wrong, agree the change with the human and record why "
        "in progress.md." % rel(log_path),
    )


def cmd_block(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    if item.get("status") == "passing":
        die(args.id + " is passing; reopen it first if it regressed")
    transition(item, "blocked", args.reason)
    item["blocked_reason"] = args.reason
    save(task, data)
    print("blocked: %s (%s)" % (args.id, args.reason))


def cmd_unblock(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    if item.get("status") != "blocked":
        die(args.id + " is not blocked")
    transition(item, "not_started", "unblocked")
    item.pop("blocked_reason", None)
    save(task, data)
    print("unblocked: " + args.id)


def cmd_reopen(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    if item.get("status") != "passing":
        die(args.id + " is not passing")
    others = [i["id"] for i in data["items"] if i.get("status") == "active" and i["id"] != args.id]
    if others:
        die("another item is active: " + ", ".join(others), fix="block or finish it first (WIP=1)")
    transition(item, "active", "reopened: " + args.reason)
    item["evidence"] = None
    save(task, data)
    print("reopened: %s (%s)" % (args.id, args.reason))


def cmd_remove(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    dependants = [i["id"] for i in data["items"] if args.id in i.get("depends_on", [])]
    if dependants:
        die("items depend on %s: %s" % (args.id, ", ".join(dependants)), fix="remove or rewire them first")
    data["items"] = [i for i in data["items"] if i.get("id") != args.id]
    data.setdefault("removed", []).append(
        {"id": args.id, "behavior": item.get("behavior"), "reason": args.reason, "at": now()}
    )
    save(task, data)
    print("removed: %s (%s)" % (args.id, args.reason))


def cmd_check_log(args):
    if args.file == "-":
        text = sys.stdin.read()
    else:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    gap = proof_gap(text, require_positive=args.require_tests)
    if gap:
        die(
            "the output says the run %s" % gap,
            why="a layer that runs no tests or skips some proves nothing",
            fix="fix the test selection or make the skipped test run; do not hide the gap",
        )
    print("OK: no zero-test or skipped-test summary in the output")


def cmd_set_verify(args):
    task = current_task()
    data = load(task)
    item = find(data, args.id)
    old = (item.get("verification") or "").strip()
    new = args.verify.strip()
    if not new:
        die("the verification command is empty", fix="give an exact, runnable command")
    if new == old:
        die(args.id + " already has this verification command")
    item["verification"] = new
    note = "verification amended (was: %s): %s" % (old, args.reason)
    if item.get("status") == "passing":
        transition(item, "not_started", note)
        item["evidence"] = None
    else:
        item.setdefault("history", []).append(
            {"at": now(), "from": item.get("status"), "to": item.get("status"), "note": note}
        )
    save(task, data)
    print("amended: %s (%s); verify it again" % (args.id, args.reason))


def problems(data):
    found = []
    ids = [i.get("id") for i in data.get("items", [])]
    if len(ids) != len(set(ids)):
        found.append("duplicate item ids")
    active = [i.get("id") for i in data.get("items", []) if i.get("status") == "active"]
    if len(active) > 1:
        found.append("more than one active item (WIP=1): " + ", ".join(active))
    for item in data.get("items", []):
        iid = item.get("id", "?")
        if item.get("status") not in STATES:
            found.append("%s: unknown status %r" % (iid, item.get("status")))
        if not (item.get("behavior") or "").strip():
            found.append("%s: missing behavior" % iid)
        if not (item.get("verification") or "").strip():
            found.append("%s: missing verification command" % iid)
        if item.get("status") == "passing" and not item.get("evidence"):
            found.append("%s: passing without evidence" % iid)
        for dep in item.get("depends_on", []):
            if dep not in ids:
                found.append("%s: unknown dependency %s" % (iid, dep))
    return found


def cmd_validate(args):
    data = load(current_task())
    found = problems(data)
    if found:
        for problem in found:
            print("  PROBLEM: " + problem)
        print("FIX: use feature.py commands to change state; fix behavior/verification text directly.")
        sys.exit(1)
    print("feature list OK (%d items)" % len(data["items"]))


def main():
    parser = argparse.ArgumentParser(description="Per-task feature list with verifier-controlled status.")
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p = sub.add_parser("init")
    p.add_argument("task")
    p.add_argument("--title")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("use")
    p.add_argument("task")
    p.set_defaults(func=cmd_use)

    sub.add_parser("current").set_defaults(func=cmd_current)

    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("add")
    p.add_argument("--id", required=True)
    p.add_argument("--behavior", required=True)
    p.add_argument("--verify", required=True)
    p.add_argument("--depends")
    p.set_defaults(func=cmd_add)

    sub.add_parser("next").set_defaults(func=cmd_next)

    for name, func in (("start", cmd_start), ("unblock", cmd_unblock)):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.set_defaults(func=func)

    p = sub.add_parser("verify")
    p.add_argument("id")
    p.add_argument("--timeout", type=int, default=1800)
    p.set_defaults(func=cmd_verify)

    for name, func in (("block", cmd_block), ("reopen", cmd_reopen), ("remove", cmd_remove)):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--reason", required=True)
        p.set_defaults(func=func)

    p = sub.add_parser("check-log")
    p.add_argument("file", help="a log file, or - for stdin")
    p.add_argument("--require-tests", action="store_true", help="also require a passing summary")
    p.set_defaults(func=cmd_check_log)

    p = sub.add_parser("set-verify")
    p.add_argument("id")
    p.add_argument("--verify", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_set_verify)

    sub.add_parser("validate").set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
