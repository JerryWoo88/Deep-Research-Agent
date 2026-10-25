"""Centralized configuration for research-agent.

All tunable parameters are defined here so that changes only need to be made
in one place.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Directory Layout
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"
MODES_DIR = PROJECT_ROOT / "modes"

# ---------------------------------------------------------------------------
# Agent Limits
# ---------------------------------------------------------------------------

# Policy: accuracy over cost and speed. Limits below are sized so that no
# collected data is dropped and thinking models never run out of budget.
# deepseek-v4-pro accepted >=488k input tokens and 128k max_tokens in testing.

# Maximum number of tool calls the agent may make for a single Part
MAX_TOOL_CALLS_PER_PART = 40

# Maximum number of LLM round-trips per Part research loop
MAX_MESSAGES_PER_PART = 45

# ---------------------------------------------------------------------------
# Token / Truncation Limits
# ---------------------------------------------------------------------------

# Max characters of a single tool result stored in raw_data_chunks
# (kept equal to what the research model saw, so extraction sees the same data)
TOOL_RESULT_RAW_CHARS = 20000

# Max characters of a single tool result sent back to the LLM
TOOL_RESULT_LLM_CHARS = 20000

# Max characters of raw_data fed into the extraction prompt.
# 40 calls x 20k = 800k chars max (~270k tokens); effectively no truncation.
# (The original 12k limit dropped 70-80% of every Part's data.)
EXTRACTION_RAW_CHARS = 1000000

# Max tokens for the research loop LLM calls (thinking included)
RESEARCH_MAX_TOKENS = 32000

# Max tokens for extraction calls (thinking included). deepseek-flash used
# ~25k (47k chars of thinking + 17k chars of answer) on a 73k-char Part.
EXTRACTION_MAX_TOKENS = 64000

# Max tokens for writing calls (thinking included)
WRITING_MAX_TOKENS = 32000

# Max tokens for the final judgment call (thinking included)
JUDGMENT_MAX_TOKENS = 32000

# Max characters of the full report passed to the final judgment prompt.
# A full 10-part body is ~70-120k chars; the original 50k cut off Parts 9-10.
JUDGMENT_REPORT_CHARS = 1000000

# Max tokens for the executive summary call (thinking included)
SUMMARY_MAX_TOKENS = 16000

# ---------------------------------------------------------------------------
# Cost Estimation (USD per 1M tokens)
# ---------------------------------------------------------------------------

# Blended average rates — update when model pricing changes
COST_PER_1M_INPUT_TOKENS = 4.0
COST_PER_1M_OUTPUT_TOKENS = 18.0

# ---------------------------------------------------------------------------
# HTTP / Scraping
# ---------------------------------------------------------------------------

import os
from dotenv import load_dotenv

env_path = Path.home() / ".agents" / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv() # Fallback to local .env

HTTP_USER_AGENT = os.environ.get("HTTP_USER_AGENT", (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
))

SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "ResearchAgent research@example.com")

# ---------------------------------------------------------------------------
# Mode Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODE = "deep_research_review"
