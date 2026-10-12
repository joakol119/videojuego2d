"""Tests de la lógica pura (sin ventana). Ejecutar: python -m unittest discover -s tests -v"""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.iso import IsoProjection  # noqa: E402
from game.levels import level_count, parse_level  # noqa: E402
from game.pathfinding import build_path, line_of_sight, manhattan, reachable  # noqa: E402


class IsoTests(unittest.TestCase):
    def test_roundtrip(self):
        proj = IsoProjection(640, 100)
        for c in range(-2, 12):
            for r in range(-2, 12):
                x, y = proj.to_screen(c, r)
                self.assertEqual(proj.tile_at(x, y), (c, r))
                gc, gr = proj.to_grid(x, y)
                self.assertAlmostEqual(gc, c)
                self.assertAlmostEqual(gr, r)

    def test_formula(self):
        proj = IsoProjection(0, 0)
        self.assertEqual(proj.to_screen(1, 0), (32, 16))
        self.assertEqual(proj.to_screen(0, 1), (-32, 16))
        self.assertEqual(proj.to_screen(2, 2), (0, 64))


class PathTests(unittest.TestCase):
    def test_reachable_and_path(self):
        wall = {(1, 0), (1, 1)}
        blocked = lambda c, r: (c, r) in wall or not (0 <= c < 4 and 0 <= r < 4)  # noqa: E731
        reach = reachable(blocked, (0, 0), 20)
        self.assertNotIn((1, 0), reach)
        path = build_path(reach, (2, 0))
        self.assertEqual(path[-1], (2, 0))
        self.assertEqual(len(path), reach[(2, 0)][0])
        for a, b in zip([(0, 0)] + path, path):
            self.assertEqual(manhattan(a, b), 1)

    def test_max_cost(self):
        reach = reachable(lambda c, r: False, (0, 0), 2)
        self.assertTrue(all(cost <= 2 for cost, _ in reach.values()))

    def test_los(self):
        solid = {(2, 0)}
        self.assertFalse(line_of_sight(lambda c, r: (c, r) in solid, (0, 0), (4, 0)))
        self.assertTrue(line_of_sight(lambda c, r: (c, r) in solid, (0, 1), (4, 1)))


class LevelTests(unittest.TestCase):
    def test_levels_are_valid_and_connected(self):
        for i in range(level_count()):
            lv = parse_level(i)
            reach = reachable(lv.is_solid, lv.player_start, 999)
            targets = [(c, r) for _, c, r in lv.enemies] + lv.potions
            self.assertTrue(lv.enemies)
            for t in targets:
                self.assertIn(t, reach, f"nivel {i + 1}: {t} inaccesible")

    def test_border_is_solid(self):
        lv = parse_level(0)
        self.assertTrue(lv.is_solid(-1, 0))
        self.assertTrue(lv.is_solid(0, 0))


if __name__ == "__main__":
    unittest.main()
