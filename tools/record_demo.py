#!/usr/bin/env python3
"""
Graba un video de demostración (15–40 s) jugando con el bot, sin necesidad de ventana.

    python tools/record_demo.py            # genera demo/gameplay_demo.mp4 (requiere ffmpeg)
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import pygame  # noqa: E402

from bot import AutoPlayer  # noqa: E402
from core.game import Game  # noqa: E402
from game.scenes.end_screens import GameOverScene, VictoryScene  # noqa: E402
from game.scenes.menu import MenuScene  # noqa: E402
from game.scenes.play import PlayScene  # noqa: E402

SECONDS = 32
FPS = 30
SPEEDUP = 2.2       # el combate se acelera un poco para entrar en 32 s


def main():
    out_dir = os.path.join(ROOT, "demo")
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="demo_frames_")
    g = Game()
    g.register("menu", MenuScene)
    g.register("play", PlayScene)
    g.register("gameover", GameOverScene)
    g.register("victory", VictoryScene)
    g.change_scene("menu")
    play = g.scenes["play"]
    play.rnd = random.Random(11)
    bot = AutoPlayer()
    frame = 0
    total = SECONDS * FPS

    def snap():
        nonlocal frame
        pygame.image.save(g.screen, os.path.join(tmp, f"f{frame:05d}.png"))
        frame += 1

    # --- menú: 2 s, luego el mouse va al botón "Comenzar Juego" y hace click
    btn = g.scenes["menu"].buttons[0].rect
    for i in range(int(2.0 * FPS)):
        ev = []
        if i == int(1.2 * FPS):
            ev.append(pygame.event.Event(pygame.MOUSEMOTION, pos=btn.center, rel=(0, 0), buttons=(0, 0, 0)))
        if i == int(1.7 * FPS):
            ev.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=btn.center, button=1))
            ev.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=btn.center, button=1))
        g.step(1000 / FPS, ev)
        snap()
    # --- juego
    sub = 1000.0 / FPS * SPEEDUP / 2        # dos pasos de simulación por cuadro grabado
    while frame < total:
        for _ in range(2):
            g.step(sub, [])
            if g.scene is play:
                bot.act(play)
        snap()
        if g.scene is not play:
            break
    audio = os.path.join(ROOT, "assets", "sounds", "music_combat.wav")
    out = os.path.join(out_dir, "gameplay_demo.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%05d.png"),
           "-stream_loop", "-1", "-i", audio, "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-af", "volume=0.6,afade=t=out:st=%d:d=2" % (frame // FPS - 2), out]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Video listo: {out} ({frame / FPS:.1f} s)")


if __name__ == "__main__":
    main()
