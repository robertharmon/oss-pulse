"""Executable-docs runner (backlog B11, verifier #6).

Reads:  every tracked Markdown file. A fenced block whose info string is
        `bash run` is executed; `bash syntax-only` is only parsed (`bash -n`),
        for commands that need credentials CI doesn't have (cutover steps).
Fails:  if any `run` block exits non-zero or any `syntax-only` block doesn't parse.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocBlock:
    path: str
    line: int
    mode: str  # "run" or "syntax-only"
    code: str


def extract_blocks(path: str, markdown: str) -> list[DocBlock]:
    """Tagged bash blocks in a Markdown document, with their 1-based start line."""
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
