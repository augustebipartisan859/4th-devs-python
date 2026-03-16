# -*- coding: utf-8 -*-

#   logger.py

"""
### Description:
Colored terminal logger with timestamp support and domain-specific log methods
for the agentic RAG module (API calls, tool invocations, reasoning summaries).

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/logger.js

"""

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
    """Get current time as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


class Logger:
    """Terminal logger with colored output for the agentic RAG module."""

    @staticmethod
    def info(msg: str) -> None:
        """Log informational message with dim timestamp."""
        print(f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} {msg}")

    @staticmethod
    def success(msg: str) -> None:
        """Log success message with green checkmark."""
        print(f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} {Colors.GREEN}✓{Colors.RESET} {msg}")

    @staticmethod
    def error(title: str, msg: str = "") -> None:
        """Log error with red X, title, and optional detail."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.RED}✗ {title}{Colors.RESET} {msg}"
        )

    @staticmethod
    def warn(msg: str) -> None:
        """Log warning with yellow triangle."""
        print(f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} {Colors.YELLOW}⚠{Colors.RESET} {msg}")

    @staticmethod
    def start(msg: str) -> None:
        """Log start event with cyan arrow."""
        print(f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} {Colors.CYAN}→{Colors.RESET} {msg}")

    @staticmethod
    def box(text: str) -> None:
        """Print text inside a bordered box — used for section headers."""
        lines = text.split("\n")
        width = max(len(line) for line in lines) + 4
        print(f"\n{Colors.CYAN}{'─' * width}{Colors.RESET}")
        for line in lines:
            padded = line.ljust(width - 3)
            print(
                f"{Colors.CYAN}│{Colors.RESET} "
                f"{Colors.BRIGHT}{padded}{Colors.RESET}"
                f"{Colors.CYAN}│{Colors.RESET}"
            )
        print(f"{Colors.CYAN}{'─' * width}{Colors.RESET}\n")

    @staticmethod
    def query(q: str) -> None:
        """Log a user query with blue background badge."""
        print(f"\n{Colors.BG_BLUE}{Colors.WHITE} QUERY {Colors.RESET} {q}\n")

    @staticmethod
    def response(r: str) -> None:
        """Log agent response, truncated to 500 chars."""
        truncated = r[:500] + ("..." if len(r) > 500 else "")
        print(f"\n{Colors.GREEN}Response:{Colors.RESET} {truncated}\n")

    @staticmethod
    def api(step: str, msg_count: int) -> None:
        """Log an API call with step label and current message count."""
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.MAGENTA}◆{Colors.RESET} {step} ({msg_count} messages)"
        )

    @staticmethod
    def api_done(usage: dict) -> None:
        """Log token usage breakdown after an API call completes."""
        if not usage:
            return
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        # Granular token counts are nested under *_details sub-objects
        input_details = usage.get("input_tokens_details") or {}
        cached = input_details.get("cached_tokens", 0)
        output_details = usage.get("output_tokens_details") or {}
        reasoning = output_details.get("reasoning_tokens", 0)
        parts = [f"{inp} in"]
        if cached:
            parts[-1] += f" ({cached} cached)"
        parts.append(f"{out} out")
        if reasoning:
            parts[-1] += f" ({reasoning} reasoning)"
        print(f"{Colors.DIM}         tokens: {' / '.join(parts)}{Colors.RESET}")

    @staticmethod
    def reasoning(text: str) -> None:
        """Log a reasoning summary item in dim cyan, indented."""
        lines = text.split("\n")
        for line in lines:
            print(f"{Colors.DIM}{Colors.CYAN}  [reasoning] {line}{Colors.RESET}")

    @staticmethod
    def tool(name: str, args: dict) -> None:
        """Log a tool invocation with truncated args (300 chars)."""
        import json
        arg_str = json.dumps(args)
        truncated = arg_str[:300] + ("..." if len(arg_str) > 300 else "")
        print(
            f"{Colors.DIM}[{_timestamp()}]{Colors.RESET} "
            f"{Colors.YELLOW}⚡{Colors.RESET} {name} {Colors.DIM}{truncated}{Colors.RESET}"
        )

    @staticmethod
    def tool_result(name: str, success: bool, output: str) -> None:
        """Log tool result, truncated to 500 chars."""
        icon = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
        truncated = output[:500] + ("..." if len(output) > 500 else "")
        print(f"{Colors.DIM}         {icon} {name}: {truncated}{Colors.RESET}")


# Module-level singleton — import `log` for convenience
log = Logger()
