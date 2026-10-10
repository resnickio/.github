# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Check labels.yml, and check that it defines every label the issue forms apply.

GitHub applies an issue form's labels only if the repository already has
them. A typo in a form's `labels:` would therefore fail nowhere; issues in
every repository using the defaults would just arrive unlabeled. This makes
that mistake fail here instead.

Run: uv run scripts/validate.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "labels.yml"
FORMS = ROOT / ".github" / "ISSUE_TEMPLATE"

# GitHub's limits on label fields.
MAX_NAME = 50
MAX_DESCRIPTION = 100
NAME = re.compile(r"^(type|priority|status|agent):[a-z0-9][a-z0-9-]*$")
COLOR = re.compile(r"^[0-9A-F]{6}$")


def check_labels(doc: object, errors: list[str]) -> set[str]:
    if not isinstance(doc, dict) or not isinstance(doc.get("labels"), list):
        errors.append("labels.yml: expected a mapping with a `labels` list")
        return set()

    names: set[str] = set()
    # GitHub label names are unique case-insensitively, so every comparison
    # below is on the lowercased name.
    seen: dict[str, str] = {}

    def claim(key: str, owner: str) -> None:
        folded = key.lower()
        if folded in seen:
            errors.append(f"labels.yml: {key!r} ({owner}) collides with {seen[folded]}")
        else:
            seen[folded] = owner

    for i, entry in enumerate(doc["labels"]):
        where = f"labels.yml: labels[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected a mapping")
            continue
        unknown = set(entry) - {"name", "color", "description", "aliases"}
        if unknown:
            errors.append(f"{where}: unknown keys {sorted(unknown)}")

        name = entry.get("name")
        if not isinstance(name, str) or not NAME.match(name) or len(name) > MAX_NAME:
            errors.append(
                f"{where}: name {name!r} must match {NAME.pattern}, at most {MAX_NAME} chars"
            )
            continue
        where = f"labels.yml: {name}"
        names.add(name)
        claim(name, "a label")

        color = entry.get("color")
        if not isinstance(color, str) or not COLOR.match(color):
            errors.append(f"{where}: color {color!r} must be six uppercase hex digits, quoted")

        description = entry.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{where}: description is required")
        elif len(description) > MAX_DESCRIPTION:
            errors.append(
                f"{where}: description is {len(description)} chars; GitHub allows {MAX_DESCRIPTION}"
            )

        aliases = entry.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(a, str) and a for a in aliases):
            errors.append(f"{where}: aliases must be a list of names")
            continue
        for alias in aliases:
            claim(alias, f"an alias of {name}")

    retired = doc.get("retired", [])
    if not isinstance(retired, list) or not all(isinstance(r, str) and r for r in retired):
        errors.append("labels.yml: retired must be a list of names")
    else:
        for name in retired:
            claim(name, "a retired label")

    return names


def check_forms(names: set[str], errors: list[str]) -> int:
    forms = sorted(p for p in FORMS.glob("*.y*ml") if p.stem != "config")
    for path in forms:
        rel = path.relative_to(ROOT).as_posix()
        form = yaml.safe_load(path.read_text(encoding="utf-8"))
        labels = form.get("labels", []) if isinstance(form, dict) else []
        if isinstance(labels, str):
            labels = [part.strip() for part in labels.split(",")]
        for label in labels:
            if label not in names:
                errors.append(f"{rel}: applies {label!r}, which labels.yml doesn't define")
        types = [label for label in labels if label.startswith("type:")]
        if len(types) != 1:
            errors.append(f"{rel}: must apply exactly one type:* label, applies {types}")
    return len(forms)


def main() -> int:
    errors: list[str] = []
    names = check_labels(yaml.safe_load(LABELS.read_text(encoding="utf-8")), errors)
    forms = check_forms(names, errors)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"ok: {len(names)} labels, {forms} issue forms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
