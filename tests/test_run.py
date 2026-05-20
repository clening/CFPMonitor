import pytest
from unittest.mock import patch
import yaml
import os


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


def test_extract_json_finds_embedded_json():
    import run
    text = 'I found some conferences.\n\n{"events": [{"name": "Test"}], "new_sources": []}'
    result = run.extract_json(text)
    assert result["events"][0]["name"] == "Test"


def test_extract_json_handles_markdown_fenced_json():
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
    text_block.type = "text"
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
