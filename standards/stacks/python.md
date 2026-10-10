# Python

## Environment

- **Use uv for everything:** environments, installs, running tools.
  - Commit `uv.lock`.
  - Never call a system `python` or `pip`. Use `uv run …`.
- **Commit a `.python-version`.** `requires-python` in `pyproject.toml` sets the floor, and ruff's `target-version` matches that floor.
- **Dev dependencies** go in PEP 735 `[dependency-groups]`, not in an extra:

  ```toml
  [dependency-groups]
  dev = ["pytest==…", "ruff==…", "mypy==…", "pre-commit==…"]
  ```

- **Runtime dependencies:**
  - **Applications** declare lower bounds and rely on the lock.
  - **Libraries** declare the widest range they're tested against.
  - Exact `==` pins in `pyproject.toml` need a comment explaining why.
- **Workspaces:** a repository with several packages uses a uv workspace (`[tool.uv.workspace] members = […]`) with one lockfile.

## Lint and format

ruff does both, configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"   # = the requires-python floor

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF", "S"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101"]   # assert is how pytest works
```

Add rule families where they pay for themselves:
- `PTH` (pathlib)
- `DTZ` (timezone-aware datetimes)
- `TID` (banned imports, for enforcing module boundaries)
- framework rules such as `DJ`

In pre-commit, ruff runs as a **local hook through uv**. A second pin in `ruff-pre-commit` could disagree with `uv.lock` about what "formatted" means:

```yaml
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check (uv-pinned)
        entry: uv run --frozen ruff check --fix --force-exclude
        language: system
        types_or: [python, pyi]
        require_serial: true
      - id: ruff-format
        name: ruff format (uv-pinned)
        entry: uv run --frozen ruff format --force-exclude
        language: system
        types_or: [python, pyi]
        require_serial: true
```

## Types

Use mypy, configured in `pyproject.toml`.
- **The minimum** is `check_untyped_defs = true`.
- **Libraries and new code** use `strict = true`.
- **Untyped third-party packages** get a per-module `ignore_missing_imports` override. Never set it globally.

## Tests

Use pytest:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers -ra -m 'not live'"
markers = ["live: talks to a real external system; run with -m live"]
```

- **The default run is offline and deterministic.** Tests that need the network or real hardware are marked, deselected by default, and run deliberately.
- **Coverage floors are optional.** If you set one, scope it to the code that matters, and remember that coverage only says a line ran, not that anything was checked (see [principles](../principles.md#5-a-check-you-havent-seen-fail-proves-nothing)).

## CI

```yaml
      - uses: astral-sh/setup-uv@<sha> # vX.Y.Z
        with:
          version: "<uv version>"
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy <package>
      - run: uv run pytest
```

## Images

- Install from the lock: `uv sync --frozen --no-dev`.
- Copy uv from a pinned image (`COPY --from=ghcr.io/astral-sh/uv:<version> /uv /bin/`).
- Never `pip install -e .` in a production image.
- See [containers](containers.md).

## Portability

- Code that runs on Windows uses `pathlib`, never hard-coded separators.
- Subprocesses are called with argument lists, never with `shell=True`.
