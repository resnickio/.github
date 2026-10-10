# Git workflow

From issue to `main`.

## Issues

Every piece of work starts as an issue, using one of the [issue forms](../.github/ISSUE_TEMPLATE).

| Type | Is | Done when |
|---|---|---|
| `type:epic` | An outcome delivered by several stories | Its exit criteria hold |
| `type:story` | A vertical slice that changes what someone can see or do; one to three PRs | Its acceptance criteria hold on `main` |
| `type:task` | One PR of work | Its "done when" list holds and the PR is merged |
| `type:bug` | Behavior that contradicts something written down | Fixed on `main` with a regression test |
| `type:spike` | A time-boxed question | The written answer is where the issue said it would be |
| `type:adr` | A decision that blocks work | The ADR is `accepted` (or `rejected`) |
| `type:chore` | Maintenance with no behavior change | Merged |

- **Hierarchy:** epics → stories → tasks, using GitHub's native **sub-issues**, never a checklist in the body. Small work skips levels: a task with no story is fine.
- **Sizing:** an issue is sized so a single agent session can finish it.
  - `agent:ready` means the body alone gives a fresh session enough to start and finish: what to change, where, and how to tell it's done.
  - If you would have to explain it out loud, it isn't ready.
- **Labels:** exactly one `type:*`, at most one `priority:*`, and `status:*` as needed. Areas are `area:*`, defined per repository. The taxonomy lives in [labels.yml](../labels.yml).
- **Blocking:** an issue waiting on a decision carries `status:needs-adr`. One waiting on another issue carries `status:blocked` and names it in the body.
- **Milestones** are roadmap phases. An issue belongs to at most one.
- **Titles:** tasks and bugs use the same `<area>: <change>` form as pull requests. Stories are `<who> can <what>`. Spikes are `Spike: <question>`. Decisions are `ADR: <decision>`.

## Branches

Name branches **`<type>/<issue>-<slug>`**:

```
feat/57-export-csv
fix/228-timeout-on-retry
docs/112-restore-runbook
```

- The type is one of `feat`, `fix`, `docs`, `chore`, `ci`, `test`, `refactor`, `spike` or `adr`.
- Branches Claude Code creates (`claude/…`) are fine. Include the issue number when there is one.
- Branch from a freshly fetched `origin/main`, never from whatever happens to be checked out.
- Branches are deleted on merge, automatically.

## Commits and pull request titles

The **pull request title** is what lands on `main`. With squash merging, the title becomes the commit subject. Its form is:

```
<area>: <change>
```

- **`area`** is the part of the system that changed. It's usually a component matching an `area:*` label, written in lowercase.
  - When a change cuts across, use `docs`, `deps`, `ci`, `build` or `test`.
  - Several areas are comma-joined: `api, cli: …`.
- **`change`** is imperative and lowercase, with no trailing period. It completes the sentence "This change will …".
- **Aim for 72 characters or fewer.** It's a guideline, not a gate. A precise long title beats a vague short one.
- GitHub appends `(#N)` when it squashes. Don't add it yourself.

```
api: reject an empty project name
scheduler: retry a run that timed out once before failing it
deps: go 1.26.9 and golang.org/x/net v0.60.0
docs: add ADR-0012, choosing Postgres for the event store
```

**Commits on a branch** are free-form. They are squashed away, so commit as often as is useful. Two things still apply:
- **Each commit should build.** It makes `git bisect` on a branch possible.
- **AI attribution.** A commit made with an AI agent carries its trailer, spelled exactly `Co-Authored-By:` (for example `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). Squashing keeps them: the squash commit's body includes each branch commit's message.

## Pull requests

1. **Open it as a draft** until the repository's `check` command passes locally.
2. **Fill in the template:** What, Why, Contracts and decisions, Verified. "Verified" says what you ran and what you saw.
3. **Put `Closes #N` in the description**, or `Part of #N` if the PR advances an issue without finishing it.
4. **Don't merge until `gate` is green.** The ruleset enforces it.
5. **Review threads:** reply to each one.
   - If you change something for it, say what changed, then resolve the thread.
   - If you disagree, say why and leave it open for the reviewer.
   - Never resolve a thread you didn't address. The ruleset requires every thread to be resolved before merge.
6. **An agent never merges its own pull request.** The maintainer merges.

## Merging

**Squash only.**
- The commit subject is the PR title.
- The body keeps the branch's commit messages, `Co-Authored-By` trailers included.
- `main` reads one line per pull request.

A repository that deliberately keeps merge commits says so and why, in its own `.github/repo-settings.json`. See [repo-settings.md](repo-settings.md).

## The `check` command

Every repository has **one command that runs exactly what CI's `gate` runs**. It is named `check` in whatever task runner the repository already uses:

| Runner | Command |
|---|---|
| Make | `make check` |
| npm / pnpm | `npm run check` |
| Scripts | `hack/check.sh` |
| pre-commit only | `uvx pre-commit@<version> run --all-files` |

- The README and CLAUDE.md name it.
- If `check` passes locally and `gate` fails, the difference between them is a bug to fix.

## Releases

This applies only to repositories that publish something versioned: libraries, providers and CLIs.

- **Versions are SemVer.** Tag `vX.Y.Z` with an annotated tag on a commit that's on `main`.
- **A workflow triggered by the tag builds and publishes the release.** It is never published from a laptop.
- **Release notes are generated from PR titles.** This is one more reason titles say what changed.
- **Deployed applications deploy from `main` through CI,** never from an ungated push. If versions are needed there, CalVer (`YYYY.MM.DD_N`) is fine.
