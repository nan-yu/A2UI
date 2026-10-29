---
name: a2ui-code-review
description: Reviews a GitHub pull request in the A2UI repository with parallel scoped reviewers, requires evidence and a suggested fix for every finding, lets the user triage each finding (post or ignore) in a local dashboard, and posts the approved findings as one inline PR review. Use when asked to review, re-review, or "run a thorough review" on an A2UI PR.
---

# A2UI Code Review

Review an A2UI PR, collect findings that each carry evidence and a suggested
fix, let the user decide in a dashboard which ones to post, then post them as
one GitHub review with inline comments.

> [!IMPORTANT]
> Nothing is posted to GitHub until the user saves decisions in the dashboard
> (or explicitly says to post in the conversation). Drafts shown to the user
> never carry the agent footer; `post_review.py` adds it to posted text only.

Read these first:

- [review_checklist.md](references/review_checklist.md): what to check, severity
  definitions, evidence rules, comment style.
- [reviewer_prompt.md](references/reviewer_prompt.md): briefs for reviewer
  subagents, output contract, re-review brief.
- [findings_schema.md](references/findings_schema.md): the `findings.json` format
  the dashboard and post script use.
- [natural-writing](../natural-writing/SKILL.md): for comment and summary text.

## Modes

- **Review:** first review of a PR.
- **Re-review:** the author pushed fixes. Report the status of each earlier
  finding and look for new bugs in the fix delta.
- **Question about one comment** (for example "what do you think about
  discussion_r123?"): answer in the conversation with evidence; skip the
  dashboard unless the user wants to post a reply.

## Workflow

Keep all scratch files (diffs, repro scripts, `findings.json`, decisions) in
your scratch directory, under `review_<N>/`.

### Step 1: Gather context

1. PR metadata, description and files:
   `gh pr view <N> --repo a2ui-project/a2ui --json title,body,author,baseRefName,headRefName,headRefOid,files,additions,deletions`
2. CI state: `gh pr checks <N>`. For each failing check, read the failed job log
   (`gh run view <run> --job <job> --log-failed`).
3. Existing reviews and inline comments, so you don't repeat them:
   `gh api repos/a2ui-project/a2ui/pulls/<N>/reviews` and
   `gh api --paginate repos/a2ui-project/a2ui/pulls/<N>/comments`. Include bot
   reviewers such as gemini-code-assist.
4. Linked issues and the spec or blueprint sections the PR touches.
5. Check out the head in a detached worktree. Never touch the main checkout
   and never use `git stash`:
   ```bash
   git fetch -q origin pull/<N>/head:refs/remotes/pr/<N>
   git worktree add --detach /tmp/wt/review-<N> pr/<N>
   ```
   Install dependencies there if reviewers need to run code (`uv sync --all-packages`,
   `yarn install --immutable`, `dart pub get`).

### Step 2: Plan scopes and fan out

1. Choose scopes from the files touched (see
   [reviewer_prompt.md](references/reviewer_prompt.md#scopes)). Typical: one per
   SDK, plus cross-SDK parity and conformance; add spec/docs/scope and design
   and risk for large PRs. Review small PRs yourself with the same contract.
2. Launch one reviewer subagent per scope in parallel, each with the shared
   preamble, its scope and the output contract. List the existing comments in
   "already raised" and any decisions the user has accepted.
3. Tell the user which scopes are running, then wait for the results.

### Step 3: Consolidate and verify

1. Merge the reviewers' findings. Deduplicate across scopes: one finding per
   root cause, with every affected SDK in `sdks`.
2. Re-run the repro for each `must` finding yourself. If you can't reproduce
   it, set `verified: false` and recommend `ignore`.
3. Drop or demote findings without evidence or a suggested fix. Don't invent
   evidence; ask the reviewer or check yourself.
4. Mark `pre_existing` and `duplicate_of` (link the existing comment).
5. Set `recommendation` and `recommendation_reason` using the defaults in
   [review_checklist.md](references/review_checklist.md#severity).
6. Pick the line for each inline comment: the exact line the fix touches at the
   head, and it must be an added or context line in the diff. Set `in_diff`;
   findings without a diff line go into the review body.
7. Draft `comment_body` for each finding in the house style: what is wrong, a
   short repro, a suggested fix phrased as a question where natural. No finding
   IDs and no footer.
8. Draft `summary`: thanks and what works, then the items with no diff line
   (conformance gaps, PR description issues), then minor notes.
9. Pick `recommended_event` with a reason. Default to `COMMENT`.
10. Write `findings.json` per [findings_schema.md](references/findings_schema.md).

### Step 4: Triage in the dashboard

1. In the conversation, give a short verdict and a list of the `must` and
   `should` findings (one line each with `file:line`), and say the full detail
   is in the dashboard.
2. Start the dashboard as a background task (`WaitMsBeforeAsync` about 1000):
   ```bash
   python3 .agents/skills/a2ui-code-review/scripts/launch_dashboard.py \
     --data-file "<scratch>/review_<N>/findings.json" \
     --output-file "<scratch>/review_<N>/review_decisions.json"
   ```
   It prints a localhost URL and opens the browser. Share the URL with the user.
3. Stop and wait. The task ends when the user clicks **Save decisions** (exit 0) or **Abort** (exit 1). If aborted, post nothing and ask the user what to
   do next.

In the dashboard the user can filter by severity and decision, read the
details, evidence and suggested fix of each finding, mark it **Post** or
**Ignore** (or accept all recommendations), edit the comment text, choose the
review event (comment, approve, request changes) and edit the summary.

If the user prefers to triage in the conversation (for example "post must and
should only" or "approve with comments for #1 and #2"), apply that to
`findings.json` yourself, write it as the decisions file, and continue.

### Step 5: Post

1. Dry run first. It checks every inline comment against the lines GitHub
   accepts for the current diff and warns if the PR head moved:
   ```bash
   python3 .agents/skills/a2ui-code-review/scripts/post_review.py \
     --decisions-file "<scratch>/review_<N>/review_decisions.json" --dry-run
   ```
2. If the head moved, or comments fell back to the body, tell the user and fix
   the lines (or re-review) before posting. Otherwise post:
   ```bash
   python3 .agents/skills/a2ui-code-review/scripts/post_review.py \
     --decisions-file "<scratch>/review_<N>/review_decisions.json"
   ```
   The script appends the `🤖 Agent-generated` footer to the body and to each
   inline comment, posts one review, and checks that every inline comment
   landed.
3. Share the review URL with the user and report: the event, how many inline
   comments were posted, what went into the body, and what was ignored.
4. Remove the worktree: `git worktree remove --force /tmp/wt/review-<N>`.

## Re-review

1. Load the earlier `findings.json` (or the posted review) and find the
   previously reviewed head.
2. Brief reviewers with the re-review brief in
   [reviewer_prompt.md](references/reviewer_prompt.md#re-review-brief): status
   of each earlier finding with evidence, plus new bugs in
   `git diff <old_sha> <new_sha>`.
3. Fill `prior_findings` with the statuses and put only new or still-open
   problems in `findings`. Then continue from Step 3.

## Bundled resources

- `scripts/launch_dashboard.py`: local server for the triage dashboard; binds to
  127.0.0.1 on a random port and blocks until the user saves or aborts.
- `assets/review_dashboard.html`: the dashboard UI.
- `scripts/post_review.py`: validates lines against the PR diff and posts the
  approved findings as one review.
- `scripts/test_post_review.py`: unit tests for the post script.
