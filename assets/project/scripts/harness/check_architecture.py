#!/usr/bin/env python3
"""check_architecture.py - enforce the boundaries in harness/architecture-rules.json.

Scans tracked and untracked (not ignored) files line by line. Every violation prints what broke,
why the rule exists and how to fix it, so an agent can correct itself from the message alone.

Usage: python3 scripts/harness/check_architecture.py [--rules PATH]
Exit codes: 0 no violations, 1 violations found, 2 invalid rules file.
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

MAX_FILE_BYTES = 2 * 1024 * 1024


def repo_root():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def repo_files(root):
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, capture_output=True, check=True,
        ).stdout
        return sorted({f for f in out.decode("utf-8", "replace").split("\0") if f})
    except (OSError, subprocess.CalledProcessError):
        found = []
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".harness")]
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), root))
        return sorted(found)


def matches(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def fail_rules(message):
    print("ERROR: invalid rules file: " + message, file=sys.stderr)
    print("FIX:   see 'Architecture rules' in harness/README.md for the format.", file=sys.stderr)
    sys.exit(2)


def load_rules(path):
    if not os.path.isfile(path):
        fail_rules("not found: " + path)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        fail_rules("%s is not valid JSON (%s)" % (path, exc))
    rules = []
    for index, rule in enumerate(data.get("rules", [])):
        for key in ("id", "paths", "forbid", "why", "fix"):
            if not rule.get(key):
                fail_rules("rule #%d is missing '%s'" % (index + 1, key))
        try:
            rule["_re"] = re.compile(rule["forbid"])
        except re.error as exc:
            fail_rules("rule %s has an invalid regex: %s" % (rule["id"], exc))
        rules.append(rule)
    return data.get("exclude", []), rules


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules")
    args = parser.parse_args()

    root = repo_root()
    rules_path = args.rules or os.path.join(root, "harness", "architecture-rules.json")
    exclude, rules = load_rules(rules_path)
    if not rules:
        print("WARN: no architecture rules configured in %s; boundaries are not enforced."
              % os.path.relpath(rules_path, root))
        return

    violations = 0
    for path in repo_files(root):
        if path.startswith(".harness/") or matches(path, exclude):
            continue
        applicable = [r for r in rules if matches(path, r["paths"]) and not matches(path, r.get("allow", []))]
        if not applicable:
            continue
        full = os.path.join(root, path)
        try:
            if not os.path.isfile(full) or os.path.getsize(full) > MAX_FILE_BYTES:
                continue
            with open(full, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            for rule in applicable:
                if rule["_re"].search(line):
                    violations += 1
                    print("ERROR: [%s] %s:%d" % (rule["id"], path, number))
                    print("       %s" % line.strip()[:200])
                    print("WHY:   %s" % rule["why"])
                    print("FIX:   %s" % rule["fix"])
                    print("")

    if violations:
        print("FAIL: %d architecture violation(s). Fix the code; do not edit the rule to pass."
              % violations)
        sys.exit(1)
    print("PASS: %d architecture rule(s), no violations" % len(rules))


if __name__ == "__main__":
    main()
