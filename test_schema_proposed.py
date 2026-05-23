"""
Proposed additional fields for the Event schema — under discussion, not yet wired up.

Added here to evaluate whether these fields belong in the ROPA before they land in
sheets.py and run.py.
"""
from typing import TypedDict


class EventExtended(TypedDict):
    # --- Fields already in production schema (omitted here) ---

    # Proposed new fields:
    ip_address: str | None              # IP of the page server at scrape time
    has_viewed_CFP: bool                # True if the CFP page has been fetched this run
    organizer_name: str | None          # Name of the person listed as organizer contact
    organizer_affiliation: str | None   # Organization the organizer contact belongs to
    previous_conferences: list[str]     # Conferences previously associated with this entry
    scrape_timestamp: str               # ISO 8601 datetime when the page was fetched
