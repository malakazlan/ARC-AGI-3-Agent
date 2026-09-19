"""Render a colour-index grid to a base64 PNG with only the standard library (zlib, struct)."""
from __future__ import annotations

import base64
import struct
import zlib

import numpy as np

# ARC-AGI-3 display palette, index = colour value 0..15.
PALETTE: tuple[tuple[int, int, int], ...] = (
    (0xFF, 0xFF, 0xFF), (0xCC, 0xCC, 0xCC), (0x99, 0x99, 0x99), (0x66, 0x66, 0x66),
    (0x33, 0x33, 0x33), (0x00, 0x00, 0x00), (0xE5, 0x3A, 0xA3), (0xFF, 0x7B, 0xCC),
    (0xF9, 0x3C, 0x31), (0x1E, 0x93, 0xFF), (0x88, 0xD8, 0xF1), (0xFF, 0xDC, 0x00),
    (0xFF, 0x85, 0x1B), (0x92, 0x12, 0x31), (0x4F, 0xCC, 0x30), (0xA3, 0x56, 0xD6),
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PALETTE_ARRAY = np.array(PALETTE, dtype=np.uint8)


def grid_to_png_b64(grid: np.ndarray, scale: int = 8) -> str:
    """Base64 PNG of the grid, each cell drawn as a scale x scale block of its palette colour."""
    return base64.b64encode(grid_to_png(grid, scale)).decode("ascii")


def grid_to_png(grid: np.ndarray, scale: int = 8) -> bytes:
    """PNG bytes (8-bit RGB, no interlace). Colour values outside 0..15 are clipped."""
    indices = np.clip(np.asarray(grid), 0, len(PALETTE) - 1).astype(np.intp)
    rgb = _PALETTE_ARRAY[indices]
    rgb = np.repeat(np.repeat(rgb, scale, axis=0), scale, axis=1)
    height, width = rgb.shape[0], rgb.shape[1]
    filter_bytes = np.zeros((height, 1), dtype=np.uint8)
    scanlines = np.concatenate([filter_bytes, rgb.reshape(height, width * 3)], axis=1).tobytes()
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (PNG_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(scanlines, 6))
            + _chunk(b"IEND", b""))


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) read from the IHDR chunk; raises ValueError if the signature is wrong."""
    if data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)
