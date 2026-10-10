# Engineering standards

How every repository owned by [@resnickio](https://github.com/resnickio) is built, tested, reviewed and shipped.

- **MUST** is a requirement.
- **SHOULD** is the default. Departing from it needs a stated reason.

A repository may depart from any rule, even a MUST, by writing down the exception and its reason where its readers will find it: its README, its CLAUDE.md, or an ADR. An unwritten exception is a defect.

## Every repository MUST

1. **Change `main` only through a pull request with a green `gate`.** The [default-branch ruleset](repo-settings.md#the-default-branch-ruleset) enforces this, with no bypass. See [git-workflow](git-workflow.md).
2. **Start work from an issue.** Every PR closes or advances one. See [git-workflow](git-workflow.md#issues).
3. **Have CI whose single aggregate `gate` job is the only required check.** See [ci](ci.md#the-gate-job).
4. **Have one local command, `check`, that runs what `gate` runs.** See [git-workflow](git-workflow.md#the-check-command).
5. **Pin everything:** actions by full commit SHA, tools by version and checksum, dependencies by a committed lockfile with frozen installs. See [ci](ci.md#pinning).
6. **Keep secrets out of git,** enforced by gitleaks in pre-commit and in CI over the full history. See [security](security.md#secrets).
7. **Turn Dependabot alerts on, and commit a `dependabot.yml`** covering actions, every package ecosystem and Docker. See [security](security.md#dependencies).
8. **Carry the [standard files](repo-settings.md#files-every-repository-has):** `.gitattributes` (LF), `.editorconfig`, `.gitignore`, `.pre-commit-config.yaml`, LICENSE, README, CLAUDE.md.
9. **Write decisions down before building on them.** See [decisions](decisions.md).

## Every repository SHOULD

- Follow the profile for its stack: [Python](stacks/python.md), [Go](stacks/go.md), [TypeScript](stacks/typescript.md), [Terraform](stacks/terraform.md), [containers](stacks/containers.md), [Godot and C#](stacks/godot.md).
- Use the reusable workflows and templates in this repository instead of re-deriving them.
- Pin container base images by digest.

## The documents

| Document | Covers |
|---|---|
| [principles.md](principles.md) | The engineering rules everything else follows from |
| [git-workflow.md](git-workflow.md) | Issues, labels, branches, commits, pull requests, merging, releases |
| [decisions.md](decisions.md) | When and how to write an ADR |
| [ci.md](ci.md) | Workflow rules, the gate job, pinning, scheduled jobs, deploys |
| [security.md](security.md) | Secrets, dependencies, scanning, public repositories |
| [repo-settings.md](repo-settings.md) | Repository settings, the ruleset, the standard files |
| [agents.md](agents.md) | Rules for AI agents, and the shape of a CLAUDE.md |
| [stacks/](stacks) | Per-language and per-platform profiles |
