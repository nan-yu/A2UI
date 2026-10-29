# Findings file format

The consolidated review is one JSON file, `findings.json`, in your scratch
directory. The dashboard reads it, and the decisions file it writes has the
same shape with `decision`, the edited `comment_body`, `event` and `summary`
filled in. `scripts/post_review.py` reads the decisions file.

## Top level

| Field                      | Type            | Notes                                                                                                                                                           |
| -------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pr`                       | object          | `repo` (`a2ui-project/a2ui`), `number`, `title`, `url`, `author`, `base`, `head_sha` (the commit you reviewed; used as `commit_id` and to detect a moved head). |
| `mode`                     | string          | `review` or `rereview`.                                                                                                                                         |
| `recommended_event`        | string          | `COMMENT`, `APPROVE` or `REQUEST_CHANGES`.                                                                                                                      |
| `recommended_event_reason` | string          | One sentence.                                                                                                                                                   |
| `event`                    | string          | Set by the dashboard. Defaults to `recommended_event`.                                                                                                          |
| `summary`                  | string          | Draft review body. Starts with thanks and what works, then the items that have no diff line. No finding IDs.                                                    |
| `prior_findings`           | list            | Re-review only: `{id, title, status, evidence}`, where `status` is `fixed`, `partially_fixed`, `not_fixed` or `not_applicable`.                                 |
| `verified_checks`          | list of strings | What passed (tests, analyzers, fuzzing, conformance runs).                                                                                                      |
| `not_verified`             | list of strings | What could not be checked, and why.                                                                                                                             |
| `findings`                 | list            | See below.                                                                                                                                                      |

## Finding

Every finding needs `evidence` and `suggested_fix`. The dashboard flags a
finding without them, and it should not be posted.

| Field                   | Type           | Notes                                                                                                                                                        |
| ----------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `id`                    | string         | `F1`, `F2`, ... Internal only; never put it in a comment body.                                                                                               |
| `title`                 | string         | One line, states the defect, not the area.                                                                                                                   |
| `severity`              | string         | `must`, `should`, `consider` or `nit`. See the checklist for definitions.                                                                                    |
| `category`              | string         | `correctness`, `parity`, `conformance`, `spec`, `api`, `performance`, `security`, `tests`, `docs`, `scope`, `ci` or `style`.                                 |
| `sdks`                  | list           | Affected SDKs, e.g. `["python", "typescript"]`.                                                                                                              |
| `path`                  | string or null | Repo-relative path at the PR head. Null for PR-level notes.                                                                                                  |
| `line`                  | int or null    | Line at the PR head (RIGHT side), or the old line with `side: LEFT`.                                                                                         |
| `start_line`            | int or null    | First line of a multi-line range.                                                                                                                            |
| `side`                  | string         | `RIGHT` (default) or `LEFT`.                                                                                                                                 |
| `in_diff`               | bool           | Whether `path:line` is a commentable diff line. False means it goes in the body.                                                                             |
| `details`               | string         | What is wrong and why it matters, in two to five sentences.                                                                                                  |
| `evidence`              | string         | Markdown. A repro with the exact command and output, a code quote with `file:line`, a spec quote with its path, a CI log excerpt, or a cross-SDK comparison. |
| `evidence_type`         | string         | `repro`, `code`, `spec`, `ci` or `comparison`.                                                                                                               |
| `verified`              | bool           | True only if the evidence was produced by running something or by quoting the code at the head.                                                              |
| `suggested_fix`         | string         | Concrete change: where, what, and a test or conformance case that would pin it.                                                                              |
| `pre_existing`          | bool           | True if the base branch already has the issue and the PR does not make it worse.                                                                             |
| `duplicate_of`          | string or null | URL of an existing review comment that already raises it.                                                                                                    |
| `recommendation`        | string         | `post` or `ignore`.                                                                                                                                          |
| `recommendation_reason` | string         | Short reason, e.g. "verified regression in all SDKs" or "nit; style only".                                                                                   |
| `comment_body`          | string         | The draft comment, ready to post. No footer; the post script adds it.                                                                                        |
| `decision`              | string or null | Set by the dashboard: `post` or `ignore`.                                                                                                                    |

## Example

````json
{
  "pr": {
    "repo": "a2ui-project/a2ui",
    "number": 3712,
    "title": "feat(express): stream Express DSL blocks incrementally across SDKs",
    "url": "https://github.com/a2ui-project/a2ui/pull/3712",
    "author": "gspencergoog",
    "base": "main",
    "head_sha": "79d571fc097c14e4cb6ff95d673e69d3b5dd7ff2"
  },
  "mode": "review",
  "recommended_event": "COMMENT",
  "recommended_event_reason": "Several verified streaming bugs; design and tests are otherwise strong.",
  "summary": "Thanks for this. Streaming Express across all three SDKs is a big step...",
  "verified_checks": [
    "Python, TS and Dart agent test suites pass",
    "dart analyze --fatal-infos is clean"
  ],
  "not_verified": ["Swift is out of scope for this PR"],
  "findings": [
    {
      "id": "F1",
      "title": "Healed component followed by id= leaves an orphan",
      "severity": "must",
      "category": "correctness",
      "sdks": ["python", "typescript", "dart"],
      "path": "python/a2ui_agent/src/a2ui/inference_formats/express/response_stream.py",
      "line": 288,
      "start_line": null,
      "side": "RIGHT",
      "in_diff": true,
      "details": "A partly streamed `hdr = Text(\"Head` is emitted under the id `hdr`. When `id=\"custom_hdr\"` arrives, the parent is re-pointed but the provisional `hdr` stays, so the topology check fails at `</a2ui>`.",
      "evidence": "```\nchunks: …root = Card(hdr)\\nhdr = Text(\"Head | er\", id=\"custom_hdr\")\\n</a2ui>\n→ IntegrityError: Component 'hdr' is not reachable from 'root'   (parse_response succeeds)\n```",
      "evidence_type": "repro",
      "verified": true,
      "suggested_fix": "Drop the provisional component from state and topology when a variable's wire id changes. Add a response_streaming.yaml case that splits inside the string.",
      "pre_existing": false,
      "duplicate_of": null,
      "recommendation": "post",
      "recommendation_reason": "Verified in all three SDKs; turns a valid response into fallback text.",
      "comment_body": "**Healed component + later `id=` leaves an orphan (all three SDKs).** ...",
      "decision": null
    }
  ]
}
````
