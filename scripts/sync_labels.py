# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Sync labels.yml, plus each repository's own .github/labels.yml, to GitHub.

    uv run scripts/sync_labels.py --repo NAME            dry run: print the plan
    uv run scripts/sync_labels.py --all --apply          make the changes
    uv run scripts/sync_labels.py --all --prune          also plan deleting retired labels

Per repository, a label is brought in line in one of these ways:

    rename  an existing alias becomes the label; every issue keeps it
    merge   a second alias, or an alias of a label that already exists, is
            folded in: each issue and PR carrying it gets the label, then the
            alias is deleted
    update  the color, description or name casing changes to match
    create  the label doesn't exist yet
    delete  a `retired` label, only with --prune, and only if no issue or PR
            carries it; one still in use is reported for you to handle

A label that neither file mentions is never touched.

A repository's .github/labels.yml is a list of entries shaped like those in
labels.yml (usually `area:*`). An entry may carry `aliases`, which is how a
repository renames its own older labels. An entry that repeats a global label
is ignored with a warning: the global definition wins.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import yaml

from common import (
    ROOT,
    Change,
    GhError,
    Repo,
    add_apply_arg,
    add_target_args,
    finish,
    gh_api,
    read_file,
    report,
    seg,
    select_repos,
)

LOCAL_PATH = ".github/labels.yml"


@dataclass(frozen=True)
class Label:
    name: str
    color: str
    description: str
    aliases: tuple[str, ...] = ()


def parse(entries: Any, where: str) -> list[Label]:
    if not isinstance(entries, list):
        raise ValueError(f"{where}: expected a list of labels")
    labels = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("color"):
            raise ValueError(f"{where}: entry {i} needs at least a name and a color")
        labels.append(
            Label(
                name=str(entry["name"]),
                color=str(entry["color"]).lstrip("#").upper(),
                description=str(entry.get("description") or ""),
                aliases=tuple(str(a) for a in entry.get("aliases") or ()),
            )
        )
    return labels


def load_global() -> tuple[list[Label], list[str]]:
    doc = yaml.safe_load((ROOT / "labels.yml").read_text(encoding="utf-8"))
    return parse(doc["labels"], "labels.yml"), [str(r) for r in doc.get("retired") or ()]


def load_local(repo: Repo, global_labels: list[Label]) -> tuple[list[Label], list[str]]:
    text = read_file(repo, LOCAL_PATH)
    if text is None:
        return [], []
    doc = yaml.safe_load(text)
    if isinstance(doc, dict):
        doc = doc.get("labels")
    entries = parse(doc, f"{repo.full_name}:{LOCAL_PATH}")

    # Every global name and alias, lowercased, mapped to the global label's name.
    taken = {n.lower(): g.name for g in global_labels for n in (g.name, *g.aliases)}
    labels, warnings = [], []
    for label in entries:
        owner = taken.get(label.name.lower())
        if owner == label.name:
            warnings.append(
                f"{LOCAL_PATH} repeats global label {label.name!r}; the global"
                " definition wins (remove it from the repository's file)"
            )
            continue
        if owner is not None:
            warnings.append(
                f"{LOCAL_PATH} defines {label.name!r}, an old name of global label"
                f" {owner!r}; it becomes {owner!r} (remove it from the repository's file)"
            )
            continue
        clashing = [a for a in label.aliases if a.lower() in taken]
        if clashing:
            warnings.append(
                f"{LOCAL_PATH}: {label.name!r} aliases {clashing}, which belong to"
                " global labels; ignoring those aliases"
            )
            label = Label(
                label.name,
                label.color,
                label.description,
                tuple(a for a in label.aliases if a.lower() not in taken),
            )
        labels.append(label)
    return labels, warnings


def issues_with(repo: Repo, label: str) -> list[int]:
    """Numbers of every issue and pull request carrying `label`, open or closed."""
    items = gh_api(f"{repo.api}/issues?labels={seg(label)}&state=all&per_page=100", paginate=True)
    return [item["number"] for item in items]


def body(label: Label) -> dict[str, str]:
    return {"color": label.color, "description": label.description}


def plan(
    repo: Repo, wanted: list[Label], retired: list[str], prune: bool
) -> tuple[list[Change], list[str]]:
    existing = {
        label["name"].lower(): label
        for label in gh_api(f"{repo.api}/labels?per_page=100", paginate=True)
    }
    changes: list[Change] = []
    notes: list[str] = []
    claimed: set[str] = set()

    def rename(old: str, label: Label) -> None:
        changes.append(
            Change(
                f"rename  {old} -> {label.name}",
                lambda: gh_api(
                    f"{repo.api}/labels/{seg(old)}",
                    method="PATCH",
                    body={"new_name": label.name, **body(label)},
                ),
            )
        )

    def merge(old: str, label: Label) -> None:
        numbers = issues_with(repo, old)

        def run() -> None:
            # Re-read at apply time rather than trusting the dry-run count.
            for number in issues_with(repo, old):
                gh_api(
                    f"{repo.api}/issues/{number}/labels",
                    method="POST",
                    body={"labels": [label.name]},
                )
            gh_api(f"{repo.api}/labels/{seg(old)}", method="DELETE")

        changes.append(Change(f"merge   {old} -> {label.name} ({len(numbers)} issues/PRs)", run))

    for label in wanted:
        current = existing.get(label.name.lower())
        aliases = [
            existing[a.lower()]["name"]
            for a in label.aliases
            if a.lower() in existing and a.lower() not in claimed
        ]
        if current is None and aliases:
            first, *aliases = aliases
            rename(first, label)
            claimed.add(first.lower())
        elif current is None:
            changes.append(
                Change(
                    f"create  {label.name}",
                    lambda label=label: gh_api(
                        f"{repo.api}/labels",
                        method="POST",
                        body={"name": label.name, **body(label)},
                    ),
                )
            )
        else:
            claimed.add(current["name"].lower())
            drift = []
            if current["name"] != label.name:
                drift.append(f"name {current['name']}")
            if current["color"].upper() != label.color:
                drift.append(f"color {current['color']} -> {label.color}")
            if (current.get("description") or "") != label.description:
                drift.append("description")
            if drift:
                old = current["name"]
                changes.append(
                    Change(
                        f"update  {label.name} ({', '.join(drift)})",
                        lambda old=old, label=label: gh_api(
                            f"{repo.api}/labels/{seg(old)}",
                            method="PATCH",
                            body={"new_name": label.name, **body(label)},
                        ),
                    )
                )
        for alias in aliases:
            merge(alias, label)
            claimed.add(alias.lower())

    if prune:
        for name in retired:
            current = existing.get(name.lower())
            if current is None or name.lower() in claimed:
                continue
            numbers = issues_with(repo, current["name"])
            if numbers:
                notes.append(
                    f"kept retired {current['name']!r}: on {len(numbers)} issues/PRs;"
                    " relabel them, then re-run"
                )
                continue
            changes.append(
                Change(
                    f"delete  {current['name']} (retired, unused)",
                    lambda n=current["name"]: gh_api(
                        f"{repo.api}/labels/{seg(n)}", method="DELETE"
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
    parser.add_argument(
        "--prune", action="store_true", help="also delete retired labels that nothing carries"
    )
    args = parser.parse_args()

    global_labels, retired = load_global()
    pending = failures = 0
    for repo in select_repos(args):
        try:
            local, warnings = load_local(repo, global_labels)
            changes, notes = plan(repo, global_labels + local, retired, args.prune)
            report(repo, changes, warnings + notes, args.apply)
            pending += len(changes)
        except (GhError, ValueError) as error:
            print(f"{repo.full_name}: error: {error}", file=sys.stderr)
            failures += 1
    return finish(args.apply, pending, failures)


if __name__ == "__main__":
    sys.exit(main())
