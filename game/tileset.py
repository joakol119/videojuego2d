"""Carga de los tiles isométricos generados en assets/tiles."""
import json

import pygame

from core.paths import BASE_DIR


class TileSet:
    def __init__(self):
        with open(BASE_DIR / "assets" / "tiles" / "tiles.json", encoding="utf-8") as f:
            data = json.load(f)
        self.tile_w = data["tile_width"]
        self.tile_h = data["tile_height"]
        self.images = {}
        self.heights = {}
        for name, info in data["tiles"].items():
            self.images[name] = pygame.image.load(str(BASE_DIR / info["file"])).convert_alpha()
            self.heights[name] = info["height"]

    def draw_floor(self, surface, name, cx, cy):
        surface.blit(self.images[name], (cx - self.tile_w // 2, cy - self.tile_h // 2))

    def block_rect(self, name, cx, cy):
        h = self.heights[name]
        return pygame.Rect(cx - self.tile_w // 2, cy - self.tile_h // 2 - h, self.tile_w, self.tile_h + h)

    def draw_block(self, surface, name, cx, cy, ghost=False):
        """`ghost=True` dibuja el bloque semitransparente (cuando tapa a un personaje)."""
        img = self.images[name]
        if ghost:
            key = name + "#ghost"
            if key not in self.images:
                g = img.copy()
                g.set_alpha(105)
                self.images[key] = g
            img = self.images[key]
        surface.blit(img, self.block_rect(name, cx, cy).topleft)
