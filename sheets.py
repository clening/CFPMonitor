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
