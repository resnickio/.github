# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Apply settings/ruleset-main.json to each repository's default branch.

    uv run scripts/apply_ruleset.py --all                            dry run
    uv run scripts/apply_ruleset.py --repo NAME --apply
    uv run scripts/apply_ruleset.py --repo NAME --without-checks --apply

The ruleset requires a `gate` check from GitHub Actions. A required check that
never reports blocks every merge, so this refuses to require one that the
default branch's latest commit hasn't reported. --without-checks applies the
rest of the ruleset (PR required, threads resolved, squash only, no
force-push, no deletion) until the repository's CI has a gate job.

It creates or updates the ruleset named in the file and deletes nothing.
Other rulesets and classic branch protection are reported for you to remove
by hand once this one is verified, since GitHub enforces all of them at once.

A repository's .github/repo-settings.json may override `ruleset`:
`allowed_merge_methods` (for example ["merge"]) and `required_status_checks`
(a list of check names, each required from GitHub Actions).
"""

from __future__ import annotations

import argparse
import sys

from common import (
    Change,
    GhError,
    Repo,
    add_apply_arg,
    add_target_args,
    check_reported,
    find_ruleset,
    finish,
    gh_api,
    load_override,
    other_branch_protection,
    report,
    required_checks,
    ruleset_diff,
    select_repos,
    wanted_ruleset,
)


def plan(repo: Repo, with_checks: bool) -> tuple[list[Change], list[str]]:
    override = load_override(repo)
    notes = [f"exception in .github/repo-settings.json: {override['$reason']}"] if override else []
    wanted = wanted_ruleset(override, with_checks=with_checks)

    missing = [c for c in required_checks(wanted) if not check_reported(repo, c)]
    if missing:
        notes.append(
            f"refused: {repo.default_branch} has no {', '.join(missing)} check run from"
            " GitHub Actions, so requiring it would block every merge. Add the gate job"
            " first, or use --without-checks"
        )
        return [], notes

    notes += [
        f"also on {repo.default_branch}: {p}; remove it once this ruleset is verified"
        for p in other_branch_protection(repo, wanted["name"])
    ]

    current = find_ruleset(repo, wanted["name"])
    if not with_checks:
        # Deferring the gate requirement must never weaken protection that is
        # already there, so checks the existing ruleset requires are kept.
        kept = [
            r for r in (current or {}).get("rules", []) if r["type"] == "required_status_checks"
        ]
        if kept:
            wanted = {**wanted, "rules": wanted["rules"] + kept}
            checks = [c["context"] for c in kept[0]["parameters"]["required_status_checks"]]
            notes.append(f"keeps the checks it already requires: {', '.join(checks)}")
        notes.append("without the gate check: re-run without --without-checks once gate reports")

    if current is None:
        change = Change(
            f"create  ruleset {wanted['name']!r}",
            lambda: gh_api(f"{repo.api}/rulesets", method="POST", body=wanted),
        )
        return [change], notes

    diffs = ruleset_diff(current, wanted)
    if not diffs:
        return [], notes
    changes = [
        Change(
            f"update  ruleset {wanted['name']!r}: " + "; ".join(diffs),
            lambda: gh_api(f"{repo.api}/rulesets/{current['id']}", method="PUT", body=wanted),
        )
    ]
    return changes, notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_target_args(parser)
    add_apply_arg(parser)
    parser.add_argument(
        "--without-checks",
        action="store_true",
        help="leave out the required status checks (for repositories without a gate job yet)",
    )
    args = parser.parse_args()

    pending = failures = 0
    for repo in select_repos(args):
        try:
            changes, notes = plan(repo, with_checks=not args.without_checks)
            report(repo, changes, notes, args.apply)
            pending += len(changes)
        except (GhError, ValueError) as error:
            print(f"{repo.full_name}: error: {error}", file=sys.stderr)
            failures += 1
    return finish(args.apply, pending, failures)


if __name__ == "__main__":
    sys.exit(main())
