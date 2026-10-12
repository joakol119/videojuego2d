"""
Matemática isométrica.

Transformación ortogonal (col, row) -> isométrica (iso_x, iso_y):

    iso_x = (col - row) * TILE_W / 2 + origen_x
    iso_y = (col + row) * TILE_H / 2 + origen_y

La inversa (pantalla -> grilla) se usa para saber sobre qué casilla está el mouse.
(col, row) es el CENTRO de la casilla, por eso la casilla (c, r) abarca
|col - c| <= 0.5 y |row - r| <= 0.5.
"""
import math

from .constants import TILE_H, TILE_W


class IsoProjection:
    def __init__(self, origin_x=0.0, origin_y=0.0):
        self.ox = origin_x
        self.oy = origin_y

    def to_screen(self, col, row):
        x = (col - row) * TILE_W / 2 + self.ox
        y = (col + row) * TILE_H / 2 + self.oy
        return x, y

    def to_grid(self, x, y):
        dx = (x - self.ox) / (TILE_W / 2)
        dy = (y - self.oy) / (TILE_H / 2)
        return (dx + dy) / 2, (dy - dx) / 2

    def tile_at(self, x, y):
        c, r = self.to_grid(x, y)
        return int(math.floor(c + 0.5)), int(math.floor(r + 0.5))

    def diamond(self, col, row, shrink=0.0):
        """Los 4 vértices del rombo de una casilla (para resaltados)."""
        cx, cy = self.to_screen(col, row)
        hw = TILE_W / 2 - shrink * 2
        hh = TILE_H / 2 - shrink
        return [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]

    def center_map(self, cols, rows, area, tallest_block=46):
        """Ubica el origen para que el mapa quede centrado dentro de `area` (Rect)."""
        self.ox, self.oy = 0.0, 0.0
        left = self.to_screen(0, rows - 1)[0] - TILE_W / 2
        right = self.to_screen(cols - 1, 0)[0] + TILE_W / 2
        top = self.to_screen(0, 0)[1] - TILE_H / 2 - tallest_block
        bottom = self.to_screen(cols - 1, rows - 1)[1] + TILE_H / 2
        self.ox = area.centerx - (left + right) / 2
        self.oy = area.centery - (top + bottom) / 2
