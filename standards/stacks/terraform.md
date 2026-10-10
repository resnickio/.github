# Terraform

## Versions

```hcl
terraform {
  required_version = "~> 1.16"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}
```

- **CI pins an exact Terraform version** in the workflow's `env:`. A wrapper script that runs Terraform locally uses the same one.
- **Commit `.terraform.lock.hcl`, with hashes for every platform** that runs Terraform:

  ```sh
  terraform providers lock -platform=linux_amd64 -platform=windows_amd64 -platform=darwin_arm64
  ```

## State

- **State is remote, always.** Use a backend with locking and encryption at rest: Terraform Cloud, or an S3-compatible bucket.
- **Local `terraform.tfstate` is not allowed for anything real.** State holds every secret the configuration touches, in plain text.
- **Never commit state, plans or real variable files.** Commit `*.tfvars.example` with placeholders. The `.gitignore` carries:

  ```gitignore
  .terraform/
  *.tfstate
  *.tfstate.*
  *.tfplan
  *.tfvars
  !*.tfvars.example
  ```

## Code

- **Variables that hold secrets** are `sensitive = true`. So are outputs that expose them.
- **Defaults are closed.**
  - No `0.0.0.0/0` or `::/0` ingress in a default value.
  - Callers who want open access say so explicitly.
- **Stateful resources** (volumes, databases, buckets) carry `lifecycle { prevent_destroy = true }`.
- **Refactors** use `moved` blocks, never `terraform state mv` by hand.

## CI

Run on every PR:

```sh
terraform fmt -check -recursive -diff
terraform init -backend=false
terraform validate
tflint --recursive
trivy config .
```

- tflint and trivy are pinned by version.
- **A plan runs on PRs only where the provider supports OIDC.** The credentials live in an `environment:`.
- **`apply` never runs from a PR.** It runs from `main`, in a deploy job (see [ci.md](../ci.md#deploys)), or by hand from a clean checkout of `main`.
