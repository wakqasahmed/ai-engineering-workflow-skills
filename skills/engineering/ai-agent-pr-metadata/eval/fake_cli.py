#!/usr/bin/env python3
"""Send fake GitHub commands to the host-owned offline service."""
import json
import os
import sys
import socket


with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.connect(os.environ["HARNESS_GITHUB_SOCKET"])
    client.sendall(json.dumps({"tool": os.path.basename(sys.argv[0]), "argv": sys.argv[1:]}).encode() + b"\n")
    client.recv(1024)
