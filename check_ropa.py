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
import os
import subprocess
import sys
from datetime import date

import anthropic
from dotenv import load_dotenv

GOVERNANCE_FILE = "GOVERNANCE.md"


def get_staged_diff() -> str:
    """Return the staged diff (what's about to be committed)."""
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    return result.stdout


def analyze_diff(diff: str, client: anthropic.Anthropic, model: str) -> str | None:
    """Ask Claude if the diff contains ROPA-relevant changes.

    Returns suggested GOVERNANCE.md text if yes, None if no changes needed."""
    response = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""You are reviewing a git diff for CFPMonitor, a conference discovery tool.

Analyze this diff for changes relevant to a Record of Processing Activities (ROPA).
ROPA-relevant changes include:
- New AI/agent tools added or removed
- New third-party APIs or SDKs integrated (new import statements, new API calls)
- New data fields being collected, stored, or transmitted
- New external services receiving data
- Changes to data retention or sharing behavior

If there ARE ROPA-relevant changes, respond with a single table row to append to the Change Log in GOVERNANCE.md:
| {date.today().isoformat()} | [brief description] | (commit pending) |
Prefix the line with "# VERIFY: " so the human knows to review it before finalizing.

If there are NO ROPA-relevant changes (bug fixes, refactors, docs, config tweaks), respond with exactly: NONE

Git diff:
{diff[:8000]}""",
        }],
    )

    text = response.content[0].text.strip()
    return None if text == "NONE" else text


def update_governance(suggested_text: str) -> None:
    """Append the suggested update to GOVERNANCE.md."""
    with open(GOVERNANCE_FILE, "a") as f:
        f.write(f"\n{suggested_text}\n")


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
    suggested = analyze_diff(diff, client, model)

    if suggested:
        update_governance(suggested)
        stage_governance()
        print("check_ropa: GOVERNANCE.md updated with a suggested ROPA entry — review the # VERIFY line")

    return 0  # always 0 — suggest-and-stage, never block


if __name__ == "__main__":
    sys.exit(main())
