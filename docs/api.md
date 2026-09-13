# python-filament 1.0 API reference

This document describes the API that exists in `python-filament` 1.0.0. It is written as a
reference for application developers, library authors, and coding agents. Signatures below use
Python notation even where an operation is implemented by the C++ extension.

## Contents

1. [Support boundary](#support-boundary)
2. [Type conventions](#type-conventions)
3. [Object ownership and destruction](#object-ownership-and-destruction)
4. [Engine and rendering](#engine-and-rendering)
5. [Scene graph and entities](#scene-graph-and-entities)
6. [Models and animation](#models-and-animation)
7. [Materials, textures, and geometry](#materials-textures-and-geometry)
8. [Lights and environments](#lights-and-environments)
9. [Offscreen objects](#offscreen-objects)
10. [Asynchronous loading](#asynchronous-loading)
11. [Math](#math)
12. [Utility value types and enums](#utility-value-types-and-enums)
13. [Controllers and timing](#controllers-and-timing)
14. [Qt integration](#qt-integration)
15. [Exceptions](#exceptions)
16. [Complete examples](#complete-examples)

## Support boundary

The package combines a native core with higher-level Python objects. “Native” below means that the
operation calls Google Filament through `filament._native`. “Python-side” means that the object
currently stores and validates state in Python but does not create the corresponding Filament GPU
resource.

| API area | 1.0 implementation |
|---|---|
| Engine creation and backend selection | Native |
| Renderer creation and frame submission | Native |
| Scene, View, Camera | Native |
| Window and headless SwapChain | Native |
| Camera `look_at` and perspective projection | Native |
| View scene, camera, and viewport binding | Native |
| Node graph and transforms | Python-side |
| Model/glTF metadata and animation controls | Python-side |
| Material, MaterialInstance, Texture, buffers, Mesh | Python-side |
| Lights and Environment | Python-side |
| RenderTarget pixel storage | Python-side NumPy buffer |
| Picking and runtime statistics | Placeholder values; see their entries below |
| `filament.qt.FilamentWidget` | Native core lifecycle with Python-side high-level resources |

This boundary matters. For example, `Engine.load_model("car.glb")` returns and caches a `Model`
descriptor, but 1.0 does not parse the file or upload glTF entities to the native scene. Likewise,
`RenderTarget.read_pixels()` returns its Python-owned buffer; it is not GPU readback. Code must not
use those APIs to claim that a model was rendered or that pixels came from Filament.

`Engine(native=False)` is a deterministic test backend. It exercises validation, ownership,
caching, callbacks, and frame sequencing without creating Filament. Never use it for rendering,
performance measurement, backend detection, or GPU tests.

## Type conventions

The implementation does not expose formal aliases, but this reference uses these names:

| Reference name | Accepted Python values |
|---|---|
| `Real` | `int`, `float`, or an object accepted by `float(value)` |
| `Vec2` | Iterable containing exactly two `Real` values |
| `Vec3` | Iterable containing exactly three `Real` values |
| `Vec4` | Iterable containing exactly four `Real` values |
| `Color3` | Three floats interpreted as linear RGB; no range check is performed |
| `Color4` | Four floats interpreted as linear RGBA; no range check is performed |
| `PathLike` | `str`, `bytes`, or `os.PathLike` accepted by `os.fspath()` |
| `ArrayLike` | Value accepted by `numpy.asarray()` |
| `NativeWindowHandle` | Non-zero integer representation of a platform native window pointer |

Vectors are converted to tuples of `float`. Unless a specific entry says otherwise, values are not
normalized and finite/range checks are not performed.

All names documented here are imported from `filament` except `FilamentWidget`, which is imported
from `filament.qt`.

```python
import filament as fl

print(fl.__version__)  # "1.0.0"
```

## Object ownership and destruction

### `Resource`

```python
Resource(engine: Engine, native_kind=None, native_handle=None)
```

Base class for objects owned by an `Engine`. Applications normally instantiate a concrete
subclass rather than `Resource` itself.

Properties:

- `engine -> Engine`: the owning engine. This reference remains available after closure.
- `alive -> bool`: `True` only when both the resource and its engine are open.

Methods:

#### `Resource.close()`

Closes the resource. The operation is idempotent. When the resource has a native handle, the handle
is destroyed by its engine. Subsequent operations that call the liveness check raise
`ResourceDestroyedError`.

Resources implement the context-manager protocol:

```python
with fl.Texture(engine, 4, 4) as texture:
    ...
# texture.alive is False
```

### Ownership rules

- An engine strongly owns its resources.
- A resource keeps its engine reachable.
- A resource cannot be transferred to another engine.
- `Engine.close()` closes resources in dependency-safe order and then closes Filament.
- Closing a `Scene` detaches it from every live `View`.
- Closing a `Camera` closes live views that reference it, because native Filament views require a
  valid camera.
- Closing a `SwapChain` during an active frame raises `RuntimeError`.
- Closing a `Renderer` during an active frame ends that frame first.
- Python garbage collection is not a substitute for deterministic shutdown. Prefer context
  managers or explicit `close()` calls.

## Engine and rendering

### `Engine`

```python
Engine(backend: Backend = Backend.AUTO, native: bool = True)
```

Creates the ownership root.

Arguments:

- `backend`: requested backend. Accepts a `Backend` member or its integer value.
- `native`: when `True`, imports `_native` and creates a real Filament engine. When `False`, skips
  the extension and enables deterministic API testing.

Raises:

- `ValueError` if `backend` is not a valid `Backend` value.
- `BackendUnavailableError` if the native extension is missing or Filament cannot initialize the
  requested backend.

Properties:

- `alive -> bool`: whether the engine is open.
- `backend -> Backend`: resolved native backend when native mode is active; requested backend in
  test mode. Raises `ResourceDestroyedError` after closure.
- `version -> str`: linked Filament version, currently `"1.76.1"`.
- `stats -> EngineStats`: currently returns a zero-filled snapshot. It does not query native GPU
  counters in 1.0.
- `resources`: cache container with mutable dictionaries `models`, `materials`, and `textures`.
- `debug`: options object with `enabled`, `show_wireframe`, and `show_shadow_cascades` booleans.
  These flags are Python-side in 1.0.

Factory methods:

```python
engine.create_renderer() -> Renderer
engine.create_scene() -> Scene
engine.create_view() -> View
engine.create_camera() -> Camera
engine.create_entity(name: str | None = None) -> Entity
```

Each method raises `ResourceDestroyedError` when the engine is closed. The first four create native
objects in native mode. `Entity` is Python-side.

#### `Engine.create_swap_chain(...)`

```python
engine.create_swap_chain(
    native_handle: int | None = None,
    width: int | None = None,
    height: int | None = None,
    headless: bool = False,
) -> SwapChain
```

Window form:

```python
swap_chain = engine.create_swap_chain(native_handle=hwnd)
```

Headless form:

```python
swap_chain = engine.create_swap_chain(width=1920, height=1080, headless=True)
```

`native_handle` is an `HWND` on Windows, an applicable native window handle on Linux, and an
`NSView` pointer on macOS. A window swap chain requires a handle. A headless swap chain requires
truthy width and height values. Native Filament performs further platform validation.

#### Resource loaders

```python
engine.load_model(path: PathLike, cache: bool = True) -> Model
engine.load_material(path: PathLike, cache: bool = True) -> Material
engine.load_texture(path: PathLike, srgb: bool = True, cache: bool = True) -> Texture
engine.load_environment(path: PathLike) -> Environment
engine.load_skybox(path: PathLike) -> Environment
engine.load_indirect_light(path: PathLike) -> Environment
```

Cache keys are normalized absolute paths with platform case normalization. With `cache=True`, a
live cached object is returned by identity. `cache=False` always constructs another object.

Important loader behavior:

- `load_model` and `load_material` do not open or validate the path in 1.0.
- Environment loaders do not open KTX files in 1.0.
- `load_texture` opens the image with Pillow, converts it to RGBA, copies it into a `Texture`, and
  therefore requires `python-filament[image]`. File and decoding errors from Pillow propagate.

#### Async model loaders

```python
engine.load_model_async(path: PathLike, cache: bool = True) -> ResourceFuture
await engine.async_load_model(path: PathLike, cache: bool = True) -> Model
```

Both use worker threads and have the same model-loading semantics as `load_model`.

#### `Engine.close()`

Closes all resources, shuts down the loader executor, destroys the native engine, and sets
`alive=False`. Safe to call repeatedly. Because it waits for loader workers, it can block until
already-submitted loader work finishes.

The engine is a context manager:

```python
with fl.Engine() as engine:
    scene = engine.create_scene()
# scene.alive and engine.alive are both False
```

### `Renderer`

Created by `Engine.create_renderer()`.

#### `Renderer.begin_frame(swap_chain: SwapChain) -> bool`

Starts a frame. Calls registered frame callbacks first, passing elapsed seconds as `float`. In
native mode the return value is Filament's `beginFrame()` result. A false result means the frame
was not accepted and `render()` / `end_frame()` must not be called.

Raises `RuntimeError` if a frame is already active. Raises `ResourceDestroyedError` if the renderer
or swap chain is closed.

#### `Renderer.render(view: View) -> None`

Submits a view during an active frame. Calls native `Renderer::render` in native mode.

Raises `RuntimeError` outside a successful `begin_frame` / `end_frame` pair.

#### `Renderer.end_frame() -> None`

Ends the active frame. The Python active-frame flag is cleared even if native shutdown raises.
Raises `RuntimeError` when no frame is active.

#### `Renderer.render_frame(swap_chain: SwapChain, view: View) -> None`

Convenience operation equivalent to:

```python
if renderer.begin_frame(swap_chain):
    try:
        renderer.render(view)
    finally:
        renderer.end_frame()
```

#### `Renderer.on_frame(callback) -> callback`

Registers `callback(dt_seconds)` and returns the same callback. Callbacks execute in registration
order in the thread that calls `begin_frame`. Exceptions propagate and prevent the frame from
starting. There is no removal method in 1.0.

### `Scene`

Created by `Engine.create_scene()`. Native scene creation and view binding are supported; adding
Python `Entity` / `Model` descriptors does not add native Filament entities in 1.0.

Properties:

- `entities -> tuple`: immutable snapshot of Python-side members. Requires a live scene.
- `environment`, `skybox`, `indirect_light`: assignable Python-side attributes; default `None`.

Methods:

```python
scene.add(entity: object) -> object
scene.remove(entity: object) -> None
```

`add` preserves insertion order, suppresses duplicate identity/equality entries, and returns the
argument. A `Resource` from another engine raises `ValueError`. Plain `Node` objects are allowed.
`remove` is a no-op when the value is absent.

### `View`

Created by `Engine.create_view()`.

Native properties:

- `scene: Scene | None`: setting this updates native Filament. A different engine raises
  `ValueError`; a wrong type raises `TypeError`.
- `camera: Camera | None`: assigning a camera updates native Filament. A different engine raises
  `ValueError`; a wrong type raises `TypeError`. In test mode it may be reset to `None`. Once a
  native view has a camera, setting it to `None` raises `ValueError`; close the view instead.
- `viewport: Viewport | None`: assigning a viewport updates native Filament. A wrong type raises
  `TypeError`.

Python-side configuration attributes:

- `clear_color: Color4`, default `(0.0, 0.0, 0.0, 1.0)`.
- `post_processing: bool`, default `True`.
- `anti_aliasing: AntiAliasing`, default `AntiAliasing.NONE`.
- `sample_count: int`, default `1`.
- `render_target: RenderTarget | None`, default `None`.
- `debug`: options object with `show_wireframe` and `show_shadow_cascades`.

Those configuration values are not forwarded to native Filament in 1.0.

#### `View.pick(x: Real, y: Real, callback=None) -> None`

Picking is not implemented in 1.0. The method verifies that the view is alive, invokes
`callback(None)` synchronously when supplied, and returns `None`.

### `Camera`

Created by `Engine.create_camera()`. It is also an `Entity` / `Node` on the Python side.

Attributes:

- `eye: Vec3`, initial `(0.0, 0.0, 1.0)`.
- `target: Vec3`, initial `(0.0, 0.0, 0.0)`.
- `up: Vec3`, initial `(0.0, 1.0, 0.0)`.
- `projection: tuple[float, float, float, float] | None`.
- `exposure: Exposure`, initial `Exposure()`; assignment is Python-side.

#### `Camera.look_at(eye: Vec3, target: Vec3, up: Vec3 = (0, 1, 0)) -> None`

Stores float tuples and calls native Filament in native mode. Each vector must contain exactly
three values or `ValueError` is raised.

#### `Camera.set_perspective(fov: Real, aspect: Real, near: Real, far: Real) -> None`

Stores `(fov, aspect, near, far)` as floats and updates native Filament. `fov` is in degrees and
uses Filament's default vertical-FOV convention. Requires `aspect > 0` and `0 < near < far`, or
raises `ValueError`.

### `SwapChain`

```python
SwapChain(
    engine: Engine,
    native_handle: int | None = None,
    width: int | None = None,
    height: int | None = None,
    headless: bool = False,
)
```

Normally created through `Engine.create_swap_chain`. Readable attributes are `native_handle`,
`width`, `height`, and `headless`. Closing an active swap chain raises `RuntimeError`.

## Scene graph and entities

### `Transform`

```python
Transform()
```

Python-side component with mutable attributes:

- `position: Vec3`, default `(0.0, 0.0, 0.0)`.
- `rotation: Quaternion`, default identity quaternion.
- `scale: Vec3`, default `(1.0, 1.0, 1.0)`.
- `matrix: Matrix4`, default identity matrix.

These fields are independent in 1.0: changing position does not recompute `matrix` and assigning a
matrix does not decompose it.

### `Node`

```python
Node(name: str | None = None)
```

Python-side scene-graph node.

Attributes:

- `name: str`: `""` when `name` is falsey.
- `parent: Node | None`.
- `children: list[Node]`.
- `transform: Transform`.
- `position: Vec3`, `rotation: Quaternion`, and `scale: Vec3`: proxies to `transform`.

Assigning `rotation` accepts a `Quaternion` or an iterable passed to `Quaternion(*value)`.

Methods:

```python
node.add_child(child: Node) -> Node
node.remove_child(child: Node) -> None
node.find(name: str) -> Node | None
```

`add_child` reparents an existing child, rejects self-parenting and ancestry cycles with
`ValueError`, appends the child, and returns it. `remove_child` raises the standard `ValueError` if
the child is absent. `find` performs a depth-first search including the receiver.

### `Entity`

```python
Entity(engine: Engine, name: str | None = None)
```

Combines `Resource` and `Node`. Usually created by `engine.create_entity(name)`.

Attributes:

- `components: list`, initially empty.
- `material`, initially `None`.

Methods:

```python
entity.add(component: object) -> object
entity.set_material(material: MaterialInstance, primitive: int = 0) -> None
```

Both require a live entity. `add` stores and returns the component. `set_material` stores the
material; `primitive` is accepted for API compatibility but is not stored or applied natively in
1.0.

### `Renderable`

```python
Renderable(
    engine: Engine,
    mesh: Mesh,
    material: Material | MaterialInstance,
    name: str | None = None,
)
```

Entity descriptor with `mesh` and `material` attributes. All three resources must belong to the
same engine or `ValueError` is raised. The default name is `"Renderable"`.

## Models and animation

### `Model`

```python
Model(engine: Engine, path: PathLike)
```

Returned by `Engine.load_model`. It is an `Entity` descriptor; construction does not read the file
or create native glTF entities in 1.0.

Attributes:

- `path: pathlib.Path`.
- `name: str`: filename stem.
- `entities -> tuple`: snapshot of child nodes.
- `materials: list`, initially empty.
- `animations: list[Animation]`, initially empty.
- `bounding_box: BoundingBox`, initially all zeros.
- `animation_speed: float`, default `1.0`.

Methods:

```python
model.animation(name: str) -> Animation
model.play_animation(name: str, loop: bool = True) -> None
model.set_morph_weight(name: str, weight: Real) -> None
```

`animation` performs an exact name search and raises `KeyError(name)` when absent.
`play_animation` records the selected animation and loop flag; it does not advance automatically.
`set_morph_weight` stores `float(weight)` by name without range validation.

### `Animation`

```python
Animation(name: str, duration: Real = 0.0)
```

Attributes are `name`, `duration: float`, and `time: float` (initially `0.0`).

```python
animation.apply(time: Real) -> None
```

Sets `animation.time = float(time)`. It does not update native bones or morph targets in 1.0.

## Materials, textures, and geometry

### `Material`

```python
Material(engine: Engine, path: PathLike | None = None, data=None)
```

Python-side descriptor. `Engine.load_material` sets `path` to `pathlib.Path(path)`; it does not read
the `.filamat` package in 1.0.

```python
material.create_instance() -> MaterialInstance
```

Requires a live material and creates an engine-owned instance referencing it.

### `MaterialInstance`

```python
MaterialInstance(engine: Engine, material: Material)
```

Attributes are `material` and `parameters: dict`.

```python
instance.set_parameter(name: str, value: object) -> None
instance[name] = value
value = instance[name]
```

Values are stored unchanged. Missing keys raise `KeyError`. Parameter names and types are not
validated against a native material package in 1.0.

### `Texture`

```python
Texture(
    engine: Engine,
    width: int,
    height: int,
    format: TextureFormat = TextureFormat.RGBA8,
    levels: int = 1,
    srgb: bool = False,
)
```

Dimensions and levels must be positive. `format` accepts a `TextureFormat` member or its string
value. Attributes mirror the arguments, and `pixels` is initially `None`.

#### `Texture.upload(pixels: ArrayLike, level: int = 0) -> None`

Creates a contiguous NumPy copy. Required shape is `(height, width, channels)`, where channels are:

| Format | Channels |
|---|---:|
| `R8` | 1 |
| `RGB8` | 3 |
| `RGBA8` | 4 |
| `RGBA16F` | 4 |
| `DEPTH24` | 1 |

Shape mismatch raises `ValueError`. Dtype is retained and not checked against the format. `level`
is accepted but only one `pixels` value is stored in 1.0. No native texture upload occurs.

#### Texture builder

```python
builder = Texture.builder(engine)
builder.width(value) -> builder
builder.height(value) -> builder
builder.levels(value) -> builder
builder.format(value) -> builder
builder.build() -> Texture
```

`width` and `height` are required by `build`; missing values produce Python's `TypeError`.

### `Mesh`

```python
Mesh(
    engine: Engine,
    vertices: ArrayLike,
    indices: ArrayLike,
    normals: ArrayLike | None = None,
    uvs: ArrayLike | None = None,
)
```

Validation and storage:

- `vertices` becomes contiguous `numpy.float32` with shape `(n, 3)`.
- `indices` must be a one-dimensional integer array. Values must be between `0` and `n - 1`.
- `normals`, when supplied, becomes contiguous `numpy.float32` and must match vertex shape.
- `uvs`, when supplied, becomes contiguous `numpy.float32` with shape `(n, 2)`.

Raises `ValueError` for invalid shapes or bounds and `TypeError` for non-integer indices. Mesh data
is not uploaded to native vertex/index buffers in 1.0.

### `VertexBuffer`

```python
VertexBuffer(
    engine: Engine,
    vertex_count: int,
    buffer_count: int = 1,
    attributes: list | None = None,
)
```

Counts must be positive. `attributes` defaults to a new empty list.

Builder API:

```python
builder = VertexBuffer.builder(engine)
builder.vertex_count(count) -> builder
builder.buffer_count(count) -> builder
builder.attribute(
    attribute: VertexAttribute,
    buffer_index: int = 0,
    type: AttributeType = AttributeType.FLOAT3,
) -> builder
builder.build() -> VertexBuffer
```

Each attribute is stored as `(attribute, int(buffer_index), type)`. Native buffer allocation and
data upload are not implemented in 1.0.

### `IndexBuffer`

```python
IndexBuffer(engine: Engine, index_count: int, type: IndexType = IndexType.UINT)
```

`index_count` must be positive. `type` accepts an `IndexType` member or its string value.

Builder API:

```python
builder = IndexBuffer.builder(engine)
builder.index_count(count) -> builder
builder.type(index_type) -> builder
builder.build() -> IndexBuffer
```

## Lights and environments

All lights are Python-side entity descriptors in 1.0. Extra keyword arguments are stored directly
as attributes without validation.

### `Light`

```python
Light(
    engine: Engine,
    type: LightType,
    color: Color3 = (1, 1, 1),
    intensity: Real = 1000,
    **kwargs,
)
```

Stores `type`, a three-float `color`, and `float(intensity)`. `name` is removed from `kwargs` and
used as the node name.

### `DirectionalLight`

```python
DirectionalLight(engine: Engine, direction: Vec3, **light_options)
```

Sets `type=LightType.DIRECTIONAL` and stores three-float `direction`. Common unvalidated options
include `color`, `intensity`, `cast_shadows`, and `name`.

### `PointLight`

```python
PointLight(engine: Engine, position: Vec3, **light_options)
```

Sets `type=LightType.POINT` and stores three-float `position`. Common options include `color`,
`intensity`, `falloff`, and `name`.

### `SpotLight`

```python
SpotLight(engine: Engine, position: Vec3, direction: Vec3, **light_options)
```

Sets `type=LightType.SPOT` and stores position/direction. Common options include `inner_cone`,
`outer_cone`, `intensity`, `color`, and `name`.

### `Environment`

```python
Environment(engine: Engine, path: PathLike)
```

Stores `path` as `pathlib.Path` and initializes `intensity = 30000.0`. It does not load native KTX
data in 1.0.

## Offscreen objects

### `RenderTarget`

```python
RenderTarget(
    engine: Engine,
    width: int,
    height: int,
    color_format: TextureFormat = TextureFormat.RGBA8,
    depth: bool = True,
)
```

Width and height must be positive. Construction creates a zero-filled `numpy.uint8` array with
shape `(height, width, 4)`.

```python
target.read_pixels() -> numpy.ndarray
target.to_pil() -> PIL.Image.Image
```

`read_pixels` returns a copy, so modifying it does not mutate the target. It is not native GPU
readback in 1.0. `to_pil` requires the `image` extra and raises `ImportError` when Pillow is absent.

## Asynchronous loading

### `ResourceFuture`

Returned by `Engine.load_model_async`.

Properties and methods:

```python
future.done -> bool
future.progress: float
future.result(timeout: float | None = None) -> Model
future.cancel() -> bool
future.cancelled() -> bool
future.exception(timeout: float | None = None) -> BaseException | None
future.add_done_callback(callback) -> ResourceFuture
await future -> Model
```

`progress` starts at `0.0` and changes to `1.0` only after `result()` returns successfully; merely
finishing the worker does not update it. A callback receives this `ResourceFuture`, not the wrapped
`concurrent.futures.Future`. Standard cancellation and timeout exceptions propagate.

## Math

### `Quaternion`

```python
Quaternion(x: Real = 0, y: Real = 0, z: Real = 0, w: Real = 1)
```

Mutable quaternion with float attributes `x`, `y`, `z`, `w`. The default is identity.

```python
Quaternion.from_euler(x: Real, y: Real, z: Real, degrees: bool = False) -> Quaternion
q1 * q2 -> Quaternion
tuple(q) -> tuple[float, float, float, float]
repr(q) -> str
```

`from_euler` applies the package's XYZ Euler conversion. Inputs are radians unless `degrees=True`.
Multiplication is Hamilton composition. Values are not normalized automatically. Multiplication by
a non-Quaternion returns `NotImplemented`, normally producing `TypeError`.

### `Matrix4`

```python
Matrix4(values: ArrayLike | None = None)
```

Stores a NumPy `float` array in `values`. `None` creates identity. Other input must contain exactly
16 values and is reshaped to `(4, 4)`.

```python
Matrix4.translation(x: Real, y: Real, z: Real) -> Matrix4
Matrix4.rotation_y(angle: Real, degrees: bool = False) -> Matrix4
left @ right -> Matrix4
numpy.asarray(matrix, dtype=None) -> numpy.ndarray
```

Matrices use the layout shown by the NumPy array, with translation stored in `values[:3, 3]`.
`rotation_y` accepts radians unless `degrees=True`. `@` performs NumPy matrix multiplication.

## Utility value types and enums

### Enums

| Enum | Members and values |
|---|---|
| `Backend` (`IntEnum`) | `AUTO=0`, `OPENGL=1`, `VULKAN=2`, `METAL=3` |
| `AntiAliasing` | `NONE="none"`, `FXAA="fxaa"` |
| `TextureFormat` | `R8`, `RGB8`, `RGBA8`, `RGBA16F`, `DEPTH24` with lowercase string values |
| `LightType` | `DIRECTIONAL="directional"`, `POINT="point"`, `SPOT="spot"` |
| `VertexAttribute` | `POSITION`, `TANGENTS`, `COLOR`, `UV0` with lowercase string values |
| `AttributeType` | `FLOAT2="float2"`, `FLOAT3="float3"`, `FLOAT4="float4"` |
| `IndexType` | `USHORT="uint16"`, `UINT="uint32"` |

### `Viewport`

```python
Viewport(x: int, y: int, width: int, height: int)
```

Frozen dataclass. Width and height must be positive; x and y may be negative. Used by `View`.

### `Exposure`

```python
Exposure(
    aperture: float = 16.0,
    shutter_speed: float = 1 / 125,
    sensitivity: float = 100.0,
)
```

Frozen data container. Values are not range-validated or forwarded natively in 1.0.

### `BoundingBox`

```python
BoundingBox(minimum: tuple = (0, 0, 0), maximum: tuple = (0, 0, 0))
```

Frozen data container. Tuple length and ordering are not validated.

### `PickResult`

```python
PickResult(entity: object, depth: float, position: tuple)
```

Frozen result shape reserved for picking. `View.pick` does not construct results in 1.0.

### `EngineStats`

```python
EngineStats(
    fps: float = 0.0,
    frame_time_ms: float = 0.0,
    gpu_time_ms: float = 0.0,
    draw_calls: int = 0,
    triangles: int = 0,
)
```

Frozen snapshot shape. `Engine.stats` returns default zero values in 1.0.

## Controllers and timing

### `Clock`

```python
Clock()
clock.tick() -> float
```

Uses `time.monotonic()`. `tick` returns elapsed seconds since construction or the previous tick and
then resets the reference time.

### `OrbitCameraController`

```python
OrbitCameraController(
    camera: Camera,
    target: Vec3 = (0, 0, 0),
    distance: Real = 5.0,
    min_distance: Real = 0.2,
    max_distance: Real = 100.0,
)
```

Stores `camera`, float `target`, `distance`, limits, and yaw/pitch (initially zero). Construction
immediately applies a camera `look_at`.

```python
controller.rotate(dx: Real, dy: Real) -> None
controller.zoom(delta: Real) -> None
```

Rotation deltas are degrees. Pitch is clamped to `[-1.55, 1.55]` radians. Zoom adds `delta` to
distance and clamps to `[min_distance, max_distance]`. Each method updates the camera.

## Qt integration

Install and import:

```bash
pip install "python-filament[qt]"
```

```python
from filament.qt import FilamentWidget
```

Importing `filament.qt` without PySide6 raises `ImportError` with the installation command.

### `FilamentWidget`

```python
FilamentWidget(parent: QWidget | None = None, backend: Backend = Backend.AUTO)
```

Subclasses `PySide6.QtWidgets.QWidget`. Construction creates these public attributes:

- `engine: Engine`
- `renderer: Renderer`
- `scene: Scene`
- `view: View`
- `camera: Camera`
- `swap_chain: SwapChain | None`

It binds scene and camera to the view, creates an orbit controller, and starts a zero-interval Qt
timer that requests widget updates.

Properties:

- `clear_color`: proxy for `view.clear_color`.
- `environment`: proxy for `scene.environment`.

Methods:

```python
widget.load_model(path: PathLike) -> Model
widget.load(path: PathLike) -> Model
widget.fit_camera() -> None
```

`load_model` delegates to the engine. `load` also adds the returned descriptor to the Python scene.
`fit_camera` resets orbit distance to `5.0`; it does not inspect model bounds in 1.0.

Qt lifecycle:

- First `showEvent` creates a window swap chain from `int(winId())`.
- `resizeEvent` assigns a viewport matching widget width and height.
- `paintEvent` submits one native frame after the swap chain exists.
- `closeEvent` closes the engine and all owned resources.

Because model and renderable upload are not native in 1.0, the widget can submit native empty-scene
frames but does not display `Model` descriptors loaded through `load()`.

## Exceptions

### `FilamentError`

Base package exception. Subclasses `RuntimeError`.

### `ResourceDestroyedError`

Raised when an operation requires a live resource or engine after it has been closed.

### `BackendUnavailableError`

Raised by native `Engine` construction when the extension is unavailable or Filament cannot create
an engine. Subclasses `FilamentError`.

Standard Python exceptions are also part of the contract:

- `TypeError` for wrong object/array kinds or missing builder arguments.
- `ValueError` for invalid dimensions, vector sizes, projections, cross-engine relationships,
  scene-graph cycles, and mesh bounds.
- `KeyError` for unknown animation or material parameter names.
- `RuntimeError` for invalid frame sequencing or closing an active swap chain.
- `ImportError` for unavailable optional Pillow or Qt dependencies.
- `concurrent.futures.TimeoutError` / `CancelledError` from futures.

## Complete examples

### Native empty-scene frame

```python
import filament as fl

with fl.Engine(fl.Backend.AUTO) as engine:
    renderer = engine.create_renderer()
    scene = engine.create_scene()
    view = engine.create_view()
    camera = engine.create_camera()

    view.scene = scene
    view.camera = camera
    view.viewport = fl.Viewport(0, 0, 1280, 720)

    camera.look_at((0, 1, 4), (0, 1, 0))
    camera.set_perspective(45, 1280 / 720, 0.1, 1000)

    swap_chain = engine.create_swap_chain(
        width=1280,
        height=720,
        headless=True,
    )
    renderer.render_frame(swap_chain, view)
```

This example exercises the native core. It does not read pixels.

### Validated geometry descriptor

```python
import numpy as np
import filament as fl

with fl.Engine(native=False) as engine:
    mesh = fl.Mesh(
        engine,
        vertices=np.array(
            [[-1, -1, 0], [1, -1, 0], [0, 1, 0]],
            dtype=np.float32,
        ),
        indices=np.array([0, 1, 2], dtype=np.uint32),
        normals=np.array([[0, 0, 1]] * 3, dtype=np.float32),
    )

    material = fl.Material(engine, data=b"application-owned material data")
    instance = material.create_instance()
    instance["baseColor"] = (0.8, 0.1, 0.05, 1.0)
    renderable = fl.Renderable(engine, mesh, instance)
    engine.create_scene().add(renderable)
```

This validates Python data and ownership only; it does not create native geometry.

### Async cache behavior

```python
import asyncio
import filament as fl


async def main():
    with fl.Engine(native=False) as engine:
        pending = engine.load_model_async("scene.glb")
        pending.add_done_callback(lambda future: print("done:", future.done))
        first = await pending
        second = engine.load_model("scene.glb")
        assert first is second


asyncio.run(main())
```

### Multi-view native frame

```python
if renderer.begin_frame(swap_chain):
    try:
        renderer.render(main_view)
        renderer.render(preview_view)
    finally:
        renderer.end_frame()
```

Both views, their cameras, and their scene must belong to the renderer's engine. The Python layer
rejects a view or swap chain owned by another engine with `ValueError` before crossing into C++.
