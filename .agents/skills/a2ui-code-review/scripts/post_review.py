#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Posts the findings approved in the review dashboard as one GitHub PR review.

Reads the decisions file written by `launch_dashboard.py`, keeps the findings
marked `post`, checks every inline comment against the lines GitHub accepts
for the PR diff, and submits a single review with `gh api`.

Findings whose line is not part of the diff are moved into the review body
instead of being dropped. Use `--dry-run` to see the plan without posting.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any

FOOTER = "<sub><!-- agent-generated --><kbd>🤖 Agent-generated</kbd></sub>"
VALID_EVENTS = ("COMMENT", "APPROVE", "REQUEST_CHANGES")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def add_footer(body: str) -> str:
    """Appends the agent footer once, separated by a blank line."""
    text = body.rstrip()
    if text.endswith(FOOTER):
        return text
    return f"{text}\n\n{FOOTER}" if text else FOOTER


def parse_patch_lines(patch: str) -> dict[str, set[int]]:
    """Returns the commentable line numbers of a unified diff patch per side.

    RIGHT holds added and context lines in the new file; LEFT holds removed and
    context lines in the old file. GitHub only accepts review comments on these.
    """
    right: set[int] = set()
    left: set[int] = set()
    old_line = new_line = 0
    in_hunk = False
    for raw in patch.splitlines():
        match = _HUNK_RE.match(raw)
        if match:
            old_line, new_line = int(match.group(1)), int(match.group(2))
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        if raw.startswith("+"):
            right.add(new_line)
            new_line += 1
        elif raw.startswith("-"):
            left.add(old_line)
            old_line += 1
        else:
            right.add(new_line)
            left.add(old_line)
            old_line += 1
            new_line += 1
    return {"RIGHT": right, "LEFT": left}


def commentable_lines(files: list[dict[str, Any]]) -> dict[str, dict[str, set[int]]]:
    """Maps each changed file path to its commentable lines per side."""
    result: dict[str, dict[str, set[int]]] = {}
    for entry in files:
        patch = entry.get("patch")
        if patch:
            result[entry["filename"]] = parse_patch_lines(patch)
    return result


def _location(finding: dict[str, Any]) -> str:
    path = finding.get("path") or ""
    line = finding.get("line")
    return f"{path}:{line}" if path and line else path


def is_inline(finding: dict[str, Any], lines: dict[str, dict[str, set[int]]]) -> bool:
    """Whether a finding can be posted as an inline comment on the diff."""
    path, line = finding.get("path"), finding.get("line")
    if not path or not isinstance(line, int):
        return False
    side = finding.get("side") or "RIGHT"
    allowed = lines.get(path, {}).get(side, set())
    start = finding.get("start_line")
    if isinstance(start, int) and start != line and start not in allowed:
        return False
    return line in allowed


def build_payload(
    decisions: dict[str, Any], lines: dict[str, dict[str, set[int]]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Builds the review payload and returns it with the findings moved to the body."""
    event = decisions.get("event") or "COMMENT"
    if event not in VALID_EVENTS:
        raise ValueError(f"Unknown review event {event!r}; use one of {VALID_EVENTS}.")

    comments: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    for finding in decisions.get("findings", []):
        if finding.get("decision") != "post":
            continue
        body = (finding.get("comment_body") or "").strip()
        if not body:
            raise ValueError(
                f"Finding {finding.get('id')} is marked post but has no comment body."
            )
        if is_inline(finding, lines):
            comment: dict[str, Any] = {
                "path": finding["path"],
                "line": finding["line"],
                "side": finding.get("side") or "RIGHT",
                "body": add_footer(body),
            }
            start = finding.get("start_line")
            if isinstance(start, int) and start < finding["line"]:
                comment["start_line"] = start
                comment["start_side"] = comment["side"]
            comments.append(comment)
        else:
            moved.append(finding)

    summary = (decisions.get("summary") or "").strip()
    if moved:
        notes = "\n\n".join(
            f"**`{_location(f)}`**\n\n{f['comment_body'].strip()}"
            if _location(f)
            else f["comment_body"].strip()
            for f in moved
        )
        summary = f"{summary}\n\n{notes}" if summary else notes
    if event == "REQUEST_CHANGES" and not summary:
        raise ValueError("A REQUEST_CHANGES review needs a summary body.")

    payload: dict[str, Any] = {"event": event, "comments": comments}
    head_sha = decisions.get("pr", {}).get("head_sha")
    if head_sha:
        payload["commit_id"] = head_sha
    if summary:
        payload["body"] = add_footer(summary)
    return payload, moved


def gh(args: list[str], stdin: str | None = None) -> str:
    """Runs a `gh` command and returns its standard output."""
    proc = subprocess.run(
        ["gh", *args], input=stdin, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def gh_json(args: list[str], stdin: str | None = None) -> Any:
    """Runs a `gh` command and parses its JSON output."""
    out = gh(args, stdin)
    return json.loads(out) if out.strip() else None


def fetch_files(repo: str, number: int) -> list[dict[str, Any]]:
    """Returns every changed file of the PR, following pagination."""
    # `--jq '.[]'` prints one compact JSON object per line across all pages,
    # which also works with gh versions that lack `--slurp`.
    out = gh([
        "api",
        "--paginate",
        "--jq",
        ".[] | {filename, patch}",
        f"repos/{repo}/pulls/{number}/files?per_page=100",
    ])
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--decisions-file", required=True, help="Path to review_decisions.json."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the plan; do not post."
    )
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help=(
            "Post even if the PR head moved since the review (line numbers may be off)."
        ),
    )
    args = parser.parse_args()

    with open(args.decisions_file, encoding="utf-8") as f:
        decisions = json.load(f)
    pr = decisions.get("pr", {})
    repo, number = pr.get("repo"), pr.get("number")
    if not repo or not isinstance(number, int):
        print("Error: decisions file needs pr.repo and pr.number.", file=sys.stderr)
        return 1

    current_head = gh_json(["api", f"repos/{repo}/pulls/{number}"])["head"]["sha"]
    reviewed_head = pr.get("head_sha")
    if reviewed_head and current_head != reviewed_head:
        print(
            f"Warning: PR head moved from {reviewed_head[:9]} to {current_head[:9]}"
            " since the review.",
            file=sys.stderr,
        )
        if not args.allow_stale and not args.dry_run:
            print("Re-check the findings or pass --allow-stale.", file=sys.stderr)
            return 2

    lines = commentable_lines(fetch_files(repo, number))
    try:
        payload, moved = build_payload(decisions, lines)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Event: {payload['event']}")
    print(f"Inline comments: {len(payload['comments'])}")
    for c in payload["comments"]:
        print(f"  - {c['path']}:{c['line']}")
    if moved:
        print(f"Moved to the review body (line not in the diff): {len(moved)}")
        for f in moved:
            print(f"  - {f.get('id')}: {_location(f) or '(no location)'}")
    ignored = sum(
        1 for f in decisions.get("findings", []) if f.get("decision") != "post"
    )
    print(f"Not posted: {ignored}")

    payload_path = args.decisions_file.replace(".json", "") + "_payload.json"
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Payload: {payload_path}")

    if args.dry_run:
        return 0

    review = gh_json(
        ["api", "-X", "POST", f"repos/{repo}/pulls/{number}/reviews", "--input", "-"],
        stdin=json.dumps(payload),
    )
    posted = gh_json([
        "api",
        f"repos/{repo}/pulls/{number}/reviews/{review['id']}/comments?per_page=100",
    ])
    print(f"Posted: {review.get('html_url')} ({review.get('state')})")
    print(f"Inline comments on GitHub: {len(posted)} of {len(payload['comments'])}")
    return 0 if len(posted) == len(payload["comments"]) else 3


if __name__ == "__main__":
    sys.exit(main())
