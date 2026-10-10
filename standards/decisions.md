# Decisions (ADRs)

An Architecture Decision Record captures a decision that other work depends on: what was decided, what else was considered, and why.

## When to write one

Write an ADR before building anything that depends on a decision that isn't written down yet. Examples:
- choosing a technology, protocol, storage engine or hosting provider
- defining or breaking a contract (a schema, an API, a file format)
- adding an invariant that every future change must respect
- reversing or narrowing an earlier ADR

Not every choice is an ADR. If reversing it later would touch only the code that made it, a comment explaining why is enough.

## Where they live

```
docs/adr/
├── README.md               index: number, title, status
├── 0000-template.md        copied from templates/adr/ in this repository
├── 0001-record-decisions.md
└── 0002-…
```

- **File names:** `NNNN-kebab-case-title.md`, four digits, never reused. Opening the file reserves the number.
- **Heading:** `# NNNN: Short title`.
- **Status:** front matter, in lowercase:
  - `proposed`
  - `accepted`
  - `rejected`
  - `deprecated`
  - `superseded by NNNN`

## The process

1. **Open a `type:adr` issue** with the [Decision form](../.github/ISSUE_TEMPLATE/adr.yml). Label each issue it blocks `status:needs-adr`.
2. **Write the ADR as `proposed`.** Include the options, the tradeoffs and a recommendation.
   - The PR touches only `docs/adr/`.
   - Code that depends on the decision waits.
3. **The maintainer accepts or rejects it,** by flipping the status in the PR or in a follow-up.
   - An agent may draft and recommend.
   - **An agent never accepts its own proposal.**
4. **Unblock.** Remove `status:needs-adr` from the blocked issues and close the ADR issue.

## Changing a decision

- **Amend** for small corrections that don't change what was decided: a fixed link, a clarified sentence, an updated version number. Add a dated line under *Amendments*.
- **Supersede** for everything else. Write a new ADR, set the old one's status to `superseded by NNNN`, and leave its text alone. History is the point.

Never edit an accepted ADR's decision in place, and never contradict one in code without superseding it first.

## Invariants

When an ADR introduces an invariant, copy it into the repository's CLAUDE.md under *Invariants*, with the ADR number. An invariant is a rule every future change must respect. The CLAUDE.md is where agents and reviewers look before changing code.

## Small repositories

A repository with only a handful of decisions may keep them in a *Decisions* section of its CLAUDE.md: one dated line each, with the reason. Once a decision has dependent work waiting on it, it moves to `docs/adr/`.
