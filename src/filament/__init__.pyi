from concurrent.futures import Future
from enum import Enum, IntEnum
from os import PathLike
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

import numpy as np

__version__: str
_Real = Union[int, float]
_Vec3 = Sequence[_Real]
_PathValue = Union[str, bytes, PathLike]

class FilamentError(RuntimeError): ...
class ResourceDestroyedError(FilamentError): ...
class BackendUnavailableError(FilamentError): ...

class Backend(IntEnum):
    AUTO: Backend
    OPENGL: Backend
    VULKAN: Backend
    METAL: Backend

class AntiAliasing(Enum):
    NONE: AntiAliasing
    FXAA: AntiAliasing

class TextureFormat(Enum):
    R8: TextureFormat
    RGB8: TextureFormat
    RGBA8: TextureFormat
    RGBA16F: TextureFormat
    DEPTH24: TextureFormat

class LightType(Enum):
    DIRECTIONAL: LightType
    POINT: LightType
    SPOT: LightType

class VertexAttribute(Enum):
    POSITION: VertexAttribute
    TANGENTS: VertexAttribute
    COLOR: VertexAttribute
    UV0: VertexAttribute

class AttributeType(Enum):
    FLOAT2: AttributeType
    FLOAT3: AttributeType
    FLOAT4: AttributeType

class IndexType(Enum):
    USHORT: IndexType
    UINT: IndexType

class Viewport:
    x: int
    y: int
    width: int
    height: int
    def __init__(self, x: int, y: int, width: int, height: int) -> None: ...

class Exposure:
    aperture: float
    shutter_speed: float
    sensitivity: float
    def __init__(self, aperture: float = ..., shutter_speed: float = ..., sensitivity: float = ...) -> None: ...

class BoundingBox:
    minimum: tuple
    maximum: tuple
    def __init__(self, minimum: tuple = ..., maximum: tuple = ...) -> None: ...

class PickResult:
    entity: object
    depth: float
    position: tuple
    def __init__(self, entity: object, depth: float, position: tuple) -> None: ...

class EngineStats:
    fps: float
    frame_time_ms: float
    gpu_time_ms: float
    draw_calls: int
    triangles: int

class Quaternion:
    x: float
    y: float
    z: float
    w: float
    def __init__(self, x: _Real = ..., y: _Real = ..., z: _Real = ..., w: _Real = ...) -> None: ...
    @classmethod
    def from_euler(cls, x: _Real, y: _Real, z: _Real, degrees: bool = ...) -> Quaternion: ...
    def __mul__(self, other: Quaternion) -> Quaternion: ...
    def __iter__(self) -> Iterator[float]: ...

class Matrix4:
    values: np.ndarray
    def __init__(self, values: Any = ...) -> None: ...
    @classmethod
    def translation(cls, x: _Real, y: _Real, z: _Real) -> Matrix4: ...
    @classmethod
    def rotation_y(cls, angle: _Real, degrees: bool = ...) -> Matrix4: ...
    def __matmul__(self, other: Matrix4) -> Matrix4: ...

class Resource:
    def __init__(self, engine: Engine, native_kind: Any = ..., native_handle: Any = ...) -> None: ...
    @property
    def engine(self) -> Engine: ...
    @property
    def alive(self) -> bool: ...
    def close(self) -> None: ...
    def __enter__(self) -> Resource: ...
    def __exit__(self, *args: Any) -> None: ...

class Transform:
    position: Tuple[float, float, float]
    rotation: Quaternion
    scale: Tuple[float, float, float]
    matrix: Matrix4
    def __init__(self) -> None: ...

class Node:
    name: str
    parent: Optional[Node]
    children: List[Node]
    transform: Transform
    position: Tuple[float, float, float]
    rotation: Quaternion
    scale: Tuple[float, float, float]
    def __init__(self, name: Optional[str] = ...) -> None: ...
    def add_child(self, node: Node) -> Node: ...
    def remove_child(self, node: Node) -> None: ...
    def find(self, name: str) -> Optional[Node]: ...

class Entity(Resource, Node):
    components: List[object]
    material: Any
    def __init__(self, engine: Engine, name: Optional[str] = ...) -> None: ...
    def add(self, component: object) -> object: ...
    def set_material(self, material: MaterialInstance, primitive: int = ...) -> None: ...

class Scene(Resource):
    environment: Optional[Environment]
    skybox: Optional[Environment]
    indirect_light: Optional[Environment]
    @property
    def entities(self) -> tuple: ...
    def add(self, entity: object) -> object: ...
    def remove(self, entity: object) -> None: ...

class Camera(Entity):
    eye: Tuple[float, float, float]
    target: Tuple[float, float, float]
    up: Tuple[float, float, float]
    projection: Optional[tuple]
    exposure: Exposure
    def look_at(self, eye: _Vec3, target: _Vec3, up: _Vec3 = ...) -> None: ...
    def set_perspective(self, fov: _Real, aspect: _Real, near: _Real, far: _Real) -> None: ...

class View(Resource):
    scene: Optional[Scene]
    camera: Optional[Camera]
    viewport: Optional[Viewport]
    clear_color: tuple
    post_processing: bool
    anti_aliasing: AntiAliasing
    sample_count: int
    render_target: Optional[RenderTarget]
    def pick(self, x: _Real, y: _Real, callback: Optional[Callable[[Optional[PickResult]], Any]] = ...) -> Optional[PickResult]: ...

class SwapChain(Resource):
    native_handle: Optional[int]
    width: Optional[int]
    height: Optional[int]
    headless: bool

class Renderer(Resource):
    def begin_frame(self, swap_chain: SwapChain) -> bool: ...
    def render(self, view: View) -> None: ...
    def end_frame(self) -> None: ...
    def render_frame(self, swap_chain: SwapChain, view: View) -> None: ...
    def on_frame(self, callback: Callable[[float], Any]) -> Callable[[float], Any]: ...

class Animation:
    name: str
    duration: float
    time: float
    def __init__(self, name: str, duration: _Real = ...) -> None: ...
    def apply(self, time: _Real) -> None: ...

class Model(Entity):
    path: Path
    materials: List[Material]
    animations: List[Animation]
    bounding_box: BoundingBox
    animation_speed: float
    @property
    def entities(self) -> tuple: ...
    def animation(self, name: str) -> Animation: ...
    def play_animation(self, name: str, loop: bool = ...) -> None: ...
    def set_morph_weight(self, name: str, weight: _Real) -> None: ...

class Material(Resource):
    path: Optional[_PathValue]
    data: Any
    def __init__(self, engine: Engine, path: Optional[_PathValue] = ..., data: Any = ...) -> None: ...
    def create_instance(self) -> MaterialInstance: ...

class MaterialInstance(Resource):
    material: Material
    parameters: Dict[str, Any]
    def set_parameter(self, name: str, value: Any) -> None: ...
    def __setitem__(self, name: str, value: Any) -> None: ...
    def __getitem__(self, name: str) -> Any: ...

class Texture(Resource):
    width: int
    height: int
    format: TextureFormat
    levels: int
    srgb: bool
    pixels: Optional[np.ndarray]
    def __init__(self, engine: Engine, width: int, height: int, format: TextureFormat = ..., levels: int = ..., srgb: bool = ...) -> None: ...
    def upload(self, pixels: Any, level: int = ...) -> None: ...
    @classmethod
    def builder(cls, engine: Engine) -> Any: ...

class VertexBuffer(Resource):
    vertex_count: int
    buffer_count: int
    attributes: list
    def __init__(self, engine: Engine, vertex_count: int, buffer_count: int = ..., attributes: Optional[list] = ...) -> None: ...
    @classmethod
    def builder(cls, engine: Engine) -> Any: ...

class IndexBuffer(Resource):
    index_count: int
    type: IndexType
    def __init__(self, engine: Engine, index_count: int, type: IndexType = ...) -> None: ...
    @classmethod
    def builder(cls, engine: Engine) -> Any: ...

class Mesh(Resource):
    vertices: np.ndarray
    indices: np.ndarray
    normals: Optional[np.ndarray]
    uvs: Optional[np.ndarray]
    def __init__(self, engine: Engine, vertices: Any, indices: Any, normals: Any = ..., uvs: Any = ...) -> None: ...

class Renderable(Entity):
    mesh: Mesh
    material: Union[Material, MaterialInstance]
    def __init__(self, engine: Engine, mesh: Mesh, material: Union[Material, MaterialInstance], name: Optional[str] = ...) -> None: ...

class Light(Entity):
    type: LightType
    color: Tuple[float, float, float]
    intensity: float
    def __init__(self, engine: Engine, type: LightType, color: _Vec3 = ..., intensity: _Real = ..., **kwargs: Any) -> None: ...

class DirectionalLight(Light):
    direction: Tuple[float, float, float]
    def __init__(self, engine: Engine, direction: _Vec3, **kwargs: Any) -> None: ...

class PointLight(Light):
    position: Tuple[float, float, float]
    def __init__(self, engine: Engine, position: _Vec3, **kwargs: Any) -> None: ...

class SpotLight(Light):
    position: Tuple[float, float, float]
    direction: Tuple[float, float, float]
    def __init__(self, engine: Engine, position: _Vec3, direction: _Vec3, **kwargs: Any) -> None: ...

class Environment(Resource):
    path: Path
    intensity: float
    def __init__(self, engine: Engine, path: _PathValue) -> None: ...

class RenderTarget(Resource):
    width: int
    height: int
    color_format: TextureFormat
    depth: bool
    def __init__(self, engine: Engine, width: int, height: int, color_format: TextureFormat = ..., depth: bool = ...) -> None: ...
    def read_pixels(self) -> np.ndarray: ...
    def to_pil(self) -> Any: ...

class ResourceFuture(Awaitable[Model]):
    progress: float
    @property
    def done(self) -> bool: ...
    def result(self, timeout: Optional[float] = ...) -> Model: ...
    def cancel(self) -> bool: ...
    def cancelled(self) -> bool: ...
    def exception(self, timeout: Optional[float] = ...) -> Optional[BaseException]: ...
    def add_done_callback(self, callback: Callable[[ResourceFuture], Any]) -> ResourceFuture: ...

class Engine:
    resources: Any
    debug: Any
    def __init__(self, backend: Backend = ..., native: bool = ...) -> None: ...
    @property
    def alive(self) -> bool: ...
    @property
    def backend(self) -> Backend: ...
    @property
    def version(self) -> str: ...
    @property
    def stats(self) -> EngineStats: ...
    def create_renderer(self) -> Renderer: ...
    def create_scene(self) -> Scene: ...
    def create_view(self) -> View: ...
    def create_camera(self) -> Camera: ...
    def create_entity(self, name: Optional[str] = ...) -> Entity: ...
    def create_swap_chain(self, native_handle: Optional[int] = ..., width: Optional[int] = ..., height: Optional[int] = ..., headless: bool = ...) -> SwapChain: ...
    def load_model(self, path: _PathValue, cache: bool = ...) -> Model: ...
    def load_material(self, path: _PathValue, cache: bool = ...) -> Material: ...
    def load_texture(self, path: _PathValue, srgb: bool = ..., cache: bool = ...) -> Texture: ...
    def load_environment(self, path: _PathValue) -> Environment: ...
    def load_skybox(self, path: _PathValue) -> Environment: ...
    def load_indirect_light(self, path: _PathValue) -> Environment: ...
    def load_model_async(self, path: _PathValue, cache: bool = ...) -> ResourceFuture: ...
    async def async_load_model(self, path: _PathValue, cache: bool = ...) -> Model: ...
    def close(self) -> None: ...
    def __enter__(self) -> Engine: ...
    def __exit__(self, *args: Any) -> None: ...

class Clock:
    def __init__(self) -> None: ...
    def tick(self) -> float: ...

class OrbitCameraController:
    camera: Camera
    target: Tuple[float, float, float]
    distance: float
    min_distance: float
    max_distance: float
    yaw: float
    pitch: float
    def __init__(self, camera: Camera, target: _Vec3 = ..., distance: _Real = ..., min_distance: _Real = ..., max_distance: _Real = ...) -> None: ...
    def rotate(self, dx: _Real, dy: _Real) -> None: ...
    def zoom(self, delta: _Real) -> None: ...
