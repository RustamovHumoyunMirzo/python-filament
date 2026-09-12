"""Pythonic, lifetime-safe bindings for Google's Filament renderer."""

from .core import (
    Animation, Camera, Clock, DirectionalLight, Engine, Entity, Environment, Light,
    IndexBuffer, Material, MaterialInstance, Mesh, Model, Node, OrbitCameraController, PointLight,
    Renderable, Renderer, RenderTarget, Resource, Scene, SpotLight, SwapChain, Texture,
    Transform, VertexBuffer, View,
)
from .errors import BackendUnavailableError, FilamentError, ResourceDestroyedError
from .math import Matrix4, Quaternion
from .types import (
    AntiAliasing, AttributeType, Backend, BoundingBox, EngineStats, Exposure, IndexType,
    LightType, PickResult, TextureFormat, VertexAttribute, Viewport,
)

__version__ = "0.1.0"

__all__ = [name for name in globals() if not name.startswith("_")]
