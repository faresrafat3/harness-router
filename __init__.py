"""harness-router — wraps external harnesses as niche Hermes agents.

One entry point for all external arms. Any bot can delegate a task to the
right harness without knowing which CLI to invoke.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    import harness_router as _hr
except ImportError:
    try:
        from . import harness_router as _hr  # type: ignore[no-redef]
    except ImportError:
        _hr = None  # type: ignore[assignment]
        logger.warning("harness-router: harness_router module unavailable")


def register(ctx) -> None:
    """Called once by the plugin loader."""
    if _hr is None:
        logger.warning("harness-router: module unavailable, skipping registration")
        return

    # Register a /harness slash command
    def _handle_harness(raw_args: str, session_id: str = "") -> str:
        if _hr is None:
            return "harness-router module unavailable"
        args = (raw_args or "").split()
        sub = args[0].lower() if args else "status"

        if sub == "status":
            st = _hr.status()
            lines = [f"harness-router v1.0.0 — {st['available_count']}/5 harnesses available"]
            for name, info in st["harnesses"].items():
                mark = "✓" if info["available"] else "✗"
                lines.append(f"  {mark} {name:<14} {info['version'] or 'not found'}")
                if info["available"]:
                    lines.append(f"      {info['strength']}")
            lines.append(f"\ntop-10 models: {', '.join(st['top_models'])}")
            return "\n".join(lines)

        if sub == "route":
            if len(args) < 2:
                return "usage: /harness route <capability or task description>"
            task = " ".join(args[1:])
            # Try capability first, then task routing
            result = _hr.route(task)
            if result:
                return f"route '{task}' -> {result}"
            r = _hr.route_task(task)
            return f"route '{task}' -> {r['harness']} ({r['reason']})"

        if sub == "run":
            if len(args) < 3:
                return "usage: /harness run <harness> <prompt>"
            harness = args[1]
            prompt = " ".join(args[2:])
            res = _hr.run(harness, prompt)
            if res.ok:
                return f"[{res.harness}] ({res.duration:.1f}s)\n{res.output[:2000]}"
            return f"[{res.harness}] FAILED: {res.error}"

        if sub == "models":
            return "top-10 models:\n" + "\n".join(f"  {m}" for m in _hr.TOP_MODELS)

        if sub == "available":
            return "available harnesses: " + ", ".join(_hr.available_harnesses())

        return ("usage: /harness <status|route|run|models|available>\n"
                "  status              show all harnesses and their availability\n"
                "  route <task>        route a task to the best harness\n"
                "  run <harness> <p>   run a prompt on a specific harness\n"
                "  models              show the top-10 model list\n"
                "  available           list available harnesses")

    try:
        ctx.register_command("harness", handler=_handle_harness,
                             description="Harness router: status, route, run, models, available")
    except Exception:
        logger.debug("harness-router: /harness command registration failed", exc_info=True)

    logger.info("harness-router: loaded, %d/%d harnesses available",
                len(_hr.available_harnesses()), len(_hr.HARNESSES))
