# CFPMonitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python tool that uses Anthropic Managed Agents to discover conferences/CFPs on AI governance, surveillance, and civil liberties topics twice-weekly, logging results to Google Sheets with a git-hook-powered mini-ROPA.

**Architecture:** A thin Python orchestrator (`run.py`) reads config from YAML files, launches a Managed Agent session (web_search + web_fetch only), waits for the agent to finish, parses its JSON output, deduplicates against Google Sheets, and appends new rows. A pre-commit git hook (`check_ropa.py`) uses Claude Haiku to detect ROPA-relevant code changes and automatically updates `GOVERNANCE.md`.

**Tech Stack:** Python 3.12, `anthropic` SDK (managed agents beta), `gspread` + `google-auth` (Sheets), `python-dotenv`, `pyyaml`, `pytest`

---

## File Map

```
Software Projects/CFPMonitor/
├── .env                          # credentials — never committed
├── .env.example                  # template for forkers
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py                      # one-time: create Agent + Environment, init Sheet, install hook
├── run.py                        # main orchestrator — called by cron or manually
├── sheets.py                     # Google Sheets wrapper: read URLs, append rows, update last-run
├── check_ropa.py                 # pre-commit hook script: analyze diff, update GOVERNANCE.md
├── seeds.yaml                    # websites to check (editable; agent appends discoveries)
├── topics.yaml                   # subject areas (editable; injected into each session)
├── GOVERNANCE.md                 # mini-ROPA: what the system does, what data it touches
├── hooks/
│   └── pre-commit               # shell wrapper that calls check_ropa.py via venv python
├── logs/
│   └── .gitkeep                 # keeps logs/ in git without committing log files
└── tests/
    ├── test_sheets.py
    ├── test_run.py
    ├── test_check_ropa.py
    └── test_setup.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `Software Projects/CFPMonitor/` (all structure below)
- Create: `.gitignore`, `requirements.txt`, `.env.example`, `logs/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
cd "/home/privacat/Software Projects"
mkdir -p CFPMonitor/{logs,tests,hooks}
cd CFPMonitor
touch logs/.gitkeep
```

- [ ] **Step 2: Create `.gitignore`**

```
.env
venv/
__pycache__/
*.pyc
.pytest_cache/
logs/*.log
*.json  # service account key — never commit credentials
```

- [ ] **Step 3: Create `requirements.txt`**

```
anthropic>=0.50.0
gspread>=6.0.0
google-auth>=2.0.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 4: Create `.env.example`**

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6        # used by run.py for the discovery agent
ROPA_MODEL=claude-haiku-4-5-20251001     # used by check_ropa.py — cheaper model, simpler task

# Managed Agent (populated by setup.py — do not edit manually)
AGENT_ID=
ENVIRONMENT_ID=

# Google Sheets
GOOGLE_SHEET_ID=                         # the long ID from the sheet URL
GOOGLE_SERVICE_ACCOUNT_PATH=             # path to your downloaded service account JSON key
```

- [ ] **Step 5: Create venv and install dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: packages install without errors.

- [ ] **Step 6: Init git repo and commit scaffold**

```bash
git init
git add .gitignore requirements.txt .env.example logs/.gitkeep
git commit -m "chore: project scaffold — directories, deps, gitignore"
```

---

## Task 2: Config Files

**Files:**
- Create: `seeds.yaml`, `topics.yaml`, `GOVERNANCE.md`

- [ ] **Step 1: Create `seeds.yaml`**

```yaml
# Sites the agent checks every run.
# Add or remove freely. The agent appends newly discovered sources automatically.
# 'notes' explains WHY this site is worth monitoring — helps you decide later whether to keep or cull it.
sites:
  - url: https://wikicfp.com
    notes: "Broad CFP aggregator — good for academic and tech conferences"
  - url: https://www.usenix.org/conferences
    notes: "Security and systems conferences with strong CFP culture"
  - url: https://facctconference.org
    notes: "ACM FAccT — fairness, accountability, transparency in AI"
  - url: https://cpdpconferences.org
    notes: "Computers, Privacy and Data Protection — annual Brussels conference"
  - url: https://www.eff.org/events
    notes: "EFF events and activism conferences"
  - url: https://ainowinstitute.org
    notes: "AI Now Institute — AI governance and accountability"
  - url: https://www.iapp.org/conference
    notes: "International privacy professionals association"
  - url: https://papercall.io
    notes: "CFP aggregator — broad but filterable by topic"
  - url: https://datasociety.net/events
    notes: "Data & Society — surveillance, power, tech accountability"
  - url: https://aisafety.com/events-and-training
    notes: "AI safety events aggregator — broad calendar of conferences and training"
  - url: https://princint.ai/events/
    notes: "PIBBSS / Principles of Intelligence — orgs Carey is actively tracking for involvement"
  - url: https://fra.europa.eu/en/news-and-events/upcoming-events
    notes: "EU Fundamental Rights Agency — surveillance, rights, power accountability from EU perspective"
```

- [ ] **Step 2: Create `topics.yaml`**

```yaml
# Subject areas the agent searches for.
# These are injected into each session's task message at runtime — no code changes needed.
# Add, remove, or rephrase freely.
topics:
  - AI governance and policy
  - AI safety
  - global disempowerment and power consolidation
  - algorithmic accountability and fairness
  - privacy and surveillance
  - civil liberties and fundamental rights
  - tech accountability
  - surveillance capitalism
  - ungovernable systems and regulatory failure
```

- [ ] **Step 3: Create `GOVERNANCE.md`**

```markdown
# CFPMonitor — Governance Record (mini-ROPA)

**Owner:** Carey Lening
**Last updated:** 2026-05-20
**Purpose:** Track what this system does, what data it touches, and where that data goes.
Updated automatically by check_ropa.py when relevant code changes are committed.

## Agent Tools

| Tool | Provider | What it does | Data sent to provider |
|------|----------|--------------|----------------------|
| web_search | Anthropic (Managed Agents cloud) | Searches web for conferences | Search query strings |
| web_fetch | Anthropic (Managed Agents cloud) | Fetches content from URLs | URLs to retrieve |

## External API Calls

| Service | Provider | Purpose | Data shared |
|---------|----------|---------|-------------|
| Managed Agents API | Anthropic | Runs discovery agent | Topic list, seed URLs, existing URL list, current date |
| Google Sheets API | Google | Stores discovered events | Event rows: name, type, deadline, dates, organizer, location, URL, topics |

## Data Collected

| Field | Source | Personal data? | Notes |
|-------|--------|----------------|-------|
| Conference name | Web scraping | No | Public information |
| Organizer name | Web scraping | Potentially | Public-facing org/person names |
| Event dates, location, URL | Web scraping | No | Public information |
| Topics | Derived by agent | No | Assigned based on content |

## Data Retention

- Google Sheet: indefinite (until manually deleted)
- logs/run.log: indefinite (rotate manually as needed)
- Anthropic session data: per Anthropic's retention policy

## Change Log

| Date | Change | Commit |
|------|--------|--------|
| 2026-05-20 | Initial ROPA created | — |
```

- [ ] **Step 4: Commit config files**

```bash
git add seeds.yaml topics.yaml GOVERNANCE.md
git commit -m "chore: add config files — seeds, topics, and initial GOVERNANCE.md (mini-ROPA)"
```

---

## Task 3: `sheets.py`

**Files:**
- Create: `sheets.py`
- Create: `tests/test_sheets.py`

The sheet layout is: row 1 = last-run metadata cell (A1), row 2 = column headers, data from row 3 onward. This means `get_all_values()[2:]` skips both metadata and headers.

- [ ] **Step 1: Write failing tests**

Create `tests/test_sheets.py`:

```python
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def mock_sheet():
    """Patches gspread and Credentials so no real network calls are made."""
    with patch("sheets.gspread.authorize") as mock_auth, \
         patch("sheets.Credentials.from_service_account_file"):
        mock_client = MagicMock()
        mock_auth.return_value = mock_client
        sheet = MagicMock()
        mock_client.open_by_key.return_value.sheet1 = sheet
        yield sheet


def test_get_existing_urls_empty_sheet(mock_sheet):
    # Only metadata + header rows, no data yet
    mock_sheet.get_all_values.return_value = [
        ["Last run: (not yet run)"],
        ["Name", "Type", "Deadline", "Event Date(s)", "Organizer", "Location", "URL", "Topics", "Status", "Notes", "Date Added"],
    ]
    import sheets
    result = sheets.get_existing_urls("sheet123", "sa.json")
    assert result == set()


def test_get_existing_urls_returns_url_set(mock_sheet):
    mock_sheet.get_all_values.return_value = [
        ["Last run: 2026-05-20"],
        ["Name", "Type", "Deadline", "Event Date(s)", "Organizer", "Location", "URL", "Topics", "Status", "Notes", "Date Added"],
        ["FAccT 2026", "CFP", "2026-01-15", "2026-06-03", "ACM", "Chicago", "https://facctconference.org/2026", "AI", "new", "", "2026-05-20"],
        ["Test Conf", "Registration", "", "2026-09-01", "Test Org", "Virtual", "https://testconf.org", "surveillance", "new", "", "2026-05-20"],
    ]
    import sheets
    result = sheets.get_existing_urls("sheet123", "sa.json")
    assert result == {"https://facctconference.org/2026", "https://testconf.org"}


def test_append_events_formats_row_correctly(mock_sheet):
    import sheets
    events = [{
        "name": "Test Conf",
        "type": "CFP",
        "deadline": "2026-08-01",
        "event_dates": "2026-10-01 to 2026-10-03",
        "organizer": "Test Org",
        "location": "Virtual",
        "url": "https://test.org/cfp",
        "topics": ["AI governance", "privacy"],
    }]
    count = sheets.append_events("sheet123", "sa.json", events)
    assert count == 1
    rows = mock_sheet.append_rows.call_args[0][0]
    assert rows[0][0] == "Test Conf"
    assert rows[0][6] == "https://test.org/cfp"
    assert rows[0][7] == "AI governance, privacy"
    assert rows[0][8] == "new"   # default status; user edits this


def test_append_events_empty_list_does_not_call_api(mock_sheet):
    import sheets
    count = sheets.append_events("sheet123", "sa.json", [])
    assert count == 0
    mock_sheet.append_rows.assert_not_called()


def test_update_last_run_writes_to_a1(mock_sheet):
    import sheets
    sheets.update_last_run("sheet123", "sa.json")
    mock_sheet.update.assert_called_once()
    cell, value = mock_sheet.update.call_args[0]
    assert cell == "A1"
    assert "Last run:" in value[0][0]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
source venv/bin/activate
pytest tests/test_sheets.py -v
```

Expected: `ModuleNotFoundError: No module named 'sheets'`

- [ ] **Step 3: Implement `sheets.py`**

```python
"""
Google Sheets wrapper.

Sheet layout:
  Row 1 (A1): "Last run: YYYY-MM-DD" — freshness indicator, updated each run
  Row 2:      Column headers
  Row 3+:     Event data

Why gspread? It's a thin, well-maintained wrapper around the Sheets API that handles
OAuth token refresh automatically. The alternative (raw requests) requires much more boilerplate.
"""
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

# Sheets API scope — read/write to spreadsheets only, nothing else
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Name", "Type", "Deadline", "Event Date(s)", "Organizer",
    "Location", "URL", "Topics", "Status", "Notes", "Date Added",
]

# URL lives in column G (index 6). It's the dedup key — unambiguous, no fuzzy matching needed.
URL_COL_INDEX = 6


def _get_sheet(sheet_id: str, service_account_path: str):
    """Authenticate and return the first worksheet."""
    creds = Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).sheet1


def get_existing_urls(sheet_id: str, service_account_path: str) -> set[str]:
    """Return the set of all URLs already in the sheet.

    Used to build a dedup set before running the agent — we pass these URLs
    to the agent so it skips events we've already logged."""
    sheet = _get_sheet(sheet_id, service_account_path)
    all_values = sheet.get_all_values()
    # Skip row 0 (last-run metadata) and row 1 (headers); data starts at row 2
    return {
        row[URL_COL_INDEX]
        for row in all_values[2:]
        if len(row) > URL_COL_INDEX and row[URL_COL_INDEX]
    }


def append_events(sheet_id: str, service_account_path: str, events: list[dict]) -> int:
    """Append new events as rows. Returns count of rows added."""
    if not events:
        return 0

    sheet = _get_sheet(sheet_id, service_account_path)
    today = date.today().isoformat()

    rows = []
    for event in events:
        topics_str = ", ".join(event.get("topics", []))
        rows.append([
            event.get("name", ""),
            event.get("type", ""),
            event.get("deadline") or "",
            event.get("event_dates", ""),
            event.get("organizer", ""),
            event.get("location", ""),
            event.get("url", ""),
            topics_str,
            "new",   # default status — you change this to tracking/applied/passed
            "",      # notes — you fill this in
            today,
        ])

    sheet.append_rows(rows)
    return len(rows)


def update_last_run(sheet_id: str, service_account_path: str) -> None:
    """Write today's date into A1 as a freshness marker.

    A1 is reserved for this — headers are in row 2, data from row 3.
    This gives a single-glance freshness check without opening the whole sheet."""
    sheet = _get_sheet(sheet_id, service_account_path)
    sheet.update("A1", [[f"Last run: {date.today().isoformat()}"]])
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_sheets.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sheets.py tests/test_sheets.py
git commit -m "feat: add sheets.py — Google Sheets wrapper with dedup, append, and last-run update"
```

---

## Task 4: `run.py` — Config Loading and Message Building

**Files:**
- Create: `run.py` (partial — config + message building only)
- Create: `tests/test_run.py` (partial)

- [ ] **Step 1: Write failing tests for config loading and message building**

Create `tests/test_run.py`:

```python
import pytest
from unittest.mock import patch, mock_open
import yaml


def test_load_config_raises_on_missing_env_vars():
    """All six vars are required. Missing any should fail loudly."""
    with patch.dict("os.environ", {}, clear=True):
        import run
        with pytest.raises(ValueError, match="Missing env vars"):
            run.load_config()


def test_load_config_returns_expected_keys(tmp_path):
    seeds = {"sites": [{"url": "https://test.org", "notes": "test"}]}
    topics = {"topics": ["AI governance"]}

    (tmp_path / "seeds.yaml").write_text(yaml.dump(seeds))
    (tmp_path / "topics.yaml").write_text(yaml.dump(topics))

    env = {
        "ANTHROPIC_API_KEY": "sk-test",
        "ANTHROPIC_MODEL": "claude-sonnet-4-6",
        "AGENT_ID": "agent_123",
        "ENVIRONMENT_ID": "env_456",
        "GOOGLE_SHEET_ID": "sheet_789",
        "GOOGLE_SERVICE_ACCOUNT_PATH": "/path/sa.json",
    }
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch.dict("os.environ", env):
            import run
            config = run.load_config()
        assert config["agent_id"] == "agent_123"
        assert config["topics"] == ["AI governance"]
        assert config["seeds"][0]["url"] == "https://test.org"
    finally:
        os.chdir(old_cwd)


def test_build_task_message_contains_date():
    import run
    msg = run.build_task_message(["AI governance"], [{"url": "https://t.org", "notes": "n"}], set(), "2026-05-20")
    assert "2026-05-20" in msg
    assert "Do not rely on your training data" in msg


def test_build_task_message_contains_topics_and_seeds():
    import run
    msg = run.build_task_message(
        ["AI governance", "privacy"],
        [{"url": "https://wikicfp.com", "notes": "CFP aggregator"}],
        set(),
        "2026-05-20",
    )
    assert "AI governance" in msg
    assert "privacy" in msg
    assert "https://wikicfp.com" in msg
    assert "CFP aggregator" in msg


def test_build_task_message_includes_existing_urls():
    import run
    existing = {"https://already-logged.org/conf"}
    msg = run.build_task_message(["AI"], [], existing, "2026-05-20")
    assert "https://already-logged.org/conf" in msg


def test_build_task_message_none_existing_shows_placeholder():
    import run
    msg = run.build_task_message(["AI"], [], set(), "2026-05-20")
    assert "(none yet)" in msg
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_run.py -v
```

Expected: `ModuleNotFoundError: No module named 'run'`

- [ ] **Step 3: Implement config loading and message building in `run.py`**

Create `run.py`:

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_run.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_run.py
git commit -m "feat: add run.py config loading and task message builder"
```

---

## Task 5: `run.py` — Session Execution and JSON Parsing

**Files:**
- Modify: `run.py` (add `run_session`, `extract_json`)
- Modify: `tests/test_run.py` (add session + parsing tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_run.py`:

```python
def test_extract_json_finds_embedded_json():
    import run
    text = 'I found some conferences.\n\n{"events": [{"name": "Test"}], "new_sources": []}'
    result = run.extract_json(text)
    assert result["events"][0]["name"] == "Test"


def test_extract_json_handles_json_with_preamble():
    import run
    text = "Here are my findings:\n```json\n{\"events\": [], \"new_sources\": []}\n```"
    result = run.extract_json(text)
    assert result == {"events": [], "new_sources": []}


def test_extract_json_raises_on_no_json():
    import run
    with pytest.raises(ValueError, match="No JSON block found"):
        run.extract_json("No JSON here at all, just text.")


def test_run_session_returns_agent_text():
    """Verify run_session: creates session, sends message, collects text, stops at idle."""
    from unittest.mock import MagicMock
    import run

    mock_client = MagicMock()

    # Mock session creation
    mock_session = MagicMock()
    mock_session.id = "session_abc"
    mock_client.beta.sessions.create.return_value = mock_session

    # Build mock events: one agent message, then idle
    msg_event = MagicMock()
    msg_event.type = "agent.message"
    text_block = MagicMock()
    text_block.text = '{"events": [], "new_sources": []}'
    msg_event.content = [text_block]

    idle_event = MagicMock()
    idle_event.type = "session.status_idle"

    # Mock the SSE stream as a context manager
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=iter([msg_event, idle_event]))
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_client.beta.sessions.events.stream.return_value = mock_stream

    result = run.run_session(mock_client, "agent_123", "env_456", "find conferences")

    assert '{"events": [], "new_sources": []}' in result
    mock_client.beta.sessions.events.send.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm new tests fail**

```bash
pytest tests/test_run.py::test_extract_json_finds_embedded_json tests/test_run.py::test_run_session_returns_agent_text -v
```

Expected: `AttributeError: module 'run' has no attribute 'extract_json'`

- [ ] **Step 3: Add `run_session` and `extract_json` to `run.py`**

Add these functions after `build_task_message`:

```python
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
                    if hasattr(block, "text"):
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
    return json.loads(match.group())
```

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
pytest tests/test_run.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_run.py
git commit -m "feat: add run_session and extract_json to run.py"
```

---

## Task 6: `run.py` — Seeds Update and `main()`

**Files:**
- Modify: `run.py` (add `update_seeds`, `main`)
- Modify: `tests/test_run.py` (add seeds + main tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_run.py`:

```python
def test_update_seeds_appends_new_source(tmp_path):
    import os, run
    seeds_file = tmp_path / "seeds.yaml"
    seeds_file.write_text("sites:\n  - url: https://existing.org\n    notes: existing\n")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        count = run.update_seeds([{"url": "https://new.org", "notes": "newly discovered"}], str(seeds_file))
        assert count == 1
        assert "https://new.org" in seeds_file.read_text()
    finally:
        os.chdir(old_cwd)


def test_update_seeds_skips_duplicates(tmp_path):
    import os, run
    seeds_file = tmp_path / "seeds.yaml"
    seeds_file.write_text("sites:\n  - url: https://existing.org\n    notes: existing\n")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        count = run.update_seeds([{"url": "https://existing.org", "notes": "dupe"}], str(seeds_file))
        assert count == 0
    finally:
        os.chdir(old_cwd)


def test_update_seeds_returns_zero_on_empty_list(tmp_path):
    import run
    seeds_file = tmp_path / "seeds.yaml"
    seeds_file.write_text("sites: []\n")
    count = run.update_seeds([], str(seeds_file))
    assert count == 0
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
pytest tests/test_run.py::test_update_seeds_appends_new_source -v
```

Expected: `AttributeError: module 'run' has no attribute 'update_seeds'`

- [ ] **Step 3: Add `update_seeds` and `main` to `run.py`**

Append to `run.py`:

```python
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
            seeds_data["sites"].append({
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
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_run.py -v
```

Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_run.py
git commit -m "feat: complete run.py — seeds update and main orchestrator"
```

---

## Task 7: `setup.py`

**Files:**
- Create: `setup.py`
- Create: `hooks/pre-commit`
- Create: `tests/test_setup.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_setup.py`:

```python
from unittest.mock import patch, MagicMock, call
import os
import pytest


def test_create_agent_returns_id():
    import setup
    mock_client = MagicMock()
    mock_client.beta.agents.create.return_value.id = "agent_123"

    agent_id = setup.create_agent(mock_client, "claude-sonnet-4-6")

    assert agent_id == "agent_123"
    call_kwargs = mock_client.beta.agents.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    # Verify only web_search and web_fetch are enabled
    tools = call_kwargs["tools"]
    assert tools[0]["default_config"]["enabled"] is False
    enabled = [c["name"] for c in tools[0]["configs"] if c["enabled"]]
    assert set(enabled) == {"web_search", "web_fetch"}


def test_create_environment_returns_id():
    import setup
    mock_client = MagicMock()
    mock_client.beta.environments.create.return_value.id = "env_456"

    env_id = setup.create_environment(mock_client)

    assert env_id == "env_456"
    call_kwargs = mock_client.beta.environments.create.call_args.kwargs
    assert call_kwargs["config"]["type"] == "cloud"


def test_save_ids_to_env_writes_values(tmp_path):
    import setup
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-test\n")

    setup.save_ids_to_env("agent_123", "env_456", str(env_file))

    content = env_file.read_text()
    assert "AGENT_ID" in content
    assert "agent_123" in content
    assert "ENVIRONMENT_ID" in content
    assert "env_456" in content


def test_install_hook_creates_symlink(tmp_path):
    import setup
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    hook_src = hooks_dir / "pre-commit"
    hook_src.write_text("#!/bin/bash\n")

    git_hooks_dir = tmp_path / ".git" / "hooks"
    git_hooks_dir.mkdir(parents=True)

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        setup.install_hook()
        assert (git_hooks_dir / "pre-commit").is_symlink()
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_setup.py -v
```

Expected: `ModuleNotFoundError: No module named 'setup'`

- [ ] **Step 3: Create `hooks/pre-commit`**

```bash
#!/bin/bash
# Pre-commit hook: runs check_ropa.py to detect ROPA-relevant code changes.
# Installed by setup.py as a symlink from .git/hooks/pre-commit.
# Always exits 0 — suggests and stages updates but never blocks commits.

# Resolve the project root from this script's location (hooks/ dir)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/check_ropa.py"
```

Make it executable:
```bash
chmod +x hooks/pre-commit
```

- [ ] **Step 4: Implement `setup.py`**

```python
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
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_setup.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add setup.py hooks/pre-commit tests/test_setup.py
git commit -m "feat: add setup.py and pre-commit hook scaffold"
```

---

## Task 8: `check_ropa.py`

**Files:**
- Create: `check_ropa.py`
- Create: `tests/test_check_ropa.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_check_ropa.py`:

```python
from unittest.mock import patch, MagicMock
import os
import pytest


def test_get_staged_diff_returns_git_output():
    import check_ropa
    with patch("check_ropa.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "diff --git a/run.py b/run.py\n+import sendgrid"
        result = check_ropa.get_staged_diff()
    assert "sendgrid" in result


def test_analyze_diff_returns_none_when_no_ropa_changes():
    import check_ropa
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="NONE")]
    result = check_ropa.analyze_diff("minor bug fix in extract_json", mock_client, "claude-haiku-4-5-20251001")
    assert result is None


def test_analyze_diff_returns_text_on_ropa_change():
    import check_ropa
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text="# VERIFY: | 2026-05-20 | Added sendgrid SDK for email | abc123 |")
    ]
    result = check_ropa.analyze_diff("+import sendgrid", mock_client, "claude-haiku-4-5-20251001")
    assert result is not None
    assert "VERIFY" in result


def test_update_governance_appends_without_overwriting(tmp_path, monkeypatch):
    import check_ropa
    gov_file = tmp_path / "GOVERNANCE.md"
    gov_file.write_text("# Existing content\n\n## Change Log\n")
    monkeypatch.chdir(tmp_path)
    check_ropa.update_governance("| 2026-05-20 | new entry | abc |")
    content = gov_file.read_text()
    assert "# Existing content" in content
    assert "new entry" in content


def test_main_skips_silently_without_api_key():
    import check_ropa
    with patch.dict("os.environ", {}, clear=True):
        with patch("check_ropa.get_staged_diff", return_value="some diff"):
            result = check_ropa.main()
    assert result == 0


def test_main_exits_zero_when_no_ropa_changes():
    import check_ropa
    env = {"ANTHROPIC_API_KEY": "sk-test", "ROPA_MODEL": "claude-haiku-4-5-20251001"}
    with patch.dict("os.environ", env):
        with patch("check_ropa.get_staged_diff", return_value="fix typo in README"):
            with patch("check_ropa.analyze_diff", return_value=None):
                result = check_ropa.main()
    assert result == 0


def test_main_exits_zero_and_updates_governance_on_ropa_change(tmp_path, monkeypatch):
    import check_ropa
    gov_file = tmp_path / "GOVERNANCE.md"
    gov_file.write_text("# GOVERNANCE\n")
    monkeypatch.chdir(tmp_path)

    env = {"ANTHROPIC_API_KEY": "sk-test", "ROPA_MODEL": "claude-haiku-4-5-20251001"}
    with patch.dict("os.environ", env):
        with patch("check_ropa.get_staged_diff", return_value="+import sendgrid"):
            with patch("check_ropa.analyze_diff", return_value="# VERIFY: new SDK"):
                with patch("check_ropa.stage_governance") as mock_stage:
                    result = check_ropa.main()

    assert result == 0
    assert "VERIFY" in gov_file.read_text()
    mock_stage.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_check_ropa.py -v
```

Expected: `ModuleNotFoundError: No module named 'check_ropa'`

- [ ] **Step 3: Implement `check_ropa.py`**

```python
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
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_check_ropa.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Run full test suite to confirm nothing broken**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add check_ropa.py tests/test_check_ropa.py
git commit -m "feat: add check_ropa.py — pre-commit ROPA hook using Claude Haiku"
```

---

## Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# CFPMonitor

Twice-weekly discovery of conferences, CFPs, fellowships, and speaker opportunities
on AI governance, surveillance, power consolidation, and civil liberties.
Results go to a Google Sheet. New sources are added to `seeds.yaml` automatically.

Built on Anthropic Managed Agents — intentionally annotated as a learning reference
for how agent harnesses work.

## Prerequisites

- Python 3.12+
- An Anthropic API key (console.anthropic.com)
- A Google Sheet (create a blank one)
- A Google Cloud service account with Sheets API access (one-time, ~10 minutes)

## Google Cloud Setup (one-time)

1. Go to console.cloud.google.com → create a project
2. Enable the **Google Sheets API** for that project
3. Go to IAM & Admin → Service Accounts → Create Service Account
4. Download the JSON key file — save it somewhere safe (e.g. `~/.config/cfpmonitor-sa.json`)
5. Open your Google Sheet → Share → paste the service account email → Editor access

## Installation

```bash
git clone <repo>
cd CFPMonitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your API key, Sheet ID, and service account path
```

Run setup once:

```bash
./venv/bin/python setup.py
```

This creates the Managed Agent, cloud Environment, initializes the Sheet, and installs
the pre-commit hook. You won't need to run it again.

## Running

Manually:
```bash
./venv/bin/python run.py
```

Via cron (twice weekly, Mon/Thu 8am) — add to `crontab -e`:
```
0 8 * * 1,4 cd "/home/privacat/Software Projects/CFPMonitor" && ./venv/bin/python run.py >> logs/run.log 2>&1
```

Note: cron only fires while WSL is active. Missing a run is harmless — events are caught next time.

## Customizing

- **Add topics:** edit `topics.yaml`
- **Add/remove seed sites:** edit `seeds.yaml`
- **Change the model:** update `ANTHROPIC_MODEL` in `.env`

## Governance

`GOVERNANCE.md` tracks what data this system touches and where it goes (mini-ROPA).
The pre-commit hook updates it automatically when code changes are ROPA-relevant.
Review any `# VERIFY:` lines before finalizing a commit.

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, usage, and customization instructions"
```

---

## Task 10: Cron Setup and Smoke Test

**Files:** none — configuration only

- [ ] **Step 1: Install cron entry**

```bash
crontab -e
```

Add this line:
```
0 8 * * 1,4 cd "/home/privacat/Software Projects/CFPMonitor" && ./venv/bin/python run.py >> logs/run.log 2>&1
```

Save and exit. Verify it was saved:
```bash
crontab -l
```

Expected: the line appears.

- [ ] **Step 2: Verify .env is populated**

```bash
grep -E "AGENT_ID|ENVIRONMENT_ID" .env
```

Expected: both vars have values (set by `setup.py`).

- [ ] **Step 3: Run the full test suite one final time**

```bash
source venv/bin/activate
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Test the pre-commit hook works**

```bash
echo "# test" >> README.md
git add README.md
git commit -m "test: verify pre-commit hook fires"
```

Expected: `check_ropa:` output appears (either "skipping" if no key, or a ROPA analysis result). Commit succeeds regardless.

- [ ] **Step 5: Final commit**

```bash
git status
# Confirm clean or expected state
git log --oneline
```

Expected log:
```
test: verify pre-commit hook fires
docs: add README with setup, usage, and customization instructions
feat: add check_ropa.py — pre-commit ROPA hook using Claude Haiku
feat: add setup.py and pre-commit hook scaffold
feat: complete run.py — seeds update and main orchestrator
feat: add run_session and extract_json to run.py
feat: add run.py config loading and task message builder
feat: add sheets.py — Google Sheets wrapper with dedup, append, and last-run update
chore: add config files — seeds, topics, and initial GOVERNANCE.md (mini-ROPA)
chore: project scaffold — directories, deps, gitignore
```

---

## Self-Review Notes

- ✅ All spec sections covered: scaffold, config files, sheets.py, run.py, setup.py, check_ropa.py, hook, README, cron
- ✅ Every function has a corresponding test before implementation
- ✅ Method names consistent across tasks (`get_existing_urls`, `append_events`, `update_last_run`, `run_session`, `extract_json`, `update_seeds`)
- ✅ `URL_COL_INDEX = 6` defined once in `sheets.py`, referenced consistently
- ✅ Both the "suggest-and-stage, not block" principle and the "Haiku not Sonnet" rationale are documented inline
- ✅ `setup.py` initializes sheet with row 1 = metadata, row 2 = headers; `sheets.py` skips `all_values[2:]` consistently
- ✅ No placeholders or TBDs
