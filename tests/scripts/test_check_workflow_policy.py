from pathlib import Path

import pytest

from scripts.check_workflow_policy import check_workflow, main

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
DIGEST = "sha256:" + "0123456789abcdef" * 4

GOOD = f"""name: ci
on:
  pull_request:
permissions:
  contents: read
jobs:
  a:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@{SHA}  # v7.0.1
      - uses: ./.github/actions/local
      - uses: docker://ghcr.io/x/y@{DIGEST}
      - run: echo ok
"""


def test_good_workflow_passes() -> None:
    assert check_workflow("ci.yml", GOOD) == []


def test_rejects_pull_request_target() -> None:
    text = GOOD.replace("  pull_request:", "  pull_request_target:")
    problems = check_workflow("ci.yml", text)
    assert len(problems) == 1
    assert "pull_request_target" in problems[0]


def test_rejects_tag_pinned_action() -> None:
    text = GOOD.replace(f"actions/checkout@{SHA}", "actions/checkout@v7")
    problems = check_workflow("ci.yml", text)
    assert len(problems) == 1
    assert "actions/checkout@v7" in problems[0]


def test_rejects_short_sha_and_unpinned_docker() -> None:
    text = GOOD.replace(f"actions/checkout@{SHA}", "actions/checkout@3d3c42e").replace(
        f"docker://ghcr.io/x/y@{DIGEST}", "docker://ghcr.io/x/y:latest"
    )
    assert len(check_workflow("ci.yml", text)) == 2


def test_requires_top_level_permissions() -> None:
    text = GOOD.replace("permissions:\n  contents: read\n", "")
    problems = check_workflow("ci.yml", text)
    assert len(problems) == 1
    assert "permissions" in problems[0]


def test_mentions_in_comments_are_not_violations() -> None:
    text = "# never use pull_request_target here\n" + GOOD
    assert check_workflow("ci.yml", text) == []


def test_rejects_pull_request_target_in_inline_trigger_list() -> None:
    text = GOOD.replace("on:\n  pull_request:\n", "on: [push, pull_request_target]\n")
    problems = check_workflow("ci.yml", text)
    assert len(problems) == 1
    assert "pull_request_target" in problems[0]


# --- Audit additions (spec: access matrix §6, security §6, module docstring) --


def test_quoted_uses_values_are_checked() -> None:
    quoted_sha = GOOD.replace(f"actions/checkout@{SHA}", f'"actions/checkout@{SHA}"')
    assert check_workflow("ci.yml", quoted_sha) == []
    quoted_tag = GOOD.replace(f"actions/checkout@{SHA}", "'actions/checkout@v7'")
    problems = check_workflow("ci.yml", quoted_tag)
    assert len(problems) == 1
    assert "actions/checkout@v7" in problems[0]


def test_forty_characters_that_arent_hex_are_not_a_sha() -> None:
    branch = "g" * 40
    text = GOOD.replace(f"actions/checkout@{SHA}", f"actions/checkout@{branch}")
    assert len(check_workflow("ci.yml", text)) == 1


def test_reusable_workflow_calls_must_be_pinned_too() -> None:
    caller = f"""name: deploy
on:
  push:
permissions:
  contents: read
jobs:
  pinned:
    uses: org/repo/.github/workflows/build.yml@{SHA}
  local:
    uses: ./.github/workflows/build.yml
  tagged:
    uses: org/repo/.github/workflows/build.yml@v1
"""
    problems = check_workflow("deploy.yml", caller)
    assert len(problems) == 1
    assert "build.yml@v1" in problems[0]


def test_rejects_pull_request_target_as_a_scalar_trigger() -> None:
    text = GOOD.replace("on:\n  pull_request:\n", "on: pull_request_target\n")
    problems = check_workflow("ci.yml", text)
    assert len(problems) == 1
    assert "pull_request_target" in problems[0]


def test_job_level_permissions_dont_replace_the_top_level_block() -> None:
    text = GOOD.replace("permissions:\n  contents: read\n", "").replace(
        "    runs-on: ubuntu-24.04\n",
        "    runs-on: ubuntu-24.04\n    permissions:\n      contents: read\n",
    )
    problems = check_workflow("ci.yml", text)
    assert len(problems) == 1
    assert "permissions" in problems[0]


def test_empty_top_level_permissions_block_is_accepted() -> None:
    text = GOOD.replace("permissions:\n  contents: read\n", "permissions: {}\n")
    assert check_workflow("ci.yml", text) == []


def _workflows(root: Path, files: dict[str, str]) -> None:
    folder = root / ".github" / "workflows"
    folder.mkdir(parents=True)
    for name, text in files.items():
        (folder / name).write_text(text)


def test_main_reads_yaml_extension_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = GOOD.replace("  pull_request:", "  pull_request_target:")
    _workflows(tmp_path, {"ci.yml": GOOD, "release.yaml": bad})
    monkeypatch.chdir(tmp_path)
    assert main() != 0


def test_main_passes_compliant_yml_and_yaml_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _workflows(tmp_path, {"ci.yml": GOOD, "release.yaml": GOOD})
    monkeypatch.chdir(tmp_path)
    assert main() == 0
