"""HUD: barra superior, panel de acciones (combate), indicadores de vida y turno."""
import math

import pygame

from core.ui import THEME, Bar, Button, Panel, draw_text, get_font
from .constants import POTION_COST


class Hud:
    def __init__(self, scene):
        self.scene = scene
        audio = scene.game.audio
        W = scene.game.ANCHO
        self.top = Panel((0, 0, W, 46), alpha=205, radius=0)
        self.bottom = Panel((0, 598, W, 122), alpha=232, radius=0)
        self.card = Panel((W - 262, 56, 250, 118), alpha=225)
        self.log_panel_rect = pygame.Rect(12, 470, 430, 118)
        self.hp_bar = Bar((26, 650, 330, 20), THEME["good"])
        self.card_bar = Bar((W - 250, 100, 226, 14), THEME["bad"])
        s = scene
        bx, by, bw, bh, gap = 452, 620, 150, 76, 10
        self.btn_move = Button((bx, by, bw, bh), "Mover", lambda: s.ui_set_mode("move"), audio, "1", "1 PA / casilla")
        self.btn_melee = Button((bx + (bw + gap), by, bw, bh), "Atacar", lambda: s.ui_set_mode("melee"), audio, "2", "")
        self.btn_ranged = Button((bx + 2 * (bw + gap), by, bw, bh), "Disparar", lambda: s.ui_set_mode("ranged"), audio, "3", "")
        self.btn_potion = Button((bx + 3 * (bw + gap), by, bw, bh), "Poción", s.ui_use_potion, audio, "4", "")
        self.btn_end = Button((bx + 4 * (bw + gap), by, bw, bh), "Terminar turno", s.ui_end_turn, audio, "5", "ESPACIO",
                              font_size=19, primary=True)
        self.buttons = [self.btn_move, self.btn_melee, self.btn_ranged, self.btn_potion, self.btn_end]
        self.f_big = get_font(26, True)
        self.f_mid = get_font(20, True)
        self.f_small = get_font(16)
        self.f_tiny = get_font(14)
        self.t = 0

    # ----------------------------------------------------------------- input
    def handle_event(self, event):
        for b in self.buttons:
            if b.handle_event(event):
                return True
        return False

    def sync(self):
        s = self.scene
        p = s.player
        can = s.turn == "player" and s.script is None and p.alive and not s.pending_outcome
        melee, ranged = p.attacks["melee"], p.attacks["ranged"]
        self.btn_move.enabled = can and p.ap >= 1
        self.btn_melee.enabled = can and p.ap >= melee.cost
        self.btn_ranged.enabled = can and p.ap >= ranged.cost
        self.btn_potion.enabled = can and p.ap >= POTION_COST and p.potions > 0
        self.btn_end.enabled = can
        self.btn_melee.subtext = f"{melee.cost} PA · Daño {melee.damage}"
        self.btn_ranged.subtext = f"{ranged.cost} PA · Daño {ranged.damage}"
        self.btn_potion.subtext = f"{POTION_COST} PA · x{p.potions}"
        self.btn_move.selected = s.mode == "move" and can
        self.btn_melee.selected = s.mode == "melee" and can
        self.btn_ranged.selected = s.mode == "ranged" and can

    def update(self, dt):
        self.t += dt
        self.sync()
        p = self.scene.player
        self.hp_bar.set_value(p.hp / p.max_hp)
        self.hp_bar.update(dt)
        for b in self.buttons:
            b.update(dt)

    # ------------------------------------------------------------------ draw
    def draw(self, surface):
        s = self.scene
        W = surface.get_width()
        self._draw_top(surface, W)
        self._draw_log(surface)
        self._draw_hint(surface, W)
        self._draw_bottom(surface)
        self._draw_hover_card(surface)

    def _draw_top(self, surface, W):
        s = self.scene
        self.top.draw(surface)
        draw_text(surface, f"Nivel {s.level.index + 1}  ·  {s.level.name}", self.f_mid, THEME["text"], (18, 23), "midleft")
        # indicador de turno
        if s.turn == "player":
            label, col = "TU TURNO", THEME["good"]
        else:
            label, col = "TURNO ENEMIGO", THEME["bad"]
        pill = pygame.Rect(0, 0, 250, 32)
        pill.center = (W // 2, 23)
        pygame.draw.rect(surface, (20, 12, 20), pill, border_radius=16)
        pulse = 0.5 + 0.5 * math.sin(self.t / 220.0)
        pygame.draw.rect(surface, tuple(int(c * (0.7 + 0.3 * pulse)) for c in col), pill, 3, border_radius=16)
        draw_text(surface, f"{label}  ·  Ronda {s.round}", self.f_small, col, pill.center, "center")
        alive = sum(1 for e in s.enemies if e.alive)
        draw_text(surface, f"Enemigos: {alive}", self.f_mid, THEME["accent"], (W - 150, 23), "midright")
        mute = "Sonido: NO [M]" if s.game.audio.muted else "Sonido: SÍ [M]"
        draw_text(surface, mute, self.f_tiny, THEME["text_dim"], (W - 14, 23), "midright")

    def _draw_hint(self, surface, W):
        s = self.scene
        if s.turn != "player":
            msg = "Los enemigos están actuando..."
        elif s.script is not None:
            return
        elif s.mode == "move":
            msg = "Click en una casilla celeste para moverte (1 PA por casilla) · Click en un enemigo adyacente para atacarlo"
        elif s.mode == "melee":
            msg = "Click en un enemigo resaltado en rojo para golpearlo · Click derecho / ESC para cancelar"
        elif s.mode == "ranged":
            msg = "Click en un enemigo en rango y con línea de visión para dispararle · Click derecho para cancelar"
        else:
            return
        img = self.f_small.render(msg, True, THEME["text"])
        r = img.get_rect(midtop=(W // 2, 54))
        bg = pygame.Surface((r.width + 24, r.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(bg, (16, 10, 20, 150), bg.get_rect(), border_radius=10)
        surface.blit(bg, (r.x - 12, r.y - 4))
        surface.blit(img, r)

    def _draw_log(self, surface):
        s = self.scene
        lines = list(s.log)[-5:]
        if not lines:
            return
        r = self.log_panel_rect
        h = 14 + 22 * len(lines)
        bg = pygame.Surface((r.width, h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (16, 10, 20, 140), bg.get_rect(), border_radius=10)
        surface.blit(bg, (r.x, 592 - h))
        for i, (txt, col) in enumerate(lines):
            fade = 140 + int(115 * (i + 1) / len(lines))
            draw_text(surface, txt, self.f_small, col, (r.x + 12, 592 - h + 8 + i * 22), "topleft", alpha=min(255, fade))

    def _draw_bottom(self, surface):
        s = self.scene
        p = s.player
        self.bottom.draw(surface)
        draw_text(surface, "Superviviente", self.f_big, THEME["text"], (26, 612), "topleft")
        self.hp_bar.draw(surface)
        draw_text(surface, f"VIDA  {p.hp}/{p.max_hp}", self.f_small, (255, 255, 255), (self.hp_bar.rect.centerx, self.hp_bar.rect.centery), "center")
        # puntos de acción
        draw_text(surface, "PA", self.f_small, THEME["text_dim"], (26, 692), "midleft")
        for i in range(p.max_ap):
            c = (60 + i * 30, 692)
            filled = i < p.ap
            pygame.draw.circle(surface, (14, 8, 14), c, 12)
            pygame.draw.circle(surface, THEME["info"] if filled else (50, 44, 60), c, 9)
            if filled:
                pygame.draw.circle(surface, (200, 235, 255), (c[0] - 2, c[1] - 3), 3)
        mel, ran = p.attacks["melee"], p.attacks["ranged"]
        draw_text(surface, f"Cuerpo a cuerpo: {mel.damage} (alc. {mel.range})", self.f_tiny, THEME["text_dim"], (254, 683), "topleft")
        draw_text(surface, f"Pistola: {ran.damage} (alc. {ran.range})", self.f_tiny, THEME["text_dim"], (254, 700), "topleft")
        for b in self.buttons:
            b.draw(surface)

    def _draw_hover_card(self, surface):
        s = self.scene
        ent = s.entity_at(s.hover_tile) if s.hover_tile else None
        if not ent or not ent.alive or ent is s.player:
            return
        self.card.draw(surface)
        x = self.card.rect.x + 14
        draw_text(surface, ent.name, self.f_mid, THEME["accent"], (x, 64), "topleft")
        state = "En alerta" if getattr(ent, "alerted", False) else "Distraído"
        draw_text(surface, state, self.f_tiny, THEME["bad"] if state == "En alerta" else THEME["text_dim"],
                  (self.card.rect.right - 14, 70), "topright")
        self.card_bar.set_value(ent.hp / ent.max_hp)
        self.card_bar.ghost = self.card_bar.value
        self.card_bar.draw(surface)
        draw_text(surface, f"{ent.hp}/{ent.max_hp}", self.f_tiny, (255, 255, 255), self.card_bar.rect.center, "center")
        a = ent.attacks["main"]
        draw_text(surface, f"Daño {a.damage}   Alcance {a.range}", self.f_small, THEME["text"], (x, 126), "topleft")
        draw_text(surface, f"PA {ent.max_ap}   Ataque {a.cost} PA", self.f_small, THEME["text_dim"], (x, 148), "topleft")
