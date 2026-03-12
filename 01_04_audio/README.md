# 01_04_audio — Audio Processing Agent (Python)

An interactive audio processing agent that transcribes, analyzes, and generates audio using Google Gemini API.

## Features

- **Transcribe Audio** — Convert speech to text with timestamps, speaker detection, emotion detection, and language translation
- **Analyze Audio** — Identify music characteristics, speech patterns, sounds, or general audio analysis
- **Query Audio** — Ask custom questions about audio content
- **Generate Audio** — Text-to-speech with 30+ voices and multi-speaker support

## Setup

### Prerequisites

- Python 3.11+
- `.env` file in repository root with API keys:
  - `GEMINI_API_KEY` — Google Gemini API key (required)
  - `OPENAI_API_KEY` or `OPENROUTER_API_KEY` — For LLM orchestration (required)

### Installation

```bash
# From project root
cd 01_04_audio

# Create virtual environment (optional)
python -m venv .venv
source .venv/Scripts/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# From 01_04_audio directory
python app.py

# Or from project root
python 01_04_audio/app.py
```

### Example Queries

```
You: Transcribe the file from workspace/input/

You: Generate audio: Welcome to our product demo

You: Analyze the speech patterns in workspace/input/tech_briefing.wav

You: What topics are discussed in this recording?
```

### Commands

- `exit` — Quit the application
- `clear` — Reset conversation history and statistics

## Tools

### transcribe_audio

Transcribe audio with optional features:

```python
{
  "audio_path": "workspace/input/recording.mp3",  # or YouTube URL
  "include_timestamps": true,
  "detect_speakers": true,
  "detect_emotions": false,
  "translate_to": null,
  "output_name": "transcript"  # Optional - saves JSON to workspace/output/
}
```

### analyze_audio

Analyze audio content:

```python
{
  "audio_path": "workspace/input/recording.mp3",
  "analysis_type": "general",  # "general", "music", "speech", "sounds"
  "custom_prompt": null,
  "output_name": "analysis"
}
```

### query_audio

Ask custom questions about audio:

```python
{
  "audio_path": "workspace/input/recording.mp3",
  "question": "What is the primary language spoken?"
}
```

### generate_audio

Generate speech from text:

```python
# Single speaker
{
  "text": "Say cheerfully: Hello! How are you?",
  "voice": "Puck",  # Upbeat
  "output_name": "greeting"
}

# Multi-speaker
{
  "text": "Speaker1: Hello! Speaker2: Hi there!",
  "speakers": [
    {"speaker": "Speaker1", "voice": "Kore"},
    {"speaker": "Speaker2", "voice": "Puck"}
  ],
  "output_name": "dialogue"
}
```

### Available TTS Voices

| Voice | Style |
|-------|-------|
| Zephyr | Bright |
| Puck | Upbeat |
| Charon | Informative |
| Kore | Firm |
| Fenrir | Excitable |
| Aoede | Breezy |
| ... | (30 voices total) |

## File Structure

```
01_04_audio/
├── app.py                      Entry point
├── mcp.json                    MCP server configuration
├── requirements.txt            Python dependencies
├── README.md                   This file
├── src/
│   ├── agent.py               Agentic loop
│   ├── api.py                 Responses API client
│   ├── config.py              Configuration
│   ├── repl.py                Interactive REPL
│   ├── helpers/
│   │   ├── logger.py          Colored terminal logger
│   │   ├── stats.py           Token usage tracker
│   │   └── shutdown.py        Signal handlers
│   ├── mcp/
│   │   └── client.py          MCP client
│   └── native/
│       ├── gemini.py          Gemini API wrapper
│       └── tools.py           Native tool handlers
└── workspace/
    ├── input/                 Source audio files
    └── output/                Generated files
```

## Supported Audio Formats

- MP3, WAV, AIFF, AAC, OGG, FLAC, M4A, WebM
- Local files up to 9.5 hours (stored locally)
- YouTube URLs (up to 1-3 hours due to context limits)
- File size > 20MB automatically uses resumable upload

## Notes

- The agent will automatically choose appropriate voices and tools
- Large audio files (>20MB) use Gemini's resumable upload API
- All outputs are saved with timestamps: `output_name_1234567890.wav`
- Token usage is displayed on exit

## Troubleshooting

### "GEMINI_API_KEY not set"

Add `GEMINI_API_KEY=your-key` to `.env` in repository root

### "No audio data in response"

The Gemini API may have failed. Check:
- Audio file is valid and readable
- File format is supported
- API key is valid and has sufficient quota

### MCP Server Connection Error

Ensure the files-mcp server is available at `../../../mcp/files-mcp/src/index.ts`
