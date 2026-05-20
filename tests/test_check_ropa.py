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


def test_analyze_diff_returns_dict_on_ropa_change():
    import check_ropa
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text='{"section": "External API Calls", "entry": "# VERIFY: | 2026-05-20 | Added sendgrid SDK | (commit pending) |"}')
    ]
    result = check_ropa.analyze_diff("+import sendgrid", mock_client, "claude-haiku-4-5-20251001")
    assert result is not None
    assert result["section"] == "External API Calls"
    assert "VERIFY" in result["entry"]


def test_analyze_diff_falls_back_on_unparseable_response():
    import check_ropa
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="This looks ROPA-relevant because...")]
    result = check_ropa.analyze_diff("+import sendgrid", mock_client, "claude-haiku-4-5-20251001")
    assert result is not None
    assert result["section"] == "Change Log"
    assert "VERIFY" in result["entry"]


def test_update_governance_inserts_under_correct_section(tmp_path, monkeypatch):
    import check_ropa
    gov_file = tmp_path / "GOVERNANCE.md"
    gov_file.write_text("# CFPMonitor\n\n## Data Collected\n| Field | Source |\n|-------|--------|\n\n## Change Log\n")
    monkeypatch.chdir(tmp_path)
    check_ropa.update_governance({"section": "Data Collected", "entry": "# VERIFY: | 2026-05-20 | new field | (commit pending) |"})
    content = gov_file.read_text()
    assert "# CFPMonitor" in content                  # existing content preserved
    assert "## Change Log" in content                 # later section preserved
    data_pos = content.index("## Data Collected")
    entry_pos = content.index("# VERIFY:")
    changelog_pos = content.index("## Change Log")
    assert data_pos < entry_pos < changelog_pos       # entry is between its section and the next


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
    gov_file.write_text("# GOVERNANCE\n\n## Data Collected\n\n## Change Log\n")
    monkeypatch.chdir(tmp_path)

    env = {"ANTHROPIC_API_KEY": "sk-test", "ROPA_MODEL": "claude-haiku-4-5-20251001"}
    ropa_result = {"section": "Data Collected", "entry": "# VERIFY: | 2026-05-20 | new field | (commit pending) |"}
    with patch.dict("os.environ", env):
        with patch("check_ropa.get_staged_diff", return_value="+import sendgrid"):
            with patch("check_ropa.analyze_diff", return_value=ropa_result):
                with patch("check_ropa.stage_governance") as mock_stage:
                    result = check_ropa.main()

    assert result == 0
    assert "VERIFY" in gov_file.read_text()
    mock_stage.assert_called_once()
