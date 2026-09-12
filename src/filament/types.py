from dataclasses import dataclass
from enum import Enum, IntEnum


class Backend(IntEnum):
    AUTO = 0
    OPENGL = 1
    VULKAN = 2
    METAL = 3


class AntiAliasing(Enum):
    NONE = "none"
    FXAA = "fxaa"


class TextureFormat(Enum):
    R8 = "r8"
    RGB8 = "rgb8"
    RGBA8 = "rgba8"
    RGBA16F = "rgba16f"
    DEPTH24 = "depth24"


class LightType(Enum):
    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"


class VertexAttribute(Enum):
    POSITION = "position"
    TANGENTS = "tangents"
    COLOR = "color"
    UV0 = "uv0"


class AttributeType(Enum):
    FLOAT2 = "float2"
    FLOAT3 = "float3"
    FLOAT4 = "float4"


class IndexType(Enum):
    USHORT = "uint16"
    UINT = "uint32"


@dataclass(frozen=True)
class Viewport:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        if min(self.width, self.height) <= 0:
            raise ValueError("viewport width and height must be positive")


@dataclass(frozen=True)
class Exposure:
    aperture: float = 16.0
    shutter_speed: float = 1 / 125
    sensitivity: float = 100.0


@dataclass(frozen=True)
class BoundingBox:
    minimum: tuple = (0.0, 0.0, 0.0)
    maximum: tuple = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class PickResult:
    entity: object
    depth: float
    position: tuple


@dataclass(frozen=True)
class EngineStats:
    fps: float = 0.0
    frame_time_ms: float = 0.0
    gpu_time_ms: float = 0.0
    draw_calls: int = 0
    triangles: int = 0
