# API guide

The public API is intentionally Pythonic. Native Filament builders remain available for advanced
use, but ordinary construction uses keyword arguments.

## Ownership

`Engine` is the lifetime root. Every `Resource` keeps its engine alive, and the engine tracks all
of its children. Closing an engine closes its children before destroying the native handle.
Closing anything twice is harmless. Resources from two engines cannot be placed in one scene.

## Core objects

- `Engine`: creates renderers, scenes, views, cameras, entities, and swap chains; loads cached
  models, materials, textures, and environments.
- `Renderer`: supports the Filament `begin_frame` / `render` / `end_frame` sequence and the
  `render_frame` convenience method. `on_frame(callback)` callbacks receive delta time.
- `Scene`: owns a set of renderable objects and light nodes.
- `View`: binds a scene and camera and carries viewport, anti-aliasing, render target, and debug
  settings.
- `Camera`: provides `look_at` and perspective projection helpers.

## Scene and resource API

`Node` supplies parenting, recursive `find`, position, scale, and quaternion rotation. `Entity`,
`Model`, `Renderable`, and lights share this interface. `Mesh` and `Texture` accept contiguous
NumPy-compatible arrays. Materials use either `set_parameter(name, value)` or mapping syntax.

Loads are cached by canonical path by default. Pass `cache=False` to request a distinct resource.
`load_model_async()` returns a conventional future wrapper; `async_load_model()` is awaitable.

## Offscreen output

Create a `RenderTarget`, assign it to `view.render_target`, render against a headless swap chain,
then call `read_pixels()` for an `(height, width, 4)` NumPy array. `to_pil()` requires the `image`
extra.

## Low-level builders

`Texture.builder(engine)`, `VertexBuffer.builder(engine)`, and `IndexBuffer.builder(engine)` mirror
Filament's fluent builder style. They are compatibility escape hatches, not the preferred API.

## Native handles

Window handles are platform-specific: an `HWND` on Windows, X11/Wayland-native handle on Linux,
and an `NSView` on macOS. The application remains responsible for creating and pumping its window.

