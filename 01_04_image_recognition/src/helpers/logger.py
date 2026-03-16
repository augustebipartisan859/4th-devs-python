# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Simple colored terminal logger with timestamp support.
Includes vision-specific logging methods for image analysis output.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/logger.js

"""

import json
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BRIGHT = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"


def _timestamp() -> str:
    """Return current time formatted as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


class Logger:
    """Terminal logger with colored output and timestamps."""

    @staticmethod
    def info(msg: str) -> None:
        """Log an informational message."""
        print(f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} {msg}")

    @staticmethod
    def success(msg: str) -> None:
        """Log a success message with a green checkmark."""
        print(f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} {Colors.GREEN}✓{Colors.RESET} {msg}")

    @staticmethod
    def error(title: str, msg: str = "") -> None:
        """Log an error message with a red X."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.RED}✗ {title}{Colors.RESET} {msg}"
        )

    @staticmethod
    def warn(msg: str) -> None:
        """Log a warning message with a yellow triangle."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.YELLOW}⚠{Colors.RESET} {msg}"
        )

    @staticmethod
    def start(msg: str) -> None:
        """Log a start/progress message with a cyan arrow."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.CYAN}→{Colors.RESET} {msg}"
        )

    @staticmethod
    def box(text: str) -> None:
        """Print text inside a bordered box."""
        lines = text.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{Colors.CYAN}{'─' * width}{Colors.RESET}")
        for line in lines:
            padded = line.ljust(width - 3)
            print(
                f"{Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT}{padded}{Colors.RESET}"
                f"{Colors.CYAN}│{Colors.RESET}"
            )
        print(f"{Colors.CYAN}{'─' * width}{Colors.RESET}\n")

    @staticmethod
    def query(q: str) -> None:
        """Log a user query with a blue background badge."""
        print(f"\n{Colors.BG_BLUE}{Colors.WHITE} QUERY {Colors.RESET} {q}\n")

    @staticmethod
    def response(r: str) -> None:
        """Log a model response, truncated to 500 characters."""
        truncated = r[:500] + ("..." if len(r) > 500 else "")
        print(f"\n{Colors.GREEN}Response:{Colors.RESET} {truncated}\n")

    @staticmethod
    def api(step: str, msg_count: int) -> None:
        """Log an API call step with message count."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.MAGENTA}◆{Colors.RESET} {step} ({msg_count} messages)"
        )

    @staticmethod
    def api_done(usage: dict | None) -> None:
        """Log API call completion with token usage."""
        if usage:
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            print(
                f"{Colors.DIM}         tokens: {input_tokens} in / {output_tokens} out"
                f"{Colors.RESET}"
            )

    @staticmethod
    def tool(name: str, args: dict) -> None:
        """Log a tool invocation with truncated arguments."""
        arg_str = json.dumps(args)
        truncated = arg_str[:100] + ("..." if len(arg_str) > 100 else "")
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.YELLOW}⚡{Colors.RESET} {name} {Colors.DIM}{truncated}{Colors.RESET}"
        )

    @staticmethod
    def tool_result(name: str, success: bool, output: str) -> None:
        """Log a tool result with success/failure indicator."""
        icon = (
            f"{Colors.GREEN}✓{Colors.RESET}"
            if success
            else f"{Colors.RED}✗{Colors.RESET}"
        )
        truncated = output[:150] + ("..." if len(output) > 150 else "")
        print(f"{Colors.DIM}         {icon} {truncated}{Colors.RESET}")

    @staticmethod
    def vision(image_path: str, question: str) -> None:
        """Log a vision API call with image path and question."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.BLUE}👁{Colors.RESET} Vision: {image_path}"
        )
        q_truncated = question[:80] + ("..." if len(question) > 80 else "")
        print(f"{Colors.DIM}         Q: {q_truncated}{Colors.RESET}")

    @staticmethod
    def vision_result(answer: str) -> None:
        """Log a vision API result, truncated to 200 characters."""
        truncated = answer[:200] + ("..." if len(answer) > 200 else "")
        print(f"{Colors.DIM}         A: {truncated}{Colors.RESET}")


# Default logger singleton
log = Logger()
