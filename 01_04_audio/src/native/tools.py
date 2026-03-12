# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions and handlers for audio processing.

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      native/tools.js

"""

import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from .gemini import (
    TTS_VOICES,
    upload_audio_file,
    transcribe_audio,
    analyze_audio,
    generate_speech,
    generate_multi_speaker_speech,
)
from ..helpers.logger import log

PROJECT_ROOT = Path(__file__).parent.parent.parent

# File size threshold for upload vs inline (20MB)
INLINE_SIZE_LIMIT = 20 * 1024 * 1024

# MIME type mapping
MIME_TYPES = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".aiff": "audio/aiff",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
}


def get_audio_mime_type(filepath: str) -> str:
    """Get MIME type for audio file."""
    ext = Path(filepath).suffix.lower()
    return MIME_TYPES.get(ext, "audio/mpeg")


def is_youtube_url(input_str: str) -> bool:
    """Check if input is a YouTube URL."""
    return "youtube.com/watch" in input_str or "youtu.be/" in input_str


async def load_audio(audio_path: str) -> dict:
    """
    Load audio file and prepare for Gemini.

    Uses upload API for large files (>20MB), inline for small ones.
    Supports YouTube URLs directly.
    """
    # Handle YouTube URLs
    if is_youtube_url(audio_path):
        log.info("YouTube URL detected")
        return {"fileUri": audio_path, "mimeType": "video/mp4"}

    full_path = PROJECT_ROOT / audio_path
    buffer = full_path.read_bytes()
    mime_type = get_audio_mime_type(audio_path)
    display_name = audio_path.split("/")[-1]

    if len(buffer) > INLINE_SIZE_LIMIT:
        # Upload large files
        log.info("Audio file > 20MB, using upload API...")
        uploaded = await upload_audio_file(buffer, mime_type, display_name)
        return {"fileUri": uploaded["fileUri"], "mimeType": mime_type}
    else:
        # Use inline for small files
        return {
            "audioBase64": base64.b64encode(buffer).decode("utf-8"),
            "mimeType": mime_type,
        }


def ensure_dir(directory: Path) -> None:
    """Ensure directory exists."""
    directory.mkdir(parents=True, exist_ok=True)


# Native tool definitions in OpenAI function format
native_tools = [
    {
        "type": "function",
        "name": "transcribe_audio",
        "description": "Transcribe audio to text with timestamps and speaker detection. Supports local files (MP3, WAV, AIFF, AAC, OGG, FLAC) and YouTube URLs. Can detect speakers, emotions, and translate to other languages.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to audio file relative to project root (e.g., workspace/input/recording.mp3) OR a YouTube URL",
                },
                "include_timestamps": {
                    "type": "boolean",
                    "description": "Include timestamps for each segment. Default: true",
                },
                "detect_speakers": {
                    "type": "boolean",
                    "description": "Identify and label different speakers. Default: true",
                },
                "detect_emotions": {
                    "type": "boolean",
                    "description": "Detect speaker emotions. Default: false",
                },
                "translate_to": {
                    "type": "string",
                    "description": "Target language for translation. If not provided, keeps original language.",
                },
                "output_name": {
                    "type": "string",
                    "description": "Optional base name for saving transcription JSON to workspace/output/",
                },
            },
            "required": ["audio_path"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "analyze_audio",
        "description": "Analyze audio content - identify sounds, music characteristics, speech patterns. Supports local files and YouTube URLs.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to audio file relative to project root OR a YouTube URL",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["general", "music", "speech", "sounds"],
                    "description": "Type of analysis. Default: general",
                },
                "custom_prompt": {
                    "type": "string",
                    "description": "Optional custom analysis prompt",
                },
                "output_name": {
                    "type": "string",
                    "description": "Optional base name for saving analysis JSON",
                },
            },
            "required": ["audio_path"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "query_audio",
        "description": "Ask any question about audio content. Supports local files and YouTube URLs.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to audio file or YouTube URL",
                },
                "question": {
                    "type": "string",
                    "description": "Question or prompt about the audio content",
                },
            },
            "required": ["audio_path", "question"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "generate_audio",
        "description": f"""Generate speech audio from text using Gemini TTS. Supports single and multi-speaker generation.

Available voices: {', '.join(f'{name} ({style})' for name, style in TTS_VOICES.items())}

For style control, include directions: "Say cheerfully: Hello!" or "In a whisper: The secret..."
For multi-speaker, format: "Speaker1: Hello! Speaker2: Hi there!\"""",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech. Include style directions. For multi-speaker, use 'SpeakerName: dialogue' format.",
                },
                "voice": {
                    "type": "string",
                    "description": "Voice name for single-speaker. Default: Kore",
                },
                "speakers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {
                                "type": "string",
                                "description": "Speaker name as used in the text",
                            },
                            "voice": {
                                "type": "string",
                                "description": "Voice name for this speaker",
                            },
                        },
                        "required": ["speaker", "voice"],
                    },
                    "description": "For multi-speaker: array of {speaker, voice} mappings. Max 2 speakers.",
                },
                "output_name": {
                    "type": "string",
                    "description": "Base name for output WAV file",
                },
            },
            "required": ["text", "output_name"],
            "additionalProperties": False,
        },
        "strict": False,
    },
]


async def transcribe_audio_handler(
    audio_path: str,
    include_timestamps: bool = True,
    detect_speakers: bool = True,
    detect_emotions: bool = False,
    translate_to: Optional[str] = None,
    output_name: Optional[str] = None,
) -> dict:
    """Handle transcribe_audio tool call."""
    log.tool(
        "transcribe_audio",
        {
            "audio_path": audio_path,
            "timestamps": include_timestamps,
            "speakers": detect_speakers,
            "emotions": detect_emotions,
            "translate": translate_to or "no",
        },
    )

    try:
        audio = await load_audio(audio_path)

        result = await transcribe_audio(
            file_uri=audio.get("fileUri"),
            audio_base64=audio.get("audioBase64"),
            mime_type=audio["mimeType"],
            include_timestamps=include_timestamps,
            detect_speakers=detect_speakers,
            detect_emotions=detect_emotions,
            target_language=translate_to,
        )

        # Save to file if output_name provided
        if output_name:
            output_dir = PROJECT_ROOT / "workspace/output"
            ensure_dir(output_dir)
            timestamp = int(datetime.now().timestamp() * 1000)
            output_path = output_dir / f"{output_name}_{timestamp}.json"
            output_path.write_text(json.dumps(result, indent=2))
            log.success(f"Transcription saved: workspace/output/{output_name}_{timestamp}.json")

            return {
                "success": True,
                "audio_path": audio_path,
                "output_path": f"workspace/output/{output_name}_{timestamp}.json",
                "transcription": result,
            }

        log.success(f"Transcribed: {len(result.get('segments', []))} segments")

        return {
            "success": True,
            "audio_path": audio_path,
            "transcription": result,
        }

    except Exception as e:
        log.error("transcribe_audio", str(e))
        return {"success": False, "error": str(e)}


async def analyze_audio_handler(
    audio_path: str,
    analysis_type: str = "general",
    custom_prompt: Optional[str] = None,
    output_name: Optional[str] = None,
) -> dict:
    """Handle analyze_audio tool call."""
    log.tool("analyze_audio", {"audio_path": audio_path, "analysis_type": analysis_type})

    try:
        audio = await load_audio(audio_path)

        result = await analyze_audio(
            file_uri=audio.get("fileUri"),
            audio_base64=audio.get("audioBase64"),
            mime_type=audio["mimeType"],
            analysis_type=analysis_type,
            custom_prompt=custom_prompt,
        )

        # Save to file if output_name provided
        if output_name:
            output_dir = PROJECT_ROOT / "workspace/output"
            ensure_dir(output_dir)
            timestamp = int(datetime.now().timestamp() * 1000)
            output_path = output_dir / f"{output_name}_{timestamp}.json"
            output_path.write_text(json.dumps(result, indent=2))
            log.success(f"Analysis saved: workspace/output/{output_name}_{timestamp}.json")

            return {
                "success": True,
                "audio_path": audio_path,
                "output_path": f"workspace/output/{output_name}_{timestamp}.json",
                "analysis": result,
            }

        log.success(f"Analyzed audio ({analysis_type})")

        return {
            "success": True,
            "audio_path": audio_path,
            "analysis": result,
        }

    except Exception as e:
        log.error("analyze_audio", str(e))
        return {"success": False, "error": str(e)}


async def query_audio_handler(audio_path: str, question: str) -> dict:
    """Handle query_audio tool call."""
    log.tool("query_audio", {"audio_path": audio_path, "question": question[:50]})

    try:
        audio = await load_audio(audio_path)

        result = await analyze_audio(
            file_uri=audio.get("fileUri"),
            audio_base64=audio.get("audioBase64"),
            mime_type=audio["mimeType"],
            analysis_type="general",
            custom_prompt=question,
        )

        log.success("Query answered")

        return {
            "success": True,
            "audio_path": audio_path,
            "question": question,
            "answer": result,
        }

    except Exception as e:
        log.error("query_audio", str(e))
        return {"success": False, "error": str(e)}


async def generate_audio_handler(
    text: str,
    voice: str = "Kore",
    speakers: Optional[list] = None,
    output_name: Optional[str] = None,
) -> dict:
    """Handle generate_audio tool call."""
    log.tool("generate_audio", {"text_length": len(text), "voice": voice, "speakers": len(speakers or [])})

    try:
        # Generate speech
        if speakers:
            # Multi-speaker mode
            speaker_map = {s["speaker"]: s["voice"] for s in speakers}
            result = await generate_multi_speaker_speech(text, speaker_map)
        else:
            # Single speaker mode
            result = await generate_speech(text, voice)

        # Save to file if output_name provided
        if output_name:
            output_dir = PROJECT_ROOT / "workspace/output"
            ensure_dir(output_dir)
            timestamp = int(datetime.now().timestamp() * 1000)
            output_path = output_dir / f"{output_name}_{timestamp}.wav"
            output_path.write_bytes(result["data"])
            log.success(f"Generated audio: workspace/output/{output_name}_{timestamp}.wav")

            return {
                "success": True,
                "output_path": f"workspace/output/{output_name}_{timestamp}.wav",
                "audio_size": len(result["data"]),
                "mime_type": result["mimeType"],
            }

        log.success(f"Generated audio ({len(result['data'])} bytes)")

        return {
            "success": True,
            "audio_size": len(result["data"]),
            "mime_type": result["mimeType"],
        }

    except Exception as e:
        log.error("generate_audio", str(e))
        return {"success": False, "error": str(e)}


# Tool registry
native_handlers = {
    "transcribe_audio": transcribe_audio_handler,
    "analyze_audio": analyze_audio_handler,
    "query_audio": query_audio_handler,
    "generate_audio": generate_audio_handler,
}


def is_native_tool(name: str) -> bool:
    """Check if tool is a native tool."""
    return name in native_handlers


async def execute_native_tool(name: str, args: dict) -> Any:
    """Execute a native tool."""
    handler = native_handlers.get(name)
    if not handler:
        raise ValueError(f"Unknown native tool: {name}")
    return await handler(**args)
