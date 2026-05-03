# AI Coding Agent Prompt — Nanobot Refactoring

## Project

**Repo:** `nanobot-main` (nanobot-ai v0.1.5.post3)
**Language:** Python 3.11+, Pydantic v2, asyncio, OpenAI SDK

---

## Objective

Slim down the Nanobot framework to a minimal, focused configuration:

1. **Channels** — Keep **Telegram only**. Delete all other channel implementations.
2. **LLM Providers** — Keep **MiniMax** (highest priority), **OpenRouter**, and **Custom** only. Delete all other provider backends.
3. **Default model** — Set to `google/gemini-3.1-flash-lite-preview` routed via OpenRouter.
4. **Tavily web search** — Add a `tavily_api_keys` list field to support round-robin multi-key fallback.
5. **Voice transcription** — Route through OpenRouter instead of Groq/OpenAI.
6. **Fix broken import** — The deleted `openai_responses` subpackage is imported in `openai_compat_provider.py`; make those imports lazy.
7. **Install** — Run `pip install -e ".[dev]"` after all changes.

---

## Step-by-Step Instructions

### Step 1 — Delete channel files

Delete every file in `nanobot/channels/` **except**:
- `__init__.py`
- `base.py`
- `manager.py`
- `registry.py`
- `telegram.py`

Files to delete:
```
nanobot/channels/dingtalk.py
nanobot/channels/discord.py
nanobot/channels/email.py
nanobot/channels/feishu.py
nanobot/channels/matrix.py
nanobot/channels/mochat.py
nanobot/channels/msteams.py
nanobot/channels/qq.py
nanobot/channels/slack.py
nanobot/channels/websocket.py
nanobot/channels/wecom.py
nanobot/channels/weixin.py
nanobot/channels/whatsapp.py
```

---

### Step 2 — Delete provider files

Delete every file in `nanobot/providers/` **except**:
- `__init__.py`
- `base.py`
- `factory.py`
- `openai_compat_provider.py`
- `registry.py`
- `transcription.py`

Files to delete:
```
nanobot/providers/anthropic_provider.py
nanobot/providers/azure_openai_provider.py
nanobot/providers/bedrock_provider.py
nanobot/providers/openai_codex_provider.py
nanobot/providers/github_copilot_provider.py
nanobot/providers/openai_responses/   ← entire directory
```

---

### Step 3 — Fix `nanobot/providers/__init__.py`

Replace the entire file with:

```python
"""LLM provider abstraction module."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from nanobot.providers.base import LLMProvider, LLMResponse

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "OpenAICompatProvider",
]

_LAZY_IMPORTS = {
    "OpenAICompatProvider": ".openai_compat_provider",
}

if TYPE_CHECKING:
    from nanobot.providers.openai_compat_provider import OpenAICompatProvider


def __getattr__(name: str):
    """Lazily expose provider implementations without importing all backends up front."""
    module_name = _LAZY_IMPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
```

---

### Step 4 — Rewrite `nanobot/providers/registry.py`

Replace the entire file. Keep only 3 providers in this order (MiniMax first = highest priority):

```python
"""
Provider Registry — MiniMax (priority), OpenRouter (gateway), Custom.
Order = match priority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic.alias_generators import to_snake


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    keywords: tuple[str, ...]
    env_key: str
    display_name: str = ""
    backend: str = "openai_compat"
    env_extras: tuple[tuple[str, str], ...] = ()
    is_gateway: bool = False
    is_local: bool = False
    detect_by_key_prefix: str = ""
    detect_by_base_keyword: str = ""
    default_api_base: str = ""
    strip_model_prefix: bool = False
    supports_max_completion_tokens: bool = False
    model_overrides: tuple[tuple[str, dict[str, Any]], ...] = ()
    is_oauth: bool = False
    is_direct: bool = False
    supports_prompt_caching: bool = False
    thinking_style: str = ""
    reasoning_as_content: bool = False

    @property
    def label(self) -> str:
        return self.display_name or self.name.title()


PROVIDERS: tuple[ProviderSpec, ...] = (
    # MiniMax — highest priority
    ProviderSpec(
        name="minimax",
        keywords=("minimax",),
        env_key="MINIMAX_API_KEY",
        display_name="MiniMax",
        backend="openai_compat",
        default_api_base="https://api.minimax.io/v1",
        thinking_style="reasoning_split",
    ),
    # OpenRouter — gateway fallback
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        backend="openai_compat",
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
        detect_by_base_keyword="openrouter",
        default_api_base="https://openrouter.ai/api/v1",
        supports_prompt_caching=True,
    ),
    # Custom — direct OpenAI-compatible endpoint
    ProviderSpec(
        name="custom",
        keywords=(),
        env_key="",
        display_name="Custom",
        backend="openai_compat",
        is_direct=True,
    ),
)


def find_by_name(name: str) -> ProviderSpec | None:
    normalized = to_snake(name.replace("-", "_"))
    for spec in PROVIDERS:
        if spec.name == normalized:
            return spec
    return None
```

---

### Step 5 — Rewrite `nanobot/providers/factory.py`

Replace the entire file — remove all backends except `openai_compat`:

```python
"""Create LLM providers from config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nanobot.config.schema import Config
from nanobot.providers.base import GenerationSettings, LLMProvider
from nanobot.providers.registry import find_by_name


@dataclass(frozen=True)
class ProviderSnapshot:
    provider: LLMProvider
    model: str
    context_window_tokens: int
    signature: tuple[object, ...]


def make_provider(config: Config) -> LLMProvider:
    """Create the LLM provider implied by config."""
    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)
    spec = find_by_name(provider_name) if provider_name else None

    from nanobot.providers.openai_compat_provider import OpenAICompatProvider

    needs_key = not (p and p.api_key)
    exempt = spec and (spec.is_oauth or spec.is_local or spec.is_direct)
    if needs_key and not exempt:
        raise ValueError(f"No API key configured for provider '{provider_name}'.")

    provider = OpenAICompatProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        spec=spec,
        extra_body=p.extra_body if p else None,
    )

    defaults = config.agents.defaults
    provider.generation = GenerationSettings(
        temperature=defaults.temperature,
        max_tokens=defaults.max_tokens,
        reasoning_effort=defaults.reasoning_effort,
    )
    return provider


def provider_signature(config: Config) -> tuple[object, ...]:
    model = config.agents.defaults.model
    defaults = config.agents.defaults
    p = config.get_provider(model)
    return (
        model,
        defaults.provider,
        config.get_provider_name(model),
        config.get_api_key(model),
        config.get_api_base(model),
        p.extra_headers if p else None,
        p.extra_body if p else None,
        defaults.max_tokens,
        defaults.temperature,
        defaults.reasoning_effort,
        defaults.context_window_tokens,
    )


def build_provider_snapshot(config: Config) -> ProviderSnapshot:
    return ProviderSnapshot(
        provider=make_provider(config),
        model=config.agents.defaults.model,
        context_window_tokens=config.agents.defaults.context_window_tokens,
        signature=provider_signature(config),
    )


def load_provider_snapshot(config_path: Path | None = None) -> ProviderSnapshot:
    from nanobot.config.loader import load_config, resolve_config_env_vars
    return build_provider_snapshot(resolve_config_env_vars(load_config(config_path)))
```

---

### Step 6 — Edit `nanobot/config/schema.py`

Make the following targeted changes:

#### 6a. Change default model and provider in `AgentDefaults`

```python
# BEFORE
model: str = "anthropic/claude-opus-4-5"
provider: str = (
    "auto"  # Provider name (e.g. "anthropic", "openrouter") or "auto" for auto-detection
)

# AFTER
model: str = "google/gemini-3.1-flash-lite-preview"
provider: str = (
    "openrouter"  # Provider name (e.g. "minimax", "openrouter") or "auto" for auto-detection
)
```

#### 6b. Replace `BedrockProviderConfig` and `ProvidersConfig`

Remove the `BedrockProviderConfig` class entirely. Replace `ProvidersConfig` with:

```python
class ProvidersConfig(Base):
    """Configuration for LLM providers.

    Only minimax, openrouter, and custom are supported.
    MiniMax is prioritized first in the provider registry.
    """

    minimax: ProviderConfig = Field(default_factory=ProviderConfig)   # MiniMax (prioritized)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig) # OpenRouter gateway
    custom: ProviderConfig = Field(default_factory=ProviderConfig)     # Any OpenAI-compatible endpoint
```

#### 6c. Update `ChannelsConfig.transcription_provider` default

```python
# BEFORE
transcription_provider: str = "groq"  # Voice transcription backend: "groq" or "openai"

# AFTER
transcription_provider: str = "openrouter"  # Voice transcription backend (routes through OpenRouter)
```

#### 6d. Update `WebSearchConfig` — add `tavily_api_keys` list and change default provider

```python
# BEFORE
class WebSearchConfig(Base):
    provider: str = "duckduckgo"
    api_key: str = ""
    base_url: str = ""
    max_results: int = 5
    timeout: int = 30

# AFTER
class WebSearchConfig(Base):
    provider: str = "tavily"  # tavily (with round-robin fallback), duckduckgo, brave, searxng, jina, kagi, olostep
    api_key: str = ""  # Single API key (legacy). Prefer tavily_api_keys for round-robin.
    tavily_api_keys: list[str] = Field(default_factory=list)  # Multiple Tavily API keys for round-robin fallback
    base_url: str = ""
    max_results: int = 5
    timeout: int = 30
```

---

### Step 7 — Edit `nanobot/channels/manager.py`

Replace both transcription resolver methods to use `openrouter` instead of `groq`/`openai`:

```python
def _resolve_transcription_key(self, provider: str) -> str:
    """Pick the API key for the configured transcription provider.

    With the slimmed provider set, transcription routes through OpenRouter.
    """
    try:
        return self.config.providers.openrouter.api_key or ""
    except AttributeError:
        return ""

def _resolve_transcription_base(self, provider: str) -> str:
    """Pick the API base URL for the configured transcription provider.

    With the slimmed provider set, transcription routes through OpenRouter.
    """
    try:
        return self.config.providers.openrouter.api_base or "https://openrouter.ai/api/v1"
    except AttributeError:
        return ""
```

### Step 7b — Rewrite `nanobot/providers/transcription.py`

Replace `GroqTranscriptionProvider` with `OpenRouterTranscriptionProvider` that uses
`google/gemini-3.1-flash-lite-preview` for multimodal audio transcription:

```python
class OpenRouterTranscriptionProvider:
    """Voice transcription via OpenRouter with Gemini Flash.

    Sends audio as base64-encoded data in a multimodal chat completion
    request. The model transcribes audio natively.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        language: str | None = None,
        model: str = "google/gemini-3.1-flash-lite-preview",
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.api_base = (
            api_base
            or os.environ.get("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.language = language or None
        self.model = model

    async def transcribe(self, file_path: str | Path) -> str:
        # 1. Read audio file, base64-encode it
        # 2. Detect MIME type (audio/ogg, audio/mpeg, etc.)
        # 3. Send as input_audio content part in chat completion:
        #    POST {api_base}/chat/completions
        #    model: google/gemini-3.1-flash-lite-preview
        #    messages: [system prompt for verbatim transcription, user with audio]
        #    temperature: 0.0
        # 4. Return choices[0].message.content.strip()
```

Keep `OpenAITranscriptionProvider` as-is (it's the fallback for `transcription_provider: openai`).

### Step 7c — Update `nanobot/channels/base.py`

In `BaseChannel`:

```python
# BEFORE
transcription_provider: str = "groq"

# AFTER
transcription_provider: str = "openrouter"
```

In `transcribe_audio()`:

```python
# BEFORE (the else branch)
from nanobot.providers.transcription import GroqTranscriptionProvider
provider = GroqTranscriptionProvider(...)

# AFTER
from nanobot.providers.transcription import OpenRouterTranscriptionProvider
provider = OpenRouterTranscriptionProvider(...)
```

---

### Step 8 — Edit `nanobot/agent/tools/web.py`

#### 8a. Update `_effective_provider` to check `tavily_api_keys`

Find the Tavily block in `_effective_provider()` and replace it:

```python
# BEFORE
if provider == "tavily":
    api_key = self.config.api_key or os.environ.get("TAVILY_API_KEY", "")
    return "tavily" if api_key else "duckduckgo"

# AFTER
if provider == "tavily":
    has_keys = (
        self.config.api_key
        or os.environ.get("TAVILY_API_KEY", "")
        or (hasattr(self.config, "tavily_api_keys") and self.config.tavily_api_keys)
    )
    return "tavily" if has_keys else "duckduckgo"
```

#### 8b. Replace `_search_tavily` with round-robin implementation

```python
async def _search_tavily(self, query: str, n: int) -> str:
    """Search via Tavily with round-robin API key fallback.

    Tries keys from config.tavily_api_keys in order, then falls back to
    config.api_key and the TAVILY_API_KEY env var. On auth/rate-limit/server
    errors the next key is attempted.
    """
    # Build ordered list of API keys to try (round-robin)
    keys: list[str] = []
    if hasattr(self.config, "tavily_api_keys") and self.config.tavily_api_keys:
        keys.extend(k for k in self.config.tavily_api_keys if k)
    # Append single api_key and env var as fallbacks (dedup)
    for fallback in (self.config.api_key, os.environ.get("TAVILY_API_KEY", "")):
        if fallback and fallback not in keys:
            keys.append(fallback)

    if not keys:
        logger.warning("No Tavily API keys configured, falling back to DuckDuckGo")
        return await self._search_duckduckgo(query, n)

    last_error: Exception | None = None
    for idx, api_key in enumerate(keys):
        try:
            async with httpx.AsyncClient(proxy=self.proxy) as client:
                r = await client.post(
                    "https://api.tavily.com/search",
                    headers={"Authorization": f"Bearer {api_key}", "User-Agent": self.user_agent},
                    json={"query": query, "max_results": n},
                    timeout=15.0,
                )
                r.raise_for_status()
            logger.debug("Tavily search succeeded with key #{}", idx + 1)
            return _format_results(query, r.json().get("results", []), n)
        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code
            if status in (401, 403, 429) or status >= 500:
                logger.warning(
                    "Tavily key #{} failed (HTTP {}), trying next key...",
                    idx + 1, status,
                )
                continue
            return f"Error: Tavily search failed (HTTP {status}): {e}"
        except Exception as e:
            last_error = e
            logger.warning("Tavily key #{} error: {}, trying next key...", idx + 1, e)
            continue

    logger.warning(
        "All {} Tavily keys exhausted (last error: {}), falling back to DuckDuckGo",
        len(keys), last_error,
    )
    return await self._search_duckduckgo(query, n)
```

---

### Step 9 — Fix `nanobot/providers/openai_compat_provider.py`

The file has a top-level import of the deleted `openai_responses` package:

```python
# REMOVE this block entirely (lines ~35-40):
from nanobot.providers.openai_responses import (
    consume_sdk_stream,
    convert_messages,
    convert_tools,
    parse_response_output,
)
```

Then add **lazy imports** at each call site:

- In `_build_responses_body`, before `convert_messages(...)`:
  ```python
  from nanobot.providers.openai_responses import convert_messages, convert_tools
  ```

- In `chat()`, before `parse_response_output(...)`:
  ```python
  from nanobot.providers.openai_responses import parse_response_output
  ```

- In `chat_stream()`, before `consume_sdk_stream(...)`:
  ```python
  from nanobot.providers.openai_responses import consume_sdk_stream
  ```

> **Why lazy?** `_should_use_responses_api()` always returns `False` for minimax/openrouter/custom (line ~645 checks for `"openai"` or `"github_copilot"` spec names only), so these code paths are unreachable. Making the imports lazy avoids the `ModuleNotFoundError` at startup.

---

### Step 10 — Edit `pyproject.toml`

#### Remove from `dependencies`:
```
"anthropic>=0.45.0,<1.0.0",
"oauth-cli-kit>=0.1.3,<1.0.0",
"dingtalk-stream>=0.24.0,<1.0.0",
"lark-oapi>=1.5.0,<2.0.0",
"slack-sdk>=3.39.0,<4.0.0",
"slackify-markdown>=0.2.0,<1.0.0",
"qq-botpy>=1.2.0,<2.0.0",
"boto3>=1.43.0",
```

#### Remove from `[project.optional-dependencies]`:
```toml
# Remove these entire groups:
wecom = [...]
weixin = [...]
msteams = [...]
matrix = [...]
discord = [...]
```

---

### Step 11 — Install

```bash
pip install -e ".[dev]"
```

---

## Validation

```bash
# Should start, respond, and report the active model
nanobot agent -m hi
nanobot agent -m "what model are you"
```

Expected: the agent starts successfully, uses MiniMax by default (or OpenRouter with `google/gemini-3.1-flash-lite-preview`), and responds without errors.

---

## Final State Summary

| Component | Before | After |
|---|---|---|
| Channels | 16 (Telegram, Discord, Slack, …) | 1 (Telegram only) |
| Provider files | 11 | 3 (`openai_compat`, `base`, `factory`) |
| Provider registry | 25+ providers | 3 (MiniMax → OpenRouter → Custom) |
| Default model | `anthropic/claude-opus-4-5` | `google/gemini-3.1-flash-lite-preview` |
| Default provider | `auto` | `openrouter` |
| Web search | DuckDuckGo default, single Tavily key | Tavily default, `tavily_api_keys` list with round-robin |
| Transcription | Groq / OpenAI | OpenRouter (google/gemini-3.1-flash-lite-preview) |

## Config Example (`~/.nanobot/config.yaml`)

```yaml
agents:
  defaults:
    model: google/gemini-3.1-flash-lite-preview
    provider: openrouter

providers:
  minimax:
    api_key: "YOUR_MINIMAX_API_KEY"
  openrouter:
    api_key: "sk-or-YOUR_OPENROUTER_KEY"
  custom:
    api_key: ""
    api_base: ""

tools:
  web:
    search:
      provider: tavily
      tavily_api_keys:
        - "tvly-key-1"
        - "tvly-key-2"
        - "tvly-key-3"

channels:
  telegram:
    enabled: true
    token: "YOUR_TELEGRAM_BOT_TOKEN"
    allow_from: ["*"]
```
