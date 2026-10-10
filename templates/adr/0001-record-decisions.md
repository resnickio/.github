---
status: accepted
date: YYYY-MM-DD
---

# 0001: Record architecture decisions

## Context

Some decisions in this repository will have work that depends on them. Unless the decision and its reasons are written down, a later change, made by a person or an agent, will contradict it without knowing it did.

## Decision

Record those decisions as ADRs in `docs/adr/`, following [resnickio/.github standards/decisions.md](https://github.com/resnickio/.github/blob/main/standards/decisions.md):
- Number them `NNNN`.
- Start each from `0000-template.md`.
- Each starts as `proposed` and is accepted by the maintainer before dependent work starts.

## Consequences

- A decision has one place to live, and the reason for it outlives the conversation that produced it.
- Writing an ADR costs time up front. That cost is the point for decisions that are expensive to reverse, and it's waived for ones that aren't (see "When to write one" in the standard).
- **Invariant introduced:** an accepted ADR is never contradicted silently; it is superseded by a new one.
