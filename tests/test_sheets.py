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
        ["Name", "Type", "Deadline", "Event Date(s)", "Organizer", "Organizer Email", "Location", "URL", "Topics", "Status", "Notes", "Date Added"],
    ]
    import sheets
    result = sheets.get_existing_urls("sheet123", "sa.json")
    assert result == set()


def test_get_existing_urls_returns_url_set(mock_sheet):
    mock_sheet.get_all_values.return_value = [
        ["Last run: 2026-05-20"],
        ["Name", "Type", "Deadline", "Event Date(s)", "Organizer", "Organizer Email", "Location", "URL", "Topics", "Status", "Notes", "Date Added"],
        ["FAccT 2026", "CFP", "2026-01-15", "2026-06-03", "ACM", "", "Chicago", "https://facctconference.org/2026", "AI", "new", "", "2026-05-20"],
        ["Test Conf", "Registration", "", "2026-09-01", "Test Org", "", "Virtual", "https://testconf.org", "surveillance", "new", "", "2026-05-20"],
    ]
    import sheets
    result = sheets.get_existing_urls("sheet123", "sa.json")
    assert result == {"https://facctconference.org/2026", "https://testconf.org"}


def test_append_events_formats_row_correctly(mock_sheet):
    import sheets
    from datetime import date
    events = [{
        "name": "Test Conf",
        "type": "CFP",
        "deadline": "2026-08-01",
        "event_dates": "2026-10-01 to 2026-10-03",
        "organizer": "Test Org",
        "organizer_email": "cfp@test.org",
        "location": "Virtual",
        "url": "https://test.org/cfp",
        "topics": ["AI governance", "privacy"],
    }]
    count = sheets.append_events("sheet123", "sa.json", events)
    assert count == 1
    rows = mock_sheet.append_rows.call_args[0][0]
    assert rows[0][0] == "Test Conf"
    assert rows[0][5] == "cfp@test.org"       # Organizer Email
    assert rows[0][7] == "https://test.org/cfp"   # URL moved to index 7
    assert rows[0][8] == "AI governance, privacy"
    assert rows[0][9] == "new"
    assert rows[0][11] == date.today().isoformat()   # Date Added column


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
