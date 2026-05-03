# Changelog — Nanobot Refactoring Session
**Date:** 2026-05-02  
**Version:** 0.1.5.post3

---

## Summary of Changes

### 1. Channels — Deleted 13 files, kept Telegram only

**Deleted:**
- `nanobot/channels/dingtalk.py`
- `nanobot/channels/discord.py`
- `nanobot/channels/email.py`
- `nanobot/channels/feishu.py`
- `nanobot/channels/matrix.py`
- `nanobot/channels/mochat.py`
- `nanobot/channels/msteams.py`
- `nanobot/channels/qq.py`
- `nanobot/channels/slack.py`
- `nanobot/channels/websocket.py`
- `nanobot/channels/wecom.py`
- `nanobot/channels/weixin.py`
- `nanobot/channels/whatsapp.py`

**Kept:** `__init__.py`, `base.py`, `manager.py`, `registry.py`, `telegram.py`

---

### 2. Providers — Deleted 5 files + `openai_responses/` dir

**Deleted:**
- `nanobot/providers/anthropic_provider.py`
- `nanobot/providers/azure_openai_provider.py`
- `nanobot/providers/bedrock_provider.py`
- `nanobot/providers/openai_codex_provider.py`
- `nanobot/providers/github_copilot_provider.py`
- `nanobot/providers/openai_responses/` ← entire directory

**Kept:** `__init__.py`, `base.py`, `factory.py`, `openai_compat_provider.py`, `registry.py`, `transcription.py`

---

### 3. `nanobot/providers/__init__.py` — Rewritten

- Removed exports for: `AnthropicProvider`, `OpenAICodexProvider`, `GitHubCopilotProvider`, `AzureOpenAIProvider`, `BedrockProvider`
- Now only exposes `OpenAICompatProvider` (lazy import)

---

### 4. `nanobot/providers/registry.py` — Rewritten

- Removed 22+ provider specs (Anthropic, Azure, Bedrock, Groq, DeepSeek, Gemini, Zhipu, DashScope, Moonshot, Mistral, StepFun, Xiaomi, LongCat, AiHubMix, SiliconFlow, VolcEngine, BytePlus, Ollama, LM Studio, OVMS, vLLM, Qianfan, Codex, Copilot, Huggingface)
- **Now contains 3 providers only, in priority order:**
  1. `minimax` — MiniMax (highest priority, matched first)
  2. `openrouter` — OpenRouter gateway (fallback)
  3. `custom` — Direct OpenAI-compatible endpoint

---

### 5. `nanobot/providers/factory.py` — Rewritten

- Removed all backend branches: `azure_openai`, `openai_codex`, `github_copilot`, `anthropic`, `bedrock`
- Now uses a single `OpenAICompatProvider` path for all providers
- Removed `region` and `profile` from `provider_signature()` (were Bedrock-only)

---

### 6. `nanobot/config/schema.py` — Edited

| Field | Before | After |
|---|---|---|
| `AgentDefaults.model` | `anthropic/claude-opus-4-5` | `google/gemini-3.1-flash-lite-preview` |
| `AgentDefaults.provider` | `"auto"` | `"openrouter"` |
| `ChannelsConfig.transcription_provider` | `"groq"` | `"openrouter"` |
| `WebSearchConfig.provider` | `"duckduckgo"` | `"tavily"` |
| `WebSearchConfig.api_key` | single key only | single key (legacy) |

**Added:**
- `WebSearchConfig.tavily_api_keys: list[str]` — multiple Tavily keys for round-robin fallback

**Removed:**
- `BedrockProviderConfig` class (region, profile fields)
- `ProvidersConfig` reduced from 25+ fields to 3: `minimax`, `openrouter`, `custom`

---

### 7. `nanobot/channels/manager.py` — Edited

- `_resolve_transcription_key()`: was reading `openai.api_key` or `groq.api_key` → now reads `openrouter.api_key`
- `_resolve_transcription_base()`: was reading from Groq/OpenAI → now reads `openrouter.api_base` (defaults to `https://openrouter.ai/api/v1`)

---

### 8. `nanobot/channels/base.py` — Edited

- `BaseChannel.transcription_provider` default: `"groq"` → `"openrouter"`
- `transcribe_audio()`: `else` branch now imports and uses `OpenRouterTranscriptionProvider` instead of `GroqTranscriptionProvider`

---

### 9. `nanobot/providers/transcription.py` — Rewritten

- **Removed:** `GroqTranscriptionProvider` (was using `whisper-large-v3` via Groq API)
- **Added:** `OpenRouterTranscriptionProvider`
  - Model: `google/gemini-3.1-flash-lite-preview` via OpenRouter
  - Method: base64-encodes the audio file, sends as `input_audio` content part in a `/chat/completions` multimodal request
  - Detects MIME type from extension (ogg, mp3, mp4, wav, webm, flac, aac, m4a)
  - System prompt instructs verbatim transcription with `temperature: 0.0`
  - Timeout: 120s
- **Kept:** `OpenAITranscriptionProvider` (used when `transcription_provider: openai`)

---

### 10. `nanobot/agent/tools/web.py` — Edited

**`_effective_provider()`:**
- Tavily check now also inspects `config.tavily_api_keys` list (not just single `api_key`)

**`_search_tavily()` — replaced with round-robin implementation:**
- Builds an ordered key list: `config.tavily_api_keys` → `config.api_key` → `TAVILY_API_KEY` env var (deduped)
- Tries each key in sequence
- On `401 / 403 / 429 / 5xx` → moves to next key
- On non-auth 4xx → returns error immediately (not retryable)
- If all keys exhausted → falls back to DuckDuckGo

---

### 11. `nanobot/providers/openai_compat_provider.py` — Edited

**Problem:** Had a top-level import of the deleted `openai_responses` subpackage → caused `ModuleNotFoundError` at startup.

**Fix:** Removed the top-level import block. Added lazy imports at the three call sites:
- `_build_responses_body()` → `from nanobot.providers.openai_responses import convert_messages, convert_tools`
- `chat()` → `from nanobot.providers.openai_responses import parse_response_output`
- `chat_stream()` → `from nanobot.providers.openai_responses import consume_sdk_stream`

These paths are unreachable (guarded by `_should_use_responses_api()` which returns `False` for minimax/openrouter/custom) so the lazy imports never actually execute.

---

### 12. `pyproject.toml` — Edited

**Removed from `dependencies`:**
- `anthropic>=0.45.0,<1.0.0`
- `oauth-cli-kit>=0.1.3,<1.0.0`
- `dingtalk-stream>=0.24.0,<1.0.0`
- `lark-oapi>=1.5.0,<2.0.0`
- `slack-sdk>=3.39.0,<4.0.0`
- `slackify-markdown>=0.2.0,<1.0.0`
- `qq-botpy>=1.2.0,<2.0.0`
- `boto3>=1.43.0`

**Removed optional dependency groups:**
- `wecom`
- `weixin`
- `msteams`
- `matrix`
- `discord`

---

### 13. `AI_PROMPT.md` — Created

Full step-by-step prompt and context document for an AI coding agent to reproduce all the above changes from scratch on a fresh clone.

---

## Validation

```bash
pip install -e ".[dev]"   # ✅ Success
nanobot agent -m hi        # ✅ Responds
nanobot agent -m "what model are you"   # ✅ Reports MiniMax or Gemini Flash
```
