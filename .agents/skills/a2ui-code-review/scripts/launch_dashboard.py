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
"""Serves the local code review dashboard and blocks until the user decides.

The dashboard loads the consolidated findings file, lets the user mark each
finding as post or ignore, edit the comment text, pick the review event, and
edit the summary. "Save decisions" writes the decisions file and exits 0;
"Abort" exits 1 without writing anything.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import sys
import threading
import urllib.parse
import webbrowser

_ASSET = os.path.join(
    os.path.dirname(__file__), "..", "assets", "review_dashboard.html"
)
_MAX_BODY_BYTES = 5 * 1024 * 1024

shutdown_event = threading.Event()
exit_status = 1


class ReviewDashboardHandler(http.server.BaseHTTPRequestHandler):
    data_file = ""
    output_file = ""

    def log_message(self, format, *args):  # noqa: A002 - signature from base class
        pass

    def _send_json(self, status: int, payload: object) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(_ASSET, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; style-src"
                " 'unsafe-inline'; connect-src 'self'",
            )
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/findings":
            try:
                with open(self.data_file, encoding="utf-8") as f:
                    self._send_json(200, json.load(f))
            except (OSError, json.JSONDecodeError) as e:
                self._send_json(500, {"error": f"Could not read findings: {e}"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        global exit_status
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/save":
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > _MAX_BODY_BYTES:
                self._send_json(413, {"error": "Request body is empty or too large."})
                return
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(data, dict) or not isinstance(
                    data.get("findings"), list
                ):
                    raise ValueError("Expected an object with a findings list.")
                with open(self.output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except (ValueError, OSError) as e:
                self._send_json(400, {"error": f"Could not save decisions: {e}"})
                return
            self._send_json(200, {"status": "saved"})
            exit_status = 0
            shutdown_event.set()
        elif path == "/api/abort":
            self._send_json(200, {"status": "aborted"})
            exit_status = 1
            shutdown_event.set()
        else:
            self._send_json(404, {"error": "Not found"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the code review dashboard.")
    parser.add_argument("--data-file", required=True, help="Path to findings.json.")
    parser.add_argument(
        "--output-file", required=True, help="Path to write review_decisions.json."
    )
    parser.add_argument("--no-browser", action="store_true", help="Print the URL only.")
    args = parser.parse_args()

    data_file = os.path.abspath(os.path.expanduser(args.data_file))
    output_file = os.path.abspath(os.path.expanduser(args.output_file))
    if not os.path.exists(data_file):
        print(f"Error: findings file '{data_file}' does not exist.", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    ReviewDashboardHandler.data_file = data_file
    ReviewDashboardHandler.output_file = output_file

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), ReviewDashboardHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://localhost:{httpd.server_port}/"
    print(f"Code review dashboard: {url}", flush=True)
    print("Waiting for decisions in the browser...", flush=True)
    if not args.no_browser:
        webbrowser.open(url)

    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        print("\nAborted (Ctrl+C).", flush=True)
    httpd.shutdown()

    if exit_status == 0:
        print(f"Decisions saved to {output_file}", flush=True)
    else:
        print("Review aborted; nothing saved.", flush=True)
    return exit_status


if __name__ == "__main__":
    sys.exit(main())
