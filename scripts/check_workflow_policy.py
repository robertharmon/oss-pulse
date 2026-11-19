"""GitHub Actions policy check (backlog B11, access matrix §6, security §6).

Reads:  .github/workflows/*.yml and *.yaml.
Fails:  if a workflow uses `pull_request_target`, has no top-level
        `permissions:` block, or references an action not pinned to a full
        40-character commit SHA (local `./` actions and digest-pinned
        `docker://` images are allowed).
"""


def check_workflow(name: str, text: str) -> list[str]:
    """One problem per policy violation in a workflow file."""
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
