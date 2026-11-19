from scripts.check_workflow_policy import check_workflow

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
