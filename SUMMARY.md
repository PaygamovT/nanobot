# Nanobot Refactoring — Summary
**Date:** 2026-05-02 | **Version:** 0.1.5.post3

---

## What Changed (TL;DR)

| Area | Before | After |
|---|---|---|
| **Channels** | 18 (Discord, Slack, Telegram, QQ, WeChat…) | ✅ Telegram only |
| **LLM Providers** | 25+ (Anthropic, Azure, Bedrock, Groq…) | ✅ MiniMax, OpenRouter, Custom |
| **Default model** | `anthropic/claude-opus-4-5` | ✅ `google/gemini-3.1-flash-lite-preview` |
| **Default provider** | `auto` | ✅ `openrouter` |
| **Web search** | DuckDuckGo, single Tavily key | ✅ Tavily with round-robin multi-key fallback |
| **Voice transcription** | Groq Whisper | ✅ OpenRouter + Gemini Flash |
| **Dependencies** | 40+ packages | ✅ Cleaned (removed 8 dead packages + 5 optional groups) |

---

## Files Changed

```
nanobot/channels/base.py          — transcription provider: groq → openrouter
nanobot/channels/manager.py       — transcription key/base resolvers → OpenRouter
nanobot/providers/__init__.py     — expose only OpenAICompatProvider
nanobot/providers/registry.py     — 3 providers only (MiniMax first)
nanobot/providers/factory.py      — single openai_compat path
nanobot/providers/transcription.py — GroqTranscriptionProvider → OpenRouterTranscriptionProvider
nanobot/providers/openai_compat_provider.py — fixed broken import (lazy imports)
nanobot/config/schema.py          — new model default, slim ProvidersConfig, tavily_api_keys
nanobot/agent/tools/web.py        — Tavily round-robin multi-key fallback
pyproject.toml                    — removed dead dependencies
```

## Files Deleted

```
nanobot/channels/  — dingtalk, discord, email, feishu, matrix,
                     mochat, msteams, qq, slack, websocket,
                     wecom, weixin, whatsapp  (13 files)

nanobot/providers/ — anthropic_provider, azure_openai_provider,
                     bedrock_provider, openai_codex_provider,
                     github_copilot_provider, openai_responses/  (5 files + 1 dir)
```

## Files Created

```
AI_PROMPT.md    — Full agent instructions to reproduce these changes
CHANGELOG.md    — Detailed per-file change log
SUMMARY.md      — This file
```

---

## Key Design Decisions

- **All providers route through `OpenAICompatProvider`** — one backend, less code, no Anthropic/Bedrock SDK deps.
- **MiniMax is first in the registry** — matched before OpenRouter when a model name is ambiguous.
- **Tavily `tavily_api_keys` list** — supports multiple keys; tries each in order, falls back to DuckDuckGo if all fail.
- **Transcription via Gemini Flash** — sends audio as base64 `input_audio` in a chat completion (no separate Whisper endpoint needed).
- **Lazy imports for `openai_responses`** — deleted module, but kept the dead code paths guarded so no runtime errors.
