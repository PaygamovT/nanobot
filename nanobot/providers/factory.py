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

    # All remaining providers use the openai_compat backend
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
    """Return the config fields that affect the primary LLM provider."""
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
