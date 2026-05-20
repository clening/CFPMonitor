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

I'm ready to analyze a git diff for CFPMonitor and identify ROPA-relevant changes. However, I don't see an actual diff content in your message—you've written "some diff" as a placeholder.

Please provide the actual git diff output, and I'll review it for:

- New AI/agent tools
- New third-party APIs or SDKs
- New data fields collected/stored/transmitted
- New external services receiving data
- Changes to data retention/sharing

Then I'll respond with either a ROPA change log entry (prefixed with "# VERIFY: ") or **NONE**.

I'd be happy to help review this diff for ROPA-relevant changes, but I don't see an actual git diff in your message. You've included a placeholder "some diff" instead.

Could you please provide the actual git diff output? Once you share it, I'll analyze it for:

- New AI/agent tools added or removed
- New third-party APIs or SDKs integrated
- New data fields being collected, stored, or transmitted
- New external services receiving data
- Changes to data retention or sharing behavior

Please paste the full diff and I'll provide either:
- A `# VERIFY:` prefixed table row for GOVERNANCE.md if ROPA-relevant changes exist
- `NONE` if there are no ROPA-relevant changes

NONE

This diff only modifies the pre-commit hook script to improve symlink resolution. It's a bug fix/refactoring that doesn't introduce any new data processing, APIs, tools, or external service integrations.
