# Repository settings

## Settings

[settings/repo.json](../settings/repo.json) is applied to every repository:

| Setting | Value | Why |
|---|---|---|
| Merge methods | Squash only | One commit per PR on `main`. The title convention is enforced in one place: the PR title. |
| Squash commit title | PR title | The convention in [git-workflow.md](git-workflow.md#commits-and-pull-request-titles) |
| Squash commit message | Commit messages | Keeps each commit's `Co-Authored-By` trailer |
| Delete branch on merge | On | Merged branches are noise, and stale ones get pushed to by mistake |
| Allow auto-merge | On | Lets a PR merge itself once `gate` is green (useful for Dependabot) |
| Suggest updating branches | On | The ruleset requires branches to be current with `main` |
| Wiki | Off | Docs live in the repository, where they're reviewed and versioned |
| Dependabot alerts and security updates | On | Free on every repository |
| Secret scanning and push protection | On, public repositories only | Not available on private repositories owned by a personal account |
| Private vulnerability reporting | On, public repositories only | Where [SECURITY.md](../SECURITY.md) sends reporters |

### Exceptions

A repository that must differ commits `.github/repo-settings.json` **in its own repository**. The file holds only the overriding keys and a `$reason`:

```json
{
  "$reason": "Merge commits record which PR landed which commits; ADR-0019.",
  "repo": { "allow_merge_commit": true, "allow_squash_merge": false },
  "ruleset": { "allowed_merge_methods": ["merge"] }
}
```

The file can contain these keys:

| Key | Contents |
|---|---|
| `$reason` | Required. Why this repository differs. |
| `repo` | Any key from [settings/repo.json](../settings/repo.json)'s `repo` section |
| `security` | Any key from its `security` section |
| `ruleset.allowed_merge_methods` | A list of merge methods, such as `["merge"]` |
| `ruleset.required_status_checks` | A list of check names. Each is required from GitHub Actions and replaces `gate`. |

The scripts reject any other key, and they reject a file without a `$reason`.

The exception lives with the repository it applies to, and nothing in this public repository has to name a private one. **Commit it before the baseline is applied to that repository;** otherwise the baseline overwrites the setting the exception exists to keep.

## The default-branch ruleset

[settings/ruleset-main.json](../settings/ruleset-main.json) is applied to every repository's default branch:

| Rule | Why |
|---|---|
| No deletion, no force-push | `main` is history. Rewriting it breaks every clone and erases the record of what was gated. |
| Pull request required, 0 approvals | With one maintainer, an approval is a rubber stamp. Requiring the PR is what forces the work through `gate`. |
| All review threads resolved | Review feedback, human or Copilot, is answered before merge, not lost |
| Merge method: squash | Matches the settings above |
| Required check: `gate`, from GitHub Actions, branch up to date | One aggregate check (see [ci.md](ci.md#the-gate-job)). Requiring it from the Actions app (ID 15368) means a commit status posted by any other token can't satisfy it. |
| **Bypass: nobody** | An AI agent acts with your credentials, so an admin bypass is also an agent bypass. For a real emergency, disable the ruleset, which leaves an audit-log entry, do the thing, and re-enable it. |

**Order matters when rolling this out.** Apply the ruleset only after the repository's CI reports a check named `gate`. A required check that never reports blocks every merge.

## Files every repository has

| File | Source | Notes |
|---|---|---|
| `.gitattributes` | `templates/common/` | `* text=auto eol=lf`. Without it, a Windows machine with `core.autocrlf=true` checks out CRLF and LF-enforcing tools fail locally. |
| `.editorconfig` | `templates/common/` | Checked by editorconfig-checker in pre-commit |
| `.gitignore` | `templates/common/` plus the stack | Must include the `.env` lines from [security.md](security.md#secrets) |
| `.pre-commit-config.yaml` | `templates/common/` plus the stack | Also run by CI |
| `.github/dependabot.yml` | `templates/common/` | See [security.md](security.md#dependencies) |
| `.github/workflows/ci.yml` | `templates/common/` | Ends in `gate` |
| `LICENSE` | `templates/licenses/` | Proprietary for private repositories, MIT for public. GitHub can't provide a default. |
| `README.md` | — | What it is, how to run it, the `check` command |
| `CLAUDE.md` | `templates/CLAUDE.md` | See [agents.md](agents.md#claudemd) |

These come from this repository's defaults unless a repository overrides them:
- SECURITY.md
- CONTRIBUTING.md
- issue forms
- the PR template

A repository with its own `.github/ISSUE_TEMPLATE/` folder loses **all** the default forms, not just the ones it replaces. It should then carry every form it needs.

**Not required:** CODEOWNERS. With one maintainer it routes every review to the same person and enforces nothing. Add it only if a second person ever reviews.
