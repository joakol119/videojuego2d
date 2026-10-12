"""Menú principal: botón "Comenzar Juego", cómo jugar y salir."""
import math
import random

import pygame

from core.game_object import GameObject
from core.paths import BASE_DIR
from core.scene import Scene
from core.ui import THEME, Button, Panel, draw_text, get_font
from ..tileset import TileSet


class MenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bg = pygame.image.load(str(BASE_DIR / "assets" / "ui" / "menu_bg.png")).convert()
        self.tileset = TileSet()
        self.f_title = get_font(78, True)
        self.f_sub = get_font(26)
        self.f_small = get_font(17)
        self.f_mid = get_font(21, True)
        audio = game.audio
        cx = 150
        self.buttons = [
            Button((cx - 130, 330, 300, 66), "Comenzar Juego", self.start_game, audio, primary=True, font_size=27),
            Button((cx - 130, 414, 300, 58), "Cómo jugar", self.toggle_help, audio, font_size=23),
            Button((cx - 130, 488, 300, 58), "Salir", self.quit, audio, font_size=23),
        ]
        self.help_open = False
        self.help_panel = Panel((330, 120, 620, 470), alpha=244, border=THEME["border"])
        self.help_close = Button((540, 520, 200, 52), "Entendido", self.toggle_help, audio, primary=True)
        # personajes del diorama (GameObject con spritesheet + JSON)
        self.actors = []
        for kind, col, row, flip in (("player", 0, 3, False), ("gunner", 2, 5, False),
                                     ("raider", 3, 3, True), ("warlord", 4, 1, True)):
            g = GameObject(0, 0, f"assets/sprites/{kind}.json")
            g.flip = flip
            g.col, g.row = col, row
            g.frame_timer = random.randint(0, 200)
            self.actors.append(g)
        self.dust = [[random.uniform(0, 1280), random.uniform(0, 720), random.uniform(10, 40), random.uniform(1, 3)] for _ in range(60)]
        self.t = 0

    def on_enter(self, **kwargs):
        self.game.audio.play_music("music_menu")
        self.help_open = False

    def start_game(self):
        self.game.audio.play("confirm")
        self.game.change_scene("play", level_index=0, new_game=True)

    def quit(self):
        self.game.running = False

    def toggle_help(self):
        self.help_open = not self.help_open

    def handle_event(self, event):
        if self.help_open:
            if self.help_close.handle_event(event):
                return
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.toggle_help()
            return
        for b in self.buttons:
            if b.handle_event(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.buttons[0].activate()
            elif event.key == pygame.K_ESCAPE:
                self.quit()

    def update(self, dt):
        self.t += dt
        for a in self.actors:
            a.update(dt, "idle")
        for d in self.dust:
            d[0] += d[2] * dt / 1000
            d[1] -= d[3] * dt / 1000 * 4
            if d[0] > 1290 or d[1] < -10:
                d[0], d[1] = -10, random.uniform(300, 720)
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        # polvo flotando
        for x, y, sp, size in self.dust:
            pygame.draw.circle(surface, (255, 214, 160), (int(x), int(y)), int(size))
        self._draw_diorama(surface)
        pulse = 0.5 + 0.5 * math.sin(self.t / 600.0)
        draw_text(surface, "CENIZAS", self.f_title, (255, 196, 96), (60, 120), "topleft")
        draw_text(surface, "DEL YERMO", self.f_title, (236, 120, 70), (60, 196), "topleft")
        draw_text(surface, "RPG isométrico por turnos", self.f_sub, THEME["text"], (66, 284), "topleft")
        for b in self.buttons:
            b.draw(surface)
        draw_text(surface, "Proyecto de Videojuegos 2D · Python + Pygame", self.f_small, THEME["text_dim"],
                  (20, 696), "bottomleft")
        draw_text(surface, "[M] sonido   [F11] pantalla completa", self.f_small, THEME["text_dim"], (1260, 696), "bottomright")
        if self.help_open:
            self._draw_help(surface)

    def _draw_diorama(self, surface):
        ox, oy = 880, 430
        order = []
        for r in range(6):
            for c in range(6):
                x = (c - r) * 32 + ox
                y = (c + r) * 16 + oy
                self.tileset.draw_floor(surface, "concrete" if (c + r) % 3 == 0 else f"sand_{(c * 3 + r) % 4}", x, y)
        for a in self.actors:
            a.x = (a.col - a.row) * 32 + ox
            a.y = (a.col + a.row) * 16 + oy + 4 + math.sin(self.t / 800 + a.col) * 0
            order.append((a.col + a.row, a))
        for _, a in sorted(order, key=lambda o: o[0]):
            shadow = pygame.Surface((50, 22), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
            surface.blit(shadow, (a.x - 25, a.y - 9))
            a.draw(surface)

    def _draw_help(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((6, 4, 12, 170))
        surface.blit(veil, (0, 0))
        self.help_panel.draw(surface)
        draw_text(surface, "CÓMO JUGAR", get_font(36, True), THEME["accent"], (640, 160), "center")
        lines = [
            ("Objetivo", "Derrotá a todos los enemigos de cada nivel (3 niveles)."),
            ("Turnos", "Tenés 6 PA por turno. Cuando se acaban, juegan los enemigos."),
            ("Mover", "[1] y click en una casilla celeste. Cuesta 1 PA por casilla."),
            ("Atacar", "[2] cuerpo a cuerpo (2 PA). Click en un enemigo adyacente."),
            ("Disparar", "[3] pistola (3 PA), alcance 5 y necesita línea de visión."),
            ("Poción", "[4] cura 28 de vida (1 PA). Las encontrás en el mapa."),
            ("Terminar", "[ESPACIO] termina tu turno. [ESC] pausa. Click derecho cancela."),
        ]
        y = 212
        for k, v in lines:
            draw_text(surface, k, self.f_mid, THEME["accent"], (362, y), "topleft")
            draw_text(surface, v, self.f_small, THEME["text"], (472, y + 3), "topleft")
            y += 44
        self.help_close.draw(surface)
