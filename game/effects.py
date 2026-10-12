"""Efectos visuales: partículas, textos flotantes y proyectiles."""
import math
import random

import pygame

from core.ui import get_font, render_text


class FxManager:
    def __init__(self):
        self.particles = []
        self.texts = []
        self.projectiles = []
        self.rnd = random.Random(7)

    # ------------------------------------------------------------ creación
    def burst(self, x, y, color, n=12, speed=140, life=500, size=3, gravity=320, up=0.6):
        for _ in range(n):
            ang = self.rnd.uniform(0, math.tau)
            sp = self.rnd.uniform(0.3, 1.0) * speed
            self.particles.append(dict(x=x, y=y, vx=math.cos(ang) * sp, vy=math.sin(ang) * sp * 0.6 - speed * up,
                                       life=life * self.rnd.uniform(0.6, 1.1), max=life, color=color,
                                       size=size * self.rnd.uniform(0.7, 1.4), g=gravity))

    def dust(self, x, y):
        self.burst(x, y, (222, 190, 140), n=4, speed=40, life=420, size=3, gravity=-20, up=0.2)

    def sparkle(self, x, y, color=(120, 255, 150)):
        for _ in range(14):
            self.particles.append(dict(x=x + self.rnd.uniform(-14, 14), y=y + self.rnd.uniform(-6, 6), vx=0,
                                       vy=-self.rnd.uniform(30, 90), life=self.rnd.uniform(500, 900), max=800,
                                       color=color, size=self.rnd.uniform(2, 4), g=0))

    def text(self, x, y, msg, color, size=26, life=1100):
        self.texts.append(dict(x=x, y=y, msg=msg, color=color, size=size, life=life, max=life))

    def projectile(self, p0, p1, color=(255, 236, 150), duration=160):
        self.projectiles.append(dict(p0=p0, p1=p1, t=0.0, d=duration, color=color))

    def projectiles_active(self):
        return bool(self.projectiles)

    # -------------------------------------------------------------- update
    def update(self, dt):
        for p in self.particles:
            p["life"] -= dt
            p["vy"] += p["g"] * dt / 1000
            p["x"] += p["vx"] * dt / 1000
            p["y"] += p["vy"] * dt / 1000
        self.particles = [p for p in self.particles if p["life"] > 0]
        for t in self.texts:
            t["life"] -= dt
            t["y"] -= 38 * dt / 1000
        self.texts = [t for t in self.texts if t["life"] > 0]
        for pr in self.projectiles:
            pr["t"] += dt
        self.projectiles = [p for p in self.projectiles if p["t"] < p["d"]]

    # ---------------------------------------------------------------- draw
    def draw(self, surface, offset=(0, 0)):
        ox, oy = offset
        for p in self.particles:
            a = max(0, min(255, int(255 * p["life"] / p["max"])))
            s = max(1, int(p["size"]))
            surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["color"], a), (s, s), s)
            surface.blit(surf, (p["x"] - s + ox, p["y"] - s + oy))
        for pr in self.projectiles:
            t = min(1.0, pr["t"] / pr["d"])
            x = pr["p0"][0] + (pr["p1"][0] - pr["p0"][0]) * t
            y = pr["p0"][1] + (pr["p1"][1] - pr["p0"][1]) * t
            t0 = max(0.0, t - 0.25)
            xt = pr["p0"][0] + (pr["p1"][0] - pr["p0"][0]) * t0
            yt = pr["p0"][1] + (pr["p1"][1] - pr["p0"][1]) * t0
            pygame.draw.line(surface, (255, 150, 60), (xt + ox, yt + oy), (x + ox, y + oy), 5)
            pygame.draw.line(surface, pr["color"], (xt + ox, yt + oy), (x + ox, y + oy), 2)
            pygame.draw.circle(surface, (255, 255, 240), (int(x + ox), int(y + oy)), 4)
        for t in self.texts:
            a = max(0, min(255, int(255 * min(1.0, t["life"] / (t["max"] * 0.5)))))
            font = get_font(t["size"], bold=True)
            img = render_text(t["msg"], font, t["color"])
            sh = render_text(t["msg"], font, (10, 6, 10))
            if a < 255:
                img = img.copy(); img.set_alpha(a)
                sh = sh.copy(); sh.set_alpha(a)
            r = img.get_rect(center=(t["x"] + ox, t["y"] + oy))
            surface.blit(sh, r.move(2, 2))
            surface.blit(img, r)
