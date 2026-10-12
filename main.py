#!/usr/bin/env python3
"""Cenizas del Yermo — RPG isométrico por turnos (Pygame). Ejecutar: python main.py"""
import sys

from core.game import Game
from game.scenes.end_screens import GameOverScene, VictoryScene
from game.scenes.menu import MenuScene
from game.scenes.play import PlayScene


def main():
    game = Game()
    game.register("menu", MenuScene)
    game.register("play", PlayScene)
    game.register("gameover", GameOverScene)
    game.register("victory", VictoryScene)
    game.run("menu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
