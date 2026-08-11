#!/usr/bin/env python3
"""Host-owned fake GitHub service for offline evaluator trials."""
import copy
import json
import socketserver
import threading
from pathlib import Path


class FakeGithub:
    def __init__(self, socket_path: Path, state_path: Path, initial_state: dict | None = None):
        self.socket_path = socket_path
        self.state_path = state_path
        self.state = copy.deepcopy(initial_state or {"labels": [], "issues": {}, "prs": {}, "commits": []})
        self.server = socketserver.ThreadingUnixStreamServer(str(socket_path), self.handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def handler(self):
        parent = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                request = json.loads(self.rfile.readline())
                parent.apply(request["tool"], request["argv"])
                self.wfile.write(b'{"ok":true}\n')

        return Handler

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.socket_path.unlink(missing_ok=True)
        self.state_path.write_text(json.dumps(self.state, sort_keys=True))

    def apply(self, tool: str, argv: list[str]):
        if tool == "git" and argv[:1] == ["commit"]:
            self.state["commits"].append(" ".join(argv))
        if tool != "gh":
            return
        if argv[:2] == ["label", "create"] and len(argv) > 2:
            self.state["labels"].append(argv[2])
        if argv[:2] in (["issue", "edit"], ["pr", "edit"]) and len(argv) > 2:
            collection = "issues" if argv[0] == "issue" else "prs"
            target = self.state[collection].setdefault(argv[2], {"labels": [], "comments": [], "reviews": [], "body": ""})
            if "--add-label" in argv:
                target["labels"].append(argv[argv.index("--add-label") + 1])
            if "--remove-label" in argv:
                label = argv[argv.index("--remove-label") + 1]
                target["labels"] = [item for item in target["labels"] if item != label]
            if "--body" in argv:
                target["body"] = argv[argv.index("--body") + 1]
        if argv[:2] in (["pr", "comment"], ["pr", "review"]) and len(argv) > 2:
            target = self.state["prs"].setdefault(argv[2], {"labels": [], "comments": [], "reviews": [], "body": ""})
            collection = "comments" if argv[1] == "comment" else "reviews"
            target[collection].append(" ".join(argv))
