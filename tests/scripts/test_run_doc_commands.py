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
