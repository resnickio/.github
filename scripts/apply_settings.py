# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Apply settings/repo.json to repositories.

    uv run scripts/apply_settings.py --all                 dry run: print the plan
    uv run scripts/apply_settings.py --repo NAME --apply   make the changes

It covers merge methods, squash commit format, branch cleanup, the wiki,
Dependabot alerts and security updates, and, on public repositories only,
secret scanning, push protection and private vulnerability reporting.

A repository's own .github/repo-settings.json overrides individual keys under
`repo` and `security`, and must give a `$reason`. See standards/repo-settings.md.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from common import (
    Change,
    GhError,
    Repo,
    add_apply_arg,
    add_target_args,
    exists,
    finish,
    gh_api,
    load_override,
    report,
    select_repos,
    settings_diff,
    wanted_settings,
)


def toggle(repo: Repo, label: str, endpoint: str, current: bool, wanted: bool) -> list[Change]:
    if current == wanted:
        return []
    verb, method = ("enable ", "PUT") if wanted else ("disable", "DELETE")
    return [Change(f"{verb} {label}", lambda: gh_api(f"{repo.api}/{endpoint}", method=method))]


def plan(repo: Repo) -> tuple[list[Change], list[str]]:
    override = load_override(repo)
    wanted = wanted_settings(override)
    notes = [f"exception in .github/repo-settings.json: {override['$reason']}"] if override else []

    changes: list[Change] = []
    diff = settings_diff(repo, wanted)
    if diff:
        summary = ", ".join(f"{k} {was} -> {now}" for k, (was, now) in diff.items())
        payload = {k: now for k, (_, now) in diff.items()}
        changes.append(
            Change(
                f"set     {summary}",
                lambda: gh_api(repo.api, method="PATCH", body=payload),
            )
        )

    # Security updates can only be turned on once alerts are, so alerts come first.
    security = wanted["security"]
    alerts = exists(f"{repo.api}/vulnerability-alerts")
    changes += toggle(
        repo,
        "Dependabot alerts",
        "vulnerability-alerts",
        alerts,
        security["vulnerability_alerts"],
    )
    fixes = gh_api(f"{repo.api}/automated-security-fixes")["enabled"]
    changes += toggle(
        repo,
        "Dependabot security updates",
        "automated-security-fixes",
        fixes,
        security["automated_security_fixes"],
    )

    if not repo.private:
        public = wanted["public_only"]
        reporting = gh_api(f"{repo.api}/private-vulnerability-reporting")["enabled"]
        changes += toggle(
            repo,
            "private vulnerability reporting",
            "private-vulnerability-reporting",
            reporting,
            public["private_vulnerability_reporting"],
        )
        current: dict[str, Any] = repo.raw.get("security_and_analysis") or {}
        analysis = {
            feature: setting
            for feature, setting in public["security_and_analysis"].items()
            if (current.get(feature) or {}).get("status") != setting["status"]
        }
        if analysis:
            changes.append(
                Change(
                    f"set     {', '.join(f'{k} {v["status"]}' for k, v in analysis.items())}",
                    lambda: gh_api(
                        repo.api, method="PATCH", body={"security_and_analysis": analysis}
                    ),
                )
            )
    return changes, notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_target_args(parser)
    add_apply_arg(parser)
    args = parser.parse_args()

    pending = failures = 0
    for repo in select_repos(args):
        try:
            changes, notes = plan(repo)
            report(repo, changes, notes, args.apply)
            pending += len(changes)
        except (GhError, ValueError) as error:
            print(f"{repo.full_name}: error: {error}", file=sys.stderr)
            failures += 1
    return finish(args.apply, pending, failures)


if __name__ == "__main__":
    sys.exit(main())
