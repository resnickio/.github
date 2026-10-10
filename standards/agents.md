# AI agents

Rules for Claude Code, Copilot and any other agent that changes a repository. They're stricter than the rules for a human in a few places, because an agent acts with the maintainer's credentials and can't be asked afterwards what it meant.

## Rules

1. **Work from an issue.** A session starts from an issue and ends in a PR that `Closes` it, or `Part of` it. Anything else that comes up becomes a new issue.
2. **Branch from a fresh `origin/main`.** Never commit to `main`; the ruleset refuses it anyway.
3. **Stage files explicitly.**
   - Use `git add <path>`, not `git add -A` or `git add .`. That keeps scratch files, logs and local config out of commits.
   - Never use `--no-verify`.
4. **Run `check` before opening a PR,** and report what it printed. "Verified" in the PR template means you ran it and saw it pass. It doesn't mean it should pass.
5. **Never merge your own PR,** and never accept your own ADR. Draft, recommend, and stop.
6. **Stop at an undecided decision.** If the work needs a choice no ADR covers, write a `proposed` ADR and stop. Don't pick one and keep going.
7. **Don't widen scope.** Adjacent improvements become issues, not diff.
8. **Handle review threads honestly.** Reply to each thread. Resolve it only if you changed something for it. Say what you changed.
9. **Attribute.** Commits carry the agent's `Co-Authored-By:` trailer.
10. **Prove tests can fail.** For each new test, break the code it guards and watch it go red before you trust it (see [principles](principles.md#5-a-check-you-havent-seen-fail-proves-nothing)).

## CLAUDE.md

Account-wide rules, which means this standard, live in the user-level `~/.claude/CLAUDE.md`. A repository's CLAUDE.md holds **only what is specific to that repository**, in this order:

```markdown
# <repository>

Standards: https://github.com/resnickio/.github/tree/main/standards
These apply here except where this file says otherwise.

## What this is
One paragraph: what it does, who uses it, what state it's in.

## Read first
The two or three files a new session must read before changing anything.

## Invariants
Rules every change must respect, each with its ADR number. Numbered, so they can be cited.

## Commands
The `check` command first, then build, run, test, and anything else a session needs.

## Layout
Where things live, only where it isn't obvious from the tree.

## Testing
What's special about testing here: fixtures, live tests and how they're gated, what a real-system check looks like.

## Decisions
A pointer to docs/adr/, or (for a small repository) the decisions themselves.
```

- **The two-line pointer at the top matters.** Sessions that don't load the user-level file still find the standard through it: cloud sessions, CI agents and Copilot review.
- **Don't restate the standard.** A repository CLAUDE.md that copies these rules drifts from them.
- **Exceptions are explicit.** "This repository keeps merge commits (ADR-0019)" beats silence.
- **Keep it current.** A CLAUDE.md that describes last month's layout is worse than none. When a PR changes something CLAUDE.md describes, update it in the same PR.
