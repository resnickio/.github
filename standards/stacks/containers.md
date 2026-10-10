# Containers

## Dockerfiles

```dockerfile
# syntax=docker/dockerfile:1
# ↑ Must be the very first line. A parser directive anywhere after a comment
#   or instruction is silently treated as an ordinary comment.

ARG PYTHON_IMAGE=python:3.13-slim-bookworm@sha256:<digest>

FROM ${PYTHON_IMAGE} AS build
# … install from the lockfile, with cache mounts …

FROM ${PYTHON_IMAGE} AS runtime
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=build --chown=10001:10001 /app /app
USER 10001:10001
HEALTHCHECK CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
```

- **Use multi-stage builds.** The runtime stage holds no compilers, package managers or build caches.
- **Pin base images by digest:** `tag@sha256:…`. The tag documents intent and the digest guarantees it. Dependabot's `docker` ecosystem keeps both current.
- **Never use `latest`,** for base images or for tools fetched during the build.
- **Run as a numeric non-root user,** `USER 10001:10001`. On distroless, use `65532:65532` (`nonroot`). A numeric UID lets Kubernetes' `runAsNonRoot` verify it; a name doesn't.
- **Use the smallest runtime that works:**
  - `distroless/static` for static binaries
  - `-slim` Debian images for interpreted languages
  - `scratch` only for a static binary, and still with a `USER`
- **Install from the lockfile.** The image must contain exactly what CI tested.
- **Verify downloads.** `curl` in a Dockerfile is followed by a checksum check.
- **Services get a `HEALTHCHECK`.** Use a stdlib or in-binary check, so there's no curl in the runtime image just for this.
- **Add OCI labels** (`org.opencontainers.image.source`, `.revision`, `.version`), so an image can be traced to a commit.

## `.dockerignore`

Every build context has one. At minimum:

```
.git
.github
.env
.env.*
!.env.example
.venv
node_modules
**/__pycache__
data/
docs/
```

Without it, everything in the context directory is sent to the build. That includes gitignored secrets and local data, whether or not anything `COPY`s it.

## Compose

- Ports bind to loopback: `"127.0.0.1:5432:5432"`, never `"5432:5432"`.
- Images are pinned like base images: tag plus digest, or at least a full version tag. Never a major-only tag or `latest`.
- Secrets come from the environment or Docker secrets, never inline.

## CI

- **hadolint** on every Dockerfile.
- **Build the image in CI,** even when nothing publishes it. An image that only gets built at deploy time breaks at deploy time.
- **`trivy image`** on the result: CRITICAL and HIGH, ignore-unfixed.
- **Publishing:**
  - push by digest
  - generate an SBOM (syft)
  - sign and attest keylessly (cosign, with `id-token: write`)
