# platform-workflows

Reusable GitHub Actions workflows for the AI-Powered SDLC Platform.

**This repository is public on purpose, and holds nothing secret.** GitHub shares reusable
workflows from a private repository only with organisations on Team or Enterprise Cloud;
`sdlc-a2z` is on Free, so the workflows every repository calls live here while everything
they build stays private.

## What is and is not in here

Secrets are referenced **by name** — `secrets.WIF_PROVIDER`, `secrets.CI_SERVICE_ACCOUNT`,
`secrets.GITHUB_TOKEN`. Their values live in the calling repository's own secret store and
are injected at run time by GitHub. Nothing here can read them outside a run, and nothing
here should ever hold one.

No project identifiers, no hostnames, no network layout: the image registry is a required
input rather than a default, so this repository names no infrastructure. The Postgres
credentials in `service-ci.yml` are for a container that exists for the length of one job,
on the runner's loopback, destroyed with it.

If you are adding a step that needs a new secret, add the *reference* here and the *value*
in the calling repository. If that feels awkward, it is the design working.

## `service-ci.yml`

The shared build for a Go service. Called, not copied — twenty services copying a workflow
means twenty places to fix a bad gate and twenty chances to miss one.

```yaml
jobs:
  build:
    uses: sdlc-a2z/platform-workflows/.github/workflows/service-ci.yml@v1
    with:
      service: job-service
    secrets: inherit
```

## `service-image.yml`

Building and signing the image is a **separate** workflow, and that split is not tidiness.
GitHub validates every job's `permissions` in a called workflow against the caller —
including a job whose `if` will skip it. With the image job inside `service-ci.yml`, a
library that never builds an image still had to grant `id-token: write` just to start, and
every call failed with a zero-second startup failure and no log.

A service that ships an image adds:

```yaml
  image:
    needs: build
    uses: sdlc-a2z/platform-workflows/.github/workflows/service-image.yml@v1
    with:
      service: job-service
      registry: <host>/<project>/<repo>
      registry-host: <host>
    permissions:
      contents: read
      id-token: write
      packages: write
    secrets: inherit
```

A library calls only `service-ci.yml` and grants nothing.

What it enforces, each because something got through without it:

- **Coverage at 80%.** `R0-WS2-002` shipped at 61.5% with its whole interceptor chain
  untested — the code delivering its acceptance criterion in production had no test at all.
- **`govulncheck`.** GO-2026-6443, a remotely triggerable gRPC server panic, was in the
  first version pinned by a library seventeen services import.
- **An unprivileged Postgres role.** A superuser bypasses RLS, so a tenancy suite run as
  one passes while proving nothing — the commonest way such a suite lies.
- **`CI: true`.** The tenancy suites `t.Fatal` rather than skip when it is set, so the
  guarantee cannot go untested behind a green build.
- **`actionlint`.** A workflow that does not parse never runs, and GitHub reports that as a
  zero-second failure with no log. One sat undetected in this platform for weeks.
- **Keyless signing, push by digest.** The signature binds to the workflow's identity, so
  there is no signing key to leak. A tag would let the running image change with no commit
  saying so.

## Why there is no `registry-check.yml`

There was one, calling into `sdlc-docs` to validate the dependency graph from every
repository. It cannot work: a called workflow's `GITHUB_TOKEN` reaches only the repository
that called it, and `sdlc-docs` is private. Minting a personal access token with read
access to every private repository, and inheriting it into a public workflow, is a
security decision rather than a workaround — so the check lives in `sdlc-docs`' own CI,
which runs it on push and on a weekday schedule.

## Pin the version you call

```yaml
uses: sdlc-a2z/platform-workflows/.github/workflows/service-ci.yml@v1
```

`@main` means every future commit here runs inside your repository with whatever secrets
you inherit to it. We own this repository, so the risk is a compromised account rather than
a stranger — but a tag is cheap and `@main` is a standing grant. Bump deliberately.
