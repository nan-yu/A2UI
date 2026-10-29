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

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import post_review  # noqa: E402

PATCH = """@@ -10,4 +10,5 @@ def f():
 context_a
-removed
+added_1
+added_2
 context_b
\\ No newline at end of file
@@ -40,2 +41,2 @@
 tail
+new_tail
"""


def _decisions(**overrides):
    data = {
        "pr": {"repo": "a2ui-project/a2ui", "number": 1, "head_sha": "abc1234"},
        "event": "COMMENT",
        "summary": "Thanks!",
        "findings": [],
    }
    data.update(overrides)
    return data


def _finding(**overrides):
    data = {
        "id": "F1",
        "decision": "post",
        "path": "a.py",
        "line": 11,
        "side": "RIGHT",
        "comment_body": "Problem.",
    }
    data.update(overrides)
    return data


class ParsePatchLinesTest(unittest.TestCase):

    def test_right_and_left_lines(self):
        lines = post_review.parse_patch_lines(PATCH)
        self.assertEqual(lines["RIGHT"], {10, 11, 12, 13, 41, 42})
        self.assertEqual(lines["LEFT"], {10, 11, 12, 40})

    def test_empty_patch(self):
        self.assertEqual(
            post_review.parse_patch_lines(""), {"RIGHT": set(), "LEFT": set()}
        )


class AddFooterTest(unittest.TestCase):

    def test_adds_once(self):
        once = post_review.add_footer("Body")
        self.assertTrue(once.endswith(post_review.FOOTER))
        self.assertIn("Body\n\n", once)
        self.assertEqual(post_review.add_footer(once), once)


class BuildPayloadTest(unittest.TestCase):

    def setUp(self):
        self.lines = {"a.py": post_review.parse_patch_lines(PATCH)}

    def test_inline_comment_and_footer(self):
        payload, moved = post_review.build_payload(
            _decisions(findings=[_finding()]), self.lines
        )
        self.assertEqual(moved, [])
        self.assertEqual(payload["commit_id"], "abc1234")
        self.assertEqual(len(payload["comments"]), 1)
        comment = payload["comments"][0]
        self.assertEqual(
            (comment["path"], comment["line"], comment["side"]), ("a.py", 11, "RIGHT")
        )
        self.assertTrue(comment["body"].endswith(post_review.FOOTER))
        self.assertTrue(payload["body"].endswith(post_review.FOOTER))

    def test_ignored_findings_are_skipped(self):
        payload, _ = post_review.build_payload(
            _decisions(findings=[_finding(decision="ignore")]), self.lines
        )
        self.assertEqual(payload["comments"], [])

    def test_line_outside_diff_moves_to_body(self):
        payload, moved = post_review.build_payload(
            _decisions(findings=[_finding(line=30, comment_body="Out of diff.")]),
            self.lines,
        )
        self.assertEqual(payload["comments"], [])
        self.assertEqual([f["id"] for f in moved], ["F1"])
        self.assertIn("`a.py:30`", payload["body"])
        self.assertIn("Out of diff.", payload["body"])

    def test_finding_without_path_moves_to_body(self):
        payload, moved = post_review.build_payload(
            _decisions(
                findings=[
                    _finding(path=None, line=None, comment_body="Conformance gap.")
                ]
            ),
            self.lines,
        )
        self.assertEqual(len(moved), 1)
        self.assertIn("Conformance gap.", payload["body"])

    def test_multi_line_range(self):
        payload, _ = post_review.build_payload(
            _decisions(findings=[_finding(start_line=10, line=12)]), self.lines
        )
        comment = payload["comments"][0]
        self.assertEqual((comment["start_line"], comment["line"]), (10, 12))
        self.assertEqual(comment["start_side"], "RIGHT")

    def test_range_start_outside_diff_moves_to_body(self):
        _, moved = post_review.build_payload(
            _decisions(findings=[_finding(start_line=5, line=12)]), self.lines
        )
        self.assertEqual(len(moved), 1)

    def test_left_side_comment(self):
        payload, moved = post_review.build_payload(
            _decisions(findings=[_finding(side="LEFT", line=11)]), self.lines
        )
        self.assertEqual(moved, [])
        self.assertEqual(payload["comments"][0]["side"], "LEFT")

    def test_post_without_body_is_an_error(self):
        with self.assertRaises(ValueError):
            post_review.build_payload(
                _decisions(findings=[_finding(comment_body=" ")]), self.lines
            )

    def test_unknown_event_is_an_error(self):
        with self.assertRaises(ValueError):
            post_review.build_payload(_decisions(event="MERGE"), self.lines)

    def test_request_changes_needs_body(self):
        with self.assertRaises(ValueError):
            post_review.build_payload(
                _decisions(event="REQUEST_CHANGES", summary=""), self.lines
            )

    def test_approve_without_summary_has_no_body(self):
        payload, _ = post_review.build_payload(
            _decisions(event="APPROVE", summary=""), self.lines
        )
        self.assertEqual(payload["event"], "APPROVE")
        self.assertNotIn("body", payload)


class CommentableLinesTest(unittest.TestCase):

    def test_skips_files_without_patch(self):
        files = [
            {"filename": "a.py", "patch": PATCH},
            {"filename": "image.png"},
        ]
        lines = post_review.commentable_lines(files)
        self.assertEqual(set(lines), {"a.py"})


if __name__ == "__main__":
    unittest.main()
