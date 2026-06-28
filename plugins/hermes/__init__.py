"""
findout Hermes plugin — /findout slash command.

Runs the findout verification pipeline (evidence-prediction, 3-angle search,
multi-pass verification) via a single slash command in TUI, CLI, or gateway.

Usage:
  /findout what is the speed of light
  /findout --pipeline hybrid how do black holes work
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

_HINT = (
    "Too long? Try a more specific query, or check FINDOUT_MODEL/FINDOUT_BASE_URL "
    "in your .env"
)


def _run_findout(args: str) -> str:
    """Run the findout CLI with given arguments, return output."""
    try:
        result = subprocess.run(
            ["findout", "run", "--skip-gate", args],
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ},
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            stderr = result.stderr.strip()
            logger.warning("findout CLI error (exit %d): %s", result.returncode, stderr)
            return f"findout error: {stderr or 'unknown (check FINDOUT_* env vars)'}"
    except FileNotFoundError:
        return "findout CLI not installed. Run `pip install findout` or activate the right venv."
    except subprocess.TimeoutExpired:
        return "findout pipeline timed out after 180s. " + _HINT
    except Exception as exc:
        logger.exception("findout plugin error")
        return f"findout error: {exc}"


def _handle_slash(raw_args: str) -> str:
    """Handle /findout <query>."""
    query = raw_args.strip()
    if not query:
        return (
            "Usage: `/findout <query>` — runs the findout verification pipeline.\n\n"
            "Example: `/findout what is the speed of light`\n"
            "Set FINDOUT_MODEL, FINDOUT_BASE_URL, FINDOUT_API_KEY in your .env"
        )

    output = _run_findout(query)
    if not output:
        return "findout returned empty output. " + _HINT

    # If the output is short enough, return directly
    if len(output) < 1900:
        return output

    # Long output: truncate with a note
    return output[:1900] + "\n\n*(output truncated; run in CLI for full result)*"


def register(ctx) -> None:
    """Register the /findout slash command."""
    ctx.register_command(
        "findout",
        handler=_handle_slash,
        description="Run the findout verification pipeline on a query (evidence-prediction + 3-angle search)",
        args_hint="<query>",
    )
