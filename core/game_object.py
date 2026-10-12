"""
GameObject: clase base del motor (la misma idea que vimos en clase).

Carga una hoja de sprites + un JSON con las animaciones, avanza los frames
con un temporizador (en milisegundos) y se dibuja en una superficie.
Todos los objetos "con sprite" del juego (Player, Enemy, Collectible...)
heredan de esta clase.
"""
import json

import pygame

from .paths import BASE_DIR


class GameObject:
    DEFAULT_FRAME_MS = 100

    def __init__(self, x=0, y=0, json_path=None):
        self.x = float(x)
        self.y = float(y)
        self.visible = True
        self.flip = False

        self.animations = {}      # nombre -> lista de Surfaces
        self.frame_ms = {}        # nombre -> duración de frame
        self.loops = {}           # nombre -> bool
        self.anchor = (0, 0)      # punto del sprite que cae sobre (x, y)
        self.action = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.finished = False     # True cuando una animación sin loop terminó
        self.image = None

        if json_path:
            self.load_animations(json_path)

    # ------------------------------------------------------------------ carga
    def load_animations(self, json_path):
        with open(BASE_DIR / json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sheet = pygame.image.load(str(BASE_DIR / data["spritesheet_path"])).convert_alpha()
        for name, frames in data["animations"].items():
            self.animations[name] = [
                sheet.subsurface(pygame.Rect(fr["x"], fr["y"], fr["width"], fr["height"])).copy()
                for fr in frames
            ]
        self.frame_ms = data.get("frame_ms", {})
        self.loops = data.get("loop", {})
        self.anchor = tuple(data.get("anchor", (0, 0)))
        self._refresh_image()

    # ------------------------------------------------------------- animación
    def set_action(self, action, restart=False):
        if action not in self.animations:
            return
        if action != self.action or restart:
            self.action = action
            self.frame_index = 0
            self.frame_timer = 0
            self.finished = False
            self._refresh_image()

    def _refresh_image(self):
        frames = self.animations.get(self.action)
        if frames:
            self.image = frames[min(self.frame_index, len(frames) - 1)]

    def update(self, dt, action=None):
        """dt en milisegundos."""
        if action:
            self.set_action(action)
        frames = self.animations.get(self.action)
        if not frames or self.finished:
            return
        duration = self.frame_ms.get(self.action, self.DEFAULT_FRAME_MS)
        self.frame_timer += dt
        while self.frame_timer >= duration:
            self.frame_timer -= duration
            self.frame_index += 1
            if self.frame_index >= len(frames):
                if self.loops.get(self.action, True):
                    self.frame_index = 0
                else:
                    self.frame_index = len(frames) - 1
                    self.finished = True
                    break
        self._refresh_image()

    # ----------------------------------------------------------------- dibujo
    def draw(self, surface, offset=(0, 0)):
        if not self.visible or self.image is None:
            return
        img = pygame.transform.flip(self.image, True, False) if self.flip else self.image
        ax = (img.get_width() - self.anchor[0]) if self.flip else self.anchor[0]
        surface.blit(img, (self.x - ax + offset[0], self.y - self.anchor[1] + offset[1]))
