#!/usr/bin/env python3
"""
Generador de assets del juego "Cenizas del Yermo".

TODOS los assets (sprites, tiles isométricos, fondo del menú, efectos de
sonido y música) se generan por código desde este script. Por eso no hay
problemas de licencias ni de atribución: el autor de todo es este repo.

Uso (desde la raíz del proyecto):

    python tools/generate_assets.py

Salida:
    assets/sprites/*.png + *.json   (hojas de sprites + animaciones)
    assets/tiles/*.png + tiles.json (tiles isométricos de 64x32)
    assets/ui/menu_bg.png           (fondo del menú)
    assets/sounds/*.wav             (SFX y música)
"""
import json
import math
import os
import random
import struct
import wave
from array import array
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "assets" / "sprites"
TILES = ROOT / "assets" / "tiles"
SOUNDS = ROOT / "assets" / "sounds"
UI = ROOT / "assets" / "ui"
for d in (SPRITES, TILES, SOUNDS, UI):
    d.mkdir(parents=True, exist_ok=True)

OUTLINE = (24, 14, 14, 255)


# =============================================================================
# Utilidades de dibujo
# =============================================================================
def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def shade(c, f):
    return (clamp(c[0] * f), clamp(c[1] * f), clamp(c[2] * f))


def jitter(c, amt, rnd):
    d = rnd.randint(-amt, amt)
    return (clamp(c[0] + d), clamp(c[1] + d), clamp(c[2] + d))


def outline_surface(surf, thickness):
    """Agrega un contorno oscuro alrededor de las partes opacas."""
    mask = pygame.mask.from_surface(surf, 20)
    sil = mask.to_surface(setcolor=OUTLINE, unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    t = thickness
    for dx in (-t, 0, t):
        for dy in (-t, 0, t):
            if dx or dy:
                out.blit(sil, (dx, dy))
    out.blit(surf, (0, 0))
    return out


# =============================================================================
# PERSONAJES
# =============================================================================
S = 3                      # supersampling
FW, FH = 104, 112          # tamaño de un frame
CX, FOOT = 52, 106          # pie del personaje dentro del frame (ancla)

SPECS = {
    "player": dict(skin=(226, 174, 132), hair=(70, 46, 32), shirt=(52, 104, 158),
                   pants=(84, 72, 60), boots=(52, 36, 30), accent=(224, 168, 60),
                   hat="goggles", weapon="machete", scale=1.0, ranged=False),
    "raider": dict(skin=(204, 152, 112), hair=(150, 40, 36), shirt=(150, 50, 40),
                   pants=(62, 56, 50), boots=(40, 30, 28), accent=(210, 70, 44),
                   hat="mohawk", weapon="club", scale=1.0, ranged=False),
    "gunner": dict(skin=(196, 156, 124), hair=(60, 50, 40), shirt=(86, 102, 62),
                   pants=(72, 66, 52), boots=(44, 36, 28), accent=(120, 150, 80),
                   hat="hood", weapon="rifle", scale=0.98, ranged=True),
    "brute": dict(skin=(172, 122, 96), hair=(40, 30, 30), shirt=(100, 100, 108),
                  pants=(54, 54, 60), boots=(34, 34, 38), accent=(170, 170, 180),
                  hat="helmet", weapon="hammer", scale=1.18, ranged=False),
    "warlord": dict(skin=(156, 108, 92), hair=(30, 24, 30), shirt=(52, 46, 62),
                    pants=(40, 36, 46), boots=(28, 24, 30), accent=(196, 44, 54),
                    hat="horns", weapon="axe", scale=1.28, ranged=False),
}


def _limb(surf, p0, p1, w, color):
    pygame.draw.line(surf, color, p0, p1, max(1, int(w)))
    r = max(1, int(w / 2))
    pygame.draw.circle(surf, color, (int(p0[0]), int(p0[1])), r)
    pygame.draw.circle(surf, color, (int(p1[0]), int(p1[1])), r)


def _draw_weapon(surf, kind, hx, hy, th, sc, flash=False):
    a = math.radians(th)
    d = (math.sin(a), -math.cos(a))
    n = (-d[1], d[0])
    k = sc * S

    def pt(along, side=0.0):
        return (hx + (d[0] * along + n[0] * side) * k,
                hy + (d[1] * along + n[1] * side) * k)

    steel = (190, 198, 208)
    wood = (118, 78, 46)
    dark = (60, 52, 50)
    if kind == "machete":
        _limb(surf, pt(-5), pt(4), 3 * k, (80, 56, 40))
        pygame.draw.polygon(surf, steel, [pt(4, -1.8), pt(22, -3.0), pt(29, 0.8),
                                          pt(22, 2.2), pt(4, 1.8)])
        pygame.draw.line(surf, (235, 240, 248), pt(5, -0.8), pt(24, -0.8), max(1, int(k * 0.8)))
        pygame.draw.line(surf, (120, 70, 40), pt(4, -5), pt(4, 5), int(2 * k))
    elif kind == "club":
        pygame.draw.polygon(surf, wood, [pt(-4, -1.4), pt(14, -2.2), pt(26, -4.2),
                                         pt(27, 4.2), pt(14, 2.2), pt(-4, 1.4)])
        for off in (-3, 3):
            for al in (19, 24):
                p = pt(al, off)
                pygame.draw.circle(surf, (210, 210, 218), (int(p[0]), int(p[1])), max(1, int(k * 1.1)))
    elif kind == "hammer":
        _limb(surf, pt(-8), pt(26), 3.2 * k, (90, 64, 42))
        pygame.draw.polygon(surf, (120, 124, 134), [pt(20, -9), pt(32, -9), pt(32, 9), pt(20, 9)])
        pygame.draw.polygon(surf, (170, 176, 188), [pt(20, -9), pt(32, -9), pt(32, -6), pt(20, -6)])
    elif kind == "axe":
        _limb(surf, pt(-8), pt(34), 3 * k, (80, 56, 40))
        pygame.draw.polygon(surf, (150, 154, 164), [pt(22, 0), pt(24, -13), pt(36, -9),
                                                    pt(33, 0), pt(36, 9), pt(24, 13)])
        pygame.draw.polygon(surf, (220, 226, 236), [pt(24, -13), pt(36, -9), pt(34, -5), pt(25, -9)])
        pygame.draw.circle(surf, (200, 40, 50), (int(pt(28, 0)[0]), int(pt(28, 0)[1])), int(1.8 * k))
    elif kind == "rifle":
        pygame.draw.polygon(surf, wood, [pt(-12, -2), pt(0, -2.4), pt(2, 2.4), pt(-12, 3.4)])
        pygame.draw.polygon(surf, dark, [pt(0, -2.4), pt(26, -1.6), pt(30, -1.2),
                                         pt(30, 1.2), pt(26, 1.6), pt(2, 2.4)])
        _limb(surf, pt(6, 3), pt(8, 8), 2.4 * k, (50, 44, 44))
        pygame.draw.line(surf, (150, 150, 160), pt(4, -2.5), pt(24, -2), max(1, int(k * 0.8)))
        if flash:
            c = pt(36)
            for r, col in ((10, (255, 140, 40)), (6.5, (255, 220, 90)), (3, (255, 255, 235))):
                pygame.draw.circle(surf, col, (int(c[0]), int(c[1])), int(r * k * 0.8))
            for ang in range(0, 360, 60):
                aa = math.radians(ang)
                pygame.draw.line(surf, (255, 200, 80), c,
                                 (c[0] + math.cos(aa) * 14 * k, c[1] + math.sin(aa) * 14 * k), int(k))


def draw_character(spec, pose):
    surf = pygame.Surface((FW * S, FH * S), pygame.SRCALPHA)
    sc = spec["scale"]
    ox = pose.get("lunge", 0) + pose.get("ox", 0)
    lean = pose.get("lean", 0)
    bob = pose.get("bob", 0)

    def P(x, y, b=True):
        X = CX + (x - CX) * sc + ox + lean * ((73 - y) / 60.0)
        Y = FOOT + (y - 73) * sc - (bob * sc if b else 0)
        return (X * S, Y * S)

    W = lambda w: max(1, w * sc * S)  # noqa: E731
    skin, shirt, pants, boots = spec["skin"], spec["shirt"], spec["pants"], spec["boots"]
    acc, hair = spec["accent"], spec["hair"]
    hat = spec["hat"]

    # --- capa trasera: capa del jefe / brazo trasero ---------------------------------
    if hat == "horns":
        pygame.draw.polygon(surf, (150, 30, 40), [P(CX - 11, 32), P(CX + 11, 32),
                                                  P(CX + 16, 72, False), P(CX - 16, 74, False)])
        pygame.draw.polygon(surf, (110, 22, 30), [P(CX - 11, 32), P(CX - 2, 32),
                                                  P(CX - 4, 74, False), P(CX - 16, 74, False)])

    def arm_hand(shoulder, phi, length):
        a = math.radians(phi)
        return (shoulder[0] + math.sin(a) * length, shoulder[1] + math.cos(a) * length)

    sh_b = (CX - 10, 34)
    hand_b = arm_hand(sh_b, pose.get("arm_back", -8), 14)
    _limb(surf, P(*sh_b), P(*hand_b), W(5.2), shade(shirt, 0.8))
    pygame.draw.circle(surf, skin, tuple(int(v) for v in P(*hand_b)), int(W(2.6)))

    # --- piernas --------------------------------------------------------------------
    for side, (dx, lift) in zip((-1, 1), pose.get("legs", [(0, 0), (0, 0)])):
        hip = P(CX + side * 4.6, 50)
        foot = P(CX + side * 4.8 + dx, 73 - lift, False)
        _limb(surf, hip, foot, W(6.4), shade(pants, 0.9 if side < 0 else 1.0))
        bx, by = foot
        pygame.draw.ellipse(surf, boots, (bx - W(5.2), by - W(2.6), W(11) + W(1.2), W(5.4)))

    # --- torso ----------------------------------------------------------------------
    tors = [P(CX - 11, 32), P(CX + 11, 32), P(CX + 9.5, 52), P(CX - 9.5, 52)]
    pygame.draw.polygon(surf, shirt, tors)
    pygame.draw.polygon(surf, shade(shirt, 0.82), [P(CX + 2, 32), P(CX + 11, 32), P(CX + 9.5, 52), P(CX + 4, 52)])
    # cinturón
    pygame.draw.polygon(surf, (62, 44, 34), [P(CX - 9.8, 48), P(CX + 9.8, 48), P(CX + 9.5, 52), P(CX - 9.5, 52)])
    bk = P(CX, 50)
    pygame.draw.rect(surf, acc, (bk[0] - W(1.8), bk[1] - W(1.6), W(3.6), W(3.2)))

    if hat in ("goggles",):
        # bufanda
        pygame.draw.polygon(surf, acc, [P(CX - 9, 30), P(CX + 9, 30), P(CX + 8, 35), P(CX - 8, 35)])
        pygame.draw.polygon(surf, shade(acc, 0.8), [P(CX + 3, 34), P(CX + 8, 34), P(CX + 11, 46), P(CX + 6, 44)])
        # chaleco de cuero
        pygame.draw.polygon(surf, (112, 76, 48), [P(CX - 11, 35), P(CX - 4, 35), P(CX - 4, 52), P(CX - 9.5, 52)])
        pygame.draw.polygon(surf, (112, 76, 48), [P(CX + 11, 35), P(CX + 4, 35), P(CX + 4, 52), P(CX + 9.5, 52)])
    if hat in ("helmet", "horns"):
        # hombreras
        for sx in (-1, 1):
            c = P(CX + sx * 12, 34)
            pygame.draw.ellipse(surf, spec["accent"] if hat == "helmet" else (60, 54, 70),
                                (c[0] - W(6.5), c[1] - W(4.5), W(13), W(9)))
            pygame.draw.ellipse(surf, shade(spec["accent"], 0.7) if hat == "helmet" else (90, 84, 104),
                                (c[0] - W(6.5), c[1] - W(0.5), W(13), W(4.5)))
            if hat == "horns":
                pygame.draw.polygon(surf, (210, 210, 220), [P(CX + sx * 12 - 2, 30), P(CX + sx * 12 + 2, 30), P(CX + sx * 12, 23)])
        if hat == "horns":
            pygame.draw.line(surf, acc, P(CX - 9, 40), P(CX + 9, 46), int(W(2.2)))
    if hat == "hood":
        pygame.draw.polygon(surf, shade(spec["accent"], 0.75), [P(CX - 12, 31), P(CX + 12, 31), P(CX + 6, 38), P(CX - 6, 38)])
        pygame.draw.line(surf, (30, 28, 24), P(CX - 6, 38), P(CX + 8, 52), int(W(2)))  # bandolera
    if hat == "mohawk":
        # tiras de cuero cruzadas
        pygame.draw.line(surf, (50, 36, 30), P(CX - 10, 33), P(CX + 8, 51), int(W(2.4)))
        pygame.draw.line(surf, (50, 36, 30), P(CX + 10, 33), P(CX - 8, 51), int(W(2.4)))
        pygame.draw.circle(surf, (200, 200, 210), tuple(int(v) for v in P(CX, 42)), int(W(1.8)))

    # --- cabeza ---------------------------------------------------------------------
    hc = P(CX, 21)
    hr = W(9.2)
    if hat == "hood":
        pygame.draw.circle(surf, shade(spec["accent"], 0.75), (int(hc[0]), int(hc[1] - W(0.6))), int(hr + W(2.2)))
        pygame.draw.circle(surf, (30, 26, 24), (int(hc[0]), int(hc[1] + W(1))), int(hr - W(0.6)))
        for ex in (-3.2, 3.2):
            e = P(CX + ex, 22)
            col = (255, 210, 90) if not pose.get("closed") else (30, 26, 24)
            pygame.draw.circle(surf, col, (int(e[0]), int(e[1])), max(1, int(W(1.5))))
    else:
        pygame.draw.circle(surf, skin, (int(hc[0]), int(hc[1])), int(hr))
        pygame.draw.circle(surf, shade(skin, 0.86), (int(hc[0] + W(3)), int(hc[1] + W(2))), int(hr * 0.62))
        pygame.draw.circle(surf, skin, (int(hc[0] - W(0.8)), int(hc[1] - W(0.6))), int(hr * 0.86))
        for ex in (-3.4, 3.4):
            e = P(CX + ex, 22)
            if pose.get("closed"):
                pygame.draw.line(surf, (40, 24, 20), (e[0] - W(1.4), e[1]), (e[0] + W(1.4), e[1]), max(1, int(W(0.9))))
            else:
                pygame.draw.circle(surf, (250, 245, 235), (int(e[0]), int(e[1])), max(1, int(W(1.8))))
                pygame.draw.circle(surf, (30, 20, 20), (int(e[0] + W(0.3)), int(e[1])), max(1, int(W(1.0))))
        m = P(CX + 0.5, 27)
        pygame.draw.line(surf, shade(skin, 0.55), (m[0] - W(2), m[1]), (m[0] + W(2), m[1]), max(1, int(W(0.8))))

    if hat == "goggles":
        pygame.draw.circle(surf, hair, (int(hc[0]), int(hc[1] - W(2))), int(hr * 0.98), draw_top_left=True, draw_top_right=True)
        pygame.draw.polygon(surf, hair, [P(CX - 9, 20), P(CX - 6, 12), P(CX + 8, 13), P(CX + 9, 20), P(CX + 3, 16)])
        pygame.draw.line(surf, (46, 40, 40), P(CX - 9.5, 15), P(CX + 9.5, 15), int(W(2.6)))
        for gx in (-4, 4):
            g = P(CX + gx, 15)
            pygame.draw.circle(surf, (36, 32, 32), (int(g[0]), int(g[1])), int(W(3.3)))
            pygame.draw.circle(surf, (110, 220, 240), (int(g[0]), int(g[1])), int(W(2.2)))
            pygame.draw.circle(surf, (230, 255, 255), (int(g[0] - W(0.7)), int(g[1] - W(0.7))), int(W(0.8)))
    elif hat == "mohawk":
        pygame.draw.polygon(surf, (36, 28, 28), [P(CX - 9, 18), P(CX + 9, 18), P(CX + 8, 13), P(CX - 8, 13)])
        for i, xx in enumerate(range(-7, 9, 4)):
            h = 7 + (i % 2) * 3
            pygame.draw.polygon(surf, hair, [P(CX + xx - 2.2, 14), P(CX + xx, 14 - h), P(CX + xx + 2.2, 14)])
        pygame.draw.line(surf, acc, P(CX - 9.4, 18), P(CX + 9.4, 18), int(W(2.4)))
    elif hat == "helmet":
        pygame.draw.circle(surf, (118, 120, 130), (int(hc[0]), int(hc[1] - W(1.5))), int(hr * 1.06), draw_top_left=True, draw_top_right=True)
        pygame.draw.rect(surf, (118, 120, 130), (hc[0] - hr * 1.06, hc[1] - W(1.6), hr * 2.12, W(5)))
        pygame.draw.rect(surf, (28, 28, 34), (hc[0] - hr * 0.8, hc[1] + W(0.2), hr * 1.6, W(2.2)))
        pygame.draw.polygon(surf, (180, 184, 196), [P(CX - 2, 11), P(CX + 2, 11), P(CX, 3)])
        pygame.draw.line(surf, (200, 204, 214), P(CX - 7, 13), P(CX - 1, 11), int(W(1.2)))
    elif hat == "horns":
        pygame.draw.circle(surf, (44, 40, 52), (int(hc[0]), int(hc[1] - W(1.5))), int(hr * 1.06), draw_top_left=True, draw_top_right=True)
        pygame.draw.rect(surf, (44, 40, 52), (hc[0] - hr * 1.06, hc[1] - W(1.6), hr * 2.12, W(4)))
        pygame.draw.rect(surf, (200, 40, 50), (hc[0] - hr * 0.8, hc[1] + W(0.6), hr * 1.6, W(1.6)))
        for sx in (-1, 1):
            pygame.draw.polygon(surf, (226, 220, 206), [P(CX + sx * 8, 14), P(CX + sx * 11.5, 15), P(CX + sx * 17, 1),
                                                         P(CX + sx * 14, 8)])
            pygame.draw.polygon(surf, (176, 170, 156), [P(CX + sx * 11.5, 15), P(CX + sx * 17, 1), P(CX + sx * 14.5, 11)])

    # --- brazo delantero + arma ----------------------------------------------------
    sh_f = (CX + 10, 34)
    phi = pose.get("arm_front", 15)
    hand_f = arm_hand(sh_f, phi, 14)
    hp = P(*hand_f)
    _draw_weapon(surf, spec["weapon"], hp[0], hp[1], pose.get("weapon", 35), sc, pose.get("flash", False))
    _limb(surf, P(*sh_f), hp, W(5.2), shirt)
    pygame.draw.circle(surf, skin, (int(hp[0]), int(hp[1])), int(W(2.8)))

    surf = outline_surface(surf, S)
    return pygame.transform.smoothscale(surf, (FW, FH))


def anim_pose(spec, name, i):
    """Devuelve el diccionario de pose para el frame i de la animación `name`."""
    ranged = spec["ranged"]
    base_theta = 95 if ranged else 35
    base_phi = 58 if ranged else 15
    pose = dict(bob=0, lean=0, lunge=0, legs=[(0, 0), (0, 0)], arm_back=-8,
                arm_front=base_phi, weapon=base_theta, flash=False, closed=False)
    if name == "idle":
        t = i / 4.0
        s = math.sin(2 * math.pi * t)
        pose.update(bob=1.2 + s * 1.2, arm_front=base_phi + s * 4, arm_back=-8 - s * 3)
    elif name == "walk":
        t = i / 6.0
        s = math.sin(2 * math.pi * t)
        c = math.cos(2 * math.pi * t)
        pose.update(bob=abs(s) * 2.2,
                    legs=[(s * 6.5, max(0, -c) * 3.5), (-s * 6.5, max(0, c) * 3.5)],
                    arm_back=-s * 26,
                    arm_front=base_phi + s * (10 if ranged else 26),
                    lean=1.5)
    elif name == "attack":
        if ranged:
            frames = [dict(arm_front=70, weapon=92, lunge=0),
                      dict(arm_front=88, weapon=90, lunge=-1, flash=True),
                      dict(arm_front=92, weapon=86, lunge=-3, flash=True),
                      dict(arm_front=80, weapon=92, lunge=-1)]
        else:
            frames = [dict(arm_front=165, weapon=15, lunge=-3, lean=-3),
                      dict(arm_front=150, weapon=30, lunge=-4, lean=-4),
                      dict(arm_front=55, weapon=125, lunge=6, lean=5),
                      dict(arm_front=35, weapon=145, lunge=4, lean=3)]
        pose.update(frames[i])
        pose["legs"] = [(-3, 0), (4, 0)] if i >= 2 else [(2, 0), (-2, 0)]
    elif name == "hurt":
        pose.update(lean=-6 if i == 0 else -4, lunge=-3, closed=True,
                    arm_front=base_phi - 15, arm_back=-30, bob=-1)
    return pose


def make_sprite(name, spec):
    anims = [("idle", 4, 170, True), ("walk", 6, 85, True), ("attack", 4, 80, False),
             ("hurt", 2, 120, False), ("dead", 3, 130, False)]
    cols = max(a[1] for a in anims)
    sheet = pygame.Surface((FW * cols, FH * len(anims)), pygame.SRCALPHA)
    data = {"spritesheet_path": f"assets/sprites/{name}.png", "frame_width": FW,
            "frame_height": FH, "anchor": [CX, FOOT], "animations": {}, "frame_ms": {}, "loop": {}}
    for row, (an, n, ms, loop) in enumerate(anims):
        frames = []
        for i in range(n):
            if an == "dead":
                ang = (40, 72, 90)[i]
                img = draw_character(spec, anim_pose(spec, "hurt", 0))
                rot = pygame.transform.rotate(img, -ang)
                ctr_off = 36 * spec["scale"]
                th = math.radians(ang)
                vx, vy = 0, -ctr_off
                nx = vx * math.cos(th) - vy * math.sin(th)
                ny = vx * math.sin(th) + vy * math.cos(th)
                pivot_x = CX - 38 * math.sin(th)
                frame = pygame.Surface((FW, FH), pygame.SRCALPHA)
                r = rot.get_rect(center=(pivot_x + nx, FOOT + ny - 2 * math.sin(th)))
                frame.blit(rot, r)
                img = frame
            else:
                img = draw_character(spec, anim_pose(spec, an, i))
            sheet.blit(img, (i * FW, row * FH))
            frames.append({"x": i * FW, "y": row * FH, "width": FW, "height": FH})
        data["animations"][an] = frames
        data["frame_ms"][an] = ms
        data["loop"][an] = loop
    pygame.image.save(sheet, str(SPRITES / f"{name}.png"))
    (SPRITES / f"{name}.json").write_text(json.dumps(data, indent=2))
    print("  sprite:", name)


def make_potion():
    fw = fh = 40
    frames = 4
    sheet = pygame.Surface((fw * frames, fh), pygame.SRCALPHA)
    data = {"spritesheet_path": "assets/sprites/potion.png", "frame_width": fw, "frame_height": fh,
            "anchor": [20, 34], "animations": {"idle": []}, "frame_ms": {"idle": 140}, "loop": {"idle": True}}
    for i in range(frames):
        s = pygame.Surface((fw * S, fh * S), pygame.SRCALPHA)
        bob = math.sin(2 * math.pi * i / frames) * 2.2
        cx = fw / 2 * S
        # resplandor
        glow = pygame.Surface((fw * S, fh * S), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 90, 90, 70 + int(25 * math.sin(2 * math.pi * i / frames))),
                           (int(cx), int((24 + bob) * S)), int(14 * S))
        s.blit(glow, (0, 0))
        by = (25 + bob) * S
        pygame.draw.ellipse(s, (210, 230, 240), (cx - 8 * S, by - 9 * S, 16 * S, 18 * S))
        pygame.draw.ellipse(s, (210, 40, 56), (cx - 7 * S, by - 4 * S, 14 * S, 12.5 * S))
        pygame.draw.ellipse(s, (255, 130, 140), (cx - 5 * S, by - 2 * S, 4 * S, 6 * S))
        pygame.draw.rect(s, (214, 230, 240), (cx - 3.5 * S, by - 14 * S, 7 * S, 7 * S))
        pygame.draw.rect(s, (150, 100, 60), (cx - 4.5 * S, by - 17 * S, 9 * S, 4 * S))
        pygame.draw.rect(s, (255, 255, 255), (cx - 1 * S, by - 2 * S, 2 * S, 8 * S))
        pygame.draw.rect(s, (255, 255, 255), (cx - 4 * S, by + 1 * S, 8 * S, 2 * S))
        s = outline_surface(s, S)
        sheet.blit(pygame.transform.smoothscale(s, (fw, fh)), (i * fw, 0))
        data["animations"]["idle"].append({"x": i * fw, "y": 0, "width": fw, "height": fh})
    pygame.image.save(sheet, str(SPRITES / "potion.png"))
    (SPRITES / "potion.json").write_text(json.dumps(data, indent=2))
    print("  sprite: potion")


# =============================================================================
# TILES ISOMÉTRICOS (64x32)
# =============================================================================
TW, TH = 64, 32


def inside_diamond(x, y, cx, cy, hw, hh):
    return abs(x - cx) / hw + abs(y - cy) / hh <= 1.0


def make_ground(name, base, seed, style):
    rnd = random.Random(seed)
    S2 = 4
    surf = pygame.Surface((TW * S2, TH * S2), pygame.SRCALPHA)
    pts = [(TW / 2 * S2, 0), (TW * S2, TH / 2 * S2), (TW / 2 * S2, TH * S2), (0, TH / 2 * S2)]
    pygame.draw.polygon(surf, base, pts)
    cx, cy, hw, hh = TW / 2, TH / 2, TW / 2, TH / 2

    def spk(n, amt, size=1):
        for _ in range(n):
            x, y = rnd.uniform(0, TW), rnd.uniform(0, TH)
            if inside_diamond(x, y, cx, cy, hw - 2, hh - 1):
                pygame.draw.circle(surf, jitter(base, amt, rnd), (int(x * S2), int(y * S2)), size * S2 // 2)

    spk(220, 16, 1)
    if style == "sand":
        spk(40, 26, 2)
        for _ in range(3):
            x, y = rnd.uniform(14, 50), rnd.uniform(8, 24)
            pygame.draw.line(surf, shade(base, 0.9), (x * S2, y * S2), ((x + rnd.uniform(4, 9)) * S2, (y + rnd.uniform(1, 3) * 0.5) * S2), S2 // 2)
    elif style == "dirt":
        spk(60, 30, 2)
        for _ in range(5):
            x, y = rnd.uniform(14, 50), rnd.uniform(8, 24)
            pygame.draw.circle(surf, shade(base, 0.72), (int(x * S2), int(y * S2)), int(rnd.uniform(1, 2.4) * S2))
    elif style == "cracked":
        for _ in range(3):
            x, y = rnd.uniform(18, 46), rnd.uniform(9, 23)
            pts2 = [(x, y)]
            for _k in range(4):
                x += rnd.uniform(-6, 6)
                y += rnd.uniform(-3, 3)
                pts2.append((x, y))
            pygame.draw.lines(surf, shade(base, 0.5), False, [(a * S2, b * S2) for a, b in pts2], S2 // 2 + 1)
    elif style == "concrete":
        # placas con junta
        pygame.draw.line(surf, shade(base, 0.62), (TW / 4 * S2, TH / 4 * S2), (TW * 3 / 4 * S2, TH * 3 / 4 * S2), S2 // 2 + 1)
        pygame.draw.line(surf, shade(base, 0.62), (TW * 3 / 4 * S2, TH / 4 * S2), (TW / 4 * S2, TH * 3 / 4 * S2), S2 // 2 + 1)
        pygame.draw.line(surf, shade(base, 1.18), (TW / 4 * S2, TH / 4 * S2 - 3), (TW * 3 / 4 * S2, TH * 3 / 4 * S2 - 3), 2)
        spk(40, 20, 2)
        for _ in range(2):
            x, y = rnd.uniform(20, 44), rnd.uniform(10, 22)
            pygame.draw.circle(surf, (110, 74, 50), (int(x * S2), int(y * S2)), int(rnd.uniform(1.4, 3) * S2))
    # contorno sutil del rombo para marcar la grilla
    pygame.draw.polygon(surf, shade(base, 0.78), pts, S2 // 2 + 1)
    pygame.draw.line(surf, shade(base, 1.18), pts[0], pts[3], S2 // 2)
    pygame.draw.line(surf, shade(base, 1.18), pts[0], pts[1], S2 // 2)
    out = pygame.transform.smoothscale(surf, (TW, TH))
    pygame.image.save(out, str(TILES / f"{name}.png"))
    return out


def draw_box(h, s, top, left, right, tex, seed, jag=False):
    """Bloque isométrico de footprint `s` (0..1) y altura h. Imagen 64x(32+h)."""
    rnd = random.Random(seed)
    S2 = 4
    surf = pygame.Surface((TW * S2, (TH + h) * S2), pygame.SRCALPHA)
    cx, cy = 32, 16
    a, b = 32 * s, 16 * s

    def Pt(x, y):
        return (x * S2, y * S2)

    T = [Pt(cx, cy - b), Pt(cx + a, cy), Pt(cx, cy + b), Pt(cx - a, cy)]
    L = [Pt(cx - a, cy), Pt(cx, cy + b), Pt(cx, cy + b + h), Pt(cx - a, cy + h)]
    R = [Pt(cx, cy + b), Pt(cx + a, cy), Pt(cx + a, cy + h), Pt(cx, cy + b + h)]
    # sombra en el suelo
    gc = (cx, cy + h)
    sh = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 70), ((gc[0] - 30 * s - 3) * S2, (gc[1] - 11 * s - 1) * S2, (60 * s + 6) * S2, (22 * s + 2) * S2))
    surf.blit(sh, (0, 0))
    pygame.draw.polygon(surf, left, L)
    pygame.draw.polygon(surf, right, R)
    pygame.draw.polygon(surf, top, T)

    def speckle(poly, base, n, amt):
        mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        for _ in range(int(n)):
            x, y = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
            pygame.draw.circle(layer, jitter(base, amt, rnd), (int(x), int(y)), rnd.randint(1, 3))
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(layer, (0, 0))

    speckle(L, left, 160 * s, 14)
    speckle(R, right, 160 * s, 14)
    speckle(T, top, 120 * s, 14)

    if tex == "brick":
        n = max(2, int(h / 9))
        for k in range(1, n):
            o = h * k / n
            pygame.draw.line(surf, shade(left, 0.7), Pt(cx - a, cy + o), Pt(cx, cy + b + o), 3)
            pygame.draw.line(surf, shade(right, 0.7), Pt(cx, cy + b + o), Pt(cx + a, cy + o), 3)
        for k in range(n):
            o0, o1 = h * k / n, h * (k + 1) / n
            for fx in (0.3, 0.72) if k % 2 == 0 else (0.5,):
                x = cx - a + a * fx
                pygame.draw.line(surf, shade(left, 0.7), Pt(x, cy + (b * fx) + o0), Pt(x, cy + (b * fx) + o1), 3)
                x2 = cx + a * fx
                pygame.draw.line(surf, shade(right, 0.7), Pt(x2, cy + b - b * fx + o0), Pt(x2, cy + b - b * fx + o1), 3)
        # manchas de óxido
        for _ in range(5):
            x = rnd.uniform(cx - a + 3, cx - 3)
            y0 = cy + (x - (cx - a)) * (b / a) + rnd.uniform(0, h * 0.4)
            pygame.draw.line(surf, (120, 70, 44), Pt(x, y0), Pt(x, y0 + rnd.uniform(5, 14)), 5)
    elif tex == "planks":
        n = 3
        for k in range(1, n):
            o = h * k / n
            pygame.draw.line(surf, shade(left, 0.62), Pt(cx - a, cy + o), Pt(cx, cy + b + o), 3)
            pygame.draw.line(surf, shade(right, 0.62), Pt(cx, cy + b + o), Pt(cx + a, cy + o), 3)
        # refuerzos en X
        pygame.draw.line(surf, shade(left, 0.65), Pt(cx - a, cy + 1), Pt(cx, cy + b + h - 1), 4)
        pygame.draw.line(surf, shade(left, 0.65), Pt(cx - a, cy + h - 1), Pt(cx, cy + b + 1), 4)
        pygame.draw.line(surf, shade(right, 0.65), Pt(cx + a, cy + 1), Pt(cx, cy + b + h - 1), 4)
        pygame.draw.line(surf, shade(right, 0.65), Pt(cx + a, cy + h - 1), Pt(cx, cy + b + 1), 4)
        pygame.draw.line(surf, shade(top, 0.7), Pt(cx - a / 2, cy - b / 2), Pt(cx + a / 2, cy + b / 2), 3)
        pygame.draw.line(surf, shade(top, 0.7), Pt(cx + a / 2, cy - b / 2), Pt(cx - a / 2, cy + b / 2), 3)

    # aristas con luz
    pygame.draw.line(surf, shade(top, 1.25), T[3], T[0], 4)
    pygame.draw.line(surf, shade(top, 1.25), T[0], T[1], 4)
    pygame.draw.line(surf, shade(left, 0.55), Pt(cx, cy + b), Pt(cx, cy + b + h), 3)
    if jag:
        # grietas y bordes rotos en la parte superior
        for _ in range(3):
            x = rnd.uniform(cx - a + 6, cx + a - 6)
            pygame.draw.polygon(surf, (0, 0, 0, 0), [Pt(x, cy - b), Pt(x + 3, cy - b), Pt(x + 1.5, cy - b + 2)])
    out = pygame.transform.smoothscale(surf, (TW, TH + h))
    return outline_surface(out, 1)


def make_barrel(h=28):
    S2 = 4
    surf = pygame.Surface((TW * S2, (TH + h) * S2), pygame.SRCALPHA)
    cx = 32 * S2
    gy = (16 + h) * S2
    pygame.draw.ellipse(surf, (0, 0, 0, 80), (cx - 17 * S2, gy - 7 * S2, 34 * S2, 14 * S2))
    w = 11 * S2
    top_y = 16 * S2
    body = pygame.Rect(cx - w, top_y, 2 * w, h * S2)
    pygame.draw.rect(surf, (120, 70, 50), body)
    pygame.draw.rect(surf, (150, 92, 62), (cx - w, top_y, w // 2 + 4, h * S2))
    pygame.draw.rect(surf, (90, 50, 38), (cx + w // 2, top_y, w // 2, h * S2))
    pygame.draw.ellipse(surf, (120, 70, 50), (cx - w, gy - 5.5 * S2, 2 * w, 11 * S2))
    for fy in (0.25, 0.7):
        yy = top_y + h * S2 * fy
        pygame.draw.ellipse(surf, (60, 58, 64), (cx - w - 2, yy - 3 * S2, 2 * w + 4, 7 * S2), 5)
    pygame.draw.ellipse(surf, (176, 112, 78), (cx - w, top_y - 5.5 * S2, 2 * w, 11 * S2))
    pygame.draw.ellipse(surf, (62, 40, 30), (cx - w + 8, top_y - 4.5 * S2, 2 * w - 16, 9 * S2))
    pygame.draw.ellipse(surf, (200, 150, 40), (cx - w + 14, top_y - 3.2 * S2, 2 * w - 28, 6 * S2))
    out = pygame.transform.smoothscale(surf, (TW, TH + h))
    return outline_surface(out, 1)


def make_cactus(h=46):
    S2 = 4
    surf = pygame.Surface((TW * S2, (TH + h) * S2), pygame.SRCALPHA)
    cx = 32 * S2
    gy = (16 + h) * S2
    pygame.draw.ellipse(surf, (0, 0, 0, 70), (cx - 15 * S2, gy - 6 * S2, 30 * S2, 12 * S2))
    g1, g2, g3 = (66, 142, 78), (46, 108, 62), (104, 182, 108)

    def column(x, y_top, y_bot, w):
        pygame.draw.rect(surf, g1, (x - w, y_top, 2 * w, y_bot - y_top))
        pygame.draw.circle(surf, g1, (x, y_top), w)
        pygame.draw.rect(surf, g2, (x + w // 2, y_top, w // 2, y_bot - y_top))
        pygame.draw.rect(surf, g3, (x - w + 3, y_top, 4, y_bot - y_top))

    column(cx, 5 * S2, gy - 3 * S2, 6 * S2)
    # brazos
    pygame.draw.rect(surf, g1, (cx - 15 * S2, 22 * S2, 10 * S2, 5 * S2))
    column(cx - 15 * S2, 12 * S2, 27 * S2, 3 * S2 + 6)
    pygame.draw.rect(surf, g1, (cx + 5 * S2, 28 * S2, 10 * S2, 5 * S2))
    column(cx + 15 * S2, 18 * S2, 33 * S2, 3 * S2 + 6)
    rnd = random.Random(5)
    for _ in range(24):
        x = cx + rnd.randint(-5 * S2, 5 * S2)
        y = rnd.randint(8 * S2, gy - 6 * S2)
        pygame.draw.line(surf, (240, 236, 200), (x, y), (x + rnd.randint(-6, 6), y - 8), 2)
    out = pygame.transform.smoothscale(surf, (TW, TH + h))
    return outline_surface(out, 1)


def make_rock(h=18):
    S2 = 4
    surf = pygame.Surface((TW * S2, (TH + h) * S2), pygame.SRCALPHA)
    cx = 32 * S2
    gy = (16 + h) * S2
    pygame.draw.ellipse(surf, (0, 0, 0, 70), (cx - 22 * S2, gy - 8 * S2, 44 * S2, 16 * S2))
    pts = [(cx - 20 * S2, gy - 2 * S2), (cx - 16 * S2, gy - 12 * S2), (cx - 6 * S2, gy - 20 * S2),
           (cx + 6 * S2, gy - 18 * S2), (cx + 17 * S2, gy - 10 * S2), (cx + 20 * S2, gy - 1 * S2),
           (cx, gy + 5 * S2)]
    pygame.draw.polygon(surf, (126, 112, 100), pts)
    pygame.draw.polygon(surf, (160, 146, 130), [pts[0], pts[1], pts[2], (cx - 2 * S2, gy - 8 * S2)])
    pygame.draw.polygon(surf, (92, 80, 74), [pts[3], pts[4], pts[5], pts[6], (cx + 2 * S2, gy - 6 * S2)])
    pygame.draw.polygon(surf, (176, 164, 148), [pts[1], pts[2], pts[3], (cx, gy - 12 * S2)])
    rnd = random.Random(8)
    for _ in range(60):
        x, y = cx + rnd.randint(-16 * S2, 16 * S2), gy + rnd.randint(-16 * S2, 3 * S2)
        pygame.draw.circle(surf, (110, 98, 88), (x, y), 3)
    out = pygame.transform.smoothscale(surf, (TW, TH + h))
    return outline_surface(out, 1)


def make_tiles():
    tiles = {}

    def save(name, surf, h=0, kind="floor"):
        pygame.image.save(surf, str(TILES / f"{name}.png"))
        tiles[name] = {"file": f"assets/tiles/{name}.png", "height": h, "kind": kind}

    for i, (col, seed) in enumerate([((214, 176, 112), 1), ((206, 166, 104), 2),
                                     ((220, 184, 120), 3), ((200, 160, 100), 4)]):
        save(f"sand_{i}", make_ground(f"sand_{i}", col, seed, "sand"))
    save("dirt", make_ground("dirt", (150, 108, 72), 11, "dirt"))
    save("cracked", make_ground("cracked", (178, 138, 96), 12, "cracked"))
    save("concrete", make_ground("concrete", (140, 138, 134), 13, "concrete"))
    save("wall", draw_box(44, 1.0, (176, 160, 138), (144, 124, 104), (102, 86, 72), "brick", 21, True), 44, "block")
    save("crate", draw_box(26, 0.62, (186, 138, 82), (150, 104, 60), (112, 76, 44), "planks", 22), 26, "block")
    save("barrel", make_barrel(), 28, "block")
    save("cactus", make_cactus(), 46, "block")
    save("rock", make_rock(), 18, "block")
    (TILES / "tiles.json").write_text(json.dumps({"tile_width": TW, "tile_height": TH, "tiles": tiles}, indent=2))
    print("  tiles:", len(tiles))


# =============================================================================
# FONDO DEL MENÚ
# =============================================================================
def make_menu_bg():
    W, H = 1280, 720
    surf = pygame.Surface((W, H))
    top, mid, bot = (22, 14, 44), (176, 70, 84), (250, 164, 70)
    horizon = 470
    for y in range(horizon):
        t = y / horizon
        if t < 0.6:
            c = [top[i] + (mid[i] - top[i]) * (t / 0.6) for i in range(3)]
        else:
            c = [mid[i] + (bot[i] - mid[i]) * ((t - 0.6) / 0.4) for i in range(3)]
        pygame.draw.line(surf, c, (0, y), (W, y))
    rnd = random.Random(3)
    for _ in range(120):
        x, y = rnd.randint(0, W), rnd.randint(0, 260)
        b = rnd.randint(120, 255)
        surf.set_at((x, y), (b, b, min(255, b + 20)))
    # sol
    sun = pygame.Surface((W, H), pygame.SRCALPHA)
    sx, sy = 880, 400
    for r, a in ((260, 18), (200, 28), (150, 44), (112, 70)):
        pygame.draw.circle(sun, (255, 190, 90, a), (sx, sy), r)
    pygame.draw.circle(sun, (255, 232, 160, 255), (sx, sy), 86)
    for k in range(6):
        pygame.draw.rect(sun, (0, 0, 0, 0), (sx - 100, sy + 12 + k * 14, 200, 3 + k))
    surf.blit(sun, (0, 0))

    def dunes(base_y, amp, color, seed, freq):
        r = random.Random(seed)
        ph = [r.uniform(0, 6.28) for _ in range(3)]
        pts = [(0, H)]
        for x in range(0, W + 8, 8):
            y = base_y + amp * (math.sin(x * freq + ph[0]) * 0.6 + math.sin(x * freq * 2.3 + ph[1]) * 0.3
                                + math.sin(x * freq * 0.5 + ph[2]) * 0.5)
            pts.append((x, y))
        pts.append((W, H))
        pygame.draw.polygon(surf, color, pts)

    dunes(horizon - 10, 18, (120, 56, 70), 1, 0.006)
    # ruinas lejanas
    r = random.Random(9)
    x = 40
    while x < W:
        w = r.randint(30, 80)
        h = r.randint(30, 150)
        col = (74, 40, 66)
        pygame.draw.rect(surf, col, (x, horizon - 8 - h, w, h + 30))
        for _ in range(r.randint(1, 3)):
            bx = x + r.randint(0, w - 8)
            pygame.draw.polygon(surf, (120, 56, 70), [(bx, horizon - 8 - h), (bx + 10, horizon - 8 - h), (bx + 5, horizon - 8 - h - r.randint(6, 18))])
        for wy in range(horizon - h, horizon - 20, 18):
            for wx in range(x + 6, x + w - 8, 14):
                if r.random() < 0.18:
                    pygame.draw.rect(surf, (255, 190, 90), (wx, wy, 5, 7))
        x += w + r.randint(30, 160)
    dunes(horizon + 25, 22, (92, 42, 60), 2, 0.005)
    dunes(horizon + 90, 26, (58, 28, 50), 3, 0.004)
    dunes(horizon + 160, 20, (34, 18, 38), 4, 0.007)
    # velo de polvo
    haze = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(horizon - 40, horizon + 60):
        a = int(70 * (1 - abs(y - horizon) / 60.0)) if abs(y - horizon) < 60 else 0
        pygame.draw.line(haze, (255, 170, 110, max(0, a)), (0, y), (W, y))
    surf.blit(haze, (0, 0))
    # viñeta
    vig = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(60):
        a = int(150 * (i / 60.0) ** 2)
        pygame.draw.rect(vig, (0, 0, 0, 150 - a), (i * 4, i * 2, W - i * 8, H - i * 4), 4)
    surf.blit(vig, (0, 0))
    pygame.image.save(surf, str(UI / "menu_bg.png"))
    print("  ui: menu_bg")


# =============================================================================
# SONIDO
# =============================================================================
SR = 22050


def silence(d):
    return [0.0] * int(SR * d)


def osc(kind, ph):
    p = ph % 1.0
    if kind == "sine":
        return math.sin(2 * math.pi * p)
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "saw":
        return 2 * p - 1
    if kind == "tri":
        return 4 * abs(p - 0.5) - 1
    return 0.0


def tone(f0, d, kind="sine", vol=0.5, f1=None, a=0.004, r=0.05, vib=0.0, vib_f=6.0):
    n = int(SR * d)
    out = [0.0] * n
    ph = 0.0
    f1 = f0 if f1 is None else f1
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        if vib:
            f *= 1 + vib * math.sin(2 * math.pi * vib_f * i / SR)
        ph += f / SR
        env = 1.0
        ts = i / SR
        if ts < a:
            env = ts / a
        rem = d - ts
        if rem < r:
            env *= max(0.0, rem / r)
        out[i] = osc(kind, ph) * vol * env
    return out


def noise(d, vol=0.5, lp=0.5, a=0.002, r=0.05, seed=1, sweep=None):
    rnd = random.Random(seed)
    n = int(SR * d)
    out = [0.0] * n
    y = 0.0
    for i in range(n):
        k = lp if sweep is None else lp + (sweep - lp) * (i / n)
        y += (rnd.uniform(-1, 1) - y) * k
        ts = i / SR
        env = 1.0
        if ts < a:
            env = ts / a
        rem = d - ts
        if rem < r:
            env *= max(0.0, rem / r)
        out[i] = y * vol * env
    return out


def mix(*tracks, offsets=None):
    offsets = offsets or [0.0] * len(tracks)
    n = max(len(t) + int(o * SR) for t, o in zip(tracks, offsets))
    out = [0.0] * n
    for t, o in zip(tracks, offsets):
        st = int(o * SR)
        for i, v in enumerate(t):
            out[st + i] += v
    return out


def seq(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def save_wav(name, samples, gain=1.0):
    peak = max(1e-6, max(abs(v) for v in samples))
    scale = min(gain, 0.95 / peak) if peak > 0.95 else gain
    data = array("h", (clamp(v * scale * 32767, -32767, 32767) for v in samples))
    with wave.open(str(SOUNDS / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("  sound:", name)


NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(note, octave):
    return 440.0 * 2 ** ((NOTE[note] - 9 + 12 * (octave - 4)) / 12.0)


def make_sfx():
    save_wav("click", seq(tone(1250, 0.03, "square", 0.35, 900, r=0.02), tone(700, 0.03, "square", 0.25, 520, r=0.02)))
    save_wav("hover", tone(880, 0.035, "sine", 0.22, 1040, r=0.025))
    save_wav("confirm", seq(tone(hz("C", 5), 0.07, "square", 0.3), tone(hz("E", 5), 0.07, "square", 0.3),
                            tone(hz("G", 5), 0.07, "square", 0.3), tone(hz("C", 6), 0.18, "square", 0.32, r=0.12)))
    save_wav("back", seq(tone(hz("G", 4), 0.06, "square", 0.28), tone(hz("C", 4), 0.1, "square", 0.28, r=0.07)))
    save_wav("hit", mix(noise(0.14, 0.9, 0.4, r=0.1, seed=3), tone(150, 0.16, "sine", 0.8, 50, r=0.1)))
    save_wav("crit", mix(noise(0.2, 1.0, 0.5, r=0.14, seed=4), tone(190, 0.2, "sine", 0.9, 45, r=0.14),
                         tone(hz("E", 6), 0.18, "square", 0.22, hz("A", 6), r=0.14)))
    save_wav("miss", noise(0.2, 0.55, 0.05, a=0.04, r=0.12, seed=5, sweep=0.5))
    save_wav("slash", mix(noise(0.16, 0.7, 0.08, a=0.01, r=0.08, seed=6, sweep=0.6), tone(520, 0.12, "saw", 0.12, 180, r=0.08)))
    save_wav("shoot", mix(noise(0.2, 1.0, 0.7, r=0.16, seed=7), tone(900, 0.14, "saw", 0.4, 110, r=0.1)))
    save_wav("step", noise(0.045, 0.6, 0.18, a=0.001, r=0.03, seed=8))
    save_wav("potion", mix(*[tone(300 + 120 * k, 0.1, "sine", 0.3, 400 + 150 * k, r=0.06, vib=0.02) for k in range(5)],
                           offsets=[0.07 * k for k in range(5)]))
    save_wav("pickup", seq(tone(hz("E", 5), 0.06, "square", 0.25), tone(hz("B", 5), 0.14, "square", 0.25, r=0.1)))
    save_wav("death", mix(tone(420, 0.55, "saw", 0.4, 50, r=0.35), noise(0.5, 0.5, 0.12, r=0.4, seed=9)))
    save_wav("turn", seq(tone(hz("A", 5), 0.09, "sine", 0.4), tone(hz("E", 6), 0.22, "sine", 0.4, r=0.16)))
    save_wav("enemy_turn", seq(tone(hz("A", 3), 0.12, "saw", 0.3, r=0.04), tone(hz("E", 3), 0.22, "saw", 0.3, r=0.16)))
    save_wav("denied", seq(tone(190, 0.08, "square", 0.3), tone(150, 0.12, "square", 0.3, r=0.08)))
    fan = [("C", 5), ("E", 5), ("G", 5), ("C", 6)]
    save_wav("victory", mix(
        seq(*[tone(hz(n, o), 0.16, "square", 0.3, r=0.05) for n, o in fan], tone(hz("C", 6), 0.7, "square", 0.3, r=0.5, vib=0.01)),
        seq(*[tone(hz(n, o - 1), 0.16, "tri", 0.4, r=0.05) for n, o in fan], tone(hz("C", 5), 0.7, "tri", 0.4, r=0.5)),
        offsets=[0, 0]))
    save_wav("gameover", seq(*[tone(hz(n, o), 0.3, "saw", 0.28, r=0.2) for n, o in [("E", 4), ("D#", 4), ("D", 4)]],
                             tone(hz("C#", 4), 1.0, "saw", 0.3, hz("C", 4), r=0.8, vib=0.015)))
    save_wav("level_up", seq(tone(hz("D", 5), 0.1, "square", 0.28), tone(hz("A", 5), 0.1, "square", 0.28),
                             tone(hz("D", 6), 0.3, "square", 0.3, r=0.2)))


def make_music(name, bpm, chords, bass_oct, arp_kind, hat=True, kick=False, bars_rep=1, vol=0.5):
    beat = 60.0 / bpm
    bar = beat * 4
    total = bar * len(chords) * bars_rep
    n = int(SR * total)
    buf = [0.0] * n

    def add(samples, t0):
        s = int(t0 * SR)
        for i, v in enumerate(samples):
            if s + i < n:
                buf[s + i] += v

    for rep in range(bars_rep):
        for ci, (root, quality) in enumerate(chords):
            t0 = (rep * len(chords) + ci) * bar
            third = 3 if quality == "m" else 4
            notes = [0, third, 7, 12, 7, third, 7, third]
            # bajo: octavas
            for b in range(8):
                add(tone(hz(root, bass_oct) * (2 if b % 2 else 1), beat * 0.5, "tri", 0.5 * vol, r=0.1), t0 + b * beat * 0.5)
            # arpegio
            base = NOTE[root]
            for b in range(8):
                semis = notes[b]
                f = 440.0 * 2 ** ((base + semis - 9 + 12 * (bass_oct + 1 - 4)) / 12.0)
                add(tone(f, beat * 0.46, arp_kind, 0.2 * vol, r=0.14), t0 + b * beat * 0.5)
            # colchón
            for k, semis in enumerate([0, third, 7]):
                f = 440.0 * 2 ** ((base + semis - 9 + 12 * (bass_oct - 4)) / 12.0)
                add(tone(f, bar * 0.98, "sine", 0.1 * vol, a=0.25, r=0.4, vib=0.004, vib_f=4.5), t0)
            if hat:
                for b in range(8):
                    add(noise(0.04, 0.22 * vol, 0.9, r=0.03, seed=ci * 10 + b), t0 + b * beat * 0.5 + (beat * 0.25 if b % 2 else 0) * 0)
            if kick:
                for b in range(4):
                    add(tone(120, 0.12, "sine", 0.7 * vol, 40, r=0.09), t0 + b * beat)
                add(noise(0.1, 0.4 * vol, 0.5, r=0.08, seed=ci), t0 + beat)
                add(noise(0.1, 0.4 * vol, 0.5, r=0.08, seed=ci + 100), t0 + beat * 3)
    # fade-out suave y fade-in para que el loop no haga click
    fade = int(SR * 0.02)
    for i in range(fade):
        buf[i] *= i / fade
        buf[n - 1 - i] *= i / fade
    save_wav(name, buf)


def make_all_music():
    make_music("music_menu", 78, [("A", "m"), ("F", "M"), ("C", "M"), ("G", "M")], 2, "tri", hat=False, vol=0.9)
    make_music("music_combat", 112, [("A", "m"), ("A", "m"), ("F", "M"), ("G", "M"), ("A", "m"), ("E", "m"), ("F", "M"), ("E", "M")],
               2, "square", hat=True, kick=True, vol=0.8)


# =============================================================================
if __name__ == "__main__":
    print("Generando sprites...")
    for nm, sp in SPECS.items():
        make_sprite(nm, sp)
    make_potion()
    print("Generando tiles...")
    make_tiles()
    print("Generando fondo del menú...")
    make_menu_bg()
    print("Generando sonidos...")
    make_sfx()
    make_all_music()
    print("Listo.")
