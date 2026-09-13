# Building and releasing

Source builds consume an extracted prebuilt Filament SDK through `FILAMENT_ROOT`, or an SDK archive
through `FILAMENT_ARCHIVE`. They never fetch or compile Filament implicitly.

`FILAMENT_ARCHIVE` may be absolute or relative. Relative paths are resolved from the project source
directory, which makes the same value portable across Windows, Linux containers, and macOS:

```bash
FILAMENT_ARCHIVE=filament-sdk.tgz pip wheel . -w dist
```

The build recognizes both official SDK archive layouts: `include/` and `lib/`
at the archive root, or those directories beneath the top-level `filament/`
directory used by the macOS SDK.

Each macOS wheel must target one architecture. CI passes that architecture to
CMake through `CMAKE_OSX_ARCHITECTURES`, ensuring an arm64 build selects the
SDK's `lib/arm64` libraries even when CMake reports an x86_64 host processor.
Filament 1.76.1's official macOS SDK contains arm64 libraries only, so the 1.0.0
release publishes macOS arm64 wheels rather than non-functional Intel wheels.

Linux wheels use the AlmaLinux 9-based `manylinux_2_34` image and its bundled
GCC toolchain. CI downloads checksum-pinned conda-forge libc++ and libc++abi
packages for the unresolved runtime symbols in the official Filament SDK,
without updating the image's glibc baseline. The resulting shared libraries
are collected into each wheel by `auditwheel`. CI pins the PyPA image to
`2025.04.19-1`, a matching image generation that includes CPython 3.7 and 3.8
as required by this package's support matrix.

The upstream 1.76.1 Linux archive references glibc 2.38's
`__isoc23_sscanf`. On older glibc, the extension supplies that ABI entry point
by forwarding Filament's conventional scan formats to `__isoc99_vsscanf`.
This compatibility unit is enabled only on glibc versions older than 2.38.

The SDK must match the target OS, architecture, and C runtime. Windows builds use Filament's `/MD`
libraries. Release wheels are repaired by cibuildwheel (`auditwheel`, `delocate`, or `delvewheel`)
and then smoke-tested in a clean environment. The CI smoke test imports the native extension and
checks its binding version; it deliberately does not initialize a graphics backend because hosted
runners do not guarantee a GPU or display server.

The GitHub Actions workflow runs tests for pushes and pull requests. Tags matching `v*` build the
same artifacts, create a GitHub release, and publish to PyPI using trusted publishing. The PyPI
environment should be configured with an OIDC trusted publisher; no long-lived API token is needed.

Upstream release archives do not include Windows ARM64. That matrix entry runs only when the
`FILAMENT_WINDOWS_ARM64_SDK_URL` repository variable points to a separately produced, immutable
prebuilt SDK artifact. CPython ARM64 wheels begin at 3.11. End users still only install wheels and
never build Filament.
