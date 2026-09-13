# python-filament

[![CI](https://github.com/RustamovHumoyunMirzo/python-filament/actions/workflows/ci.yml/badge.svg)](https://github.com/RustamovHumoyunMirzo/python-filament/actions/workflows/ci.yml)

Pythonic, lifetime-safe bindings for [Google Filament](https://github.com/google/filament),
a physically based real-time renderer for Windows, Linux, and macOS.

**1.0 stable release.** Engine creation, renderer frames, scenes, views, cameras, viewports, and
window/headless swap chains execute through the native Filament runtime. Higher-level Python
objects provide validated ownership, scene-graph, resource-caching, NumPy, and async interfaces.

## Install

```bash
pip install python-filament
```

Published wheels contain Filament itself. Users do not need CMake, a C++ compiler, or a local
Filament build. Filament's authoring tools (`matc`, `cmgen`, `filamesh`, and similar tools) are
deliberately not bundled; install those from a Filament release when your asset pipeline needs
them.

Optional integrations are separate:

```bash
pip install "python-filament[qt,image]"
```

Python 3.7 through 3.13 is supported. PySide6 itself no longer supports every old Python release,
so the `qt` extra requires Python 3.8 or newer.

## Five-minute example

This submits an empty scene through the native Filament renderer. Supply a platform window handle
instead of the headless dimensions when presenting to a desktop window.

```python
import filament as fl

with fl.Engine(backend=fl.Backend.AUTO) as engine:
    renderer = engine.create_renderer()
    scene = engine.create_scene()
    view = engine.create_view()
    camera = engine.create_camera()

    camera.look_at(eye=(0, 1, 4), target=(0, 1, 0))
    camera.set_perspective(fov=45, aspect=16 / 9, near=0.1, far=1000)
    view.camera = camera
    view.scene = scene
    view.viewport = fl.Viewport(0, 0, 1280, 720)

    swap_chain = engine.create_swap_chain(width=1280, height=720, headless=True)
    renderer.render_frame(swap_chain, view)
```

The exact native/Python support boundary is part of the API contract. In 1.0, the engine, renderer,
scene, view, camera, swap chains, and frame submission are native. Models, materials, geometry,
lights, and render-target pixels are validated Python-side descriptors and are not uploaded to the
GPU yet. See the [complete API reference](docs/api.md#support-boundary) before building rendering
features on a high-level object.

The distribution includes `py.typed` and complete `.pyi` signatures, so editors, type checkers,
and coding agents can inspect the public contract without importing the native extension.

Resources retain their engine and are closed automatically. `close()` is deterministic and
idempotent; using a resource after either it or its engine is closed raises
`ResourceDestroyedError` instead of reaching a dangling C++ pointer.

## NumPy and Qt

```python
import numpy as np
import filament as fl

engine = fl.Engine()
texture = fl.Texture(engine, width=256, height=256, format=fl.TextureFormat.RGBA8)
texture.upload(np.zeros((256, 256, 4), dtype=np.uint8))
```

```python
from PySide6.QtWidgets import QApplication
from filament.qt import FilamentWidget

app = QApplication([])
viewer = FilamentWidget()
viewer.scene.add(viewer.load_model("car.glb"))
viewer.fit_camera()
viewer.show()
app.exec()
```

See the [complete API reference](docs/api.md), [building wheels](docs/building.md), and the
[architecture notes](docs/architecture.md). See [the changelog](CHANGELOG.md) for compatibility
and release details.

## License

Apache License 2.0. Binary wheels include Filament's license and notices.
