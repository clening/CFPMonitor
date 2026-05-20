#!/usr/bin/env python3
"""
Pre-commit hook: detects ROPA-relevant changes in staged code and updates GOVERNANCE.md.
Called via hooks/pre-commit, which is symlinked to .git/hooks/pre-commit by setup.py.

Why Claude Haiku (not Sonnet)?
  Diff analysis is a pattern-matching task — "does this diff add a new SDK or data field?"
  Haiku is ~20x cheaper and fast enough that you won't notice it during a commit.
  Save Sonnet for tasks that need judgment.

Why exit 0 always?
  This hook suggests and stages updates — it never blocks commits. A governance hook
  that breaks git workflow gets bypassed immediately, defeating the whole purpose.
"""
import json
import os
import subprocess
import sys
from datetime import date

import anthropic
from dotenv import load_dotenv

GOVERNANCE_FILE = "GOVERNANCE.md"

# Maps each ROPA change category to its section in GOVERNANCE.md
SECTION_MAP = {
    "Agent Tools": "## Agent Tools",
    "External API Calls": "## External API Calls",
    "Data Collected": "## Data Collected",
    "Change Log": "## Change Log",
}


def get_staged_diff() -> str:
    """Return the staged diff (what's about to be committed)."""
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    return result.stdout


def analyze_diff(diff: str, client: anthropic.Anthropic, model: str) -> dict | None:
    """Ask Claude if the diff contains ROPA-relevant changes.

    Returns {"section": "...", "entry": "..."} if yes, None if no changes needed.
    Diffs are truncated to 8000 chars — large commits may miss late-file changes."""
    response = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""You are reviewing a git diff for CFPMonitor, a conference discovery tool.

Analyze this diff for ROPA-relevant changes. Each change type maps to a GOVERNANCE.md section:
- New AI/agent tools added or removed → "Agent Tools"
- New third-party APIs or SDKs integrated → "External API Calls"
- New data fields being collected, stored, or transmitted → "Data Collected"
- New external services receiving data → "External API Calls"

If ROPA-relevant, respond with ONLY this JSON — no explanation, no other text:
{{"section": "<Agent Tools|External API Calls|Data Collected|Change Log>", "entry": "# VERIFY: | {date.today().isoformat()} | [one-line description] | (commit pending) |"}}

If NOT ROPA-relevant (bug fixes, refactors, docs, config tweaks, test changes), respond with ONLY:
NONE

Git diff:
{diff[:8000]}""",
        }],
    )

    text = response.content[0].text.strip()
    if text == "NONE":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Haiku returned something unparseable — fall back to Change Log with a note
        return {
            "section": "Change Log",
            "entry": f"# VERIFY: | {date.today().isoformat()} | (auto-detection failed — review diff manually) | (commit pending) |",
        }


def update_governance(result: dict) -> None:
    """Insert the suggested entry under the correct section in GOVERNANCE.md.

    Mode "a" on the fallback open creates the file if absent."""
    section_header = SECTION_MAP.get(result.get("section", "Change Log"), "## Change Log")
    entry = result.get("entry", "")

    try:
        with open(GOVERNANCE_FILE, "r") as f:
            content = f.read()
    except FileNotFoundError:
        with open(GOVERNANCE_FILE, "w") as f:
            f.write(f"{section_header}\n{entry}\n")
        return

    if section_header in content:
        # Insert just before the next ## section (or at end if this is the last section)
        section_start = content.index(section_header)
        next_section = content.find("\n## ", section_start + 1)
        if next_section == -1:
            content = content.rstrip() + f"\n{entry}\n"
        else:
            content = content[:next_section] + f"\n{entry}" + content[next_section:]
    else:
        content = content.rstrip() + f"\n\n{section_header}\n{entry}\n"

    with open(GOVERNANCE_FILE, "w") as f:
        f.write(content)


def stage_governance() -> None:
    """Stage GOVERNANCE.md so it's included in the current commit."""
    subprocess.run(["git", "add", GOVERNANCE_FILE], check=True)


def main() -> int:
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Don't block commits if API key isn't configured yet
        print("check_ropa: ANTHROPIC_API_KEY not set — skipping ROPA check")
        return 0

    model = os.getenv("ROPA_MODEL", "claude-haiku-4-5-20251001")

    diff = get_staged_diff()
    if not diff.strip():
        return 0  # nothing staged, nothing to analyze

    client = anthropic.Anthropic(api_key=api_key)
    result = analyze_diff(diff, client, model)

    if result:
        update_governance(result)
        stage_governance()
        print(f"check_ropa: GOVERNANCE.md updated under '{result.get('section')}' — review the # VERIFY line")

    return 0  # always 0 — suggest-and-stage, never block


if __name__ == "__main__":
    sys.exit(main())
