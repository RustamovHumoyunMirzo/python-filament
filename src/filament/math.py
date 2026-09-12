import math

import numpy as np


class Quaternion:
    __slots__ = ("x", "y", "z", "w")

    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.x, self.y, self.z, self.w = map(float, (x, y, z, w))

    @classmethod
    def from_euler(cls, x, y, z, degrees=False):
        if degrees:
            x, y, z = map(math.radians, (x, y, z))
        cx, sx = math.cos(x / 2), math.sin(x / 2)
        cy, sy = math.cos(y / 2), math.sin(y / 2)
        cz, sz = math.cos(z / 2), math.sin(z / 2)
        return cls(
            sx * cy * cz - cx * sy * sz,
            cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz,
            cx * cy * cz + sx * sy * sz,
        )

    def __mul__(self, other):
        if not isinstance(other, Quaternion):
            return NotImplemented
        a, b = self, other
        return Quaternion(
            a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
            a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
            a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
            a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
        )

    def __iter__(self):
        return iter((self.x, self.y, self.z, self.w))

    def __repr__(self):
        return "Quaternion(x={!r}, y={!r}, z={!r}, w={!r})".format(*self)


class Matrix4:
    def __init__(self, values=None):
        self.values = np.eye(4) if values is None else np.asarray(values, dtype=float).reshape(4, 4)

    @classmethod
    def translation(cls, x, y, z):
        value = np.eye(4)
        value[:3, 3] = (x, y, z)
        return cls(value)

    @classmethod
    def rotation_y(cls, angle, degrees=False):
        angle = math.radians(angle) if degrees else angle
        c, s = math.cos(angle), math.sin(angle)
        return cls(((c, 0, s, 0), (0, 1, 0, 0), (-s, 0, c, 0), (0, 0, 0, 1)))

    def __matmul__(self, other):
        return Matrix4(self.values @ other.values)

    def __array__(self, dtype=None):
        return np.asarray(self.values, dtype=dtype)
