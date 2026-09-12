# Building and releasing

Source builds consume an extracted prebuilt Filament SDK through `FILAMENT_ROOT`, or an SDK archive
through `FILAMENT_ARCHIVE`. They never fetch or compile Filament implicitly.

```bash
FILAMENT_ARCHIVE=/path/to/filament-v1.76.1-linux.tgz pip wheel . -w dist
```

The SDK must match the target OS, architecture, and C runtime. Windows builds use Filament's `/MD`
libraries. Release wheels are repaired by cibuildwheel (`auditwheel`, `delocate`, or `delvewheel`)
and then smoke-tested in a clean environment.

The GitHub Actions workflow runs tests for pushes and pull requests. Tags matching `v*` build the
same artifacts, create a GitHub release, and publish to PyPI using trusted publishing. The PyPI
environment should be configured with an OIDC trusted publisher; no long-lived API token is needed.

Upstream release archives do not cover every CPU/OS pair. For those targets, set the corresponding
`FILAMENT_SDK_URL` matrix entry to a separately produced, immutable prebuilt SDK artifact. End users
still only install wheels and never build Filament.

