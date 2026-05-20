# PLACEHOLDER — not real code, used to test the ROPA pre-commit hook
# Simulates a change that adds GitHub as a new external API and data destination.

import requests

GITHUB_TOKEN = None  # loaded from env
GITHUB_REPO = "carey/cfpmonitor-events"


def push_events_to_github(events: list[dict]) -> None:
    """Push discovered events to a GitHub repository as a JSON file.

    Stores event data externally on GitHub — new data recipient."""
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/events.json",
        headers=headers,
        json={"message": "update events", "content": events},
    )
