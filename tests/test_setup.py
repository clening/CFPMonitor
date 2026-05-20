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
