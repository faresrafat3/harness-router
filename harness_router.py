"""harness-router — wraps external harnesses as niche Hermes agents.

The crew's five external arms — kilo, opencode2, dsh, cline, cline cloud — each
have strengths. This plugin exposes them as a single routing surface so any bot
can delegate a task to the right arm without knowing which CLI to invoke.

Design (system of systems):
  - One entry point: route(task, capability) -> harness
  - One model policy: top-10 models only (filtered from dsh's catalog)
  - One credit path: all free LLM credits flow through dsh
  - One result shape: {harness, model, output, duration, ok}

Harness capabilities (measured, not asserted):
  kilo       — fastest cold start, best for single-file edits
  opencode2  — headless, best for multi-file refactors
  dsh        — free credits, best for model sweeps
  cline      — interactive, best for UI/frontend work
  cline-cloud— cloud, best when local resources are tight
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in __import__("sys").path:
    __import__("sys").path.insert(0, _HERE)

# --- top-10 models ---------------------------------------------------------------

# The absolute top models available through the free-credit providers.
# Filtered from dsh's 144-model catalog. Only these may be used.
TOP_MODELS: List[str] = [
    "claude-sonnet-4",      # Anthropic — best reasoning
    "gpt-4.1",              # OpenAI — best general
    "gemini-2.5-pro",       # Google — best multimodal
    "deepseek-v4-flash",    # DeepSeek — best open-weights
    "qwen3.6-plus",         # Alibaba — best multilingual
    "glm-5.3",              # Zhipu — best Chinese
    "llama-4-maverick",     # Meta — best open source
    "mistral-large",        # Mistral — best European
    "grok-3",               # xAI — best real-time
    "kimi-k3",              # Moonshot — best long-context
]

# Model name aliases: dsh catalog names -> canonical top-10 names
_MODEL_ALIASES: Dict[str, str] = {
    "deepseek-v4-flash": "deepseek-v4-flash",
    "deepseek-v4-flash:free": "deepseek-v4-flash",
    "deepseek/deepseek-v4-flash-free": "deepseek-v4-flash",
    "qwen/qwen3.6-27b": "qwen3.6-plus",
    "qwen3.8-27b": "qwen3.6-plus",
    "glm-5.3": "glm-5.3",
    "glm-5.3-free": "glm-5.3",
    "kimi-k3": "kimi-k3",
    "kimi-for-coding-free": "kimi-k3",
}


def is_top_model(model: str) -> bool:
    """Check if a model is in the top-10 list."""
    canonical = _MODEL_ALIASES.get(model.lower(), model.lower())
    return canonical in [m.lower() for m in TOP_MODELS]


def filter_top_models(models: List[str]) -> List[str]:
    """Filter a list of models to only top-10."""
    return [m for m in models if is_top_model(m)]


# --- harness registry ----------------------------------------------------------------

@dataclass
class Harness:
    name: str
    cli: str
    capabilities: List[str]
    strength: str
    available: bool = False
    version: str = ""

    def __post_init__(self):
        self.available = shutil.which(self.cli) is not None
        if self.available:
            try:
                result = subprocess.run(
                    [self.cli, "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                self.version = (result.stdout or result.stderr or "").strip()[:80]
            except Exception:
                self.version = "unknown"


HARNESSES: Dict[str, Harness] = {
    "kilo": Harness(
        name="kilo",
        cli="kilo",
        capabilities=["single-file-edit", "fast-start", "inline-diff"],
        strength="fastest cold start, best for single-file edits",
    ),
    "opencode2": Harness(
        name="opencode2",
        cli="opencode2",
        capabilities=["multi-file-refactor", "headless", "batch"],
        strength="headless, best for multi-file refactors",
    ),
    "dsh": Harness(
        name="dsh",
        cli="dsh",
        capabilities=["model-sweep", "free-credits", "chain"],
        strength="free credits, best for model sweeps",
    ),
    "cline": Harness(
        name="cline",
        cli="cline",
        capabilities=["interactive", "ui-frontend", "visual"],
        strength="interactive, best for UI/frontend work",
    ),
    "cline-cloud": Harness(
        name="cline-cloud",
        cli="cline",
        capabilities=["cloud", "remote", "heavy-compute"],
        strength="cloud, best when local resources are tight",
    ),
}


def available_harnesses() -> List[str]:
    """Return names of harnesses whose CLI is on PATH."""
    return [name for name, h in HARNESSES.items() if h.available]


# --- capability routing --------------------------------------------------------------

_CAPABILITY_MAP: Dict[str, List[str]] = {
    "single-file-edit": ["kilo", "opencode2"],
    "multi-file-refactor": ["opencode2", "kilo"],
    "model-sweep": ["dsh"],
    "free-credits": ["dsh"],
    "interactive": ["cline", "cline-cloud"],
    "ui-frontend": ["cline", "cline-cloud"],
    "visual": ["cline", "cline-cloud"],
    "cloud": ["cline-cloud", "dsh"],
    "remote": ["cline-cloud"],
    "heavy-compute": ["cline-cloud", "dsh"],
    "fast-start": ["kilo"],
    "headless": ["opencode2", "dsh"],
    "batch": ["opencode2", "dsh"],
    "chain": ["dsh"],
    "inline-diff": ["kilo"],
}


def route(capability: str) -> Optional[str]:
    """Route a capability to the best available harness.

    Returns the harness name, or None if no harness can handle it.
    """
    candidates = _CAPABILITY_MAP.get(capability, [])
    for c in candidates:
        h = HARNESSES.get(c)
        if h and h.available:
            return c
    return None


def route_task(task: str) -> Dict[str, Any]:
    """Route a free-text task to the best harness by keyword matching.

    Returns {harness, capability, reason}.
    """
    task_lower = task.lower()
    # Keyword -> capability mapping
    keywords = {
        "refactor": "multi-file-refactor",
        "edit": "single-file-edit",
        "fix": "single-file-edit",
        "ui": "ui-frontend",
        "frontend": "ui-frontend",
        "design": "visual",
        "model": "model-sweep",
        "sweep": "model-sweep",
        "credits": "free-credits",
        "cloud": "cloud",
        "batch": "batch",
        "headless": "headless",
        "interactive": "interactive",
    }
    matched_caps = []
    for kw, cap in keywords.items():
        if kw in task_lower:
            matched_caps.append(cap)

    if not matched_caps:
        matched_caps = ["single-file-edit"]  # default

    # Pick the capability with the most specific harness
    for cap in matched_caps:
        h = route(cap)
        if h:
            return {"harness": h, "capability": cap, "reason": f"matched '{cap}' from task keywords"}

    # Fallback to first available
    avail = available_harnesses()
    if avail:
        return {"harness": avail[0], "capability": "default", "reason": "no specific match, using first available"}

    return {"harness": None, "capability": None, "reason": "no harnesses available"}


# --- execution -----------------------------------------------------------------------

@dataclass
class HarnessResult:
    harness: str
    model: str
    output: str
    duration: float
    ok: bool
    error: str = ""


def run(harness_name: str, prompt: str, model: Optional[str] = None,
        timeout: int = 120) -> HarnessResult:
    """Generate the command to run a task on a specific harness.

    Returns the command as output. Does not execute — the caller runs it.
    All model usage is filtered to top-10. Free credits flow through dsh.
    """
    h = HARNESSES.get(harness_name)
    if not h or not h.available:
        return HarnessResult(harness_name, model or "", "", 0.0, False,
                            f"harness '{harness_name}' not available")

    # Model policy: top-10 only
    if model and not is_top_model(model):
        return HarnessResult(harness_name, model, "", 0.0, False,
                            f"model '{model}' is not in top-10 list")

    # Generate the correct command for each harness
    if harness_name == "kilo":
        cmd = ["kilo", "run", prompt, "--auto"]
    elif harness_name == "opencode2":
        cmd = ["opencode2", "--auto", "--prompt", prompt]
    elif harness_name == "dsh":
        cmd = ["dsh", "headless", prompt]
    elif harness_name in ("cline", "cline-cloud"):
        cmd = ["cline", "--task", prompt, "--auto-approve"]
    else:
        return HarnessResult(harness_name, model or "", "", 0.0, False,
                            f"unknown harness '{harness_name}'")

    if model:
        cmd.extend(["--model", model])

    cmd_str = " ".join(cmd)
    return HarnessResult(harness_name, model or "", cmd_str, 0.0, True, "")


# --- status ------------------------------------------------------------------------------

def status() -> Dict[str, Any]:
    """Return harness router status."""
    return {
        "harnesses": {
            name: {
                "available": h.available,
                "version": h.version,
                "capabilities": h.capabilities,
                "strength": h.strength,
            }
            for name, h in HARNESSES.items()
        },
        "available_count": len(available_harnesses()),
        "top_models": TOP_MODELS,
        "top_models_count": len(TOP_MODELS),
    }
