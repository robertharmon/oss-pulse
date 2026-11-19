"""Executable-docs runner (backlog B11, verifier #6).

Reads:  every tracked Markdown file. A fenced block whose info string is
        `bash run` is executed; `bash syntax-only` is only parsed (`bash -n`),
        for commands that need credentials CI doesn't have (cutover steps).
Fails:  if any `run` block exits non-zero or any `syntax-only` block doesn't parse.
"""

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# A fence may be indented, e.g. inside a list item; group 1 is the indent.
_FENCE_OPEN = re.compile(r"^( *)```(bash|sh)\s+(run|syntax-only)\s*$")


@dataclass(frozen=True)
class DocBlock:
    path: str
    line: int
    mode: str  # "run" or "syntax-only"
    code: str


def extract_blocks(path: str, markdown: str) -> list[DocBlock]:
    """Tagged bash blocks in a Markdown document, with their 1-based start line."""
    blocks: list[DocBlock] = []
    lines = markdown.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        opener = _FENCE_OPEN.match(lines[index].rstrip("\n"))
        if opener is None:
            index += 1
            continue
        start = index
        indent = len(opener.group(1))
        body: list[str] = []
        index += 1
        while index < len(lines) and not lines[index].lstrip(" ").startswith("```"):
            line = lines[index]
            # CommonMark: remove up to the fence's indentation from each line.
            removable = len(line) - len(line.lstrip(" "))
            body.append(line[min(indent, removable) :])
            index += 1
        blocks.append(DocBlock(path, start + 1, opener.group(3), "".join(body)))
        index += 1
    return blocks


def _exe(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} not found on PATH")
    return path


def _tracked_markdown() -> list[str]:
    out = subprocess.run(  # noqa: S603 - fixed git argv, no shell
        [_exe("git"), "ls-files", "*.md"], check=True, capture_output=True, text=True
    ).stdout
    return out.split()


def _run(block: DocBlock) -> bool:
    flags = ["-n"] if block.mode == "syntax-only" else ["-euo", "pipefail"]
    argv = [_exe("bash"), *flags]
    result = subprocess.run(  # noqa: S603 - executing doc commands is this tool's job
        argv, input=block.code, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print(f"::error file={block.path},line={block.line}::{block.mode} block failed")
        print(result.stdout + result.stderr)
    return result.returncode == 0


def main() -> int:
    blocks = [
        block
        for path in _tracked_markdown()
        for block in extract_blocks(path, Path(path).read_text(encoding="utf-8"))
    ]
    failures = sum(not _run(block) for block in blocks)
    print(f"{len(blocks)} tagged blocks, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
