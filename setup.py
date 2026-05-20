#!/usr/bin/env python3
"""
One-time setup. Run this once to:
  1. Create the Managed Agent on Anthropic's platform
  2. Create the cloud Environment where sessions run
  3. Save Agent ID and Environment ID to .env
  4. Initialize the Google Sheet structure
  5. Install the pre-commit ROPA hook

After this, run.py handles everything. Re-run setup.py only to reset from scratch.

Why create Agent and Environment separately?
  The Agent defines WHAT runs (model, system prompt, tools).
  The Environment defines WHERE it runs (cloud container config).
  Keeping them separate lets you update one without recreating the other.
"""
import os
import sys
from pathlib import Path

import anthropic
import gspread
from dotenv import load_dotenv, set_key
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SYSTEM_PROMPT = """You are a conference and CFP discovery agent. Your job is to find upcoming conferences,
calls for papers (CFPs), calls for speakers, fellowship opportunities, and seminars
where speakers or presenters are being sought, or where registration is currently open.

You will be given a list of topics and a list of seed websites to check. Check all seed
sites first, then use web_search to discover additional sources not on the list.

Only include events that are:
- In the future (not already passed)
- Actively seeking speakers/presenters OR have open registration
- Relevant to at least one of the provided topics

At the end of your research, output a single JSON block with two arrays:
1. "events" — the events you found
2. "new_sources" — websites you discovered that aren't on the seed list but are worth monitoring

Do not include any other text after the JSON block."""

HEADERS = [
    "Name", "Type", "Deadline", "Event Date(s)", "Organizer",
    "Location", "URL", "Topics", "Status", "Notes", "Date Added",
]


def create_agent(client: anthropic.Anthropic, model: str) -> str:
    """Create the Managed Agent. Returns the agent ID.

    Only web_search and web_fetch are enabled. Bash and file ops are disabled —
    the agent has no reason to run shell commands, and a smaller toolset means
    less surface area for unexpected behavior."""
    agent = client.beta.agents.create(
        name="CFPMonitor Discovery Agent",
        model=model,
        system=SYSTEM_PROMPT,
        tools=[{
            "type": "agent_toolset_20260401",
            "default_config": {"enabled": False},   # start with everything off
            "configs": [
                {"name": "web_search", "enabled": True},
                {"name": "web_fetch", "enabled": True},
            ],
        }],
    )
    return agent.id


def create_environment(client: anthropic.Anthropic) -> str:
    """Create the cloud environment. Returns the environment ID.

    Unrestricted networking lets the agent reach any public conference website."""
    env = client.beta.environments.create(
        name="cfpmonitor-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    return env.id


def save_ids_to_env(agent_id: str, env_id: str, env_path: str = ".env") -> None:
    """Write Agent and Environment IDs to .env."""
    set_key(env_path, "AGENT_ID", agent_id)
    set_key(env_path, "ENVIRONMENT_ID", env_id)


def init_sheet(sheet_id: str, service_account_path: str) -> None:
    """Initialize sheet structure: last-run marker in A1, headers in row 2.

    Row 1 = freshness metadata, Row 2 = headers, data from Row 3.
    This layout lets sheets.py update A1 without touching the headers."""
    creds = Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1
    sheet.update("A1", [["Last run: (not yet run)"]])
    sheet.update("A2", [HEADERS])


def install_hook() -> None:
    """Symlink hooks/pre-commit into .git/hooks/.

    The hook lives in hooks/ (committed to git) so it travels with the repo.
    setup.py activates it by creating the symlink."""
    hook_src = Path("hooks/pre-commit").resolve()
    hook_dst = Path(".git/hooks/pre-commit")

    if hook_dst.exists() or hook_dst.is_symlink():
        hook_dst.unlink()

    hook_dst.symlink_to(hook_src)
    hook_src.chmod(0o755)
    print(f"  Installed: {hook_dst} → {hook_src}")


def main() -> None:
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")

    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)
    if not sheet_id or not sa_path:
        print("Error: GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_PATH must be set in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("1. Creating Managed Agent...")
    agent_id = create_agent(client, model)
    print(f"   Agent ID: {agent_id}")

    print("2. Creating cloud Environment...")
    env_id = create_environment(client)
    print(f"   Environment ID: {env_id}")

    print("3. Saving IDs to .env...")
    save_ids_to_env(agent_id, env_id)

    print("4. Initializing Google Sheet...")
    init_sheet(sheet_id, sa_path)
    print("   Sheet initialized")

    print("5. Installing pre-commit hook...")
    install_hook()

    print("\nSetup complete. Run: ./venv/bin/python run.py")


if __name__ == "__main__":
    main()
