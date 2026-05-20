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
    seeds_str = "\n".join(f"- {s['url']} — {s.get('notes', '')}" for s in seeds)
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
