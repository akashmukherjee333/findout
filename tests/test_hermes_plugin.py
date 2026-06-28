"""Tests for the Hermes slash-command plugin."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_PATH = Path(__file__).resolve().parents[1] / "plugins" / "hermes" / "__init__.py"


def _load_plugin():
    spec = importlib.util.spec_from_file_location("findout_hermes_plugin", PLUGIN_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Ctx:
    def __init__(self):
        self.commands = {}

    def register_command(self, name, **kwargs):
        self.commands[name] = kwargs


def test_registers_findout_and_foundit_commands():
    plugin = _load_plugin()
    ctx = _Ctx()

    plugin.register(ctx)

    assert set(ctx.commands) == {"findout", "foundit"}
    assert ctx.commands["findout"]["handler"] is ctx.commands["foundit"]["handler"]
    assert ctx.commands["foundit"]["args_hint"] == "<query>"


def test_plugin_env_loads_hermes_dotenv(monkeypatch, tmp_path):
    plugin = _load_plugin()
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("FINDOUT_TIMEOUT=301\nEXTRA_FLAG=1\n")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.delenv("FINDOUT_TIMEOUT", raising=False)
    monkeypatch.delenv("EXTRA_FLAG", raising=False)

    env = plugin._plugin_env()

    assert env["EXTRA_FLAG"] == "1"
    assert plugin._timeout_from_env(env) == 301


def test_plugin_env_does_not_override_existing_env(monkeypatch, tmp_path):
    plugin = _load_plugin()
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("EXTRA_FLAG=from-file\n")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("EXTRA_FLAG", "from-process")

    env = plugin._plugin_env()

    assert env["EXTRA_FLAG"] == "from-process"
