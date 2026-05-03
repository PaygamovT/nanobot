"""Voice transcription providers (OpenRouter Gemini and OpenAI Whisper)."""

import base64
import mimetypes
import os
from pathlib import Path

import httpx
from loguru import logger


class OpenAITranscriptionProvider:
    """Voice transcription provider using OpenAI's Whisper API."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        language: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_url = (
            api_base
            or os.environ.get("OPENAI_TRANSCRIPTION_BASE_URL")
            or "https://api.openai.com/v1/audio/transcriptions"
        )
        self.language = language or None

    async def transcribe(self, file_path: str | Path) -> str:
        if not self.api_key:
            logger.warning("OpenAI API key not configured for transcription")
            return ""
        path = Path(file_path)
        if not path.exists():
            logger.error("Audio file not found: {}", file_path)
            return ""
        try:
            async with httpx.AsyncClient() as client:
                with open(path, "rb") as f:
                    files = {"file": (path.name, f), "model": (None, "whisper-1")}
                    if self.language:
                        files["language"] = (None, self.language)
                    headers = {"Authorization": f"Bearer {self.api_key}"}
                    response = await client.post(
                        self.api_url, headers=headers, files=files, timeout=60.0,
                    )
                    response.raise_for_status()
                    return response.json().get("text", "")
        except Exception as e:
            logger.error("OpenAI transcription error: {}", e)
            return ""


class OpenRouterTranscriptionProvider:
    """Voice transcription provider using OpenRouter with Gemini Flash.

    Sends audio as a base64-encoded data URL in a multimodal chat completion
    request to OpenRouter, using google/gemini-3.1-flash-lite-preview as the
    model. The model is instructed to transcribe the audio content verbatim.
    """

    # Audio MIME types the provider can handle
    _SUPPORTED_MIMES = frozenset({
        "audio/ogg", "audio/mpeg", "audio/mp3", "audio/mp4",
        "audio/wav", "audio/webm", "audio/flac", "audio/aac",
        "audio/x-wav", "audio/x-m4a",
    })

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
        """Transcribe an audio file using OpenRouter Gemini Flash.

        The audio is base64-encoded and sent as an input_audio content part
        in a chat completion request. Gemini processes the audio natively
        and returns the transcription.

        Args:
            file_path: Path to the audio file.

        Returns:
            Transcribed text, or empty string on failure.
        """
        if not self.api_key:
            logger.warning("OpenRouter API key not configured for transcription")
            return ""

        path = Path(file_path)
        if not path.exists():
            logger.error("Audio file not found: {}", file_path)
            return ""

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            # Fallback based on common voice message extensions
            ext_map = {
                ".ogg": "audio/ogg", ".oga": "audio/ogg",
                ".mp3": "audio/mpeg", ".mp4": "audio/mp4",
                ".m4a": "audio/x-m4a", ".wav": "audio/wav",
                ".webm": "audio/webm", ".flac": "audio/flac",
                ".aac": "audio/aac",
            }
            mime_type = ext_map.get(path.suffix.lower(), "audio/ogg")

        try:
            # Read and base64-encode the audio
            audio_data = path.read_bytes()
            audio_b64 = base64.standard_b64encode(audio_data).decode("ascii")

            # Build the transcription prompt
            system_prompt = (
                "You are a precise audio transcription assistant. "
                "Transcribe the audio exactly as spoken, word for word. "
                "Output ONLY the transcribed text with no commentary, "
                "no timestamps, and no formatting."
            )
            if self.language:
                system_prompt += f" The audio is in {self.language}."

            # Build multimodal request with input_audio
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_b64,
                                    "format": mime_type.split("/")[-1],
                                },
                            },
                            {
                                "type": "text",
                                "text": "Transcribe this audio.",
                            },
                        ],
                    },
                ],
                "max_tokens": 4096,
                "temperature": 0.0,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/HKUDS/nanobot",
                "X-Title": "nanobot-transcription",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120.0,
                )
                response.raise_for_status()

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                logger.warning("OpenRouter transcription returned no choices")
                return ""

            content = choices[0].get("message", {}).get("content", "")
            return content.strip()

        except Exception as e:
            logger.error("OpenRouter transcription error: {}", e)
            return ""
