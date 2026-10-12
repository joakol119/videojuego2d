"""Prueba de humo sin ventana: recorre las escenas y toma capturas."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from core.game import Game
from game.scenes.end_screens import GameOverScene, VictoryScene
from game.scenes.menu import MenuScene
from game.scenes.play import PlayScene

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
g = Game()
g.register("menu", MenuScene); g.register("play", PlayScene)
g.register("gameover", GameOverScene); g.register("victory", VictoryScene)
g.change_scene("menu")
for _ in range(30): g.step(16, [])
pygame.image.save(g.screen, f"{OUT}/shot_menu.png")
g.change_scene("play", level_index=0, new_game=True)
for _ in range(200): g.step(16, [])
pygame.image.save(g.screen, f"{OUT}/shot_play.png")
print("ok")
