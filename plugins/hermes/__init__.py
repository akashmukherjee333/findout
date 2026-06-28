"""
findout Hermes plugin — /findout and /foundit slash commands.

Runs the findout verification pipeline (evidence-prediction, 3-angle search,
multi-pass verification) via a single slash command in TUI, CLI, or gateway.

Usage:
  /findout what is the speed of light
  /foundit what is the speed of light
  /findout --pipeline hybrid how do black holes work
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_COMMANDS = ("findout", "foundit")
_DEFAULT_TIMEOUT_SECONDS = 300
_HINT = "Check FINDOUT_MODEL/FINDOUT_BASE_URL/FINDOUT_API_KEY in ~/.hermes/.env."


def _load_dotenv(path: Path, env: dict[str, str]) -> None:
    """Load simple KEY=VALUE pairs into env without overriding existing values."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in env:
            continue
        env[key] = value.strip().strip('"').strip("'")


def _plugin_env() -> dict[str, str]:
    """Return subprocess env, including ~/.hermes/.env for fresh Hermes sessions."""
    env = {**os.environ}
    hermes_home = Path(env.get("HERMES_HOME") or Path.home() / ".hermes")
    _load_dotenv(hermes_home / ".env", env)
    return env


def _timeout_from_env(env: dict[str, str]) -> int:
    raw = env.get("FINDOUT_TIMEOUT", str(_DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS


def _run_findout(args: str) -> str:
    """Run the findout CLI with given arguments, return output."""
    env = _plugin_env()
    timeout = _timeout_from_env(env)
    try:
        result = subprocess.run(
            ["findout", "run", "--skip-gate", args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        stderr = result.stderr.strip()
        logger.warning("findout CLI error (exit %d): %s", result.returncode, stderr)
        return f"findout error: {stderr or 'unknown (check FINDOUT_* env vars)'}"
    except FileNotFoundError:
        return "findout CLI not installed. Run `pip install -e .` from the findout repo or activate the right venv."
    except subprocess.TimeoutExpired:
        return f"findout pipeline timed out after {timeout}s. " + _HINT
    except Exception as exc:
        logger.exception("findout plugin error")
        return f"findout error: {exc}"


def _handle_slash(raw_args: str) -> str:
    """Handle /findout <query> and /foundit <query>."""
    query = raw_args.strip()
    if not query:
        return (
            "Usage: `/findout <query>` or `/foundit <query>` — runs the findout verification pipeline.\n\n"
            "Example: `/foundit what is the speed of light`\n"
            "Set FINDOUT_MODEL, FINDOUT_BASE_URL, FINDOUT_API_KEY in ~/.hermes/.env"
        )

    output = _run_findout(query)
    if not output:
        return "findout returned empty output. " + _HINT

    if len(output) < 1900:
        return output

    return output[:1900] + "\n\n*(output truncated; run in CLI for full result)*"


def register(ctx) -> None:
    """Register /findout and /foundit."""
    for command in _COMMANDS:
        ctx.register_command(
            command,
            handler=_handle_slash,
            description="Run the findout verification pipeline on a query (evidence-prediction + 3-angle search)",
            args_hint="<query>",
        )
