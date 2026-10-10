# resnickio/.github

Account-wide defaults and engineering standards for repositories owned by [@resnickio](https://github.com/resnickio).

## What's here

| Path | What it is | How it reaches other repositories |
|---|---|---|
| [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md) | Community health defaults | Automatic. GitHub shows them for any repository without its own. |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE) | Default issue forms | Automatic, but only for repositories with **no** `.github/ISSUE_TEMPLATE/` folder of their own. A repo's own folder replaces all of these, not just the matching ones. |
| [`.github/pull_request_template.md`](.github/pull_request_template.md) | Default pull request template | Automatic, for repositories without their own. |
| [`labels.yml`](labels.yml) | The global label taxonomy | Synced by script. Labels are never inherited, and an issue form can only apply a label that already exists in the repository. |
| [`standards/`](standards) | The engineering standard | Linked from each repository's CONTRIBUTING and CLAUDE.md. |
| [`settings/`](settings) | Baseline repository settings and the default-branch ruleset | Applied per repository by script. |
| [`templates/`](templates) | Copy-in starters | Copied when a repository is created or brought up to standard. |

## Rules for this repository

- **It is public, because it has to be.** GitHub only serves defaults from a public `.github` repository.
  - Nothing here may name, describe or report on a private repository.
  - Scripts that work across repositories run locally and print to the terminal, never to this repository's workflow logs or issues.
- **Changes follow the standard they describe:** issue, branch, pull request, green `gate`.
- **The `check` command** for this repository is:

  ```sh
  uvx pre-commit@4.6.2 run --all-files
  ```

  Install the hooks once per clone with `uvx pre-commit@4.6.2 install`.

## Scripts

These scripts bring other repositories up to the baseline. They run **on your machine**, using your `gh` login, and print only to your terminal.

- They never run in this repository's CI: their output names private repositories.
- Every script that changes something is a dry run unless you pass `--apply`.
- Choose targets with `--repo NAME` (repeatable) or `--all`. `--all` covers every non-fork, non-archived repository.

| Command | What it does |
|---|---|
| `uv run scripts/audit.py --all --details` | Read-only report of every repository against the baseline |
| `uv run scripts/apply_settings.py --all` | Merge settings, branch cleanup, Dependabot, and the security features for public repositories ([settings/repo.json](settings/repo.json)) |
| `uv run scripts/sync_labels.py --all [--prune]` | Global [labels.yml](labels.yml) plus each repository's own `.github/labels.yml`. Old names are renamed or merged, so no issue loses a label. `--prune` deletes retired labels that no issue still carries. |
| `uv run scripts/apply_ruleset.py --all [--without-checks]` | The default-branch ruleset ([settings/ruleset-main.json](settings/ruleset-main.json)). It refuses to require `gate` until the branch reports it. `--without-checks` applies the rest and keeps any checks the existing ruleset already requires. |
| `uv run scripts/validate.py` | This repository's own check that `labels.yml` and the issue forms agree. It also runs in pre-commit. |

**Before an `--all --apply`:** make sure every repository that needs an exception already has its `.github/repo-settings.json`. Without it, the baseline applies there as well. See [standards/repo-settings.md](standards/repo-settings.md#exceptions).

## Limits of a personal account

`resnickio` is a user account, not an organization, so some features don't apply:

- **No workflow templates.** The "New workflow" starters are organization-only. Shared CI is delivered as reusable workflows (`workflow_call`) plus files in `templates/`.
- **No account-wide rulesets.** [`settings/ruleset-main.json`](settings/ruleset-main.json) is applied to each repository individually.
- **No default LICENSE or CODEOWNERS.** Every repository carries its own LICENSE.
- **No code scanning or secret scanning on private repositories** without GitHub Advanced Security. gitleaks in pre-commit and CI is the control there, and SARIF uploads are best-effort.
- **The profile README** lives in `resnickio/resnickio`, not here.
