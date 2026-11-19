import subprocess
from pathlib import Path

import pytest

from scripts.run_doc_commands import DocBlock, extract_blocks, main

DOC = """# Title

```bash run
echo hello
```

Some prose.

```bash syntax-only
gcloud projects describe "$PROJECT"
```

```bash
echo untagged blocks are ignored
```

```python run
print("only bash blocks are tagged")
```
"""


def test_extracts_only_tagged_bash_blocks_with_line_numbers() -> None:
    assert extract_blocks("docs/x.md", DOC) == [
        DocBlock(path="docs/x.md", line=3, mode="run", code="echo hello\n"),
        DocBlock(
            path="docs/x.md",
            line=9,
            mode="syntax-only",
            code='gcloud projects describe "$PROJECT"\n',
        ),
    ]


def test_sh_is_accepted_as_bash() -> None:
    blocks = extract_blocks("a.md", "```sh run\ntrue\n```\n")
    assert [b.mode for b in blocks] == ["run"]


def test_no_blocks() -> None:
    assert extract_blocks("a.md", "just prose\n") == []


# CommonMark lets a fence sit up to 3 spaces in, and a fence inside a list item
# sits at the item's content column (3 spaces under "1. "). docs/author_setup.md
# §2.3 does exactly this; the runner must still find the block.
LIST_DOC = """# Setup

1. Clone the repo:

   ```bash syntax-only
   git clone \\
     https://github.com/example/oss-pulse.git
   cd oss-pulse
   ```

2. Carry on.
"""


def test_indented_tagged_block_in_list_item_is_extracted() -> None:
    # Lines: 1 "# Setup", 2 blank, 3 "1. Clone...", 4 blank, 5 opening fence.
    # Code loses the fence's 3-space indent only; the continuation line keeps
    # the 2 spaces it has beyond the fence (5 - 3 = 2).
    assert extract_blocks("docs/x.md", LIST_DOC) == [
        DocBlock(
            path="docs/x.md",
            line=5,
            mode="syntax-only",
            code=(
                "git clone \\\n"
                "  https://github.com/example/oss-pulse.git\n"
                "cd oss-pulse\n"
            ),
        )
    ]


def test_indented_untagged_block_is_ignored_but_tagged_one_is_not() -> None:
    doc = """1. Untagged:

   ```bash
   echo untagged blocks are ignored
   ```

2. Tagged:

   ```sh run
   true
   ```
"""
    # Lines: 1 "1. Untagged:", 2 blank, 3-5 untagged block, 6 blank,
    # 7 "2. Tagged:", 8 blank, 9 tagged opening fence.
    assert extract_blocks("a.md", doc) == [
        DocBlock(path="a.md", line=9, mode="run", code="true\n"),
    ]


def test_column_zero_and_indented_blocks_are_both_extracted() -> None:
    doc = """```bash run
echo top
```

1. Step:

   ```bash run
   echo nested
   ```
"""
    # Lines: 1-3 column-0 block, 4 blank, 5 "1. Step:", 6 blank,
    # 7 indented opening fence.
    assert extract_blocks("a.md", doc) == [
        DocBlock(path="a.md", line=1, mode="run", code="echo top\n"),
        DocBlock(path="a.md", line=7, mode="run", code="echo nested\n"),
    ]


# --- Audit additions (spec: module docstring; CommonMark fenced code blocks) --


def test_tilde_fences_are_fenced_blocks_too() -> None:
    assert extract_blocks("a.md", "~~~bash run\ntrue\n~~~\n") == [
        DocBlock(path="a.md", line=1, mode="run", code="true\n"),
    ]


def test_longer_fence_keeps_inner_backtick_lines_as_code() -> None:
    doc = "````bash run\ncat <<'EOF'\n```\nEOF\n````\n"
    assert extract_blocks("a.md", doc) == [
        DocBlock(path="a.md", line=1, mode="run", code="cat <<'EOF'\n```\nEOF\n"),
    ]


def test_tagged_fence_shown_inside_an_example_block_is_not_a_block() -> None:
    # A doc that shows how to tag a block: the inner fence is content of the
    # outer (untagged) block, not a block of its own.
    doc = "````markdown\n```bash run\nrm -rf build\n```\n````\n"
    assert extract_blocks("a.md", doc) == []


def test_multiline_code_keeps_blank_lines() -> None:
    doc = "intro\n\n```bash run\nset -e\n\necho one\necho two\n```\n"
    assert extract_blocks("a.md", doc) == [
        DocBlock(
            path="a.md", line=3, mode="run", code="set -e\n\necho one\necho two\n"
        ),
    ]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def docs_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    monkeypatch.chdir(root)
    return root


def _track(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    _git(repo, "add", rel)


def test_main_fails_when_a_run_block_exits_non_zero(docs_repo: Path) -> None:
    _track(docs_repo, "docs/ok.md", "```bash run\ntrue\n```\n")
    _track(docs_repo, "docs/bad.md", "```bash run\nexit 3\n```\n")
    assert main() != 0


def test_main_only_parses_syntax_only_blocks(docs_repo: Path) -> None:
    marker = (docs_repo.parent / "ran").as_posix()
    doc = f'```bash syntax-only\ntouch "{marker}"\nfalse\n```\n'
    _track(docs_repo, "docs/cutover.md", doc)
    assert main() == 0  # `false` never ran
    assert not Path(marker).exists()


def test_main_fails_when_a_syntax_only_block_doesnt_parse(docs_repo: Path) -> None:
    _track(docs_repo, "docs/cutover.md", "```bash syntax-only\nif then fi\n```\n")
    assert main() != 0


def test_main_reads_only_tracked_markdown(docs_repo: Path) -> None:
    _track(docs_repo, "docs/ok.md", "```bash run\ntrue\n```\n")
    (docs_repo / "scratch.md").write_text("```bash run\nexit 1\n```\n")
    assert main() == 0
