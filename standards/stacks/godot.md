# Godot and C#

## Engine

- **Pin the engine version exactly** in the workflow's `env:`, for example `GODOT_VERSION: 4.6.2-stable`.
  - CI downloads it and verifies the SHA-512 from the release's checksum file before running it.
  - The cache key includes that checksum.
- **Upgrade the engine in its own PR,** with the project re-imported and the result committed.

## Tests

- Run headless suites and a clean-shutdown check in CI.
- **Judge by stderr, not by exit code.** Godot can exit 0 after a script fails to compile, so the runner greps the log for `ERROR:` and `SCRIPT ERROR`, and fails on either.
- **Start from a cold import** (no `.godot/`) in CI, so a stale cache can't hide an import failure.

## Warnings are errors

- **GDScript:** run a strict pass with the warnings that matter set to error (`=2`) in a copy of `project.godot`.
- **C#:** set `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` and `<Nullable>enable</Nullable>`, and build with `-warnaserror`.

## .NET

- Commit a `global.json` pinning the SDK. CI's `setup-dotnet` reads it.
- Keep deterministic simulation code in its own project with no Godot dependency, so it's testable with NUnit and no engine.

## Repository files

```gitattributes
* text=auto eol=lf
*.res binary
*.scn binary
*.png binary
*.wav binary
*.ogg binary
```

```gitignore
.godot/
export_presets.cfg   # can hold signing credentials
*.translation
```

Large binary assets use Git LFS, or stay out of the repository entirely.
