"""Centralized configuration for model-router.

All tunable parameters are defined here so that changes only need to be made
in one place.
"""

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------

# Base URL for the Anthropic/OpenAI-compatible API endpoint
API_BASE_URL = "https://api.deepseek.com/v1"

# Whether to test all API models before starting a long research task
ENABLE_PREFLIGHT_CHECK = True

# How many times to send a request that came back with an empty answer before
# raising an error (empty answers must never reach the report)
EMPTY_REPLY_ATTEMPTS = 3

# Fallback configuration (if primary model fails)
ENABLE_FALLBACK = True
FALLBACK_MODEL = {"model": "deepseek-chat", "provider": "openai"}

# ---------------------------------------------------------------------------
# Model Mapping (tier → model info)
# ---------------------------------------------------------------------------
# "provider" can be "anthropic" or "openai"
# Optional "extra_body" is sent as-is with OpenAI-compatible requests.
#
# Same split as the original repo: reading data with flash, conclusions with
# pro. Thinking is on only where checking and reasoning happen:
#   medium  = research loop (tool calls)        -> flash, no thinking
#   low     = data extraction / conflict checks -> flash, thinking
#   high    = report writing, final judgment    -> pro, thinking
#   summary = executive summary                 -> pro, no thinking
# Thinking models spend max_tokens on reasoning before answering, so their
# budgets in config.py are large (32k-64k); with 4-8k the answer came back
# empty or cut off.
# Note: "deepseek-chat" is deepseek-flash in non-thinking mode, while
# "deepseek-flash" thinks. Thinking is switched off per tier with
#     "extra_body": {"thinking": {"type": "disabled"}}

NO_THINKING = {"thinking": {"type": "disabled"}}

# ===== Active: DeepSeek =====
MODEL_MAP = {
    "high": {"model": "deepseek-v4-pro", "provider": "openai"},
    "medium": {"model": "deepseek-chat", "provider": "openai"},
    "low": {"model": "deepseek-flash", "provider": "openai"},
    "summary": {"model": "deepseek-v4-pro", "provider": "openai", "extra_body": NO_THINKING},
}

# ===== Backup: Gemini =====
# MODEL_MAP = {
#     "high": {"model": "gemini-3.1-pro-preview", "provider": "openai"},
#     "medium": {"model": "gemini-3.1-pro-preview", "provider": "openai"},
#     "low": {"model": "gemini-3-flash-preview", "provider": "openai"},
# }

# ===== Backup: Claude (uncomment to switch back) =====
# MODEL_MAP = {
#     "high": {"model": "claude-opus-4-6", "provider": "anthropic"},
#     "medium": {"model": "claude-sonnet-4-6", "provider": "anthropic"},
#     "low": {"model": "gemini-3-flash-preview", "provider": "openai"},
# }

# Model used for the initial complexity classification call
CLASSIFY_MODEL = {"model": "deepseek-chat", "provider": "openai"}

# Human-readable labels for each tier (used in logging / display)
TIER_LABELS = {
    "high": "DeepSeek V4 Pro (thinking)",
    "medium": "DeepSeek Chat (flash, no thinking)",
    "low": "DeepSeek Flash (thinking)",
    "summary": "DeepSeek V4 Pro (no thinking)",
}

# ---------------------------------------------------------------------------
# Classification Prompt
# ---------------------------------------------------------------------------

CLASSIFY_PROMPT = (
    "Classify this task's complexity as exactly one of: high, medium, low.\n"
    "- high: architecture design, complex reasoning, multi-step planning\n"
    "- medium: coding, debugging, moderate analysis\n"
    "- low: simple Q&A, classification, extraction, translation\n"
    "Respond with only the word."
)

# ---------------------------------------------------------------------------
# Default Parameters
# ---------------------------------------------------------------------------

DEFAULT_MAX_TOKENS = 4096
CLASSIFY_MAX_TOKENS = 10

