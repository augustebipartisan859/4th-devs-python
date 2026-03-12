# -*- coding: utf-8 -*-

#   gemini.py

"""
### Description:
Google Gemini API wrapper for audio processing (transcription, analysis, TTS).

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      native/gemini.js

"""

import json
import base64
from typing import Optional, Union

import httpx

from ..config import GEMINI_CONFIG
from ..helpers.logger import log
from ..helpers.stats import record_gemini

UPLOAD_ENDPOINT = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GENERATE_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CONFIG['audio_model']}:generateContent"
TTS_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CONFIG['tts_model']}:generateContent"

# Available TTS voices
TTS_VOICES = {
    "Zephyr": "Bright",
    "Puck": "Upbeat",
    "Charon": "Informative",
    "Kore": "Firm",
    "Fenrir": "Excitable",
    "Leda": "Youthful",
    "Orus": "Firm",
    "Aoede": "Breezy",
    "Callirrhoe": "Easy-going",
    "Autonoe": "Bright",
    "Enceladus": "Breathy",
    "Iapetus": "Clear",
    "Umbriel": "Easy-going",
    "Algieba": "Smooth",
    "Despina": "Smooth",
    "Erinome": "Clear",
    "Algenib": "Gravelly",
    "Rasalgethi": "Informative",
    "Laomedeia": "Upbeat",
    "Achernar": "Soft",
    "Alnilam": "Firm",
    "Schedar": "Even",
    "Gacrux": "Mature",
    "Pulcherrima": "Forward",
    "Achird": "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat": "Warm",
}


async def upload_audio_file(
    audio_buffer: bytes, mime_type: str, display_name: str
) -> dict:
    """
    Upload an audio file to Gemini Files API (resumable upload).

    Args:
        audio_buffer: Audio file bytes
        mime_type: MIME type (audio/mp3, audio/wav, etc.)
        display_name: Display name for the file

    Returns:
        Dict with fileUri, name, mimeType
    """
    log.gemini("Uploading audio file", display_name)

    async with httpx.AsyncClient() as client:
        # Step 1: Initialize resumable upload
        init_response = await client.post(
            UPLOAD_ENDPOINT,
            headers={
                "x-goog-api-key": GEMINI_CONFIG["api_key"],
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(len(audio_buffer)),
                "X-Goog-Upload-Header-Content-Type": mime_type,
                "Content-Type": "application/json",
            },
            json={"file": {"display_name": display_name}},
        )

        if not init_response.is_success:
            raise Exception(f"Upload init failed: {await init_response.atext()}")

        upload_url = init_response.headers.get("x-goog-upload-url")
        if not upload_url:
            raise Exception("No upload URL received from Gemini")

        # Step 2: Upload the actual bytes
        upload_response = await client.post(
            upload_url,
            headers={
                "Content-Length": str(len(audio_buffer)),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
            content=audio_buffer,
        )

        if not upload_response.is_success:
            raise Exception(f"Upload failed: {await upload_response.atext()}")

        file_info = upload_response.json()

        if not file_info.get("file", {}).get("uri"):
            raise Exception("No file URI in upload response")

        log.gemini_result(True, f"Uploaded: {file_info['file']['name']}")
        record_gemini("upload")

        return {
            "fileUri": file_info["file"]["uri"],
            "name": file_info["file"]["name"],
            "mimeType": file_info["file"].get("mimeType"),
        }


async def process_audio(
    file_uri: Optional[str] = None,
    audio_base64: Optional[str] = None,
    mime_type: Optional[str] = None,
    prompt: Optional[str] = None,
    response_schema: Optional[dict] = None,
) -> Union[str, dict]:
    """
    Process audio with Gemini (transcription, analysis, etc.).

    Args:
        file_uri: Uploaded file URI (for large files)
        audio_base64: Base64 audio data (for inline, <20MB)
        mime_type: Audio MIME type
        prompt: Instructions for processing
        response_schema: Optional JSON schema for structured output

    Returns:
        Processing result (string or parsed JSON)
    """
    if not prompt:
        raise ValueError("Prompt is required")
    if not file_uri and not audio_base64:
        raise ValueError("Either fileUri or audioBase64 must be provided")

    log.gemini("Processing audio", prompt[:80])

    parts = [{"text": prompt}]

    # Add audio as file_data (uploaded) or inline_data
    if file_uri:
        parts.append({
            "file_data": {
                "mime_type": mime_type,
                "file_uri": file_uri,
            }
        })
    else:
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": audio_base64,
            }
        })

    body = {"contents": [{"parts": parts}]}

    # Add structured output schema if provided
    if response_schema:
        body["generation_config"] = {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GENERATE_ENDPOINT,
            headers={
                "x-goog-api-key": GEMINI_CONFIG["api_key"],
                "Content-Type": "application/json",
            },
            json=body,
            timeout=120.0,
        )

        data = response.json()

        if data.get("error"):
            raise Exception(data["error"].get("message") or json.dumps(data["error"]))

        record_gemini("process")

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")

        if not text:
            raise Exception("No text response from Gemini")

        log.gemini_result(True, f"Processed audio ({len(text)} chars)")

        # Parse JSON if schema was provided
        if response_schema:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        return text


async def transcribe_audio(
    file_uri: Optional[str] = None,
    audio_base64: Optional[str] = None,
    mime_type: Optional[str] = None,
    include_timestamps: bool = True,
    detect_speakers: bool = True,
    detect_emotions: bool = False,
    target_language: Optional[str] = None,
) -> dict:
    """
    Transcribe audio with speaker diarization and timestamps.

    Args:
        file_uri: Uploaded file URI
        audio_base64: Base64 audio data
        mime_type: Audio MIME type
        include_timestamps: Include MM:SS timestamps
        detect_speakers: Identify speakers
        detect_emotions: Detect speaker emotions
        target_language: Translate to this language

    Returns:
        Structured transcription with summary, segments, language
    """
    prompt = "Process this audio file and generate a detailed transcription.\n\nRequirements:\n"

    if detect_speakers:
        prompt += "- Identify distinct speakers (e.g., Speaker 1, Speaker 2, or names if context allows).\n"
    if include_timestamps:
        prompt += "- Provide accurate timestamps for each segment (Format: MM:SS).\n"
    prompt += "- Detect the primary language of each segment.\n"
    if target_language:
        prompt += f"- Translate all segments to {target_language}.\n"
    if detect_emotions:
        prompt += "- Identify the primary emotion of the speaker. Choose exactly one: happy, sad, angry, neutral.\n"
    prompt += "- Provide a brief summary of the entire audio at the beginning."

    schema = {
        "type": "OBJECT",
        "properties": {
            "summary": {
                "type": "STRING",
                "description": "A concise summary of the audio content.",
            },
            "duration_estimate": {
                "type": "STRING",
                "description": "Estimated duration of the audio.",
            },
            "primary_language": {
                "type": "STRING",
                "description": "Primary language detected in the audio.",
            },
            "segments": {
                "type": "ARRAY",
                "description": "List of transcribed segments.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "speaker": {"type": "STRING"},
                        "timestamp": {"type": "STRING"},
                        "content": {"type": "STRING"},
                        "language": {"type": "STRING"},
                        "translation": {"type": "STRING"} if target_language else None,
                        "emotion": {
                            "type": "STRING",
                            "enum": ["happy", "sad", "angry", "neutral"],
                        }
                        if detect_emotions
                        else None,
                    },
                    "required": ["content"]
                    + (["timestamp"] if include_timestamps else [])
                    + (["speaker"] if detect_speakers else []),
                },
            },
        },
        "required": ["summary", "segments"],
    }

    # Remove None values from schema
    schema["properties"] = {k: v for k, v in schema["properties"].items() if v is not None}
    schema["items"]["properties"] = {
        k: v for k, v in schema["items"]["properties"].items() if v is not None
    }

    return await process_audio(
        file_uri=file_uri,
        audio_base64=audio_base64,
        mime_type=mime_type,
        prompt=prompt,
        response_schema=schema,
    )


async def analyze_audio(
    file_uri: Optional[str] = None,
    audio_base64: Optional[str] = None,
    mime_type: Optional[str] = None,
    analysis_type: str = "general",
    custom_prompt: Optional[str] = None,
) -> dict:
    """
    Analyze audio content (music, speech, sounds).

    Args:
        file_uri: Uploaded file URI
        audio_base64: Base64 audio data
        mime_type: Audio MIME type
        analysis_type: "general", "music", "speech", or "sounds"
        custom_prompt: Custom analysis prompt

    Returns:
        Analysis result
    """
    prompts = {
        "general": """Analyze this audio file comprehensively. Describe:
- Type of audio (speech, music, ambient sounds, mixed)
- Main content and topics discussed (if speech)
- Notable sounds or instruments (if music/sounds)
- Audio quality assessment
- Any notable characteristics or anomalies""",
        "music": """Analyze this music audio. Describe:
- Genre and style
- Tempo (BPM estimate) and time signature
- Key and mood
- Instruments identified
- Song structure (verse, chorus, bridge, etc.)
- Vocals (if any): gender, style, language
- Production quality assessment""",
        "speech": """Analyze the speech in this audio. Describe:
- Number of speakers and their characteristics
- Speaking style (formal, casual, emotional)
- Speech clarity and pace
- Background noise assessment
- Language and accent identification
- Key topics and themes discussed""",
        "sounds": """Analyze the sounds in this audio. Identify:
- All distinct sound sources
- Environmental context (indoor, outdoor, etc.)
- Temporal patterns (continuous, intermittent)
- Sound quality and recording conditions
- Any notable or unusual sounds""",
    }

    prompt = custom_prompt or prompts.get(analysis_type, prompts["general"])

    return await process_audio(
        file_uri=file_uri,
        audio_base64=audio_base64,
        mime_type=mime_type,
        prompt=prompt,
    )


async def generate_speech(text: str, voice: str = "Puck") -> dict:
    """
    Generate speech from text (single speaker TTS).

    Args:
        text: Text to generate speech from
        voice: Voice name from TTS_VOICES

    Returns:
        Dict with audio data (bytes) and mimeType
    """
    if voice not in TTS_VOICES:
        raise ValueError(f"Unknown voice: {voice}. Choose from: {', '.join(TTS_VOICES.keys())}")

    log.gemini("Generating speech", f"{voice} voice, {len(text)} chars")

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f'Generate TTS audio using voice "{voice}". Text: {text}',
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TTS_ENDPOINT,
            headers={
                "x-goog-api-key": GEMINI_CONFIG["api_key"],
                "Content-Type": "application/json",
            },
            json=body,
            timeout=120.0,
        )

        data = response.json()

        if data.get("error"):
            raise Exception(data["error"].get("message") or json.dumps(data["error"]))

        record_gemini("generate")

        # Extract audio
        audio_data = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inline_data")

        if not audio_data:
            raise Exception("No audio data in TTS response")

        audio_bytes = base64.b64decode(audio_data["data"])
        log.gemini_result(True, f"Generated audio ({len(audio_bytes)} bytes)")

        return {"data": audio_bytes, "mimeType": audio_data.get("mime_type", "audio/wav")}


async def generate_multi_speaker_speech(text: str, speakers: dict) -> dict:
    """
    Generate multi-speaker speech (up to 2 speakers).

    Args:
        text: Text with speaker labels ("Speaker1: text Speaker2: text")
        speakers: Dict mapping speaker names to voice names

    Returns:
        Dict with audio data and mimeType
    """
    if len(speakers) > 2:
        raise ValueError("Maximum 2 speakers supported")

    for voice in speakers.values():
        if voice not in TTS_VOICES:
            raise ValueError(f"Unknown voice: {voice}")

    log.gemini("Generating multi-speaker speech", f"{len(speakers)} speakers")

    speaker_config = "\n".join([f"- {name}: use voice '{voice}'" for name, voice in speakers.items()])

    prompt = f"""Generate multi-speaker TTS audio with these speaker voices:
{speaker_config}

Text to generate (follow speaker labels):
{text}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TTS_ENDPOINT,
            headers={
                "x-goog-api-key": GEMINI_CONFIG["api_key"],
                "Content-Type": "application/json",
            },
            json=body,
            timeout=120.0,
        )

        data = response.json()

        if data.get("error"):
            raise Exception(data["error"].get("message") or json.dumps(data["error"]))

        record_gemini("generate")

        audio_data = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inline_data")

        if not audio_data:
            raise Exception("No audio data in multi-speaker TTS response")

        audio_bytes = base64.b64decode(audio_data["data"])
        log.gemini_result(True, f"Generated audio ({len(audio_bytes)} bytes)")

        return {"data": audio_bytes, "mimeType": audio_data.get("mime_type", "audio/wav")}
