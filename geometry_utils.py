"""Calcoli planari nel CRS metrico del layer, azimut dal nord griglia."""
from .i18n import tr
import math


def direction(origin, target):
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    distance = math.hypot(dx, dy)
    if distance <= 1e-9:
        raise ValueError(tr('Il clic deve essere distinto dal punto di presa.'))
    return math.degrees(math.atan2(dx, dy)) % 360.0, distance


def aperture(axis, edge):
    return 2.0 * abs((edge - axis + 180.0) % 360.0 - 180.0)


def endpoint(origin, angle, distance):
    a = math.radians(angle)
    return origin[0] + distance * math.sin(a), origin[1] + distance * math.cos(a)


def valid_fov(value):
    return math.isfinite(value) and 1.0 <= value <= 179.0
