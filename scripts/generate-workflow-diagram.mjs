#!/usr/bin/env node
// Regenerates the README workflow diagram from the skills actually on disk.
// Run with --check in CI to fail on drift instead of rewriting the file.

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const skillsRoot = join(repoRoot, "skills");
const readmePath = join(repoRoot, "README.md");
const START = "<!-- WORKFLOW_DIAGRAM:START -->";
const END = "<!-- WORKFLOW_DIAGRAM:END -->";

// Stage assignment is the one thing the directory tree cannot tell us: it comes
// from the delivery loop in AI_ENGINEERING_WORKFLOW.md and the AGENTS.md trigger
// map. Skill existence, naming, and category still come from disk, so a skill
// added, renamed, or removed changes the diagram without touching this table.
const STAGES = [
  {
    id: "S0",
    label: "0 - Pressure-test the idea",
    skills: ["roast"],
  },
  {
    id: "S1",
    label: "1 - Clarify",
    skills: ["clarify-work", "to-prd"],
  },
  {
    id: "S2",
    label: "2 - Decompose",
    skills: ["decompose-to-issues", "define-done"],
  },
  {
    id: "S3",
    label: "3 - Execute",
    skills: ["subagent-pipeline", "diagnose", "resolving-merge-conflicts", "wizard"],
  },
  {
    id: "S4",
    label: "4 - Verify & Review",
    skills: ["review-gate", "ai-agent-pr-metadata", "open-code-review-setup"],
  },
  {
    id: "S5",
    label: "5 - Release",
    skills: ["release-gate", "changesets-release"],
  },
];

// Stages that are not a step in the linear loop: they attach to the stage where
// they are actually reached from.
const SIDE_STAGES = [
  {
    id: "CTXOUT",
    label: "Any stage - context runs out",
    attach: "S3",
    edge: "session or agent boundary",
    skills: ["handover", "caveman"],
  },
];

const TRACKS = [
  {
    id: "EXT",
    label: "External-repo contribution track",
    from: "ROUTER",
    skills: ["external-pr-viability", "external-pr-style", "external-campaign-triage"],
    sequential: true,
  },
  {
    id: "GUARD",
    label: "Always-on guardrails & repo setup",
    skills: [
      "git-guardrails-claude-code",
      "docker-volume-guardrails",
      "writing-for-agents",
      "write-prompt-guide",
      "tmux-orphaned-socket",
    ],
  },
  {
    id: "BLOCK",
    label: "Blocked on a human",
    attach: "S3",
    edge: "human-only blocker",
    skills: ["hitl-blocker"],
  },
];

const ENTRY_SKILL = "workflow-router";

function readFrontmatterName(skillFile) {
  const text = readFileSync(skillFile, "utf8");
  if (!text.startsWith("---")) return null;
  const end = text.indexOf("\n---", 3);
  if (end === -1) return null;
  const match = text.slice(3, end).match(/^name:\s*["']?([^"'\n]+?)["']?\s*$/m);
  return match ? match[1] : null;
}

function discoverSkills() {
  const found = new Map();
  for (const category of readdirSync(skillsRoot, { withFileTypes: true })) {
    if (!category.isDirectory()) continue;
    for (const dir of readdirSync(join(skillsRoot, category.name), { withFileTypes: true })) {
      if (!dir.isDirectory()) continue;
      const skillFile = join(skillsRoot, category.name, dir.name, "SKILL.md");
      let name;
      try {
        name = readFrontmatterName(skillFile);
      } catch {
        continue; // a directory without a SKILL.md is not an installable skill
      }
      found.set(name ?? dir.name, { category: category.name, dir: dir.name });
    }
  }
  return found;
}

const nodeId = (name) => "s_" + name.replace(/[^a-zA-Z0-9]/g, "_");

function buildDiagram(skills) {
  const assigned = new Set([ENTRY_SKILL]);
  const groups = [];

  for (const group of [...STAGES, ...SIDE_STAGES, ...TRACKS]) {
    const present = group.skills.filter((name) => skills.has(name));
    present.forEach((name) => assigned.add(name));
    if (present.length > 0) groups.push({ ...group, skills: present });
  }

  // Anything on disk this script has no stage for still has to show up, grouped
  // by its category, so the diagram can never quietly under-report the pack.
  const unassigned = [...skills.keys()].filter((name) => !assigned.has(name)).sort();
  const byCategory = new Map();
  for (const name of unassigned) {
    const category = skills.get(name).category;
    if (!byCategory.has(category)) byCategory.set(category, []);
    byCategory.get(category).push(name);
  }
  for (const [category, names] of [...byCategory].sort()) {
    groups.push({
      id: "X_" + category.replace(/[^a-zA-Z0-9]/g, "_"),
      label: `Unrouted ${category} skills`,
      skills: names,
    });
  }

  const lines = ["```mermaid", "flowchart TD"];
  lines.push('    REQ([" Work request "]) --> ROUTER');
  lines.push(`    ROUTER["${ENTRY_SKILL}<br/>route to the smallest applicable workflow"]`);
  lines.push("");
  lines.push('    subgraph CTX["Loaded before any skill runs"]');
  lines.push("        direction LR");
  lines.push('        CORE["system-level/core.md<br/>invariant operating rules"]');
  lines.push('        MAP["AGENTS.md / CLAUDE.md<br/>trigger map"]');
  lines.push('        FLOW["AI_ENGINEERING_WORKFLOW.md<br/>stages, risk levels, gates"]');
  lines.push("    end");
  lines.push("    CTX -.- ROUTER");
  lines.push("");

  const stageIds = [];
  for (const group of groups) {
    const isStage = STAGES.some((stage) => stage.id === group.id);
    if (isStage) stageIds.push(group.id);
    lines.push(`    subgraph ${group.id}["${group.label}"]`);
    lines.push("        direction LR");
    for (const name of group.skills) {
      lines.push(`        ${nodeId(name)}["${name}"]`);
    }
    if (group.sequential) {
      for (let i = 1; i < group.skills.length; i += 1) {
        lines.push(`        ${nodeId(group.skills[i - 1])} --> ${nodeId(group.skills[i])}`);
      }
    }
    lines.push("    end");
    lines.push("");
  }

  if (stageIds.length > 0) {
    lines.push(`    ROUTER --> ${stageIds[0]}`);
    for (let i = 1; i < stageIds.length; i += 1) {
      lines.push(`    ${stageIds[i - 1]} --> ${stageIds[i]}`);
    }
    lines.push(`    ${stageIds[stageIds.length - 1]} --> DONE([" Merged & released "])`);
  }

  for (const group of [...SIDE_STAGES, ...TRACKS]) {
    if (!groups.some((rendered) => rendered.id === group.id)) continue;
    if (group.from) {
      lines.push(`    ${group.from} --> ${group.id}`);
    } else if (group.attach && stageIds.includes(group.attach)) {
      lines.push(`    ${group.attach} -.${group.edge}.-> ${group.id}`);
    }
  }
  if (groups.some((group) => group.id === "GUARD")) {
    lines.push("    GUARD -.enforced throughout.-> ROUTER");
  }

  lines.push("```");
  return lines.join("\n");
}

function buildBlock(skills) {
  const categories = [...new Set([...skills.values()].map((skill) => skill.category))].sort();
  const caption =
    `_${skills.size} skills across ${categories.join(", ")}. ` +
    "Generated by `scripts/generate-workflow-diagram.mjs` and regenerated on every Changesets release._";
  return [START, "", buildDiagram(skills), "", caption, "", END].join("\n");
}

const readme = readFileSync(readmePath, "utf8");
const start = readme.indexOf(START);
const end = readme.indexOf(END);
if (start === -1 || end === -1 || end < start) {
  console.error(`README.md is missing the ${START} / ${END} markers`);
  process.exit(1);
}

const updated = readme.slice(0, start) + buildBlock(discoverSkills()) + readme.slice(end + END.length);

if (process.argv.includes("--check")) {
  if (updated !== readme) {
    console.error(
      "README.md workflow diagram is out of date.\nRun: node scripts/generate-workflow-diagram.mjs",
    );
    process.exit(1);
  }
  console.log("README.md workflow diagram is up to date");
} else if (updated !== readme) {
  writeFileSync(readmePath, updated);
  console.log("README.md workflow diagram regenerated");
} else {
  console.log("README.md workflow diagram already up to date");
}
