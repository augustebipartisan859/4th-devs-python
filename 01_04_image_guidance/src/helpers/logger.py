# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Colored terminal logger for the image guidance agent.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/logger.js

"""

from datetime import datetime
from typing import Any, Optional


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _truncate(value: Any, max_len: int) -> str:
    text = str(value) if value is not None else ""
    return text[:max_len] + "..." if len(text) > max_len else text


# ANSI color codes
_R = "\x1b[0m"   # reset
_B = "\x1b[1m"   # bright/bold
_D = "\x1b[2m"   # dim
_RED = "\x1b[31m"
_GRN = "\x1b[32m"
_YLW = "\x1b[33m"
_BLU = "\x1b[34m"
_MAG = "\x1b[35m"
_CYN = "\x1b[36m"
_WHT = "\x1b[37m"
_BGBLU = "\x1b[44m"
_BGMAG = "\x1b[45m"


class _Logger:
    def info(self, msg: str) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {msg}")

    def success(self, msg: str) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_GRN}✓{_R} {msg}")

    def error(self, title: str, msg: str = "") -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_RED}✗ {title}{_R} {msg}")

    def warn(self, msg: str) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_YLW}⚠{_R} {msg}")

    def start(self, msg: str) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_CYN}→{_R} {msg}")

    def box(self, text: str) -> None:
        lines = text.split("\n")
        width = max(len(l) for l in lines) + 4
        print(f"\n{_CYN}{'─' * width}{_R}")
        for line in lines:
            print(f"{_CYN}│{_R} {_B}{line.ljust(width - 3)}{_R}{_CYN}│{_R}")
        print(f"{_CYN}{'─' * width}{_R}\n")

    def heading(self, title: str, description: Optional[str] = None) -> None:
        print(f"\n{_B}═══ {title} ═══{_R}")
        if description:
            print(f"{_D}{description}{_R}")

    def example(self, text: str) -> None:
        print(f"  {_GRN}→{_R} {_B}{text}{_R}")

    def hint(self, text: str) -> None:
        print(f"\n{_D}{text}{_R}\n")

    def query(self, q: str) -> None:
        print(f"\n{_BGBLU}{_WHT} QUERY {_R} {q}\n")

    def api(self, step: str, msg_count: int) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_MAG}◆{_R} {step} ({msg_count} messages)")

    def api_done(self, usage: Optional[dict]) -> None:
        if usage:
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            print(f"{_D}         tokens: {inp} in / {out} out{_R}")

    def tool(self, name: str, args: Any) -> None:
        import json
        arg_str = _truncate(json.dumps(args), 100)
        print(f"{_D}[{_timestamp()}]{_R} {_YLW}⚡{_R} {name} {_D}{arg_str}{_R}")

    def tool_result(self, name: str, success: bool, output: str) -> None:
        icon = f"{_GRN}✓{_R}" if success else f"{_RED}✗{_R}"
        print(f"{_D}         {icon} {_truncate(output, 150)}{_R}")

    def vision(self, path: str, question: str) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_BLU}👁{_R} Vision: {path}")
        print(f"{_D}         Q: {question}{_R}")

    def vision_result(self, answer: str) -> None:
        print(f"{_D}         A: {_truncate(answer, 200)}{_R}")

    def gemini(self, action: str, detail: Optional[str] = None) -> None:
        print(f"{_D}[{_timestamp()}]{_R} {_BGMAG}{_WHT} GEMINI {_R} {action}")
        if detail:
            print(f"{_D}         {detail}{_R}")

    def gemini_result(self, success: bool, msg: str) -> None:
        icon = f"{_GRN}✓{_R}" if success else f"{_RED}✗{_R}"
        print(f"{_D}         {icon} {msg}{_R}")


log = _Logger()
