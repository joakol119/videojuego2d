"""Flujo con eventos reales de mouse/teclado: menú -> juego -> Game Over -> menú, y Victoria -> menú."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from core.game import Game
from game.scenes.end_screens import GameOverScene, VictoryScene
from game.scenes.menu import MenuScene
from game.scenes.play import PlayScene

g = Game()
g.register("menu", MenuScene); g.register("play", PlayScene)
g.register("gameover", GameOverScene); g.register("victory", VictoryScene)
g.change_scene("menu")


def click(pos):
    g.step(16, [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))])
    g.step(16, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)])
    g.step(16, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)])
    g.step(16, [])


def name():
    return [k for k, v in g.scenes.items() if v is g.scene][0]


g.step(16, [])
assert name() == "menu"
click(g.scenes["menu"].buttons[0].rect.center)          # Comenzar Juego
assert name() == "play", name()
play = g.scenes["play"]
for _ in range(200): g.step(16, [])
# mover con el mouse: click en una casilla alcanzable
play.ui_set_mode("move")
tile = [t for t in play.reach if t != play.player.pos and play.reach[t][0] == 2][0]
ap0 = play.player.ap
click(play.proj.to_screen(*tile))
for _ in range(200): g.step(16, [])
assert play.player.pos == tile and play.player.ap == ap0 - 2, (play.player.pos, tile, play.player.ap)
# terminar turno con Espacio y dejar jugar a los enemigos
g.step(16, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" ", scancode=0)])
for _ in range(900): g.step(16, [])
assert play.turn == "player" and play.round >= 2
# Game Over
play.player.take_hit(999); play.check_outcome()
for _ in range(400): g.step(16, [])
assert name() == "gameover", name()
click(g.scene.buttons[1].rect.center)                    # Volver al menú
assert name() == "menu"
# Victoria
g.change_scene("victory")
for _ in range(10): g.step(16, [])
assert name() == "victory"
click(g.scene.buttons[1].rect.center)                    # Volver al menú
assert name() == "menu"
print("flujo OK")
