"""Entidades del juego. Todas heredan de GameObject (clase base del motor)."""
import json
import math
from dataclasses import dataclass

import pygame

from core.game_object import GameObject
from core.paths import BASE_DIR
from .constants import STEP_MS


@dataclass
class Attack:
    name: str
    damage: int
    range: int
    cost: int
    kind: str      # "melee" | "ranged"


class Entity(GameObject):
    """Personaje en la grilla isométrica: atributos (vida, daño, alcance), PA y animaciones."""

    def __init__(self, name, json_path, col, row, proj, max_hp, max_ap, attacks):
        super().__init__(0, 0, json_path)
        self.name = name
        self.proj = proj
        self.col, self.row = col, row              # posición lógica (matriz del mapa)
        self.fcol, self.frow = float(col), float(row)  # posición visual (interpolada)
        self.max_hp = self.hp = max_hp
        self.max_ap = self.ap = max_ap
        self.attacks = {a.name: a for a in attacks}
        self.alive = True
        self.gone = False
        self.alpha = 255
        self.moving = False
        self._from = (col, row)
        self._to = (col, row)
        self._t = 0.0
        self.attack_timer = 0
        self.hurt_timer = 0
        self.flash = 0
        self.fade = 0
        self.flip = False
        self._flash_cache = {}
        self.sync_screen()

    # ------------------------------------------------------------ posición
    def sync_screen(self):
        self.x, self.y = self.proj.to_screen(self.fcol, self.frow)

    @property
    def pos(self):
        return (self.col, self.row)

    def face_towards(self, col, row):
        sx = (col - self.col) - (row - self.row)   # signo del desplazamiento horizontal en pantalla
        if sx != 0:
            self.flip = sx < 0

    def step_to(self, col, row):
        """Empieza a caminar una casilla. La posición lógica cambia ya (reserva la casilla)."""
        self.face_towards(col, row)
        self._from = (self.fcol, self.frow)
        self._to = (col, row)
        self._t = 0.0
        self.col, self.row = col, row
        self.moving = True

    def play_attack(self, target_col, target_row):
        self.face_towards(target_col, target_row)
        self.attack_timer = 4 * self.frame_ms.get("attack", 80)
        self.set_action("attack", restart=True)

    def take_hit(self, amount):
        self.hp = max(0, self.hp - amount)
        self.flash = 150
        if self.hp <= 0:
            self.alive = False
            self.set_action("dead", restart=True)
        else:
            self.hurt_timer = 2 * self.frame_ms.get("hurt", 120) + 60
            self.set_action("hurt", restart=True)

    def heal(self, amount):
        gained = min(amount, self.max_hp - self.hp)
        self.hp += gained
        return gained

    # --------------------------------------------------------------- update
    def update(self, dt, action=None):
        if self.moving:
            self._t += dt / STEP_MS
            t = min(1.0, self._t)
            self.fcol = self._from[0] + (self._to[0] - self._from[0]) * t
            self.frow = self._from[1] + (self._to[1] - self._from[1]) * t
            if self._t >= 1.0:
                self.fcol, self.frow = float(self._to[0]), float(self._to[1])
                self.moving = False
            self.sync_screen()
        self.attack_timer = max(0, self.attack_timer - dt)
        self.hurt_timer = max(0, self.hurt_timer - dt)
        self.flash = max(0, self.flash - dt)

        if not self.alive:
            act = "dead"
            if self.finished:
                self.fade += dt
                self.alpha = max(0, 255 - int(255 * self.fade / 900))
                if self.alpha <= 0:
                    self.gone = True
        elif self.attack_timer > 0:
            act = "attack"
        elif self.hurt_timer > 0:
            act = "hurt"
        elif self.moving:
            act = "walk"
        else:
            act = "idle"
        super().update(dt, act)

    # ---------------------------------------------------------------- dibujo
    def sort_key(self):
        return self.fcol + self.frow + (0.25 if self.alive else -0.4)

    def _flashed(self, img):
        key = (id(img), self.flip)
        surf = self._flash_cache.get(key)
        if surf is None:
            surf = img.copy()
            surf.fill((200, 200, 200, 0), special_flags=pygame.BLEND_RGB_ADD)
            self._flash_cache[key] = surf
        return surf

    def draw_shadow(self, surface, offset=(0, 0)):
        if self.gone:
            return
        w, h = (46, 20) if self.alive else (60, 22)
        shadow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90 if self.alive else int(90 * self.alpha / 255)), shadow.get_rect())
        surface.blit(shadow, (self.x - w / 2 + offset[0], self.y - h / 2 + 2 + offset[1]))

    def draw(self, surface, offset=(0, 0)):
        if self.gone or self.image is None:
            return
        img = self.image
        if self.flash > 0 and self.alive:
            img = self._flashed(img)
        if self.flip:
            img = pygame.transform.flip(img, True, False)
        ax = (img.get_width() - self.anchor[0]) if self.flip else self.anchor[0]
        if self.alpha < 255:
            img = img.copy()
            img.set_alpha(self.alpha)
        surface.blit(img, (self.x - ax + offset[0], self.y - self.anchor[1] + offset[1]))

    def head_pos(self):
        return (self.x, self.y - 78 * (1.0 if self.name != "Caudillo" else 1.28))


class Player(Entity):
    def __init__(self, col, row, proj):
        super().__init__("Superviviente", "assets/sprites/player.json", col, row, proj,
                         max_hp=70, max_ap=6,
                         attacks=[Attack("melee", 14, 1, 2, "melee"),
                                  Attack("ranged", 9, 5, 3, "ranged")])
        self.potions = 2


class Enemy(Entity):
    TYPES = {
        "raider": dict(name="Saqueador", hp=28, ap=5, atk=Attack("main", 9, 1, 2, "melee"), aggro=9),
        "gunner": dict(name="Pistolero", hp=20, ap=5, atk=Attack("main", 8, 5, 3, "ranged"), aggro=11),
        "brute": dict(name="Bruto", hp=48, ap=4, atk=Attack("main", 15, 1, 3, "melee"), aggro=8),
        "warlord": dict(name="Caudillo", hp=80, ap=5, atk=Attack("main", 16, 1, 3, "melee"), aggro=30),
    }

    def __init__(self, kind, col, row, proj):
        t = self.TYPES[kind]
        super().__init__(t["name"], f"assets/sprites/{kind}.json", col, row, proj,
                         max_hp=t["hp"], max_ap=t["ap"], attacks=[t["atk"]])
        self.kind = kind
        self.aggro = t["aggro"]
        self.alerted = False
        self.flip = True

    @property
    def attack(self):
        return self.attacks["main"]


class Collectible(GameObject):
    """Objeto recogible del mapa (poción)."""

    def __init__(self, col, row, proj, kind="potion"):
        super().__init__(0, 0, f"assets/sprites/{kind}.json")
        self.kind = kind
        self.col, self.row = col, row
        self.proj = proj
        self.collected = False
        self.x, self.y = proj.to_screen(col, row)
        self.frame_timer = (col * 37 + row * 91) % 300

    def sort_key(self):
        return self.col + self.row
