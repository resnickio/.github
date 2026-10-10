# CI

Rules for GitHub Actions workflows. Most of them are here because their absence once produced a green run that meant nothing.

## Triggers

```yaml
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
```

- **Never combine a bare `on: push` with `pull_request`.** Every PR then runs twice: once for the push to the branch, once for the PR.
- **Don't use `on.paths` on a workflow that holds a required check.** When the paths don't match, the workflow never runs, the required check never reports, and the PR can't merge. Filter inside the job instead: a first step decides whether there is work, and the job reports success either way.

## Permissions

```yaml
permissions:
  contents: read
```

- Set this at the top of every workflow.
- A job that needs more asks for it in its own `permissions:` block, and asks for no more than it uses: `issues: write`, `id-token: write`, `security-events: write`.
- Every `actions/checkout` sets `persist-credentials: false`, unless a later step in that job pushes.

## Concurrency

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

- A new push to a PR makes the in-flight run obsolete, so cancel it.
- **Never cancel runs on `main`.** They are the record that a commit was gated.
- Deploy workflows use their own group with `cancel-in-progress: false`, so two deploys never overlap and none is abandoned halfway.

## Shell and timeouts

```yaml
defaults:
  run:
    shell: bash
```

- **Name the shell explicitly.** A `run:` block with no `shell:` gets `bash -e {0}`, which has **no `pipefail`**. In `go test ./... | tee log`, the step's status then comes from `tee`, and a failing suite reports success. Naming `shell: bash` adds `-o pipefail`.
- **Every job sets `timeout-minutes`.** The default is six hours, which on a self-hosted runner means a hung job holds the only slot all day. The `check-github-workflows-require-timeout` hook (from check-jsonschema) enforces this in pre-commit.

## The gate job

Every CI workflow ends with one aggregate job, and **it is the only check the ruleset requires**:

```yaml
  gate:
    name: gate
    if: always()
    needs: [lint, test, security]   # every job that must pass
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - name: Every required job passed
        env:
          RESULTS: ${{ join(needs.*.result, ' ') }}
        run: |
          echo "upstream results: ${RESULTS}"
          for r in ${RESULTS}; do
            if [ "${r}" != "success" ]; then
              echo "::error::a required job did not pass (${RESULTS})"
              exit 1
            fi
          done
```

- **Why one check.** If the ruleset requires jobs by name, then renaming, adding or conditionally skipping a job silently changes what "green" means.
- **Why `if: always()`.** Without it, `gate` is *skipped* when a dependency fails, and a skipped required check counts as passing.
- **Keep `gate` in the repository's own `ci.yml`,** not inside a reusable workflow. A job inside a called workflow reports as `<caller-job> / gate`, while one in the caller reports as plain `gate`, which is what the ruleset names.
- **A job that is skipped on purpose** (for example "no Go files changed") must leave the result as `success` by running and exiting early. It must not be skipped with a job-level `if:`.

## Pinning

| Input | Pin by | Why |
|---|---|---|
| Actions | Full commit SHA, with a `# vX.Y.Z` comment | Tags are mutable. A compromised action can repoint `@v4` at malicious code in every repository that uses it. Dependabot updates the SHA and the comment together. |
| Reusable workflows from this repository | Full commit SHA | Same reason. Dependabot updates these too. |
| Tool binaries (linters, scanners) | Version plus sha256, in the workflow's `env:` | `curl` piped to a shell runs whatever the server sends. Never use `@latest` or `version: latest`. |
| Language toolchains | The repository's own version file (`go.mod`, `.python-version`, `.nvmrc`/`engines`) | One source of truth, shared by laptop and CI. |
| Dependencies | A committed lockfile, installed frozen | See below. |
| Container images | `tag@sha256:digest` | See [containers](stacks/containers.md). |

**Freshness.**
- Dependabot uses a `cooldown` of 7 days, so a release ages a week before it's adopted. Most compromised releases are caught and pulled within days.
- When pinning by hand, apply the same rule and take the previous release.

**Frozen installs**, everywhere CI or an image installs dependencies:

| Ecosystem | Command |
|---|---|
| uv | `uv sync --frozen` |
| npm | `npm ci` |
| pnpm | `pnpm install --frozen-lockfile` |
| Go | `go mod download`, plus a `go mod tidy -diff` check |
| Terraform | `terraform init` with the committed `.terraform.lock.hcl` |

A production image built without the lock runs versions that CI never tested.

## Scanning

- **Secrets:** gitleaks over the full history, with `fetch-depth: 0`. The pre-commit hook only sees what's being committed; a secret committed and later deleted is still in the history.
- **Vulnerabilities:** one scanner per stack (see [security.md](security.md#scanning)). The scanner's own exit code is the gate.
- **SARIF:** upload with `continue-on-error: true`. Code scanning isn't available on private repositories owned by a personal account, and a failed upload must not fail the build. Keep the SARIF as an artifact too.

## Caching

Use the setup action's built-in cache when it is keyed correctly; otherwise use `actions/cache/restore` and `actions/cache/save`.
- Save from `main`, not from every PR push.
- A PR restores `main`'s latest entry by prefix.
- Tests run with caching that cannot replay results: `go test -count=1`.

## Scheduled workflows

- **Cron off the hour** (`17 7 * * *`, not `0 7 * * *`). On-the-hour schedules are the ones GitHub delays or drops under load.
- **A scheduled job that opens issues** gets job-level `issues: write`, and it dedupes by title before creating one.
- **In a public repository, scheduled workflows are disabled after 60 days without activity.** Anything that matters is monitored somewhere besides its own run history.

## Deploys

- **Split build from deploy.**
  - The build job has no secrets and uploads an artifact.
  - The deploy job downloads that artifact and runs in an `environment:` that holds the credentials.
- **Prefer OIDC (`id-token: write`) over stored credentials** wherever the provider supports it (Azure, AWS, GCP). Otherwise use a narrowly scoped token stored as an *environment* secret, never a repository secret.
- **Gate deploys on CI.** A provider's "deploy on push" integration bypasses CI entirely, so it is not used for anything that matters.
- **A deploy job without credentials skips cleanly and says so.** That way forks and fresh clones still go green.

## Reusable workflows

Shared jobs live in this repository's `.github/workflows/` as `workflow_call` workflows: hygiene, language baselines, security scans and the PR title check.
- A repository calls them from its own `ci.yml`, next to its own jobs, and lists them in `gate`'s `needs:`.
- Pass secrets explicitly with `secrets:`. `secrets: inherit` is only promised within an organization.
