#!/usr/bin/env python3
"""
Main orchestrator — runs twice weekly via cron, or manually:
  ./venv/bin/python run.py

Flow:
  1. Load config from .env + yaml files
  2. Read existing sheet URLs (for deduplication)
  3. Build and send task to the Managed Agent session
  4. Wait for session.status_idle (agent is done)
  5. Parse the agent's JSON output
  6. Write new events to Google Sheets
  7. Update seeds.yaml with newly discovered sources
"""
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

import sheets

# Ensure logs/ directory exists before setting up file handler.
# logging.basicConfig fires at import time, so the directory must pre-exist.
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/run.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    """Load all config from .env, seeds.yaml, and topics.yaml.

    Raises immediately if any required variable is missing — better to fail fast
    with a clear message than to fail mid-run with a cryptic KeyError."""
    load_dotenv()

    required = [
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "AGENT_ID", "ENVIRONMENT_ID",
        "GOOGLE_SHEET_ID", "GOOGLE_SERVICE_ACCOUNT_PATH",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing env vars: {', '.join(missing)} — run setup.py first")

    with open("seeds.yaml") as f:
        seeds_data = yaml.safe_load(f)

    with open("topics.yaml") as f:
        topics_data = yaml.safe_load(f)

    return {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": os.getenv("ANTHROPIC_MODEL"),
        "agent_id": os.getenv("AGENT_ID"),
        "env_id": os.getenv("ENVIRONMENT_ID"),
        "sheet_id": os.getenv("GOOGLE_SHEET_ID"),
        "service_account_path": os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH"),
        "seeds": seeds_data.get("sites", []),
        "topics": topics_data.get("topics", []),
    }


def build_task_message(topics: list[str], seeds: list[dict], existing_urls: set[str], today: str) -> str:
    """Build the session task message from config file contents.

    Topics and seeds come from yaml files (not the system prompt) so they can be
    updated by editing a file — no agent recreation needed."""
    topics_str = "\n".join(f"- {t}" for t in topics)
    seeds_str = "\n".join(f"- {s.get('url', '')} — {s.get('notes', '')}" for s in seeds)
    existing_str = "\n".join(f"- {url}" for url in sorted(existing_urls)) if existing_urls else "(none yet)"

    return f"""Today's date is {today}. Use this as your reference for determining whether events are upcoming or already passed. Do not rely on your training data for the current date.

Topics to search for:
{topics_str}

Seed websites to check first:
{seeds_str}

Events already in the tracking sheet (do not include these):
{existing_str}

Output a single JSON block with this exact structure — no other text after it:
{{
  "events": [
    {{
      "name": "string",
      "type": "CFP | Speaker Opportunity | Fellowship | Registration | Seminar",
      "deadline": "YYYY-MM-DD or null",
      "event_dates": "string",
      "organizer": "string",
      "organizer_email": "email address or null",
      "location": "string or Virtual",
      "url": "string",
      "topics": ["string"]
    }}
  ],
  "new_sources": [
    {{
      "url": "string",
      "notes": "why this site is worth monitoring"
    }}
  ]
}}"""


def run_session(client: anthropic.Anthropic, agent_id: str, env_id: str, task_message: str) -> str:
    """Create a session, send the task, stream until idle, return the agent's full text output.

    Why wait for status_idle? The agent calls multiple tools in sequence (web_search,
    then web_fetch on individual pages, then more searches). status_idle is the signal
    that it has truly finished — not just paused between tool calls."""
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title=f"CFP discovery {date.today().isoformat()}",
    )
    log.info(f"Session created: {session.id}")

    final_text = ""

    with client.beta.sessions.events.stream(session.id) as stream:
        # Send the task after opening the stream — the API buffers events until the stream attaches
        client.beta.sessions.events.send(
            session.id,
            events=[{
                "type": "user.message",
                "content": [{"type": "text", "text": task_message}],
            }],
        )

        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        final_text += block.text
            elif event.type == "agent.tool_use":
                log.info(f"Tool call: {event.name}")
            elif event.type == "session.status_idle":
                log.info("Session idle — agent finished")
                break

    return final_text


def extract_json(text: str) -> dict:
    """Find and parse the JSON block in the agent's output.

    The agent is instructed to end with a JSON block. We use regex rather than
    parsing the entire output as JSON because the agent may include reasoning
    text before the block."""
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        raise ValueError(f"No JSON block found in agent output. Output was:\n{text[:500]}")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Matched a JSON-like block but it failed to parse: {e}\n"
            f"Matched text was:\n{match.group()[:500]}"
        ) from e


def update_seeds(new_sources: list[dict], seeds_path: str = "seeds.yaml") -> int:
    """Append newly discovered sources to seeds.yaml. Returns count added.

    The agent discovers sites we don't know about — this persists them so future
    runs check those sites automatically without any manual intervention."""
    with open(seeds_path) as f:
        seeds_data = yaml.safe_load(f)

    existing_urls = {site["url"] for site in seeds_data.get("sites", [])}

    added = 0
    for source in new_sources:
        if source.get("url") and source["url"] not in existing_urls:
            seeds_data.setdefault("sites", []).append({
                "url": source["url"],
                "notes": source.get("notes", "Discovered by agent"),
            })
            added += 1

    if added > 0:
        with open(seeds_path, "w") as f:
            yaml.dump(seeds_data, f, default_flow_style=False, allow_unicode=True)

    return added


def main() -> None:
    log.info("=== CFPMonitor run started ===")

    config = load_config()
    client = anthropic.Anthropic(api_key=config["api_key"])

    # Read existing URLs first — passed to agent so it skips already-logged events
    log.info("Reading existing sheet URLs for deduplication...")
    existing_urls = sheets.get_existing_urls(config["sheet_id"], config["service_account_path"])
    log.info(f"Found {len(existing_urls)} existing events in sheet")

    task_message = build_task_message(
        config["topics"],
        config["seeds"],
        existing_urls,
        date.today().isoformat(),
    )

    log.info("Starting agent session...")
    agent_output = run_session(client, config["agent_id"], config["env_id"], task_message)

    log.info("Parsing agent output...")
    result = extract_json(agent_output)

    events = result.get("events", [])
    new_sources = result.get("new_sources", [])

    # Deduplicate: O(1) set lookup per event — the set was built from the full sheet above
    new_events = [e for e in events if e.get("url") not in existing_urls]
    log.info(f"Agent found {len(events)} events; {len(new_events)} are new")

    if new_events:
        added = sheets.append_events(config["sheet_id"], config["service_account_path"], new_events)
        log.info(f"Wrote {added} new events to sheet")

    sheets.update_last_run(config["sheet_id"], config["service_account_path"])

    seeds_added = update_seeds(new_sources) if new_sources else 0
    if seeds_added:
        log.info(f"Added {seeds_added} new sources to seeds.yaml")

    log.info(f"=== Run complete: {len(new_events)} new events, {seeds_added} new sources ===")


if __name__ == "__main__":
    main()
