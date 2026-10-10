# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Check repositories against the baseline in standards/README.md. Read-only.

    uv run scripts/audit.py --all
    uv run scripts/audit.py --all --details
    uv run scripts/audit.py --repo NAME --details

Run it locally. Its output names repositories and their gaps, so it never runs
in this public repository's CI, and its output never goes into its issues.

    ok  meets the standard     NO  doesn't     ~  partly     -  not applicable

Columns:
    alerts    Dependabot alerts are on
    ruleset   the `main` ruleset matches settings/ruleset-main.json
            (~: the ruleset differs, or only other protection exists)
    gate      the default branch's head reports each required check from GitHub Actions
    settings  repository settings match settings/repo.json, after the repo's exceptions
    ci        there are workflows
    pins      every `uses:` in the workflows is pinned to a full commit SHA
    leaks     gitleaks runs in pre-commit or in CI
    dbot      dependabot.yml exists and covers github-actions, plus docker where
            there's a Dockerfile
    attrs     .gitattributes normalizes line endings to LF
    econf     .editorconfig exists
    license   a LICENSE file exists
    lock      every Python, Node and Terraform project has a lockfile (uv.lock for Python)
    readme    a README exists
    claude    a CLAUDE.md exists
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import yaml

from common import (
    OVERRIDE_PATH,
    WORKERS,
    GhError,
    Repo,
    add_target_args,
    check_reported,
    exists,
    find_ruleset,
    load_override,
    other_branch_protection,
    read_file,
    required_checks,
    ruleset_diff,
    select_repos,
    settings_diff,
    tree,
    wanted_ruleset,
    wanted_settings,
)

OK, NO, PARTLY, NA = "ok", "NO", "~", "-"
COLUMNS = [
    "alerts",
    "ruleset",
    "gate",
    "settings",
    "ci",
    "pins",
    "leaks",
    "dbot",
    "attrs",
    "econf",
    "license",
    "lock",
    "readme",
    "claude",
]

# Manifests under these directories aren't projects this repository builds:
# vendored dependencies, test corpora, and examples (a Terraform provider's
# examples/ are documentation, not root modules anyone applies from here).
VENDORED = re.compile(
    r"(^|/)(node_modules|vendor|third_party|testdata|fixtures|corpus|examples|\.terraform)/"
)
WORKFLOW = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")
USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)", re.MULTILINE)
SHA_PIN = re.compile(r"@[0-9a-f]{40}$")


@dataclass
class Result:
    repo: Repo
    cells: dict[str, str] = field(default_factory=dict)
    details: list[str] = field(default_factory=list)
    error: str | None = None

    def mark(self, column: str, passed: bool, detail: str = "", *, partly: bool = False) -> None:
        self.cells[column] = OK if passed else (PARTLY if partly else NO)
        if not passed and detail:
            self.details.append(f"{column}: {detail}")


def dirs_with(paths: list[str], *names: str) -> set[str]:
    return {
        posixpath.dirname(p)
        for p in paths
        if posixpath.basename(p) in names and not VENDORED.search(p)
    }


def covered(directory: str, lock_dirs: set[str]) -> bool:
    """True if `directory` or one of its ancestors (a workspace root) has a lockfile."""
    while True:
        if directory in lock_dirs:
            return True
        if not directory:
            return False
        directory = posixpath.dirname(directory)


def lock_problems(paths: list[str]) -> tuple[list[str], bool]:
    problems = []
    python = dirs_with(paths, "pyproject.toml")
    node = dirs_with(paths, "package.json")
    terraform = {
        posixpath.dirname(p) for p in paths if p.endswith(".tf") and not VENDORED.search(p)
    }
    uv_locks = dirs_with(paths, "uv.lock")
    node_locks = dirs_with(paths, "package-lock.json", "pnpm-lock.yaml", "yarn.lock")
    tf_locks = dirs_with(paths, ".terraform.lock.hcl")
    problems += [
        f"{d or '.'}/pyproject.toml has no uv.lock"
        for d in sorted(python)
        if not covered(d, uv_locks)
    ]
    problems += [
        f"{d or '.'}/package.json has no lockfile"
        for d in sorted(node)
        if not covered(d, node_locks)
    ]
    # Only root modules carry a lock; without telling those apart from child
    # modules, the honest check is that some lock exists at all.
    if terraform and not tf_locks:
        problems.append("Terraform without a .terraform.lock.hcl")
    return problems, bool(python or node or terraform)


def audit(repo: Repo) -> Result:
    result = Result(repo)
    paths, truncated = tree(repo)
    files = set(paths)
    if truncated:
        result.details.append("file list truncated by GitHub: file checks may be incomplete")

    result.mark("alerts", exists(f"{repo.api}/vulnerability-alerts"), "Dependabot alerts are off")

    override = {}
    if OVERRIDE_PATH in files:
        try:
            override = load_override(repo)
        except ValueError as error:
            result.details.append(f"exceptions file ignored: {error}")

    ruleset = wanted_ruleset(override)
    current = find_ruleset(repo, ruleset["name"])
    if current is not None:
        diffs = ruleset_diff(current, ruleset)
        result.mark("ruleset", not diffs, "; ".join(diffs), partly=True)
    else:
        others = other_branch_protection(repo, ruleset["name"])
        detail = (
            f"no {ruleset['name']!r} ruleset; has {', '.join(others)}"
            if others
            else f"{repo.default_branch} is unprotected"
        )
        result.mark("ruleset", False, detail, partly=bool(others))

    missing = [c for c in required_checks(ruleset) if not check_reported(repo, c)]
    result.mark(
        "gate",
        not missing,
        f"{repo.default_branch} has no {', '.join(missing)} check run from GitHub Actions",
    )

    diff = settings_diff(repo, wanted_settings(override))
    result.mark("settings", not diff, ", ".join(f"{k} {a} -> {b}" for k, (a, b) in diff.items()))

    workflows = sorted(p for p in paths if WORKFLOW.match(p))
    result.mark("ci", bool(workflows), "no workflows")
    texts = [read_file(repo, p) or "" for p in workflows]
    if workflows:
        unpinned = sorted(
            {
                ref
                for text in texts
                for ref in USES.findall(text)
                if not ref.startswith(("./", "docker://")) and not SHA_PIN.search(ref)
            }
        )
        shown = ", ".join(unpinned[:5]) + (", ..." if len(unpinned) > 5 else "")
        result.mark("pins", not unpinned, f"{len(unpinned)} not SHA-pinned: {shown}")
    else:
        result.cells["pins"] = NA

    hooks = read_file(repo, ".pre-commit-config.yaml") or ""
    result.mark(
        "leaks",
        "gitleaks" in hooks or any("gitleaks" in t for t in texts),
        "gitleaks runs in neither pre-commit nor CI",
    )

    dependabot = next(
        (p for p in (".github/dependabot.yml", ".github/dependabot.yaml") if p in files), None
    )
    if dependabot is None:
        result.mark("dbot", False, "no dependabot.yml")
    else:
        doc = yaml.safe_load(read_file(repo, dependabot) or "") or {}
        ecosystems = {u.get("package-ecosystem") for u in doc.get("updates") or []}
        needed = {"github-actions"} if workflows else set()
        if any(
            posixpath.basename(p).startswith("Dockerfile") or p.endswith(".Dockerfile")
            for p in paths
            if not VENDORED.search(p)
        ):
            needed.add("docker")
        uncovered = sorted(needed - ecosystems)
        result.mark("dbot", not uncovered, f"doesn't cover {', '.join(uncovered)}", partly=True)

    attributes = read_file(repo, ".gitattributes") if ".gitattributes" in files else None
    result.mark(
        "attrs",
        attributes is not None and "eol=lf" in attributes,
        "no .gitattributes" if attributes is None else ".gitattributes doesn't set eol=lf",
        partly=attributes is not None,
    )
    result.mark("econf", ".editorconfig" in files, "no .editorconfig")

    root = [p for p in paths if "/" not in p]
    result.mark(
        "license",
        any(p.upper().startswith(("LICENSE", "LICENCE", "COPYING")) for p in root),
        "no LICENSE",
    )
    problems, any_projects = lock_problems(paths)
    if any_projects:
        result.mark("lock", not problems, "; ".join(problems))
    else:
        result.cells["lock"] = NA
    result.mark("readme", any(p.upper().startswith("README") for p in root), "no README")
    result.mark("claude", "CLAUDE.md" in files, "no CLAUDE.md")
    return result


def safe_audit(repo: Repo) -> Result:
    try:
        return audit(repo)
    except (GhError, ValueError, yaml.YAMLError) as error:
        return Result(repo, error=str(error))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_target_args(parser)
    parser.add_argument("--details", action="store_true", help="explain every gap")
    args = parser.parse_args()

    repos = select_repos(args)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(safe_audit, repos))

    width = max([len("repository"), *(len(r.repo.full_name) for r in results)])
    print("repository".ljust(width), *(c.rjust(8) for c in COLUMNS))
    for result in results:
        if result.error:
            print(result.repo.full_name.ljust(width), "  error (see below)")
            continue
        cells = (result.cells.get(c, "?").rjust(8) for c in COLUMNS)
        print(result.repo.full_name.ljust(width), *cells)

    audited = [r for r in results if not r.error]
    totals = []
    for column in COLUMNS:
        applicable = [r for r in audited if r.cells.get(column) != NA]
        passing = sum(r.cells.get(column) == OK for r in applicable)
        totals.append(f"{passing}/{len(applicable)}".rjust(8))
    print("meets the standard".ljust(width), *totals)

    if args.details:
        for result in results:
            if result.error or result.details:
                print(f"\n{result.repo.full_name}")
                for line in [f"error: {result.error}"] if result.error else result.details:
                    print(f"  {line}")

    errors = [r for r in results if r.error]
    for result in errors:
        print(f"{result.repo.full_name}: error: {result.error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
