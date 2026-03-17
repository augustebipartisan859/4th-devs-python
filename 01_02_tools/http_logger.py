# -*- coding: utf-8 -*-

#   http_logger.py

"""
### Description:
httpx event hooks for structured file-based logging of all HTTP requests and
responses, including headers and bodies.  Sensitive authorization fields are
redacted before writing.

---

@Author:        Daniel Szczepanski
@Created on:    11.03.2026
@Contact:       d.szczepanski@raceon-gmbh.com
@License:       Copyright 2025 RaceOn GmbH, All rights reserved

"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import httpx

# ---------------------------------------------------------------------------
# Log file setup
# ---------------------------------------------------------------------------

_LOGS_DIR = Path(__file__).parent / "logs"
_LOGS_DIR.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_LOGS_DIR / "http_debug.log", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)

_http_log = logging.getLogger("http_debug")
_http_log.setLevel(logging.DEBUG)
_http_log.addHandler(_file_handler)
_http_log.propagate = False  # do not bubble up to root logger / console

# ---------------------------------------------------------------------------
# Header redaction
# ---------------------------------------------------------------------------

_SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie"}


def _redact_headers(headers: httpx.Headers) -> Dict[str, str]:
    """Return headers as a dict with sensitive values replaced by [REDACTED].

    Args:
        headers: httpx Headers object from a request or response.

    Returns:
        Dict with header names as keys and safe values.
    """
    return {
        name: "[REDACTED]" if name.lower() in _SENSITIVE_HEADERS else value
        for name, value in headers.items()
    }


def _format_headers(headers: httpx.Headers) -> str:
    """Return headers as a nicely indented, redacted multi-line string.

    Args:
        headers: httpx Headers object from a request or response.

    Returns:
        Multi-line string with one ``Name: value`` pair per line, indented for
        log readability.
    """
    redacted = _redact_headers(headers)
    if not redacted:
        return "<none>"
    lines = "\n".join(f"    {name}: {value}" for name, value in redacted.items())
    return "\n" + lines


# ---------------------------------------------------------------------------
# Body formatting
# ---------------------------------------------------------------------------


def _format_body(raw: str, content_type: str) -> str:
    """Strip whitespace from *raw* and pretty-print if content type is JSON.

    Args:
        raw: Raw body text.
        content_type: Value of the Content-Type header (may be empty).

    Returns:
        Formatted body string ready for logging.
    """
    raw = raw.strip()
    if not raw:
        return "<empty>"
    if "application/json" in content_type:
        try:
            return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except Exception:
            pass
    return raw


# ---------------------------------------------------------------------------
# Event hooks
# ---------------------------------------------------------------------------


async def _log_request(request: httpx.Request) -> None:
    """httpx request event hook — log method, URL, headers, and body.

    Args:
        request: The outgoing httpx Request object.
    """
    try:
        raw = request.content.decode("utf-8") if request.content else ""
    except Exception:
        raw = "<binary>"

    body_text = _format_body(raw, request.headers.get("content-type", ""))

    _http_log.debug(
        ">>> REQUEST\n"
        "  %s %s\n"
        "  Headers: %s\n"
        "  Body: %s",
        request.method,
        request.url,
        _format_headers(request.headers),
        body_text,
    )


async def _log_response(response: httpx.Response) -> None:
    """httpx response event hook — log status, headers, and body.

    Args:
        response: The incoming httpx Response object.
    """
    await response.aread()

    try:
        raw = response.text
    except Exception:
        raw = "<binary>"

    body_text = _format_body(raw, response.headers.get("content-type", ""))

    _http_log.debug(
        "<<< RESPONSE\n"
        "  %s %s\n"
        "  Headers: %s\n"
        "  Body: %s",
        response.status_code,
        response.url,
        _format_headers(response.headers),
        body_text,
    )


def get_event_hooks() -> Dict[str, Any]:
    """Return httpx event_hooks dict with request and response loggers.

    Returns:
        Dict suitable for passing as ``event_hooks=`` to ``httpx.AsyncClient``.
    """
    return {
        "request": [_log_request],
        "response": [_log_response],
    }
