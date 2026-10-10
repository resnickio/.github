"""Shared helpers for the account-wide scripts in this directory.

Every GitHub call goes through `gh api`, so the scripts act with the
maintainer's own `gh` login and never see a token. Everything they print goes
to the local terminal. That matters because this repository is public, and
its own workflow logs must never carry another repository's details.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OWNER = "resnickio"
# Concurrent read-only requests. Writes are always sequential.
WORKERS = 6

# A repository's own exceptions to the baseline (standards/repo-settings.md).
OVERRIDE_PATH = ".github/repo-settings.json"
OVERRIDE_KEYS = {"$reason", "repo", "security", "ruleset"}
RULESET_OVERRIDE_KEYS = {"allowed_merge_methods", "required_status_checks"}

# Required checks are pinned to the GitHub Actions app, so a commit status
# posted by any other token can't satisfy them (gh api apps/github-actions).
GITHUB_ACTIONS_APP_ID = 15368

_STATUS = re.compile(r"\(HTTP (\d{3})\)")


class GhError(RuntimeError):
    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status


def seg(value: str) -> str:
    """Quote one URL path segment: a label name, a branch, a file path piece."""
    return quote(value, safe="")


def gh_api(
    path: str,
    *,
    method: str = "GET",
    body: Any = None,
    paginate: bool = False,
) -> Any:
    """Call the GitHub REST API through gh and return the parsed JSON (or None).

    `paginate` is for endpoints that return a JSON array; the pages are
    concatenated. A non-2xx response raises GhError with its status.
    """
    gh = shutil.which("gh")
    if gh is None:
        sys.exit("gh is not on PATH: install the GitHub CLI and run `gh auth login`")
    args = [gh, "api", path, "--method", method, "-H", "X-GitHub-Api-Version: 2022-11-28"]
    if paginate:
        args += ["--paginate", "--slurp"]
    if body is not None:
        args += ["--input", "-"]
    # The argv is fixed apart from `path`, whose variable parts every caller
    # quotes with seg(); there is no shell.
    proc = subprocess.run(  # noqa: S603
        args,
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        match = _STATUS.search(proc.stderr)
        status = int(match.group(1)) if match else None
        detail = proc.stdout.strip() or proc.stderr.strip()
        raise GhError(status, f"{method} {path}: {detail}")
    if not proc.stdout.strip():
        return None
    data = json.loads(proc.stdout)
    if paginate:
        return [item for page in data for item in page]
    return data


def exists(path: str) -> bool:
    """True if GET `path` succeeds, False on 404; anything else raises."""
    try:
        gh_api(path)
    except GhError as error:
        if error.status == 404:
            return False
        raise
    return True


@dataclass(frozen=True)
class Repo:
    full_name: str
    default_branch: str
    private: bool
    raw: dict[str, Any] = field(repr=False, compare=False)

    @property
    def api(self) -> str:
        return f"repos/{self.full_name}"


def get_repo(name: str) -> Repo:
    full = name if "/" in name else f"{OWNER}/{name}"
    raw = gh_api(f"repos/{full}")
    return Repo(raw["full_name"], raw["default_branch"], raw["private"], raw)


def owned_repos() -> list[Repo]:
    """Every non-fork, non-archived repository the account owns, public or private."""
    listing = gh_api("user/repos?affiliation=owner&per_page=100", paginate=True)
    names = sorted(
        r["full_name"]
        for r in listing
        if r["owner"]["login"] == OWNER and not r["fork"] and not r["archived"]
    )
    # The list endpoint omits the merge settings, so each repository is fetched.
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(get_repo, names))


def add_target_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--repo",
        action="append",
        metavar="NAME",
        help=f"a repository, as NAME or OWNER/NAME (default owner {OWNER}); repeatable",
    )
    group.add_argument(
        "--all", action="store_true", help=f"every non-fork, non-archived {OWNER} repository"
    )


def select_repos(args: argparse.Namespace) -> list[Repo]:
    if args.all:
        return owned_repos()
    repos = []
    for name in args.repo:
        repo = get_repo(name)
        if repo.raw["fork"] or repo.raw["archived"]:
            kind = "a fork" if repo.raw["fork"] else "archived"
            print(f"{repo.full_name}: skipped, {kind}", file=sys.stderr)
            continue
        repos.append(repo)
    return repos


def read_file(repo: Repo, path: str) -> str | None:
    """A file's text on the default branch, or None if it doesn't exist."""
    try:
        data = gh_api(f"{repo.api}/contents/{quote(path, safe='/')}?ref={seg(repo.default_branch)}")
    except GhError as error:
        if error.status == 404:
            return None
        raise
    if not isinstance(data, dict) or data.get("type") != "file":
        return None
    return base64.b64decode(data["content"]).decode("utf-8")


def tree(repo: Repo) -> tuple[list[str], bool]:
    """Every file path on the default branch, and whether GitHub truncated the list."""
    data = gh_api(f"{repo.api}/git/trees/{seg(repo.default_branch)}?recursive=1")
    paths = [item["path"] for item in data["tree"] if item["type"] == "blob"]
    return paths, bool(data.get("truncated"))


def load_json(relative: str) -> dict[str, Any]:
    data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("$")}


def load_override(repo: Repo) -> dict[str, Any]:
    """The repository's .github/repo-settings.json, validated, or {}."""
    text = read_file(repo, OVERRIDE_PATH)
    if text is None:
        return {}
    where = f"{repo.full_name}:{OVERRIDE_PATH}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{where}: not valid JSON ({error})") from error
    if not isinstance(data, dict):
        raise ValueError(f"{where}: expected a JSON object")
    reason = data.get("$reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"{where}: an exception needs a $reason")
    unknown = set(data) - OVERRIDE_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    unknown = set(data.get("ruleset", {})) - RULESET_OVERRIDE_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown ruleset keys {sorted(unknown)}")
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# ---------------------------------------------------------------- settings


def wanted_settings(override: dict[str, Any]) -> dict[str, Any]:
    base = load_json("settings/repo.json")
    return deep_merge(base, {k: override[k] for k in ("repo", "security") if k in override})


def settings_diff(repo: Repo, wanted: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    """Repository settings that differ from `wanted["repo"]`: {key: (current, wanted)}.

    The squash commit format means nothing on a repository that doesn't allow
    squashing, so it isn't compared there.
    """
    squash = wanted["repo"].get("allow_squash_merge", True)
    return {
        key: (repo.raw.get(key), value)
        for key, value in wanted["repo"].items()
        if repo.raw.get(key) != value and (squash or not key.startswith("squash_merge_commit_"))
    }


# ----------------------------------------------------------------- ruleset


def wanted_ruleset(override: dict[str, Any], *, with_checks: bool = True) -> dict[str, Any]:
    ruleset = load_json("settings/ruleset-main.json")
    custom = override.get("ruleset", {})
    rules = []
    for rule in ruleset["rules"]:
        params = rule.get("parameters")
        if rule["type"] == "pull_request" and "allowed_merge_methods" in custom:
            params = {**params, "allowed_merge_methods": custom["allowed_merge_methods"]}
        if rule["type"] == "required_status_checks":
            if not with_checks:
                continue
            if "required_status_checks" in custom:
                checks = [
                    {"context": c, "integration_id": GITHUB_ACTIONS_APP_ID}
                    for c in custom["required_status_checks"]
                ]
                params = {**params, "required_status_checks": checks}
        rules.append({"type": rule["type"], **({"parameters": params} if params else {})})
    return {**ruleset, "rules": rules}


def required_checks(ruleset: dict[str, Any]) -> list[str]:
    for rule in ruleset["rules"]:
        if rule["type"] == "required_status_checks":
            return [c["context"] for c in rule["parameters"]["required_status_checks"]]
    return []


def _canon(value: Any) -> Any:
    """Order-insensitive form for comparing lists such as merge methods or checks."""
    if isinstance(value, dict):
        return {k: _canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted((_canon(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    return value


def ruleset_diff(current: dict[str, Any], wanted: dict[str, Any]) -> list[str]:
    """How `current` differs from `wanted`, comparing only what `wanted` specifies.

    GitHub fills in parameters the file doesn't set, so a parameter present on
    GitHub but absent from the file is not a difference.
    """
    diffs = []
    for key in ("target", "enforcement", "bypass_actors", "conditions"):
        if _canon(current.get(key)) != _canon(wanted[key]):
            diffs.append(f"{key}: {json.dumps(current.get(key))} -> {json.dumps(wanted[key])}")
    have = {r["type"]: r.get("parameters", {}) for r in current.get("rules", [])}
    want = {r["type"]: r.get("parameters", {}) for r in wanted["rules"]}
    diffs += [f"add rule {t}" for t in sorted(want.keys() - have.keys())]
    diffs += [f"remove rule {t}" for t in sorted(have.keys() - want.keys())]
    for rule in sorted(want.keys() & have.keys()):
        for key, value in want[rule].items():
            if _canon(have[rule].get(key)) != _canon(value):
                was = json.dumps(have[rule].get(key))
                diffs.append(f"{rule}.{key}: {was} -> {json.dumps(value)}")
    return diffs


def find_ruleset(repo: Repo, name: str) -> dict[str, Any] | None:
    for summary in gh_api(f"{repo.api}/rulesets?per_page=100", paginate=True):
        if summary.get("source_type") == "Repository" and summary["name"] == name:
            return gh_api(f"{repo.api}/rulesets/{summary['id']}")
    return None


def other_branch_protection(repo: Repo, name: str) -> list[str]:
    """Protection on the default branch besides the ruleset called `name`."""
    found = []
    for summary in gh_api(f"{repo.api}/rulesets?per_page=100", paginate=True):
        if summary["name"] != name and summary.get("target") == "branch":
            found.append(f"ruleset {summary['name']!r} ({summary.get('enforcement')})")
    if exists(f"{repo.api}/branches/{seg(repo.default_branch)}/protection"):
        found.append("classic branch protection")
    return found


def check_reported(repo: Repo, context: str) -> bool:
    """True if the default branch's head has a check run `context` from GitHub Actions."""
    data = gh_api(
        f"{repo.api}/commits/{seg(repo.default_branch)}/check-runs"
        f"?check_name={seg(context)}&per_page=100"
    )
    return any(run["app"]["id"] == GITHUB_ACTIONS_APP_ID for run in data["check_runs"])


# ------------------------------------------------------------- plan / apply


@dataclass
class Change:
    summary: str
    run: Callable[[], object]


def add_apply_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--apply",
        action="store_true",
        help="make the changes (without it, only print what would change)",
    )


def report(repo: Repo, changes: list[Change], notes: list[str], apply: bool) -> None:
    """Print a repository's plan, and carry it out if `apply`."""
    if not changes and not notes:
        print(f"{repo.full_name}: up to date")
        return
    count = f"{len(changes)} change{'s' if len(changes) != 1 else ''}"
    print(f"{repo.full_name}: {count if changes else 'no changes'}")
    for change in changes:
        print(f"  {change.summary}")
    for note in notes:
        print(f"  ! {note}")
    if apply and changes:
        for change in changes:
            change.run()
        print(f"  applied {count}")


def finish(apply: bool, pending: int, failures: int) -> int:
    if pending and not apply:
        print(f"\ndry run: {pending} change(s) not made. Re-run with --apply to make them.")
    if failures:
        print(f"\n{failures} repository(ies) failed; see the errors above.", file=sys.stderr)
        return 1
    return 0
