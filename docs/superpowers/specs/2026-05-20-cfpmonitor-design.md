# CFPMonitor — Design Spec
*Created: 2026-05-20*

## What This Is

A twice-weekly conference discovery tool that finds speaking opportunities, CFPs, fellowships, and seminars in Carey's research areas (AI governance, surveillance, power consolidation, civil liberties, etc.) and logs them to a Google Sheet for tracking.

**Learning goal:** This project is intentionally built to demonstrate how Anthropic's Managed Agents work in practice — how you create a harness, run sessions, stream events, and process agent output. The code comments explain the *why* behind architectural choices, not just the *what*.

---

## Why Managed Agents (not standard Messages API)

The standard Messages API is stateless: you call `messages.create()`, get a response, done. If you want multi-step tool use, you build your own loop — send message, check if Claude wants to use a tool, execute it, send the result back, repeat.

Managed Agents give you that loop out of the box, plus:
- A **cloud container** where the agent runs (so it can browse the web, run commands, etc.)
- **Persistent sessions** you can steer mid-run
- **Built-in tools** (web_search, web_fetch, bash, file ops) without you wiring them up
- **SSE streaming** so you see what the agent is doing in real time

For open-ended research tasks — "go find conferences on these topics across the web" — managed agents are the right tool. You'd have to build a lot of scaffolding to replicate this behavior with the standard API.

---

## Architecture

```
cron (Mon/Thu 8am)
  → run.py
      → sheets.py          read existing URLs (for deduplication)
      → Managed Agent session
            web_search + web_fetch  (Anthropic's cloud container)
            outputs structured JSON
      → parse JSON
      → sheets.py          deduplicate + append new rows
      → update seeds.yaml  add newly discovered sources

git commit (any time)
  → hooks/pre-commit
      → check_ropa.py      analyze staged diff with Claude Haiku
      → if ROPA-relevant:  update + stage GOVERNANCE.md automatically
```

**Key design decision: agent created once, sessions are ephemeral.**
The Agent (its model, system prompt, and tool config) is created once via `setup.py` and reused forever. Each run creates a new Session — a fresh execution of that same agent against a new task. Think of the Agent as a job description; Sessions are individual work orders.

This is different from the standard API where there's no persistent "agent" object — just API calls.

---

## Components

| File | Role |
|---|---|
| `setup.py` | One-time setup: creates Agent + Environment, saves IDs to `.env` |
| `run.py` | Main orchestrator: loads config, runs session, writes results |
| `sheets.py` | Google Sheets wrapper: read existing rows, append new ones |
| `seeds.yaml` | Websites the agent checks every run (editable; agent appends new discoveries) |
| `topics.yaml` | Subject areas to search for (editable; injected into each session at runtime) |
| `.env` | Credentials and IDs (never committed to git) |
| `.env.example` | Template for anyone forking this project |
| `logs/run.log` | Append-only log of each run's summary |
| `GOVERNANCE.md` | Mini-ROPA: record of what the system does, what data it touches, and where it goes — updated automatically on relevant commits |
| `check_ropa.py` | Git pre-commit hook script: analyzes staged diff with Claude Haiku, updates GOVERNANCE.md if ROPA-relevant changes detected |
| `hooks/pre-commit` | Shell wrapper that calls `check_ropa.py` — symlinked into `.git/hooks/` by `setup.py` |

### Config surface — where things live and why

Everything user-customizable lives in config files so you can change it without touching code. Nothing personal is baked into the codebase, making it safe to share.

- **`.env`** — secrets and generated IDs (API keys, Sheet ID, Agent ID, Environment ID, model name)
- **`seeds.yaml`** — websites: you edit, agent appends
- **`topics.yaml`** — subject areas: you edit freely
- **`.env.example`** — placeholder template for sharing/forking

---

## Data Model

### Google Sheet columns

| Column | Notes |
|---|---|
| Name | Conference/event name |
| Type | CFP / Speaker Opportunity / Fellowship / Registration / Seminar |
| Deadline | Submission or registration deadline (blank if not found) |
| Event Date(s) | When the event happens |
| Organizer | Who's running it |
| Location | City + country, or "Virtual" |
| URL | **Deduplication key** — checked before every append |
| Topics | Relevant tags (e.g., "AI governance, surveillance") |
| Status | You manage this: `new` / `tracking` / `applied` / `passed` |
| Notes | Your freeform notes column |
| Date Added | When the script logged it (YYYY-MM-DD) |

The URL column is the dedup key because it's unambiguous — no fuzzy matching needed.

### `seeds.yaml` structure

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

### `topics.yaml` structure

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

---

## Agent Design

### Model and tools

- **Model:** `claude-sonnet-4-6` (set via `ANTHROPIC_MODEL` in `.env`)
  - Sonnet is sufficient for structured extraction and relevance judgment; Opus would be ~5x more expensive for no meaningful quality gain on this task
- **Tools enabled:** `web_search` and `web_fetch` only
  - Bash and file operations are disabled — the agent has no reason to run shell commands, and limiting the toolset keeps it focused and reduces the surface area for unexpected behavior

### System prompt (stable — set at agent creation)

```
You are a conference and CFP discovery agent. Your job is to find upcoming conferences,
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

Do not include any other text after the JSON block.
```

### Session task message (dynamic — built at runtime from config files)

The specific topics and seed sites are injected here, not in the system prompt. This means you can change topics or seeds without touching the agent configuration.

**Date grounding:** The orchestrator fetches the real current date from Python (`datetime.date.today()`) and injects it into the message. This prevents the agent from treating its training cutoff as "now" and mistakenly excluding future events or including past ones.

```
Today's date is 2026-05-20. Use this as your reference for determining whether events
are upcoming or already passed. Do not rely on your training data for the current date.

Topics to search for:
- AI governance and policy
- [... from topics.yaml ...]

Seed websites to check first:
- https://wikicfp.com — Broad CFP aggregator
- [... from seeds.yaml ...]

Events already in the tracking sheet (do not include these):
- https://facctconference.org/2026 — FAccT 2026
- [... from Google Sheet URL column ...]

Output format:
{
  "events": [
    {
      "name": "string",
      "type": "CFP | Speaker Opportunity | Fellowship | Registration | Seminar",
      "deadline": "YYYY-MM-DD or null",
      "event_dates": "string",
      "organizer": "string",
      "location": "string or Virtual",
      "url": "string",
      "topics": ["string"]
    }
  ],
  "new_sources": [
    {
      "url": "string",
      "notes": "why this site is worth monitoring"
    }
  ]
}
```

---

## Orchestrator Flow (`run.py`)

```
1. Load config
   Read .env → API keys, Sheet ID, Agent ID, Environment ID, model
   Read seeds.yaml → list of site URLs + notes
   Read topics.yaml → list of subject areas

2. Read existing sheet
   Pull URL column from Google Sheets → build a set for O(1) dedup lookups
   (Why a set? Checking "is this URL already in the sheet" happens once per event found.
    A set lookup is instant regardless of sheet size; iterating a list would be slow.)

3. Build the session task message
   Format topics and seed sites into the prompt template
   Append the already-logged URL list so the agent skips them

4. Create and run the agent session
   POST to /sessions with Agent ID + Environment ID
   Open SSE stream → write all agent events to logs/run.log (for debugging)
   Wait for session.status_idle event
   (Why wait for status_idle? The agent may call multiple tools in sequence.
    status_idle means it has nothing more to do — the task is complete.)

5. Extract and parse JSON
   Find the JSON block in the agent's final message
   Parse into events[] and new_sources[] arrays

6. Deduplicate and append
   For each event: check URL against the set from step 2
   Append only new events to Google Sheets, with today's date in Date Added column

7. Update seeds.yaml
   Append any new_sources URLs not already in seeds.yaml

8. Log summary
   Write a one-line summary to logs/run.log: "Run complete: X new events, Y new sources"
```

---

## Setup & Scheduling

### One-time setup (`setup.py`)

1. Creates the Managed Agent via API → saves `AGENT_ID` to `.env`
2. Creates the cloud Environment → saves `ENVIRONMENT_ID` to `.env`
3. Tests Google Sheets connection → confirms write access
4. Symlinks `hooks/pre-commit` → `.git/hooks/pre-commit` (installs the ROPA hook)

After this, `setup.py` is never needed again unless you want to reset from scratch.

### Google Cloud (manual, one-time, ~10 minutes)

Required for Google Sheets write access. The README will include step-by-step instructions:
1. Create a project in Google Cloud Console
2. Enable the Google Sheets API
3. Create a service account, download the JSON key
4. Share your Google Sheet with the service account's email address
5. Set `GOOGLE_SERVICE_ACCOUNT_PATH` in `.env` to the JSON key path

### Scheduling (WSL cron)

```bash
# Run CFPMonitor every Monday and Thursday at 8am
0 8 * * 1,4 cd "/home/privacat/Software Projects/CFPMonitor" && ./venv/bin/python run.py >> logs/run.log 2>&1
```

**WSL caveat:** Cron only runs while WSL is active. Missing a run is harmless — events will be caught on the next run, nothing is lost.

---

## `.env.example`

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6        # Used by run.py for the discovery agent
ROPA_MODEL=claude-haiku-4-5-20251001     # Used by check_ropa.py — cheaper model, simpler task

# Managed Agent (populated by setup.py — do not edit manually)
AGENT_ID=
ENVIRONMENT_ID=

# Google Sheets
GOOGLE_SHEET_ID=                        # The long ID from the sheet's URL
GOOGLE_SERVICE_ACCOUNT_PATH=            # Path to your downloaded service account JSON key
```

---

## Governance Automation (`check_ropa.py` + pre-commit hook)

### The idea

Git already knows what changed in a commit — that's the diff. If the commit message is enough to describe a change, then Claude can read the same diff and determine whether `GOVERNANCE.md` needs updating. This turns governance documentation from "remember to update it" into "it updates itself."

This is CI/CD for governance: the same philosophy as running a linter on every commit, but applied to data processing records instead of code style.

### What counts as ROPA-relevant

The hook watches for four categories of change:

| Category | Example |
|---|---|
| New agent tool | Adding `bash` to the toolset in `setup.py` |
| New third-party API or SDK | Adding `import sendgrid` or a new `requests.post()` to a new service |
| New data field collected | Adding a column to the Google Sheet schema |
| New data recipient | Sending event data to a new external service |

Changes that are *not* ROPA-relevant: bug fixes, refactors, log message changes, README updates, config value changes that don't add new data flows.

### How it works

```
git commit
  → .git/hooks/pre-commit (symlink to hooks/pre-commit)
      → check_ropa.py
          → git diff --cached          get the staged diff
          → Claude Haiku               classify: ROPA-relevant or not?
          → if relevant:
               update GOVERNANCE.md   append suggested section (marked # VERIFY)
               git add GOVERNANCE.md  stage it for inclusion in this commit
               print summary          "GOVERNANCE.md updated — review the addition"
          → if not relevant:
               silent pass
  → commit proceeds (GOVERNANCE.md included if updated)
```

**Key design choice: suggest-and-stage, not block.**
The hook doesn't gate the commit — it adds to it. You review the GOVERNANCE.md diff in the same commit review. If the suggestion is wrong, you amend it. This avoids the failure mode where governance tooling becomes so annoying that people bypass it.

**If `ANTHROPIC_API_KEY` is missing:** the hook skips silently with a warning. It won't break your git workflow if the project isn't fully set up.

### `GOVERNANCE.md` structure

```markdown
# CFPMonitor — Governance Record (mini-ROPA)

**Owner:** Carey Lening
**Last updated:** YYYY-MM-DD
**Purpose of this file:** Track what this system does, what data it touches,
and where that data goes. Updated automatically by check_ropa.py on relevant commits.

## Agent Tools
| Tool | Provider | What it does | Data sent |
|------|----------|--------------|-----------|
| web_search | Anthropic (Managed Agents cloud) | Searches web for conferences | Search query strings |
| web_fetch | Anthropic (Managed Agents cloud) | Fetches content from URLs | URLs to retrieve |

## External API Calls
| Service | Provider | Purpose | Data shared |
|---------|----------|---------|-------------|
| Managed Agents API | Anthropic | Runs discovery agent | Topic list, seed URLs, dedup URL list, current date |
| Google Sheets API | Google | Stores discovered events | Event rows: name, type, deadline, dates, organizer, location, URL, topics |

## Data Collected
| Field | Source | Personal data? | Notes |
|-------|--------|----------------|-------|
| Conference name | Web scraping | No | Public information |
| Organizer name | Web scraping | Potentially | Public-facing org/person names |
| Event dates, location, URL | Web scraping | No | Public information |

## Data Retention
- Google Sheet: indefinite (until manually deleted)
- logs/run.log: indefinite (rotate manually as needed)
- Anthropic session data: per Anthropic's retention policy

## Change Log
| Date | Change | Commit |
|------|--------|--------|
| 2026-05-20 | Initial ROPA created | — |
```

### The experiment

The theory being tested: *can a lightweight governance artifact stay accurate through real development if updating it is automated rather than manual?* ROPAs almost universally drift because nobody updates them when code changes. By wiring the update to the commit itself, the cost of compliance drops to "review a diff" instead of "remember to update a separate document." Track whether it actually stays current.

---

## What You'll Learn Building This

- **Agent vs. Session:** The separation between a reusable agent definition and ephemeral work sessions
- **SSE streaming:** How to consume server-sent events and why `status_idle` is the terminal signal
- **Tool restriction:** Why you limit tools to only what the agent needs (web_search + web_fetch), not everything available
- **Config injection:** Why topics and seeds go in the session message rather than the system prompt — keeping the agent reusable across different topic sets
- **Orchestrator pattern:** How a thin Python script handles the deterministic work (dedup, sheet writes) while the agent handles judgment work (relevance, discovery)
