"""Pythonic, lifetime-safe bindings for Google's Filament renderer."""

from .core import (
    Animation, Camera, Clock, DirectionalLight, Engine, Entity, Environment, Light,
    IndexBuffer, Material, MaterialInstance, Mesh, Model, Node, OrbitCameraController, PointLight,
    Renderable, Renderer, RenderTarget, Resource, Scene, SpotLight, SwapChain, Texture,
    ResourceFuture, Transform, VertexBuffer, View,
)
from .errors import BackendUnavailableError, FilamentError, ResourceDestroyedError
from .math import Matrix4, Quaternion
from .types import (
    AntiAliasing, AttributeType, Backend, BoundingBox, EngineStats, Exposure, IndexType,
    LightType, PickResult, TextureFormat, VertexAttribute, Viewport,
)

__version__ = "1.0.0"

__all__ = [
    "Animation", "AntiAliasing", "AttributeType", "Backend", "BackendUnavailableError",
    "BoundingBox", "Camera", "Clock", "DirectionalLight", "Engine", "EngineStats", "Entity",
    "Environment", "Exposure", "FilamentError", "IndexBuffer", "IndexType", "Light",
    "LightType", "Material", "MaterialInstance", "Matrix4", "Mesh", "Model", "Node",
    "OrbitCameraController", "PickResult", "PointLight", "Quaternion", "Renderable",
    "Renderer", "RenderTarget", "Resource", "ResourceDestroyedError", "ResourceFuture", "Scene",
    "SpotLight", "SwapChain", "Texture", "TextureFormat", "Transform", "VertexAttribute",
    "VertexBuffer", "View", "Viewport",
]
