# Go

## Toolchain

- **`go.mod`'s `go` directive is the version.** CI reads it with `actions/setup-go` and `go-version-file: go.mod`. Never hard-code a version in a workflow.
- **Keep current with patch releases.** govulncheck will force it anyway: the standard library ships security fixes in patches.
- **`go.mod` stays tidy.** CI runs `go mod tidy -diff` and fails on any output.

## Lint and format

golangci-lint v2, configured in `.golangci.yml`:

```yaml
version: "2"

linters:
  enable:
    - gosec
  exclusions:
    rules:
      # One rule, one path, one reason. Never disable a rule wholesale.
      # - path: '^internal/exec/runner\.go$'
      #   linters: [gosec]
      #   text: '^G204:'

# The defaults hide everything past the third identical finding and the
# fiftieth per linter, which turns a count into a sample. A gate reports
# everything.
issues:
  max-issues-per-linter: 0
  max-same-issues: 0

formatters:
  enable:
    - gofmt
    - goimports
```

- **Install the release binary, verified by checksum.** CI installs it from the release tarball with the sha256 pinned next to the version. A local `lint` script refuses a binary whose version differs.
- **One-off suppressions** are inline, with the rule and a reason: `//nolint:gosec // G304: path is from the operator's own config`.
- **No standalone `go vet` step.** golangci-lint's govet runs the same analyzers.

## Tests

- **`go test -count=1 ./...`** in CI, so restored caches can't replay "ok (cached)" for tests that didn't run.
- **Run `-race` at least on pushes to `main`,** and on PRs when the suite is fast enough.
  - It needs cgo and a C toolchain, which `ubuntu-latest` has.
  - A concurrent test gets its positive control under the detector: remove the lock, watch it report.
- **Skips are audited.** Run with `-json` and fail on any skip that isn't on a committed expected list. A skipped test is a check that didn't run.

## Vulnerabilities

govulncheck, pinned by version: `go install golang.org/x/vuln/cmd/govulncheck@vX.Y.Z`.
- It fails only on vulnerabilities reachable from your code.
- A hit is fixed by a bump, or excluded with a comment naming the follow-up issue.

## Builds

- Use `CGO_ENABLED=0 -trimpath` for anything shipped as a binary or in a container, unless cgo is genuinely needed.
- Inject the version with `-ldflags "-X main.version=…"`, never by editing source.

## Releases

This applies to libraries, providers and CLIs.

- Tag `vX.Y.Z` (SemVer) and run a workflow triggered by the tag. A module at v2 or later changes its import path (`/v2`).
- Use goreleaser at a **pinned version**, never `latest`, with signed checksums.
- **No `before` hooks that change the tree,** such as `go mod tidy`. The release must build exactly the commit that was tagged and gated; tidiness is checked in CI instead.
- The signing-key import action is pinned by SHA, like every action.
