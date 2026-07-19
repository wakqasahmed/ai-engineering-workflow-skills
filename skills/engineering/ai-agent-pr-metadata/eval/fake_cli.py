#!/usr/bin/env python3
"""Record GitHub and git commands without giving the evaluator real access."""
import json
import os
import sys
from pathlib import Path


artifact = Path(os.environ["HARNESS_ARTIFACT"])
with artifact.open("a") as stream:
    stream.write(json.dumps({"tool": Path(sys.argv[0]).name, "argv": sys.argv[1:]}) + "\n")
