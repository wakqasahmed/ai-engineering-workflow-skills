#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
missing = []
for skill in plugin.get("skills", []):
    if not (root / skill / "SKILL.md").is_file():
        missing.append(skill)
if missing:
    raise SystemExit("Missing plugin skill paths: " + ", ".join(missing))
print(f"validated {len(plugin.get('skills', []))} plugin skills")
