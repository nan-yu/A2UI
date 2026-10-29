# Reviewer briefs

Each reviewer subagent gets the shared preamble, one scope, and the output
contract. Fill in the `<...>` placeholders. Keep the scope narrow enough that
the reviewer can run things, not just read the diff.

## Shared preamble

```text
You are reviewing GitHub PR #<N> in the A2UI repo (a2ui-project/a2ui):
"<title>" by <author> (+<adds>/-<dels>, <files> files). <One-paragraph summary
of what the PR claims to do.>

A detached worktree of the PR head (<sha>) is at <worktree>. The base is
origin/<base>; see the PR diff with
`git -C <worktree> diff origin/<base>...HEAD -- <paths>`. Read the surrounding
code at the head, not just the diff.

Rules:
- READ-ONLY. Do not modify tracked files, change branches, commit, push, or
  post anything to GitHub. Never touch the main checkout and never use
  `git stash`. Put scratch scripts under <scratch>/<scope>/.
- Read AGENTS.md and the skill for your language first
  (.agents/skills/a2ui-python-development, a2ui-swift-development,
  a2ui-dart-versioning, ...). For SDK behavior, read the relevant blueprint
  under blueprints/modules/.
- Authoritative sources: specification/<version>/json first, then
  specification/<version>/docs, then conformance/**/*.yaml.
- Read .agents/skills/a2ui-code-review/references/review_checklist.md and
  apply the parts that fit your scope.
- Confirm every claimed bug with a small runnable repro or a code/spec quote,
  and report the exact output. Mark anything you could not confirm as
  unconfirmed.
- Separate issues the PR introduces from pre-existing ones
  (pre_existing=true if the base already has it and the PR doesn't make it worse).
- Already raised, don't repeat: <list existing review comments and bot
  findings, with links>.
- Accepted decisions, don't report: <list, or "none">.

Focus areas (in addition to logic and correctness, which you always check):
<for each selected area that applies to this scope: "- <Area>: <checks from
references/focus_areas.md, or the agreed description of a custom area>">
Check every focus area listed, and report for each one what you checked and
what you found, even if nothing. Report serious correctness problems outside
these areas too, but don't spend time hunting for them.
```

## Scopes

Pick scopes from what the PR touches, then layer the selected focus areas on
top (see `focus_areas.md`). An area that needs dedicated runs, such as
performance timings or streaming fuzzing across SDKs, can get its own
reviewer whose scope is that area across all SDKs. Typical scopes:

- **One per SDK** (Python, TypeScript, Dart, Swift): correctness, error
  handling, public exports and facades, tests, CHANGELOG, analyzers
  (`uv run pytest`, `ruff`, `pyink --check`; `yarn build`, `vitest`, `eslint`;
  `dart analyze --fatal-infos`, `dart test`; `swift test`).
- **Cross-SDK parity and conformance:** do all SDKs implement the same rules?
  Run the same adversarial inputs through each and compare. Do all runners run
  every case and check every expectation? Were existing cases weakened?
- **Spec, docs and scope:** spec and blueprint edits, version leaks, README
  commands that actually work, PR description accuracy, unrelated changes.
- **Design and risk** (PRs that change architecture or many SDKs at once): is
  this the right layer, does it hide problems, does it conflict with in-flight
  PRs (`git merge-tree`)? Large PRs are fine; don't ask to split them.
- **Samples:** imports work, every example validates against the right
  version's schema and catalog, capabilities and catalog negotiation per
  version, session state handling.

Small PRs (a few hundred lines in one language) don't need fan-out; review
them directly with the same contract.

## Output contract

```text
Return JSON only:
{
  "scope": "<scope>",
  "findings": [
    {
      "title": "...",
      "severity": "must|should|consider|nit",
      "category": "correctness|parity|conformance|spec|api|performance|security|tests|docs|scope|ci|style",
      "focus_area": "correctness, one of the focus areas above, or other",
      "sdks": ["python"],
      "path": "repo/relative/path at the head, or null",
      "line": 123, "start_line": null, "side": "RIGHT",
      "details": "what is wrong and why it matters",
      "evidence": "exact repro command and output, or file:line quote, or spec quote",
      "evidence_type": "repro|code|spec|ci|comparison",
      "verified": true,
      "suggested_fix": "concrete change plus the test or conformance case that pins it",
      "pre_existing": false
    }
  ],
  "verified_checks": ["commands you ran that passed"],
  "not_verified": ["what you could not check and why"],
  "focus_coverage": [{"area": "<focus area>", "summary": "what you checked and found"}]
}
Return at most ~10 findings, highest severity first. Skip pure style
preferences. An empty findings list is a valid answer.
```

## Re-review brief

Add this to the preamble when the author says earlier findings are fixed:

```text
The previous review was at <old_sha>; its findings are in <path>. See the fix
delta with `git -C <worktree> diff <old_sha> <new_sha> -- <paths>`.
A) For each earlier finding in your scope, report status: fixed /
   partially_fixed / not_fixed / not_applicable, with file:line evidence at the
   new head. Check the code, not the commit messages.
B) Look for NEW bugs introduced by the fix commits, including cross-SDK parity
   of each fix and missing tests for it. Reuse the earlier repro scripts in
   <dirs> where they apply.
Return the same JSON, plus "prior": [{"id", "status", "evidence"}].
```
