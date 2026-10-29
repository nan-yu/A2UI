# What to check in an A2UI pull request

This list comes from earlier reviews of A2UI PRs, including the things the
maintainers pushed back on and the blind spots they caught after a review. Use
it to plan the reviewer scopes and to brief each reviewer.

## Severity

| Severity   | Meaning                                                                                                                                                                                          | Default recommendation                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| `must`     | Wrong output, crash, data loss, spec or contract violation, cross-SDK divergence in behavior or error codes, a CI failure caused by the PR, or a security issue.                                 | post                                       |
| `should`   | Real but contained: performance regressions, missing tests or conformance cases for risky paths, undocumented breaking changes, API design that will be hard to undo, AGENTS.md rule violations. | post                                       |
| `consider` | Improvements and design questions that are worth raising but not blocking.                                                                                                                       | ignore unless the maintainer asks for them |
| `nit`      | Wording, naming, small style points.                                                                                                                                                             | ignore                                     |

Recommend `ignore` for anything unconfirmed, pre-existing and not made worse,
already raised by another reviewer (including bots such as gemini-code-assist),
already deferred with a reason in an earlier round, or out of the PR's scope.
When the reviewer selected focus areas (see `focus_areas.md`), findings outside
those areas also default to `ignore` unless they are `must`.

## Evidence

Every finding needs evidence that a maintainer can check in a minute:

- **Repro:** the exact input or command and its output. Streaming bugs need
  the chunking that triggers them.
- **Code quote:** `file:line` at the PR head, with the lines that matter.
- **Spec quote:** the path under `specification/<version>/` and the sentence or
  schema property.
- **Comparison:** the same input through Python, TypeScript and Dart (and Swift
  when it is in scope), with each result.
- **CI:** the failing job name and the relevant log lines.

A claim such as "Dart doesn't support v1.0" without a quote or a run is not a
finding. Mark it unconfirmed or drop it.

## Checks

### Spec and versions

- Base protocol behavior on `specification/` (schemas first, catalogs second,
  protocol docs third). Default to v0.9.1 unless the PR targets another version.
- Look for version leaks: hard-coded `"v1.0"` in messages, version-specific
  constants in version-agnostic generators, v1.0 features added under `v0_9`
  directories, and `is_v10`-style names that really mean "at least v1.0"
  (prefer `at_least_v10` / `atLeastV10`).
- When the legacy Python implementation is about to be replaced, judge against
  the blueprint and the spec, not against Python.

### System contracts, top down

Don't stop at "does the code do what it says". Ask what the output must
guarantee when it crosses a boundary:

- Catalogs are negotiated per client. What happens with a pruned catalog, a
  client that lacks a component the agent emits, mixed catalogs on one surface,
  a component-level `catalogId`, or a surface with no default catalog?
- Streaming must match whole-response parsing. Feed the same responses at chunk
  sizes 1, 2, 7 and 1000 and compare with `parse_response`. Check that a
  `feed()` that throws leaves state unchanged, and what `close()` does.
- Failures must be loud. Look for `except` blocks that log and continue, and
  fallbacks that forward invalid UI to the renderer.

### Cross-SDK parity and conformance

- Python, TypeScript, Dart (and Swift for core changes) must give the same
  output and the same error codes and paths for the same input.
- Shared behavior belongs in `conformance/` YAML, not in per-language unit
  tests. Flag new unit tests that could be conformance cases.
- Check that every runner executes every new case: no skips by name, no ignored
  expectation keys, no silent known-failure lists. Check that existing cases
  were not weakened or deleted.
- Check that cases make the difference explicit in the YAML (for example, a
  specific validation config property) instead of hiding it in the runner.

### Repository rules (AGENTS.md)

- Public facades only; no deep imports in code, tests, docs or READMEs.
- Imports grouped (standard, third party, local) and sorted; no wildcards.
- Inference formats stay catalog-agnostic: no catalog-specific names or rules
  in prompts, parsers or compilers.
- Node packages implement the canonical Yarn script targets.
- Agent instructions and skills use vendor-agnostic wording.

### API design

- Keep the public surface small. Question new public setters, constructor
  parameters that expose internals (such as catalog resolvers), and new
  options that duplicate an existing umbrella option.
- Required means required: a model that can't work without a catalog should
  not accept `None`.
- Don't add runtime type checks that repeat the type hints.
- Derive data instead of keeping copies. A catalog's `to_json` should be
  computed from the models (caching the result is fine), not read back from
  the authored document.
- Breaking changes are acceptable in pre-1.0 SDKs when they give a cleaner API,
  but they must be in the CHANGELOG.

### Scope

- Is every change needed for the PR's stated purpose? Unrelated changes belong
  in a separate PR. Size alone is not a problem: PRs are written and reviewed
  with AI help, so don't ask to split a large PR whose changes all serve one
  purpose.
- Keep diffs to specs, proposals, examples and test data minimal: no
  reordering, no renames (such as `Card` to `ComponentA`), no removed sections
  unless the PR needs it.
- CHANGELOG entries are short. Dart packages follow
  `.agents/skills/a2ui-dart-versioning/SKILL.md`.
- Check that the PR description matches the diff and that its links resolve.

### Tests and CI

- Tests actually run (wired into the runner) and assert the error, not just
  that something failed.
- Report each failing check caused by the PR as a `must` finding with the fix.
  Pending checks are not findings.

## Comment style

- Brief and friendly. Open the review body with thanks and what works.
- One problem per inline comment: what is wrong, a short repro, then a
  suggested fix, often as a question ("Could the stream ...?").
- Put the comment on the exact line the fix touches.
- No finding IDs (`M1`, `F3`), no mention of subagents or review rounds.
- Follow `.agents/skills/natural-writing/SKILL.md`.
- Post as `COMMENT` unless the user picks another event.
