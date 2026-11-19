from scripts.run_doc_commands import DocBlock, extract_blocks

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
