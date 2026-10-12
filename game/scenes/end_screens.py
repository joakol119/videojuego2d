"""Pantallas de Game Over y Victoria (ambas con camino de vuelta al menú)."""
import math

import pygame

from core.paths import BASE_DIR
from core.scene import Scene
from core.ui import THEME, Button, Panel, draw_text, get_font


class EndScreen(Scene):
    TITLE = ""
    SUBTITLE = ""
    COLOR = (255, 255, 255)
    TINT = (0, 0, 0, 120)
    MUSIC_SFX = ""

    def __init__(self, game):
        super().__init__(game)
        self.bg = pygame.image.load(str(BASE_DIR / "assets" / "ui" / "menu_bg.png")).convert()
        self.f_title = get_font(88, True)
        self.f_sub = get_font(28)
        self.f_stat = get_font(24)
        self.f_statb = get_font(24, True)
        self.panel = Panel((390, 330, 500, 170), alpha=225)
        self.buttons = []
        self.t = 0
        self.level_index = 0

    def on_enter(self, **kwargs):
        self.t = 0
        self.level_index = kwargs.get("level_index", 0)
        self.game.audio.stop_music(300)
        self.game.audio.current_music = None
        self.game.audio.play(self.MUSIC_SFX)
        self.build_buttons()

    def build_buttons(self):
        raise NotImplementedError

    def go_menu(self):
        self.game.change_scene("menu")

    def handle_event(self, event):
        for b in self.buttons:
            if b.handle_event(event):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.buttons[-1].activate()

    def update(self, dt):
        self.t += dt
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        tint = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        tint.fill(self.TINT)
        surface.blit(tint, (0, 0))
        k = min(1.0, self.t / 600.0)
        wob = math.sin(self.t / 500.0) * 4
        draw_text(surface, self.TITLE, self.f_title, self.COLOR, (640, 150 + wob), "center", alpha=int(255 * k))
        draw_text(surface, self.SUBTITLE, self.f_sub, THEME["text"], (640, 232), "center", alpha=int(255 * k))
        stats = self.game.shared.get("stats", {})
        self.panel.draw(surface)
        rows = [("Turnos jugados", stats.get("turns", 0)), ("Enemigos derrotados", stats.get("kills", 0)),
                ("Daño infligido", stats.get("damage_dealt", 0)), ("Daño recibido", stats.get("damage_taken", 0)),
                ("Pociones usadas", stats.get("potions_used", 0))]
        y = 342
        for label, val in rows:
            draw_text(surface, label, self.f_stat, THEME["text_dim"], (430, y), "topleft")
            draw_text(surface, str(val), self.f_statb, THEME["accent"], (850, y), "topright")
            y += 30
        for b in self.buttons:
            b.draw(surface)


class GameOverScene(EndScreen):
    TITLE = "HAS CAÍDO"
    SUBTITLE = "El yermo no perdona... pero siempre hay otra oportunidad."
    COLOR = (232, 84, 76)
    TINT = (60, 0, 0, 150)
    MUSIC_SFX = "gameover"

    def build_buttons(self):
        a = self.game.audio
        self.buttons = [
            Button((390, 540, 240, 64), "Reintentar nivel", self.retry, a, primary=True, font_size=23),
            Button((650, 540, 240, 64), "Volver al menú", self.go_menu, a, font_size=23),
        ]

    def retry(self):
        self.game.change_scene("play", level_index=self.level_index, new_game=False, retry=True)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.buttons[0].activate()


class VictoryScene(EndScreen):
    TITLE = "¡VICTORIA!"
    SUBTITLE = "Liberaste el yermo del Caudillo y su banda."
    COLOR = (255, 208, 90)
    TINT = (50, 30, 0, 90)
    MUSIC_SFX = "victory"

    def build_buttons(self):
        a = self.game.audio
        self.buttons = [
            Button((390, 540, 240, 64), "Jugar de nuevo", self.again, a, font_size=23),
            Button((650, 540, 240, 64), "Volver al menú", self.go_menu, a, primary=True, font_size=23),
        ]

    def again(self):
        self.game.change_scene("play", level_index=0, new_game=True)
