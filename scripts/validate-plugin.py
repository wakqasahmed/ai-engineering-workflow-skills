#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
manifest_skills = set(plugin.get("skills", []))

# 1. Check manifest -> disk
missing_on_disk = []
for skill in manifest_skills:
    normalized = skill.lstrip("./")
    if not (root / normalized / "SKILL.md").is_file():
        missing_on_disk.append(skill)
if missing_on_disk:
    raise SystemExit("Plugin manifest references nonexistent skills: " + ", ".join(sorted(missing_on_disk)))

# 2. Check disk -> manifest
disk_skills = []
for skill_file in sorted((root / "skills").glob("*/*/SKILL.md")):
    rel_dir = skill_file.parent.relative_to(root)
    candidate_dot = f"./{rel_dir}"
    candidate_bare = str(rel_dir)
    if candidate_dot not in manifest_skills and candidate_bare not in manifest_skills:
        disk_skills.append(candidate_dot)

if disk_skills:
    raise SystemExit("Skills on disk omitted from plugin manifest: " + ", ".join(sorted(disk_skills)))

print(f"validated {len(manifest_skills)} plugin skills (bidirectional)")
