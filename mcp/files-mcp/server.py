# -*- coding: utf-8 -*-

#   server.py

"""
### Description:
Python MCP stdio server — sandboxed filesystem tools (fs_read, fs_write,
fs_search, fs_manage). Pure Python replacement for the Node.js files-mcp server.
Scoped to FS_ROOT env var (default: ./workspace relative to the caller's CWD).

Run:
    python server.py

Environment:
    FS_ROOT     - Absolute or relative path to the sandbox root directory
    LOG_LEVEL   - Logging level: debug | info | warning | error (default: info)

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      Node.js `files-mcp` server (mcp/files-mcp/src/)

"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

_LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

_raw_level = os.environ.get("LOG_LEVEL", "info").lower()
logging.basicConfig(
    level=_LOG_LEVEL_MAP.get(_raw_level, logging.INFO),
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("files-mcp")

# ---------------------------------------------------------------------------
# Sandbox root
# ---------------------------------------------------------------------------

_raw_fs_root = os.environ.get("FS_ROOT", "./workspace")
# Relative paths resolve against CWD (set by the client via StdioServerParameters.cwd),
# which is the module directory (e.g. 01_03_mcp_translator/). This matches the JS behaviour.
FS_ROOT: Path = (
    Path(_raw_fs_root).resolve()
    if Path(_raw_fs_root).is_absolute()
    else (Path.cwd() / _raw_fs_root).resolve()
)
FS_ROOT.mkdir(parents=True, exist_ok=True)
log.info(f"Sandbox root: {FS_ROOT}")

# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

_OUT_OF_SCOPE_ERROR: dict[str, Any] = {
    "success": False,
    "code": "OUT_OF_SCOPE",
    "error": "Path resolves outside the sandbox root.",
}


def _resolve_safe(relative: str) -> Path | None:
    """Resolve a relative path inside FS_ROOT.

    Args:
        relative: A relative path string provided by the caller (``"."`` = root).

    Returns:
        Resolved absolute ``Path`` if inside sandbox, else ``None``.
    """
    if relative in ("", "."):
        return FS_ROOT
    candidate = (FS_ROOT / relative).resolve()
    try:
        candidate.relative_to(FS_ROOT)
        return candidate
    except ValueError:
        return None


def _checksum(path: Path) -> str:
    """Return MD5 hex digest of a file's contents.

    Args:
        path: Absolute path to file.

    Returns:
        Hex MD5 string.
    """
    return hashlib.md5(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    """Return path relative to FS_ROOT as a POSIX string.

    Args:
        path: Absolute path inside sandbox.

    Returns:
        POSIX-style relative path string.
    """
    return path.relative_to(FS_ROOT).as_posix()


# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("files-mcp")

# ---------------------------------------------------------------------------
# fs_read
# ---------------------------------------------------------------------------

_FS_READ_MAX_LINES = 100


def _parse_line_range(spec: str, total: int) -> tuple[int, int]:
    """Parse a line range spec into (start, end) 0-based indices (inclusive).

    Args:
        spec: A string like ``"10"`` or ``"10-50"``.
        total: Total number of lines in the file.

    Returns:
        Tuple of (start_index, end_index) 0-based, clamped to [0, total-1].

    Raises:
        ValueError: If the spec format is invalid.
    """
    spec = spec.strip()
    if "-" in spec:
        parts = spec.split("-", 1)
        start = int(parts[0]) - 1
        end = int(parts[1]) - 1
    else:
        start = int(spec) - 1
        end = start
    start = max(0, start)
    end = min(total - 1, end)
    return start, end


def _read_file_content(path: Path, lines_spec: Optional[str]) -> dict[str, Any]:
    """Read file content and return a content response dict.

    Args:
        path: Absolute file path inside sandbox.
        lines_spec: Optional line range string (e.g. ``"10"`` or ``"10-50"``).

    Returns:
        Dict with keys ``text``, ``checksum``, ``totalLines``, ``truncated``.
    """
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    all_lines = raw_text.splitlines()
    total = len(all_lines)
    checksum = _checksum(path)
    truncated = False

    if lines_spec:
        start, end = _parse_line_range(lines_spec, total)
        selected = all_lines[start : end + 1]
        numbered = "\n".join(f"{i + start + 1}|{line}" for i, line in enumerate(selected))
    elif total > _FS_READ_MAX_LINES:
        selected = all_lines[:_FS_READ_MAX_LINES]
        numbered = "\n".join(f"{i + 1}|{line}" for i, line in enumerate(selected))
        truncated = True
    else:
        numbered = "\n".join(f"{i + 1}|{line}" for i, line in enumerate(all_lines))

    return {
        "text": numbered,
        "checksum": checksum,
        "totalLines": total,
        "truncated": truncated,
    }


def _entry_dict(
    p: Path, details: bool, children_count: Optional[int] = None
) -> dict[str, Any]:
    """Build an entry dict for a filesystem item.

    Args:
        p: Absolute path to item.
        details: Whether to include size/modified fields.
        children_count: Number of direct children (directories only).

    Returns:
        Dict with ``path``, ``kind``, and optionally ``children``, ``size``,
        ``modified`` fields.
    """
    entry: dict[str, Any] = {
        "path": _rel(p),
        "kind": "directory" if p.is_dir() else "file",
    }
    if children_count is not None:
        entry["children"] = children_count
    if details:
        stat = p.stat()
        entry["size"] = stat.st_size
        entry["modified"] = stat.st_mtime
    return entry


def _list_directory(
    path: Path,
    depth: int,
    limit: int,
    offset: int,
    details: bool,
    mode: str,
) -> list[dict[str, Any]]:
    """Collect directory entries up to a given recursion depth.

    Args:
        path: Absolute directory path.
        depth: How many levels to recurse (1 = immediate children only).
        limit: Max total entries to return (0 = unlimited).
        offset: Skip first N entries.
        details: Include size/modified info.
        mode: ``"tree"`` returns directories only; ``"list"`` returns all.

    Returns:
        List of entry dicts.
    """
    entries: list[dict[str, Any]] = []
    _collect_entries(path, depth, details, mode, entries)
    # Apply offset + limit
    paginated = entries[offset : offset + limit] if limit else entries[offset:]
    return paginated


def _collect_entries(
    path: Path,
    depth: int,
    details: bool,
    mode: str,
    accumulator: list[dict[str, Any]],
) -> None:
    """Recursively collect entries into accumulator.

    Args:
        path: Current directory to scan.
        depth: Remaining recursion depth.
        details: Include size/modified.
        mode: ``"tree"`` for dirs only, ``"list"`` for everything.
        accumulator: List to append entries to.
    """
    if depth < 1:
        return
    try:
        children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return
    for child in children:
        if child.is_dir():
            child_count = sum(1 for _ in child.iterdir()) if depth > 1 else None
            accumulator.append(_entry_dict(child, details, child_count))
            _collect_entries(child, depth - 1, details, mode, accumulator)
        elif mode != "tree":
            accumulator.append(_entry_dict(child, details))


@mcp.tool()
def fs_read(
    path: str,
    mode: str = "auto",
    limit: int = 100,
    offset: int = 0,
    lines: Optional[str] = None,
    depth: int = 1,
    details: bool = False,
) -> str:
    """Read files or list directories within the sandbox.

    Args:
        path: Relative path within sandbox. ``"."`` means the root.
        mode: ``"auto"`` | ``"tree"`` | ``"list"`` | ``"content"``.
        limit: Max directory entries to return.
        offset: Skip first N directory entries.
        lines: Line range to read, e.g. ``"10"`` or ``"10-50"``.
        depth: Recursion depth for directory listing.
        details: Include size/modified in directory entries.

    Returns:
        JSON-encoded result dict.
    """
    resolved = _resolve_safe(path)
    if resolved is None:
        return json.dumps(_OUT_OF_SCOPE_ERROR)

    effective_mode = mode
    if mode == "auto":
        effective_mode = "directory" if resolved.is_dir() else "content"

    # --- Directory ---
    if effective_mode in ("directory", "list", "tree"):
        if not resolved.exists():
            return json.dumps({"success": False, "error": f"Path not found: {path}"})
        if not resolved.is_dir():
            return json.dumps({"success": False, "error": f"Not a directory: {path}"})

        entries = _list_directory(
            resolved,
            depth=depth,
            limit=limit,
            offset=offset,
            details=details,
            mode=effective_mode,
        )
        total = sum(1 for _ in resolved.rglob("*")) if depth > 1 else sum(1 for _ in resolved.iterdir())
        dirs = sum(1 for e in entries if e["kind"] == "directory")
        files = sum(1 for e in entries if e["kind"] == "file")
        return json.dumps({
            "success": True,
            "path": path,
            "type": "directory",
            "entries": entries,
            "summary": f"{len(entries)} entries ({dirs} dirs, {files} files)",
            "stats": {"total": total, "returned": len(entries), "offset": offset},
        })

    # --- File content ---
    if not resolved.exists():
        return json.dumps({"success": False, "error": f"Path not found: {path}"})
    if not resolved.is_file():
        return json.dumps({"success": False, "error": f"Not a file: {path}"})

    content = _read_file_content(resolved, lines)
    hint = (
        f"File has {content['totalLines']} lines total. "
        "Use 'lines' parameter to read specific ranges."
        if content["truncated"]
        else None
    )
    return json.dumps({
        "success": True,
        "path": path,
        "type": "file",
        "content": content,
        **({"hint": hint} if hint else {}),
    })


# ---------------------------------------------------------------------------
# fs_write
# ---------------------------------------------------------------------------

def _make_diff(original_lines: list[str], new_lines: list[str]) -> str:
    """Produce a simple unified-style diff between two line lists.

    Args:
        original_lines: Lines before the change.
        new_lines: Lines after the change.

    Returns:
        Diff string with ``-`` / ``+`` prefixes.
    """
    import difflib

    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        lineterm="",
        n=2,
    )
    return "\n".join(diff)


@mcp.tool()
def fs_write(
    path: str,
    operation: str,
    content: Optional[str] = None,
    action: Optional[str] = None,
    lines: Optional[str] = None,
    checksum: Optional[str] = None,
    dryRun: bool = False,
) -> str:
    """Create or update files within the sandbox.

    Args:
        path: Relative path within sandbox.
        operation: ``"create"`` or ``"update"``.
        content: Text content to write.
        action: Required for update: ``"replace"`` | ``"insert_before"``
            | ``"insert_after"`` | ``"delete_lines"``.
        lines: Target line range, e.g. ``"10"`` or ``"10-15"``.
        checksum: If given, verify file hasn't changed since last read.
        dryRun: Preview diff without writing.

    Returns:
        JSON-encoded result dict.
    """
    resolved = _resolve_safe(path)
    if resolved is None:
        return json.dumps(_OUT_OF_SCOPE_ERROR)

    # Ensure parent directory exists
    resolved.parent.mkdir(parents=True, exist_ok=True)

    if operation == "create":
        if content is None:
            return json.dumps({"status": "error", "error": "'content' required for create"})
        original_lines: list[str] = resolved.read_text(encoding="utf-8").splitlines() if resolved.exists() else []
        new_lines = content.splitlines()
        diff = _make_diff(original_lines, new_lines)
        if not dryRun:
            resolved.write_text(content, encoding="utf-8")
        new_cksum = _checksum(resolved) if resolved.exists() and not dryRun else hashlib.md5(content.encode()).hexdigest()
        return json.dumps({
            "status": "preview" if dryRun else "applied",
            "path": path,
            "operation": operation,
            "result": {"action": "create", "newChecksum": new_cksum, "diff": diff},
        })

    if operation == "update":
        if not resolved.exists():
            return json.dumps({"status": "error", "error": f"File not found: {path}"})
        if not resolved.is_file():
            return json.dumps({"status": "error", "error": f"Not a file: {path}"})

        # Verify checksum if provided
        if checksum and _checksum(resolved) != checksum:
            return json.dumps({
                "status": "error",
                "error": "Checksum mismatch — file has changed since last read.",
                "hint": "Re-read the file with fs_read to get the current checksum.",
            })

        if action is None:
            return json.dumps({"status": "error", "error": "'action' required for update"})
        if lines is None and action != "delete_lines":
            return json.dumps({"status": "error", "error": "'lines' required for update"})

        original_text = resolved.read_text(encoding="utf-8")
        original_lines = original_text.splitlines()
        total = len(original_lines)
        new_lines = list(original_lines)

        if action == "delete_lines":
            if lines is None:
                return json.dumps({"status": "error", "error": "'lines' required for delete_lines"})
            start, end = _parse_line_range(lines, total)
            del new_lines[start : end + 1]
        else:
            start, end = _parse_line_range(lines, total)  # type: ignore[arg-type]
            incoming = content.splitlines() if content else []
            if action == "replace":
                new_lines[start : end + 1] = incoming
            elif action == "insert_before":
                new_lines[start:start] = incoming
            elif action == "insert_after":
                new_lines[end + 1 : end + 1] = incoming
            else:
                return json.dumps({"status": "error", "error": f"Unknown action: {action}"})

        new_text = "\n".join(new_lines)
        diff = _make_diff(original_lines, new_lines)
        if not dryRun:
            resolved.write_text(new_text, encoding="utf-8")
        new_cksum = _checksum(resolved) if not dryRun else hashlib.md5(new_text.encode()).hexdigest()
        return json.dumps({
            "status": "preview" if dryRun else "applied",
            "path": path,
            "operation": operation,
            "result": {"action": action, "newChecksum": new_cksum, "diff": diff},
        })

    return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})


# ---------------------------------------------------------------------------
# fs_search
# ---------------------------------------------------------------------------

def _is_text_file(path: Path) -> bool:
    """Heuristic check whether a file appears to be text (not binary).

    Args:
        path: Absolute file path.

    Returns:
        ``True`` if the file seems to be text.
    """
    try:
        chunk = path.read_bytes()[:4096]
        return b"\x00" not in chunk
    except OSError:
        return False


@mcp.tool()
def fs_search(
    path: str,
    query: str,
    target: str = "all",
    patternMode: str = "literal",
    caseInsensitive: bool = False,
    depth: int = 5,
    maxResults: int = 100,
) -> str:
    """Find files by name or search file content within the sandbox.

    Args:
        path: Starting directory within sandbox (``"."`` for root).
        query: Search term.
        target: ``"all"`` | ``"filename"`` | ``"content"``.
        patternMode: ``"literal"`` | ``"regex"`` | ``"fuzzy"``.
        caseInsensitive: Case-insensitive matching.
        depth: Maximum directory depth to traverse.
        maxResults: Maximum number of results to return.

    Returns:
        JSON-encoded result dict.
    """
    resolved = _resolve_safe(path)
    if resolved is None:
        return json.dumps(_OUT_OF_SCOPE_ERROR)
    if not resolved.is_dir():
        return json.dumps({"success": False, "error": f"Not a directory: {path}"})

    flags = re.IGNORECASE if caseInsensitive else 0

    # Build compiled pattern
    if patternMode == "regex":
        try:
            pattern = re.compile(query, flags)
        except re.error as exc:
            return json.dumps({"success": False, "error": f"Invalid regex: {exc}"})
    elif patternMode == "fuzzy":
        # Convert query chars to a loose pattern with .* between them
        escaped = [re.escape(c) for c in query]
        pattern = re.compile(".*".join(escaped), flags)
    else:
        pattern = re.compile(re.escape(query), flags)

    file_matches: list[dict[str, str]] = []
    content_matches: list[dict[str, Any]] = []
    total_count = 0
    truncated = False

    def _walk(dirpath: Path, current_depth: int) -> None:
        nonlocal total_count, truncated
        if current_depth > depth:
            return
        try:
            items = sorted(dirpath.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            return
        for item in items:
            if total_count >= maxResults:
                truncated = True
                return
            if item.is_dir():
                _walk(item, current_depth + 1)
            elif item.is_file():
                matched_name = False
                if target in ("all", "filename") and pattern.search(item.name):
                    file_matches.append({"name": item.name, "path": _rel(item)})
                    total_count += 1
                    matched_name = True

                if target in ("all", "content") and not matched_name and _is_text_file(item):
                    try:
                        for lineno, line in enumerate(
                            item.read_text(encoding="utf-8", errors="replace").splitlines(),
                            start=1,
                        ):
                            if total_count >= maxResults:
                                truncated = True
                                break
                            if pattern.search(line):
                                content_matches.append({
                                    "path": _rel(item),
                                    "line": lineno,
                                    "text": line.rstrip(),
                                })
                                total_count += 1
                    except OSError:
                        pass

    _walk(resolved, current_depth=1)

    return json.dumps({
        "success": True,
        "query": query,
        "files": file_matches,
        "content": content_matches,
        "totalCount": total_count,
        "truncated": truncated,
        "hint": (
            f"Results truncated at {maxResults}. Use 'path' to narrow scope or increase 'maxResults'."
            if truncated
            else None
        ),
    })


# ---------------------------------------------------------------------------
# fs_manage
# ---------------------------------------------------------------------------

@mcp.tool()
def fs_manage(
    operation: str,
    path: str,
    target: Optional[str] = None,
    recursive: bool = False,
    force: bool = False,
) -> str:
    """Perform structural filesystem operations within the sandbox.

    Args:
        operation: ``"delete"`` | ``"rename"`` | ``"move"`` | ``"copy"``
            | ``"mkdir"`` | ``"stat"``.
        path: Source path within sandbox.
        target: Destination path for rename/move/copy.
        recursive: Create parent dirs (mkdir) or include subdirs (copy/move).
        force: Overwrite if target exists.

    Returns:
        JSON-encoded result dict.
    """
    resolved = _resolve_safe(path)
    if resolved is None:
        return json.dumps({**_OUT_OF_SCOPE_ERROR, "operation": operation, "path": path})

    # --- stat ---
    if operation == "stat":
        if not resolved.exists():
            return json.dumps({"success": False, "operation": operation, "path": path,
                               "error": f"Path not found: {path}"})
        stat = resolved.stat()
        return json.dumps({
            "success": True,
            "operation": operation,
            "path": path,
            "stat": {
                "kind": "directory" if resolved.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            },
        })

    # --- mkdir ---
    if operation == "mkdir":
        resolved.mkdir(parents=recursive, exist_ok=True)
        return json.dumps({"success": True, "operation": operation, "path": path})

    # --- delete ---
    if operation == "delete":
        if not resolved.exists():
            return json.dumps({"success": False, "operation": operation, "path": path,
                               "error": f"Path not found: {path}"})
        if resolved.is_dir():
            if any(resolved.iterdir()):
                return json.dumps({
                    "success": False,
                    "operation": operation,
                    "path": path,
                    "error": "Directory is not empty. Only empty directories can be deleted.",
                    "hint": "Delete files inside first, or use fs_manage with operation='delete' per file.",
                })
            resolved.rmdir()
        else:
            resolved.unlink()
        return json.dumps({"success": True, "operation": operation, "path": path})

    # --- rename / move / copy — require target ---
    if target is None:
        return json.dumps({"success": False, "operation": operation, "path": path,
                           "error": f"'target' required for operation '{operation}'"})

    resolved_target = _resolve_safe(target)
    if resolved_target is None:
        return json.dumps({**_OUT_OF_SCOPE_ERROR, "operation": operation, "path": path})

    if not resolved.exists():
        return json.dumps({"success": False, "operation": operation, "path": path,
                           "error": f"Source not found: {path}"})

    if operation in ("rename", "move"):
        if resolved_target.exists() and not force:
            return json.dumps({"success": False, "operation": operation, "path": path,
                               "error": f"Target already exists: {target}. Use force=true to overwrite."})
        resolved_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(resolved), str(resolved_target))
        return json.dumps({"success": True, "operation": operation, "path": path, "target": target})

    if operation == "copy":
        if resolved_target.exists() and not force:
            return json.dumps({"success": False, "operation": operation, "path": path,
                               "error": f"Target already exists: {target}. Use force=true to overwrite."})
        resolved_target.parent.mkdir(parents=True, exist_ok=True)
        if resolved.is_dir():
            if recursive:
                shutil.copytree(str(resolved), str(resolved_target), dirs_exist_ok=force)
            else:
                return json.dumps({"success": False, "operation": operation, "path": path,
                                   "error": "Source is a directory. Use recursive=true to copy directories."})
        else:
            shutil.copy2(str(resolved), str(resolved_target))
        return json.dumps({"success": True, "operation": operation, "path": path, "target": target})

    return json.dumps({"success": False, "operation": operation, "path": path,
                       "error": f"Unknown operation: {operation}"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("Starting files-mcp server (stdio transport)")
    mcp.run(transport="stdio")
