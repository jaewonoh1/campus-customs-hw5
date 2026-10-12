"""Shared configuration for the Campus Customs agent team.

One place for: where the project lives, how to build the model (every agent talks
to the AI through the Portkey gateway, using `PORTKEY_API_KEY`), and the single
allowed model — `gpt-6-luna` — for all agents.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent
HW_DIR = BACKEND_DIR.parent          # homework5_1014/
PROJECT_ROOT = HW_DIR.parent         # the course repo root (holds the shared .env)
PROMPTS_DIR = BACKEND_DIR / "prompts"

# Load .env from the course root first (per the course rules), then the hw5
# folder, then backend/. First to define a variable wins; all are optional.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(HW_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

# Only gpt-6-luna is allowed for every agent in this homework. The env var exists
# for environment plumbing, but it must stay gpt-6-luna.
ALLOWED_MODEL = "gpt-6-luna"
MODEL_NAME = os.getenv("HW5_MODEL", ALLOWED_MODEL)
if MODEL_NAME != ALLOWED_MODEL:
    raise RuntimeError(
        f"Only '{ALLOWED_MODEL}' is allowed for the agents; got '{MODEL_NAME}'."
    )

# gpt-6-luna rejects function tools unless reasoning_effort is 'none' on the chat
# completions endpoint, so set it here for every agent.
MODEL_SETTINGS = OpenAIChatModelSettings(openai_reasoning_effort="none", timeout=60)


def make_model() -> OpenAIChatModel:
    """Build the chat model for the agents, routed through Portkey."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("Set PORTKEY_API_KEY in the project-root .env.")
    base_url = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
    return OpenAIChatModel(
        MODEL_NAME, provider=OpenAIProvider(api_key=api_key, base_url=base_url)
    )
