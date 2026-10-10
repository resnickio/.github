# Security

## Secrets

**Never in git.** This covers code, tests, fixtures, compose files, CI config, Terraform state and docs.

- **`.env` is gitignored, and `.env.example` is committed** with placeholder values and a comment per variable. The standard `.gitignore` lines:

  ```gitignore
  .env
  .env.*
  !.env.example
  ```

- **pre-commit blocks `.env` files outright** with a `language: fail` hook, so a forced `git add -f` still can't commit one:

  ```yaml
  - repo: local
    hooks:
      - id: block-env-files
        name: Block .env files (only .env.example is allowed)
        language: fail
        entry: "Secrets never go in git. Commit a .env.example with placeholder values instead:"
        files: '(^|/)\.env(\..+)?$'
        exclude: '(^|/)\.env\.example$'
  ```

- **gitleaks runs twice:** in pre-commit on each commit, and in CI over the full history.
  - An allowlist entry in `.gitleaks.toml` or `.gitleaksignore` is narrow: one rule, one path, with the reason in a comment.
  - Vendored test keys from deliberately vulnerable apps are allowlisted by path and labeled as public.
- **Never bypass hooks.** No `--no-verify`. If a hook is wrong, fix the hook in its own PR.

**Where real secrets live:**

| Context | Store |
|---|---|
| Your machine | The OS credential store or a password manager, loaded into the environment at run time |
| CI | Environment secrets, scoped to the job that needs them. OIDC instead of a stored secret wherever the provider supports it. |
| Terraform | Remote state with encryption at rest. Never a local `terraform.tfstate` holding credentials. Variables holding secrets are `sensitive = true`. |
| Containers | Injected at run time. Never baked into an image layer, and never in a `.dockerignore`-less build context. |

**Logs:**
- Never log credentials, tokens or full connection strings.
- Mask anything that looks like one in error messages.

## Dependencies

Every repository commits a `dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule: { interval: weekly, day: monday }
    cooldown: { default-days: 7 }
    open-pull-requests-limit: 5
    labels: ["type:chore"]
    commit-message: { prefix: "deps" }
    groups:
      actions: { patterns: ["*"], update-types: [minor, patch] }
  # One entry per ecosystem (uv, npm, gomod, terraform, nuget, …) and one for
  # `docker` wherever there is a Dockerfile, in the same shape. Majors stay
  # ungrouped, so a breaking change is never bundled with noise.
```

- **An `ignore` entry carries a comment** naming the blocker and when to revisit. For example, "stay on Django 5.2 LTS until 6.2 LTS."
- **Dependabot alerts and security updates are on** in every repository. [settings/repo.json](../settings/repo.json) applies them.

## Scanning

| Stack | Scanner | Gate |
|---|---|---|
| Any | gitleaks (full history) | Any finding |
| Go | govulncheck | A reachable vulnerability |
| Python | `trivy fs` on the lockfile, or pip-audit | CRITICAL or HIGH with a fix available |
| Node | `trivy fs` on the lockfile | CRITICAL or HIGH with a fix available |
| Containers | hadolint and `trivy image` | CRITICAL or HIGH with a fix available |
| Terraform, Dockerfiles, workflows | checkov or `trivy config` | Per policy |
| Source (SHOULD) | semgrep with the security rulesets, plus project-specific rules | Any finding |

- **`ignore-unfixed`** keeps the gate actionable. A CVE with no fix gives the author nothing to do except disable the gate.
- **Every ignore entry** (`.trivyignore.yaml`, `nolint`, `# nosec`, a gitleaks allowlist) carries a reason and, where the format allows, an **expiry date**. An expired ignore fails the scan again, and that's the point.

## Least privilege in code

- Containers run as a non-root numeric UID. See [containers](stacks/containers.md).
- Local development stacks bind to `127.0.0.1`, never to all interfaces. This matters most for deliberately vulnerable test targets.
- Infrastructure defaults to closed: no `0.0.0.0/0` ingress defaults, SSH restricted to known ranges or a VPN.

## Public repositories

On top of everything above, a public repository has:
- **secret scanning and push protection** turned on
- **private vulnerability reporting** turned on. The [security policy](../SECURITY.md) points reporters there.
- **the default-branch ruleset.** This is non-negotiable for anything that publishes signed releases: an unprotected `main` means anyone holding your credentials can push straight to what gets signed.
- **release signing keys** used only by pinned (SHA) actions, in a job with `contents: write` and nothing else

## Reporting

[SECURITY.md](../SECURITY.md) is the account-wide default. A repository with different needs, such as a supported-versions table, writes its own.
