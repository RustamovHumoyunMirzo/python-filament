# Architecture

The package has two deliberately separate layers:

1. `filament._native` is a pybind11 extension linked to a pinned prebuilt Filament SDK. It owns
   engine, renderer, scene, view, camera, and swap-chain pointers and performs frame submission.
2. The `filament` Python package implements ergonomic resources, scene graph helpers, caching,
   asynchronous loading, NumPy validation, and optional UI integration.

This division keeps Python-facing policy easy to evolve and avoids duplicating every convenience
class in C++. The native layer must never expose an unowned pointer. Engine shutdown is ordered:
children first, native engine last. Every public operation validates liveness.

Filament authoring executables are asset-pipeline tools, not runtime libraries. They are excluded
from wheels to keep runtime artifacts focused and to let users choose the matching external toolset.
