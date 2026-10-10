# Principles

The rules the rest of the standard follows from. Each one exists because ignoring it cost real time at least once.

## 1. Issue first

Every pull request closes or advances an issue.
- When work turns up something out of scope, it becomes a new linked issue, not a bigger PR.
- A PR that does two things gets reviewed as neither.

## 2. Decide before building

A change that needs a decision no ADR covers stops, and a `proposed` ADR gets written with options and a recommendation. Building waits until it is accepted. See [decisions.md](decisions.md).

An accepted ADR is never contradicted silently. If it's wrong, a new ADR supersedes it.

## 3. Contracts are versioned

Schemas, wire formats, APIs and file formats that something else reads are contracts.
- An additive change is fine.
- A breaking change bumps the version, and the PR calls it out.
- A reader is never broken silently.

## 4. Generated code is never edited by hand

- Change the source and regenerate.
- CI regenerates and fails if the result differs from what's committed. Use `git status --porcelain`, not `git diff --exit-code`: a newly generated file is untracked, and `git diff` reports a tree with only untracked changes as clean.

## 5. A check you haven't seen fail proves nothing

A test that passes the first time it runs might be testing nothing.
- Every new test, gate and assertion gets a positive control: break the code it guards, watch it go red, then put the code back.
- That applies to CI steps too. A pipeline that can't fail is decoration.

## 6. Every bug fix ships with its regression test

The test lands in the same PR as the fix, and it fails without the fix (see 5).

## 7. Fail loudly

- **No silent defaults.** An unknown flag, a missing config key or an ambiguous input raises an error. It is never treated as "off" or "empty".
- **A check that didn't run says so.** A skipped test, a disabled scanner or a narrower run on this event says so where a reader will see it: in the run summary, not in a log fold nobody opens.

## 8. Measure, don't assume

- Verify against the real system where that's possible: a real protocol, a real build artifact, a real run, not only mocks.
- Report what was measured, not what was intended. "Tests pass" means you ran them and saw them pass.

## 9. Comments explain why

- The code says what it does. A comment says why it does it that way, or what was tried and rejected.
- A comment that makes a claim about another file, a version or a behavior gets checked when the claim is made, and fixed when it stops being true.

## 10. Git holds source, not secrets or bulk

Never commit:
- secrets
- third-party assets you don't have the right to redistribute
- large binaries or data beyond small test fixtures

pre-commit enforces a size cap. See [security.md](security.md#secrets).

## 11. Pin everything

- **Locked:** dependencies.
- **By version and checksum:** tools.
- **By commit SHA:** actions.
- **By digest:** base images (SHOULD).

An unpinned input is a build that can change without a commit. See [ci.md](ci.md#pinning).

## 12. No premature abstraction

The second consumer pays for generality. Until then, the simplest thing that serves the one real use is correct.

## 13. Docs change with the code

When a PR changes behavior, operator steps or a contract, it updates the README, runbook or ADR that describes them in the same PR.
