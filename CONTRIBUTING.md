# Contributing

These are personal projects with one maintainer.
- **Issues** are welcome on every repository you can see.
- **Pull requests** are welcome on public repositories. Please open an issue first, so we agree on the change before you spend time on it.

## The short version

1. **Start from an issue.** Every pull request closes or advances one, with `Closes #N` in its description.
2. **Branch from an up-to-date `main`**, named `<type>/<issue>-<slug>`, for example `fix/42-empty-name`.
3. **Run the repository's `check` command before you push.** It runs exactly what CI's `gate` job runs. The README or CLAUDE.md says what it is.
4. **Title the pull request `<area>: <change>`**, for example `api: reject an empty project name`. The title becomes the commit subject on `main`.
5. **Fixing a bug? Add the test that would have caught it**, and check that it fails without your fix.

The full rules are in [standards/](https://github.com/resnickio/.github/tree/main/standards). When a repository's own README, CONTRIBUTING.md or CLAUDE.md says something different, the repository's version wins.

## Licensing

By contributing to a repository, you agree that your contribution is licensed under that repository's license.
