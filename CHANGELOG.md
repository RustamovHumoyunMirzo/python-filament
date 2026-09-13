# Changelog

## 1.0.0 - 2026-09-13

- Promoted the package to a stable public API.
- Added native renderer, scene, view, camera, viewport, window swap-chain, and headless swap-chain
  bindings on top of the existing native engine.
- Added deterministic, dependency-ordered destruction of native resources.
- Added cross-engine and type validation for view bindings and renderables.
- Added mesh index, normal, UV, texture, buffer, and render-target validation.
- Expanded `ResourceFuture` with cancellation, exception, callback, and `await` support.
- Added Python 3.7-3.13 and native wheel release automation for major desktop platforms.
- Documented the stable API, architecture, binary build policy, and PyPI release procedure.
- Added a complete argument/type/return/exception reference, explicit native-support matrix,
  machine-readable type stubs, and documentation coverage tests.

## 0.1.0 - 2026-09-12

- Initial alpha API and native engine bridge.
