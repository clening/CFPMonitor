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
| Organizer email | Web scraping | Yes | Contact email — verify scraping is from public CFP pages only |
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
| 2026-05-20 | Added organizer_email field — collects personal contact data from web scraping | 447eda1 |
# VERIFY: | 2026-05-20 | (auto-detection failed — review diff manually) | (commit pending) |
