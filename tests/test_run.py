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
