# TypeScript and Node

## Toolchain

- **Use an active LTS Node: 22 or 24.** Never a release past end-of-life; Node 20 reached EOL in April 2026.
- **Declare the toolchain in `package.json`:**

  ```json
  {
    "engines": { "node": ">=22" },
    "packageManager": "pnpm@<version>"
  }
  ```

  CI's `actions/setup-node` reads the version from `engines`, or from an `.nvmrc`. It's never hard-coded in the workflow.
- **Pick one package manager** per repository (npm or pnpm), commit its lockfile, and install frozen: `npm ci` or `pnpm install --frozen-lockfile`.
- **Monorepos** use workspaces (npm `workspaces` or `pnpm-workspace.yaml`) with one lockfile at the root.

## Types

`tsconfig.json` sets at least:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

- Frameworks with their own strict preset, such as `astro/tsconfigs/strict`, extend it and add the above.
- CI type-checks with `tsc --noEmit`, or the framework's checker. A passing build is not proof that types check.

## Format and lint

- **Use one formatter** (prettier), pinned in `package.json`.
  - CI runs `format:check`.
  - pre-commit runs it as a local hook through the package manager, so there is one version of truth: `npm exec --no -- prettier --write --ignore-unknown`.
- **Add ESLint** where the framework has rules worth having, such as React hooks. Type-checking does most of what generic lint rules used to.

## Generated code

Types generated from a schema (OpenAPI, JSON Schema) are never written by hand. A script regenerates them, and CI fails if the committed output differs (see [principles](../principles.md#4-generated-code-is-never-edited-by-hand)).

## Scripts

`package.json` exposes the standard names:

```json
{
  "scripts": {
    "check": "npm run format:check && npm run typecheck && npm run test && npm run build",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "build": "…"
  }
}
```

## Tests

- vitest for units.
- Anything that depends on layout, WebGL, workers or real browser behavior gets a Playwright test against the production build, because jsdom can't see those failures.
- Browser tests stub the network so a slow third party can't turn them red.
