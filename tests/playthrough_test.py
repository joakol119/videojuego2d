"""Simula partidas completas con el bot (sin ventana) para detectar errores y calibrar el balance."""
import os, random, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from core.game import Game
from game.scenes.end_screens import GameOverScene, VictoryScene
from game.scenes.menu import MenuScene
from game.scenes.play import PlayScene
from bot import AutoPlayer


_G = None


def get_game():
    global _G
    if _G is None:
        _G = Game()
        _G.register("menu", MenuScene); _G.register("play", PlayScene)
        _G.register("gameover", GameOverScene); _G.register("victory", VictoryScene)
        for sc in _G.scenes.values():
            sc.draw = lambda surface: None      # sin render: mucho más rápido
    return _G


def run(seed, max_frames=60 * 60 * 6):
    g = get_game()
    g.change_scene("play", level_index=0, new_game=True)
    g.step(16, [])
    play = g.scenes["play"]
    play.rnd = random.Random(seed)
    bot = AutoPlayer()
    levels_won = 0
    last_level = 0
    for f in range(max_frames):
        g.step(16, [])
        if g.scene is play:
            last_level = play.level_index
            levels_won = max(levels_won, play.level_index)
            bot.act(play)
        else:
            return ("victoria" if g.scene is g.scenes["victory"] else "derrota"), last_level, play.stats["turns"], f
    return "timeout", last_level, play.stats["turns"], max_frames


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    res = [run(s) for s in range(n)]
    for r in res: print(r)
    wins = sum(1 for r in res if r[0] == "victoria")
    print(f"victorias {wins}/{n}")
    from collections import Counter
    print("derrotas por nivel:", Counter(r[1] + 1 for r in res if r[0] == "derrota"))
