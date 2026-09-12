import concurrent.futures
import os
import threading
import time
from pathlib import Path

import numpy as np

from .errors import BackendUnavailableError, ResourceDestroyedError
from .math import Matrix4, Quaternion
from .types import (
    AntiAliasing, AttributeType,
    Backend,
    BoundingBox,
    EngineStats,
    Exposure,
    IndexType, LightType,
    TextureFormat,
)


def _vector(value, size, name):
    result = tuple(float(item) for item in value)
    if len(result) != size:
        raise ValueError("{} must contain {} values".format(name, size))
    return result


class _DebugOptions:
    def __init__(self):
        self.enabled = False
        self.show_wireframe = False
        self.show_shadow_cascades = False


class Resource:
    """Lifetime-safe base for every object owned by an :class:`Engine`."""

    def __init__(self, engine):
        if engine is None or not engine.alive:
            raise ResourceDestroyedError("Engine has already been destroyed")
        self._engine = engine
        self._alive = True
        engine._register(self)

    @property
    def engine(self):
        return self._engine

    @property
    def alive(self):
        return self._alive and self._engine.alive

    def _check_alive(self):
        if not self.alive:
            raise ResourceDestroyedError("{} has already been destroyed".format(type(self).__name__))

    def close(self):
        if self._alive:
            self._alive = False
            engine = self._engine
            if engine is not None:
                engine._unregister(self)

    def __enter__(self):
        self._check_alive()
        return self

    def __exit__(self, *_):
        self.close()


class Transform:
    def __init__(self):
        self.position = (0.0, 0.0, 0.0)
        self.rotation = Quaternion()
        self.scale = (1.0, 1.0, 1.0)
        self.matrix = Matrix4()


class Node:
    def __init__(self, name=None):
        self.name = name or ""
        self.parent = None
        self.children = []
        self.transform = Transform()

    @property
    def position(self):
        return self.transform.position

    @position.setter
    def position(self, value):
        self.transform.position = _vector(value, 3, "position")

    @property
    def rotation(self):
        return self.transform.rotation

    @rotation.setter
    def rotation(self, value):
        if not isinstance(value, Quaternion):
            value = Quaternion(*value)
        self.transform.rotation = value

    @property
    def scale(self):
        return self.transform.scale

    @scale.setter
    def scale(self, value):
        self.transform.scale = _vector(value, 3, "scale")

    def add_child(self, node):
        if node is self or self._contains(node, self):
            raise ValueError("a node cannot be its own ancestor")
        if node.parent is not None:
            node.parent.remove_child(node)
        node.parent = self
        self.children.append(node)
        return node

    def remove_child(self, node):
        self.children.remove(node)
        node.parent = None

    @staticmethod
    def _contains(root, target):
        return root is target or any(Node._contains(child, target) for child in root.children)

    def find(self, name):
        if self.name == name:
            return self
        for child in self.children:
            result = child.find(name)
            if result is not None:
                return result
        return None


class Entity(Resource, Node):
    def __init__(self, engine, name=None):
        Resource.__init__(self, engine)
        Node.__init__(self, name)
        self.components = []
        self.material = None

    def add(self, component):
        self._check_alive()
        self.components.append(component)
        return component

    def set_material(self, material, primitive=0):
        self._check_alive()
        self.material = material


class Scene(Resource):
    def __init__(self, engine):
        super().__init__(engine)
        self._entities = []
        self.environment = None
        self.skybox = None
        self.indirect_light = None

    @property
    def entities(self):
        self._check_alive()
        return tuple(self._entities)

    def add(self, entity):
        self._check_alive()
        if isinstance(entity, Resource) and entity.engine is not self.engine:
            raise ValueError("resources from different engines cannot share a scene")
        if entity not in self._entities:
            self._entities.append(entity)
        return entity

    def remove(self, entity):
        self._check_alive()
        if entity in self._entities:
            self._entities.remove(entity)


class Camera(Entity):
    def __init__(self, engine, name=None):
        super().__init__(engine, name or "Camera")
        self.eye = (0.0, 0.0, 1.0)
        self.target = (0.0, 0.0, 0.0)
        self.up = (0.0, 1.0, 0.0)
        self.projection = None
        self.exposure = Exposure()

    def look_at(self, eye, target, up=(0.0, 1.0, 0.0)):
        self._check_alive()
        self.eye = _vector(eye, 3, "eye")
        self.target = _vector(target, 3, "target")
        self.up = _vector(up, 3, "up")

    def set_perspective(self, fov, aspect, near, far):
        self._check_alive()
        if aspect <= 0 or near <= 0 or far <= near:
            raise ValueError("perspective requires aspect > 0 and 0 < near < far")
        self.projection = (float(fov), float(aspect), float(near), float(far))


class View(Resource):
    def __init__(self, engine):
        super().__init__(engine)
        self.scene = None
        self.camera = None
        self.viewport = None
        self.clear_color = (0.0, 0.0, 0.0, 1.0)
        self.post_processing = True
        self.anti_aliasing = AntiAliasing.NONE
        self.sample_count = 1
        self.render_target = None
        self.debug = _DebugOptions()

    def pick(self, x, y, callback=None):
        self._check_alive()
        result = None
        if callback is not None:
            callback(result)
        return result


class SwapChain(Resource):
    def __init__(self, engine, native_handle=None, width=None, height=None, headless=False):
        super().__init__(engine)
        if headless and (not width or not height):
            raise ValueError("headless swap chains require width and height")
        if not headless and native_handle is None:
            raise ValueError("a native_handle is required for a window swap chain")
        self.native_handle = native_handle
        self.width, self.height, self.headless = width, height, bool(headless)


class Renderer(Resource):
    def __init__(self, engine):
        super().__init__(engine)
        self._in_frame = False
        self._callbacks = []
        self._last_time = time.monotonic()

    def begin_frame(self, swap_chain):
        self._check_alive()
        swap_chain._check_alive()
        if self._in_frame:
            raise RuntimeError("begin_frame called while a frame is active")
        now = time.monotonic()
        dt, self._last_time = now - self._last_time, now
        for callback in tuple(self._callbacks):
            callback(dt)
        self._in_frame = True
        return True

    def render(self, view):
        self._check_alive()
        view._check_alive()
        if not self._in_frame:
            raise RuntimeError("render must be called between begin_frame and end_frame")

    def end_frame(self):
        self._check_alive()
        if not self._in_frame:
            raise RuntimeError("no frame is active")
        self._in_frame = False

    def render_frame(self, swap_chain, view):
        if self.begin_frame(swap_chain):
            try:
                self.render(view)
            finally:
                self.end_frame()

    def on_frame(self, callback):
        self._callbacks.append(callback)
        return callback


class Animation:
    def __init__(self, name, duration=0.0):
        self.name, self.duration = name, float(duration)
        self.time = 0.0

    def apply(self, time):
        self.time = float(time)

    def __repr__(self):
        return "Animation(name={!r}, duration={!r})".format(self.name, self.duration)


class Model(Entity):
    def __init__(self, engine, path):
        super().__init__(engine, Path(path).stem)
        self.path = Path(path)
        self.materials = []
        self.animations = []
        self.bounding_box = BoundingBox()
        self.animation_speed = 1.0
        self._morph_weights = {}
        self._playing = None

    @property
    def entities(self):
        return tuple(self.children)

    def animation(self, name):
        for animation in self.animations:
            if animation.name == name:
                return animation
        raise KeyError(name)

    def play_animation(self, name, loop=True):
        self._playing = (self.animation(name), bool(loop))

    def set_morph_weight(self, name, weight):
        self._morph_weights[name] = float(weight)


class Material(Resource):
    def __init__(self, engine, path=None, data=None):
        super().__init__(engine)
        self.path, self.data = path, data

    def create_instance(self):
        self._check_alive()
        return MaterialInstance(self.engine, self)


class MaterialInstance(Resource):
    def __init__(self, engine, material):
        super().__init__(engine)
        self.material, self.parameters = material, {}

    def set_parameter(self, name, value):
        self._check_alive()
        self.parameters[name] = value

    def __setitem__(self, name, value):
        self.set_parameter(name, value)

    def __getitem__(self, name):
        self._check_alive()
        return self.parameters[name]


class Texture(Resource):
    _channels = {TextureFormat.R8: 1, TextureFormat.RGB8: 3, TextureFormat.RGBA8: 4,
                 TextureFormat.RGBA16F: 4, TextureFormat.DEPTH24: 1}

    def __init__(self, engine, width, height, format=TextureFormat.RGBA8, levels=1, srgb=False):
        super().__init__(engine)
        if width <= 0 or height <= 0 or levels <= 0:
            raise ValueError("texture dimensions and levels must be positive")
        self.width, self.height = int(width), int(height)
        self.format, self.levels, self.srgb = format, int(levels), bool(srgb)
        self.pixels = None

    def upload(self, pixels, level=0):
        self._check_alive()
        array = np.ascontiguousarray(pixels)
        expected = (self.height, self.width, self._channels[self.format])
        if array.shape != expected:
            raise ValueError("pixel shape must be {}, got {}".format(expected, array.shape))
        self.pixels = array.copy()

    @classmethod
    def builder(cls, engine):
        return _TextureBuilder(engine)


class _Builder:
    def __init__(self, engine):
        self.engine = engine
        self.options = {}

    def _set(self, name, value):
        self.options[name] = value
        return self


class _TextureBuilder(_Builder):
    def width(self, value): return self._set("width", value)
    def height(self, value): return self._set("height", value)
    def levels(self, value): return self._set("levels", value)
    def format(self, value): return self._set("format", value)
    def build(self): return Texture(self.engine, **self.options)


class VertexBuffer(Resource):
    def __init__(self, engine, vertex_count, buffer_count=1, attributes=None):
        super().__init__(engine)
        self.vertex_count, self.buffer_count = int(vertex_count), int(buffer_count)
        self.attributes = attributes or []

    @classmethod
    def builder(cls, engine): return _VertexBufferBuilder(engine)


class _VertexBufferBuilder(_Builder):
    def __init__(self, engine):
        super().__init__(engine)
        self.options["attributes"] = []

    def vertex_count(self, value): return self._set("vertex_count", value)
    def buffer_count(self, value): return self._set("buffer_count", value)
    def attribute(self, attribute, buffer_index=0, type=AttributeType.FLOAT3):
        self.options["attributes"].append((attribute, int(buffer_index), type))
        return self
    def build(self): return VertexBuffer(self.engine, **self.options)


class IndexBuffer(Resource):
    def __init__(self, engine, index_count, type=IndexType.UINT):
        super().__init__(engine)
        self.index_count, self.type = int(index_count), type

    @classmethod
    def builder(cls, engine): return _IndexBufferBuilder(engine)


class _IndexBufferBuilder(_Builder):
    def index_count(self, value): return self._set("index_count", value)
    def type(self, value): return self._set("type", value)
    def build(self): return IndexBuffer(self.engine, **self.options)


class Mesh(Resource):
    def __init__(self, engine, vertices, indices, normals=None, uvs=None):
        super().__init__(engine)
        self.vertices = np.ascontiguousarray(vertices, dtype=np.float32)
        self.indices = np.ascontiguousarray(indices)
        if self.vertices.ndim != 2 or self.vertices.shape[1] != 3:
            raise ValueError("vertices must have shape (n, 3)")
        if self.indices.ndim != 1:
            raise ValueError("indices must be one-dimensional")
        self.normals = None if normals is None else np.ascontiguousarray(normals, dtype=np.float32)
        self.uvs = None if uvs is None else np.ascontiguousarray(uvs, dtype=np.float32)


class Renderable(Entity):
    def __init__(self, engine, mesh, material, name=None):
        super().__init__(engine, name or "Renderable")
        self.mesh, self.material = mesh, material


class Light(Entity):
    def __init__(self, engine, type, color=(1, 1, 1), intensity=1000, **kwargs):
        super().__init__(engine, kwargs.pop("name", None))
        self.type, self.color = type, _vector(color, 3, "color")
        self.intensity = float(intensity)
        for name, value in kwargs.items():
            setattr(self, name, value)


class DirectionalLight(Light):
    def __init__(self, engine, direction, **kwargs):
        super().__init__(engine, LightType.DIRECTIONAL, direction=_vector(direction, 3, "direction"), **kwargs)


class PointLight(Light):
    def __init__(self, engine, position, **kwargs):
        super().__init__(engine, LightType.POINT, position=_vector(position, 3, "position"), **kwargs)


class SpotLight(Light):
    def __init__(self, engine, position, direction, **kwargs):
        super().__init__(engine, LightType.SPOT, position=_vector(position, 3, "position"),
                         direction=_vector(direction, 3, "direction"), **kwargs)


class Environment(Resource):
    def __init__(self, engine, path):
        super().__init__(engine)
        self.path = Path(path)
        self.intensity = 30000.0


class RenderTarget(Resource):
    def __init__(self, engine, width, height, color_format=TextureFormat.RGBA8, depth=True):
        super().__init__(engine)
        self.width, self.height = int(width), int(height)
        self.color_format, self.depth = color_format, bool(depth)
        self._pixels = np.zeros((self.height, self.width, 4), dtype=np.uint8)

    def read_pixels(self):
        self._check_alive()
        return self._pixels.copy()

    def to_pil(self):
        try:
            from PIL import Image
        except ImportError as exc:
            raise ImportError("Install python-filament[image] to use to_pil()") from exc
        return Image.fromarray(self.read_pixels())


class ResourceFuture:
    def __init__(self, future):
        self._future = future
        self.progress = 0.0

    @property
    def done(self):
        return self._future.done()

    def result(self, timeout=None):
        value = self._future.result(timeout)
        self.progress = 1.0
        return value


class _ResourceCache:
    def __init__(self):
        self.textures, self.materials, self.models = {}, {}, {}


class Engine:
    """Owns the native Filament engine and all resources created from it."""

    def __init__(self, backend=Backend.AUTO, native=True):
        self._alive = True
        # Native resources are owned by the Engine, matching Filament's lifetime root.
        # Resource.close() removes itself from this set deterministically.
        self._resources = set()
        self._lock = threading.RLock()
        self.resources = _ResourceCache()
        self.debug = _DebugOptions()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._native = None
        self._backend = Backend(backend)
        if native:
            try:
                from . import _native
                self._native = _native.Engine(int(self._backend))
            except ImportError as exc:
                raise BackendUnavailableError(
                    "the native extension is not installed; install a platform wheel or use native=False for tests"
                ) from exc
            except RuntimeError as exc:
                raise BackendUnavailableError(str(exc)) from exc

    @property
    def alive(self):
        return self._alive

    @property
    def backend(self):
        if not self.alive:
            raise ResourceDestroyedError("Engine has already been destroyed")
        if self._native is not None:
            try:
                return Backend(self._native.backend)
            except ValueError:
                return self._backend
        return self._backend

    @property
    def version(self):
        try:
            from ._native import FILAMENT_VERSION
            return FILAMENT_VERSION
        except ImportError:
            return "1.76.1"

    @property
    def stats(self):
        return EngineStats()

    def _register(self, resource):
        with self._lock:
            self._resources.add(resource)

    def _unregister(self, resource):
        with self._lock:
            self._resources.discard(resource)

    def _check_alive(self):
        if not self.alive:
            raise ResourceDestroyedError("Engine has already been destroyed")

    def create_renderer(self): self._check_alive(); return Renderer(self)
    def create_scene(self): self._check_alive(); return Scene(self)
    def create_view(self): self._check_alive(); return View(self)
    def create_camera(self): self._check_alive(); return Camera(self)
    def create_entity(self, name=None): self._check_alive(); return Entity(self, name)

    def create_swap_chain(self, native_handle=None, width=None, height=None, headless=False):
        self._check_alive()
        return SwapChain(self, native_handle, width, height, headless)

    @staticmethod
    def _key(path):
        return os.path.normcase(os.path.abspath(os.fspath(path)))

    def _cached(self, cache, path, factory, enabled):
        key = self._key(path)
        if enabled and key in cache and cache[key].alive:
            return cache[key]
        resource = factory()
        if enabled:
            cache[key] = resource
        return resource

    def load_model(self, path, cache=True):
        self._check_alive()
        return self._cached(self.resources.models, path, lambda: Model(self, path), cache)

    def load_material(self, path, cache=True):
        self._check_alive()
        return self._cached(self.resources.materials, path, lambda: Material(self, path=Path(path)), cache)

    def load_texture(self, path, srgb=True, cache=True):
        self._check_alive()
        def create():
            try:
                from PIL import Image
                pixels = np.asarray(Image.open(path).convert("RGBA"))
            except ImportError as exc:
                raise ImportError("Install python-filament[image] to load image files") from exc
            texture = Texture(self, pixels.shape[1], pixels.shape[0], srgb=srgb)
            texture.upload(pixels)
            return texture
        return self._cached(self.resources.textures, path, create, cache)

    def load_environment(self, path): return Environment(self, path)
    def load_skybox(self, path): return Environment(self, path)
    def load_indirect_light(self, path): return Environment(self, path)

    def load_model_async(self, path, cache=True):
        return ResourceFuture(self._executor.submit(self.load_model, path, cache))

    async def async_load_model(self, path, cache=True):
        import asyncio
        return await asyncio.get_running_loop().run_in_executor(None, self.load_model, path, cache)

    def close(self):
        with self._lock:
            if not self._alive:
                return
            for resource in list(self._resources):
                resource.close()
            # Mark dead before joining workers so a concurrent loader cannot register
            # another child while shutdown is in progress.
            self._alive = False
        self._executor.shutdown(wait=True)
        with self._lock:
            if self._native is not None:
                self._native.close()

    def __enter__(self):
        self._check_alive()
        return self

    def __exit__(self, *_):
        self.close()


class Clock:
    def __init__(self):
        self._last = time.monotonic()

    def tick(self):
        now = time.monotonic()
        elapsed, self._last = now - self._last, now
        return elapsed


class OrbitCameraController:
    def __init__(self, camera, target=(0, 0, 0), distance=5.0, min_distance=0.2, max_distance=100.0):
        self.camera, self.target = camera, _vector(target, 3, "target")
        self.distance = float(distance)
        self.min_distance, self.max_distance = float(min_distance), float(max_distance)
        self.yaw = self.pitch = 0.0
        self._apply()

    def _apply(self):
        cp = np.cos(self.pitch)
        eye = (self.target[0] + self.distance * cp * np.sin(self.yaw),
               self.target[1] + self.distance * np.sin(self.pitch),
               self.target[2] + self.distance * cp * np.cos(self.yaw))
        self.camera.look_at(eye, self.target)

    def rotate(self, dx, dy):
        self.yaw += np.radians(dx)
        self.pitch = float(np.clip(self.pitch + np.radians(dy), -1.55, 1.55))
        self._apply()

    def zoom(self, delta):
        self.distance = float(np.clip(self.distance + delta, self.min_distance, self.max_distance))
        self._apply()
