![cover-v5-optimized](./images/GitHub_README.png)

<div align="center">
  <p>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/channel-Telegram-2CA5E0?logo=telegram" alt="Telegram">
    <img src="https://img.shields.io/badge/providers-MiniMax%20%7C%20OpenRouter%20%7C%20Custom-blueviolet" alt="Providers">
    <img src="https://img.shields.io/badge/search-Tavily%20round--robin-orange" alt="Tavily">
  </p>
</div>

> **This is a slimmed-down fork of [nanobot](https://github.com/HKUDS/nanobot) (v0.1.5.post3).**  
> It removes unused channels and providers to keep the codebase minimal and focused.  
> See [What Changed](#-what-changed-from-upstream) for a full diff.

---

🐈 **nanobot** is an open-source, ultra-lightweight AI agent. It keeps the core agent loop small and readable while supporting chat channels, memory, MCP, and practical deployment paths — so you can go from local setup to a long-running personal agent with minimal overhead.

---

## 📦 Install

**From this repo (recommended)**

```bash
git clone https://github.com/PaygamovT/nanobot.git
cd nanobot
pip install -e .
```

**With dev tools (ruff, pytest)**

```bash
pip install -e ".[dev]"
```

> [!NOTE]
> `pip install nanobot-ai` from PyPI will install the **original upstream** version, not this fork.
> Always install from source to get the changes described below.

---

## 🚀 Quick Start

**1. Initialize**

```bash
nanobot onboard
```

**2. Configure** (`~/.nanobot/config.json`)

This fork uses **OpenRouter** as the default provider with `google/gemini-3.1-flash-lite-preview`.  
Set your OpenRouter API key:

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-YOUR_KEY_HERE"
    }
  }
}
```

To use **MiniMax** instead (highest priority in the registry):

```json
{
  "providers": {
    "minimax": {
      "apiKey": "YOUR_MINIMAX_KEY"
    }
  },
  "agents": {
    "defaults": {
      "provider": "minimax",
      "model": "MiniMax-Text-01"
    }
  }
}
```

To override the default model (still routed via OpenRouter):

```json
{
  "agents": {
    "defaults": {
      "provider": "openrouter",
      "model": "google/gemini-3.1-flash-lite-preview"
    }
  }
}
```

**3. Web search with Tavily round-robin keys**

```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "tavily",
        "tavilyApiKeys": [
          "tvly-key-1",
          "tvly-key-2",
          "tvly-key-3"
        ]
      }
    }
  }
}
```

Keys are tried in order. On `401 / 429 / 5xx` the next key is used automatically. Falls back to DuckDuckGo if all keys fail.

**4. Telegram channel**

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_TELEGRAM_USER_ID"]
    }
  }
}
```

**5. Chat**

```bash
nanobot agent
# or send a single message:
nanobot agent -m "hello"
```

---

## 🔊 Voice Transcription

Voice messages from Telegram are transcribed using **OpenRouter + Gemini Flash** (no separate Whisper API needed).

Make sure your OpenRouter key is set in `providers.openrouter.apiKey`. Transcription uses `google/gemini-3.1-flash-lite-preview` by default.

To use OpenAI Whisper instead:

```json
{
  "channels": {
    "transcriptionProvider": "openai"
  },
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-..."
    }
  }
}
```

---

## 🔄 What Changed From Upstream

This fork makes the following targeted changes to the original nanobot v0.1.5.post3:

### Channels — Telegram only

All channel implementations removed **except Telegram**:

| Removed | Kept |
|---|---|
| Discord, Slack, DingTalk, Feishu | ✅ `telegram.py` |
| WeChat, WeCom, WhatsApp, QQ | ✅ `base.py`, `manager.py`, `registry.py` |
| Matrix, MS Teams, Email, WebSocket, MoChat | |

### LLM Providers — 3 only

Provider registry reduced from 25+ entries to 3, in priority order:

| Priority | Provider | Notes |
|---|---|---|
| 1st | **MiniMax** | `MINIMAX_API_KEY` · `https://api.minimax.io/v1` |
| 2nd | **OpenRouter** | `OPENROUTER_API_KEY` · gateway for any model |
| 3rd | **Custom** | Any OpenAI-compatible endpoint |

Removed: Anthropic, Azure OpenAI, AWS Bedrock, Groq, DeepSeek, Gemini (native), Zhipu, DashScope, Moonshot, Mistral, StepFun, Xiaomi MiMo, LongCat, AiHubMix, SiliconFlow, VolcEngine, BytePlus, Ollama, LM Studio, OVMS, vLLM, Qianfan, Codex, Copilot, HuggingFace.

### Default Model

```
Before: anthropic/claude-opus-4-5  (provider: auto)
After:  google/gemini-3.1-flash-lite-preview  (provider: openrouter)
```

### Tavily Round-Robin Search

`WebSearchConfig` now accepts a list of Tavily keys:

```json
{ "tools": { "web": { "search": { "tavilyApiKeys": ["key1", "key2"] } } } }
```

Default search provider changed from `duckduckgo` → `tavily`.

### Voice Transcription

```
Before: Groq Whisper API (whisper-large-v3)
After:  OpenRouter → google/gemini-3.1-flash-lite-preview (multimodal audio)
```

### Dependencies Removed

`anthropic`, `boto3`, `oauth-cli-kit`, `dingtalk-stream`, `lark-oapi`, `slack-sdk`, `slackify-markdown`, `qq-botpy` and optional groups `wecom`, `weixin`, `msteams`, `matrix`, `discord`.

---

## 🏗️ Architecture

<p align="center">
  <img src="images/nanobot_arch.png" alt="nanobot architecture" width="800">
</p>

nanobot stays lightweight by centering everything around a small agent loop: messages come in from Telegram, the LLM decides when tools are needed, and memory or skills are pulled in only as context. The core path is readable and easy to extend.

---

## 📚 Docs

- [AI_PROMPT.md](./AI_PROMPT.md) — Step-by-step guide for an AI agent to reproduce all changes from a fresh clone
- [CHANGELOG.md](./CHANGELOG.md) — Detailed per-file change log
- [SUMMARY.md](./SUMMARY.md) — One-page overview of all changes
- Original upstream docs: [nanobot.wiki](https://nanobot.wiki/docs/latest/getting-started/nanobot-overview)

---

## 🤝 Upstream

This fork is based on [HKUDS/nanobot](https://github.com/HKUDS/nanobot).  
All credit for the original agent core goes to [Xubin Ren](https://github.com/re-bin) and contributors.

<p align="center">
  <em>Thanks for visiting ✨ nanobot!</em>
</p>
