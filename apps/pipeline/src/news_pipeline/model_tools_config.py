"""Human-maintained configuration for model and tool release discovery."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")


def _env_list(name: str, defaults: list[str] | None = None) -> list[str]:
    values = os.getenv(name, ",".join(defaults or [])).split(",")
    return [value.strip() for value in values if value.strip()]


def _env_enabled(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


# Core feeds are always active. Override the complete list with
# MODEL_TOOL_CORE_FEEDS only when a local run needs a different baseline.
MODEL_TOOL_CORE_FEEDS_DEFAULT = [
    "https://openai.com/news/rss.xml",
    "https://developers.openai.com/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://research.google/blog/rss/",
    "https://developers.googleblog.com/feeds/posts/default",
    "https://blog.google/technology/ai/rss/",
    "https://blog.google/technology/developers/rss/",
    "https://www.microsoft.com/en-us/research/feed/",
    "https://blogs.microsoft.com/ai/feed/",
    "https://azure.microsoft.com/en-us/blog/feed/",
    "https://developer.nvidia.com/blog/feed/",
    "https://feeds.feedburner.com/nvidiablog",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://github.blog/ai-and-ml/feed/",
]
MODEL_TOOL_CORE_FEEDS = _env_list("MODEL_TOOL_CORE_FEEDS", MODEL_TOOL_CORE_FEEDS_DEFAULT)

# Source pages are official non-RSS fallbacks for providers with sparse feeds.
MODEL_TOOL_SOURCE_PAGES = [
    "https://www.anthropic.com/news",
    "https://www.anthropic.com/engineering",
    "https://ai.google.dev/gemini-api/docs/changelog",
    "https://ai.meta.com/blog/",
    "https://mistral.ai/news/",
    "https://cohere.com/blog/",
]
MODEL_TOOL_SOURCE_PAGES += _env_list("MODEL_TOOL_SOURCE_PAGES_EXTRA")

# Emerging feeds rotate within the candidate allow-list. They supplement core
# feeds and never replace them.
MODEL_TOOL_EMERGING_FEEDS = [
    "https://blog.google/rss/",
    "https://github.blog/category/ai-and-ml/feed/",
    "https://cloud.google.com/blog/feed/",
    "https://openrss.org/openai.com/news/rss.xml",
]
MODEL_TOOL_EMERGING_FEEDS += _env_list("MODEL_TOOL_EMERGING_FEEDS_EXTRA")
MODEL_TOOL_FEED_CANDIDATES = sorted(
    set(
        MODEL_TOOL_EMERGING_FEEDS
        + [
            "https://blog.google/technology/ai/rss/",
            "https://developers.googleblog.com/feeds/posts/default",
            "https://developer.nvidia.com/blog/feed/",
            "https://blogs.microsoft.com/ai/feed/",
            "https://aws.amazon.com/blogs/machine-learning/feed/",
        ]
    )
)

# Core terms are deterministic classifier inputs. Emerging terms are appended
# at runtime from the generated dynamic state.
MODEL_TOOL_CORE_MODEL_TERMS = [
    "model",
    "models",
    "frontier model",
    "foundation model",
    "gpt",
    "o3",
    "o4",
    "o4-mini",
    "claude",
    "gemini",
    "gemini api",
    "llama",
    "mistral",
    "mixtral",
    "command",
    "cohere",
    "grok",
    "deepseek",
    "qwen",
    "phi",
    "gemma",
    "sonnet",
    "opus",
    "haiku",
    "embedding",
    "embeddings",
    "reasoning",
    "multimodal",
    "vision-language",
    "speech",
    "tts",
    "video model",
    "image model",
    "veo",
    "imagen",
    "sora",
    "whisper",
    "voxtral",
    "sam",
]
MODEL_TOOL_CORE_TOOL_SERVICE_TERMS = [
    "agent",
    "agents",
    "agentic",
    "codex",
    "claude code",
    "gemini cli",
    "antigravity",
    "copilot",
    "jules",
    "ai studio",
    "studio",
    "sdk",
    "api",
    "responses api",
    "gemini api",
    "adk",
    "agent development kit",
    "service",
    "platform",
    "connector",
    "tool",
    "tools",
    "workflow",
    "terminal",
    "ide",
    "inference",
    "serving",
    "deployment",
    "benchmark",
    "eval",
    "evaluation",
]

MODEL_TOOL_KNOWN_BENCHMARK_URLS = {
    "claude opus 4 8": "https://artificialanalysis.ai/models/claude-opus-4-8",
    "gemini 3 5 flash": "https://artificialanalysis.ai/models/gemini-3-5-flash",
    "step 3 7 flash": "https://artificialanalysis.ai/models/step-3-7-flash",
}

MODEL_TOOL_HOSTING_RELEASE_TERMS = [
    "amazon bedrock",
    "amazon sagemaker",
    "aws",
    "azure",
    "foundry",
    "jumpstart",
    "microsoft foundry",
    "nvidia-accelerated",
    "nvidia gpus",
    "sagemaker",
]

MODEL_TOOL_MODEL_UPDATE_ONLY_TERMS = [
    "new capabilities to",
    "new capability to",
    "updates to",
    "upgrade to",
]
MODEL_TOOL_RELEASE_TERMS = [
    "announce",
    "announcing",
    "introduce",
    "introducing",
    "launch",
    "launched",
    "release",
    "released",
    "available",
    "generally available",
    "preview",
    "beta",
    "new",
    "upgrade",
    "updated",
    "updates",
    "rollout",
    "rolling out",
    "changelog",
]

# Limits and toggles are environment-overridable for local operations.
MODEL_TOOL_MAX_ITEMS = int(os.getenv("MODEL_TOOL_MAX_ITEMS", "8"))
MODEL_TOOL_DYNAMIC_AUTO_UPDATE = _env_enabled("MODEL_TOOL_DYNAMIC_AUTO_UPDATE")
MODEL_TOOL_DYNAMIC_MAX_EMERGING_FEEDS = int(os.getenv("MODEL_TOOL_DYNAMIC_MAX_EMERGING_FEEDS", "5"))
MODEL_TOOL_DYNAMIC_MAX_FEED_REPLACEMENTS = int(os.getenv("MODEL_TOOL_DYNAMIC_MAX_FEED_REPLACEMENTS", "2"))
MODEL_TOOL_DYNAMIC_MAX_EMERGING_TERMS = int(os.getenv("MODEL_TOOL_DYNAMIC_MAX_EMERGING_TERMS", "12"))
MODEL_TOOL_DYNAMIC_MAX_TERM_REPLACEMENTS = int(os.getenv("MODEL_TOOL_DYNAMIC_MAX_TERM_REPLACEMENTS", "4"))
MODEL_TOOL_LLM_CLASSIFY = _env_enabled("MODEL_TOOL_LLM_CLASSIFY")
MODEL_TOOL_LLM_CLASSIFY_LIMIT = int(os.getenv("MODEL_TOOL_LLM_CLASSIFY_LIMIT", "24"))
