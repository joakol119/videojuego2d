"""
PlayScene: el juego en sí. RPG isométrico por turnos con puntos de acción (PA).

Flujo de un turno:
  * Turno del jugador: tiene `max_ap` PA y los gasta en Mover (1 PA/casilla),
    Atacar cuerpo a cuerpo, Disparar a distancia o Usar una poción.
  * Turno enemigo: cada enemigo en alerta usa sus PA para acercarse y atacar.

La secuencia de acciones (caminar, atacar, esperar animaciones) se escribe con
generadores de Python: cada `yield` pausa el "guion" hasta que pasó el tiempo
(o hasta que se cumple una condición) y el bucle de UPDATE lo retoma.
"""
import random
from collections import deque

import pygame

from core.paths import BASE_DIR
from core.scene import Scene
from core.ui import THEME, Button, Panel, draw_text, get_font
from ..constants import (CRIT_CHANCE, CRIT_MULT, DAMAGE_VARIANCE, MOVE_COST, PLAY_AREA_BOTTOM,
                         PLAY_AREA_TOP, POTION_COST, POTION_HEAL)
from ..effects import FxManager
from ..entities import Collectible, Enemy, Player
from ..hud import Hud
from ..iso import IsoProjection
from ..levels import level_count, parse_level
from ..pathfinding import build_path, line_of_sight, manhattan, reachable
from ..tileset import TileSet

COL_LOG_PLAYER = (150, 214, 255)
COL_LOG_ENEMY = (255, 150, 130)
COL_LOG_INFO = (232, 220, 190)
COL_LOG_GOOD = (140, 230, 150)


class PlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.audio = game.audio
        self.tileset = TileSet()
        self.fx = FxManager()
        self.rnd = random.Random()
        bg = pygame.image.load(str(BASE_DIR / "assets" / "ui" / "menu_bg.png")).convert()
        dark = pygame.Surface(bg.get_size(), pygame.SRCALPHA)
        dark.fill((10, 6, 18, 150))
        bg.blit(dark, (0, 0))
        self.bg = bg
        self.overlay = pygame.Surface((game.ANCHO, game.ALTO), pygame.SRCALPHA)
        self.f_banner = get_font(54, True)
        self.f_sub = get_font(24)
        self.f_hp = get_font(13, True)

        self.level = None
        self.player = None
        self.enemies = []
        self.pickups = []
        self.stats = {}
        self.checkpoint = None
        self.level_index = 0
        self.log = deque(maxlen=8)
        self.script = None
        self._wait_ms = 0
        self._wait_fn = None
        self.pending_outcome = None
        self.ending = False
        self.mode = "move"
        self.turn = "player"
        self.round = 1
        self.reach = {}
        self.targets = []
        self.hover_tile = None
        self.active_enemy = None
        self.shake = 0.0
        self.banner = None
        self.turn_banner = 0
        self.fade = 255
        self.fade_target = 0
        self.paused = False
        self.t = 0
        self.hud = None

        self.pause_panel = Panel((440, 190, 400, 330), alpha=240)
        self.pause_buttons = [
            Button((480, 270, 320, 60), "Continuar", self.toggle_pause, self.audio, primary=True),
            Button((480, 346, 320, 60), "Reiniciar nivel", self._restart_level, self.audio),
            Button((480, 422, 320, 60), "Volver al menú", self._to_menu, self.audio),
        ]

    # ================================================================= ciclo
    def on_enter(self, level_index=0, new_game=True, retry=False):
        if self.hud is None:
            self.hud = Hud(self)
        if new_game:
            self.stats = dict(turns=0, kills=0, damage_dealt=0, damage_taken=0, potions_used=0)
            self.checkpoint = None
            self.game.shared["stats"] = self.stats
        self.audio.play_music("music_combat")
        self.paused = False
        self.load_level(level_index)

    def on_exit(self):
        self.script = None

    def load_level(self, index):
        self.level_index = index
        self.level = parse_level(index)
        area = pygame.Rect(0, PLAY_AREA_TOP, self.game.ANCHO, PLAY_AREA_BOTTOM - PLAY_AREA_TOP)
        self.proj = IsoProjection()
        self.proj.center_map(self.level.cols, self.level.rows, area)
        self.player = Player(*self.level.player_start, self.proj)
        if self.checkpoint:
            self.player.hp = self.checkpoint["hp"]
            self.player.potions = self.checkpoint["potions"]
        else:
            self.checkpoint = dict(hp=self.player.hp, potions=self.player.potions)
        self.enemies = [Enemy(k, c, r, self.proj) for k, c, r in self.level.enemies]
        self.pickups = [Collectible(c, r, self.proj) for c, r in self.level.potions]
        self.fx = FxManager()
        self.log.clear()
        self.script = None
        self._wait_ms = 0
        self._wait_fn = None
        self.pending_outcome = None
        self.ending = False
        self.active_enemy = None
        self.round = 0
        self.shake = 0
        self.hover_tile = None
        self.banner = dict(title=f"Nivel {index + 1}: {self.level.name}", sub=self.level.hint, t=0)
        self.fade = 255
        self.fade_target = 0
        self.log_msg("Derrotá a todos los enemigos para avanzar.", COL_LOG_INFO)
        self.start_player_turn()

    # ============================================================== utilidades
    def log_msg(self, text, color=COL_LOG_INFO):
        self.log.append((text, color))

    def living_enemies(self):
        return [e for e in self.enemies if e.alive]

    def entity_at(self, tile):
        if tile is None:
            return None
        if self.player.alive and self.player.pos == tile:
            return self.player
        for e in self.enemies:
            if e.alive and e.pos == tile:
                return e
        return None

    def blocked(self, c, r, ignore=None):
        """Colisión: muros/props de la matriz del mapa + entidades vivas."""
        if self.level.is_solid(c, r):
            return True
        ent = self.entity_at((c, r))
        return ent is not None and ent is not ignore

    def los(self, a, b):
        return line_of_sight(self.level.is_solid, a, b)

    def check_outcome(self):
        if not self.player.alive:
            self.pending_outcome = "lose"
        elif not self.living_enemies():
            self.pending_outcome = "win"

    # ====================================================== turnos y modos (UI)
    def start_player_turn(self):
        self.turn = "player"
        self.round += 1
        self.stats["turns"] += 1
        self.player.ap = self.player.max_ap
        self.active_enemy = None
        self.turn_banner = 1000
        self.audio.play("turn")
        self.set_mode("move")

    def set_mode(self, mode):
        self.mode = mode
        p = self.player
        self.reach, self.targets = {}, []
        if self.turn != "player" or not p.alive:
            return
        if mode == "move":
            self.reach = reachable(lambda c, r: self.blocked(c, r, ignore=p), p.pos, p.ap // MOVE_COST)
        elif mode in ("melee", "ranged"):
            atk = p.attacks[mode]
            for e in self.living_enemies():
                d = manhattan(p.pos, e.pos)
                if d <= atk.range and (atk.range == 1 or self.los(p.pos, e.pos)):
                    self.targets.append(e)

    def _can_act(self):
        return (self.turn == "player" and self.script is None and self.player.alive
                and not self.pending_outcome and not self.paused and self.fade < 200)

    def ui_set_mode(self, mode):
        if not self._can_act():
            return
        p = self.player
        if mode != "move" and p.ap < p.attacks[mode].cost:
            self.audio.play("denied")
            self.log_msg("No te alcanzan los PA para esa acción.", COL_LOG_INFO)
            return
        self.set_mode(mode)
        if mode != "move" and not self.targets:
            self.log_msg("No hay enemigos a tu alcance.", COL_LOG_INFO)

    def ui_use_potion(self):
        if not self._can_act():
            return
        p = self.player
        if p.hp >= p.max_hp:
            self.audio.play("denied")
            self.log_msg("Ya tenés la vida completa.", COL_LOG_INFO)
            return
        self.script = self._player_action(self._script_potion())

    def ui_end_turn(self):
        if not self._can_act():
            return
        self.script = self._player_action(self._noop(), force_end=True)

    def toggle_pause(self):
        if self.pending_outcome or self.ending:
            return
        self.paused = not self.paused
        self.audio.play("back" if not self.paused else "click")

    def _restart_level(self):
        self.paused = False
        self.checkpoint_apply_and_reload()

    def checkpoint_apply_and_reload(self):
        self.load_level(self.level_index)

    def _to_menu(self):
        self.paused = False
        self.game.change_scene("menu")

    # ================================================================== input
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.paused or self.mode == "move":
                    self.toggle_pause()
                else:
                    self.set_mode("move") if self._can_act() else None
                return
        if self.paused:
            for b in self.pause_buttons:
                if b.handle_event(event):
                    return
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover_tile = self.proj.tile_at(*event.pos) if event.pos[1] < 596 else None
            if self.hover_tile and not self.level.in_bounds(*self.hover_tile):
                self.hover_tile = None
        if self.hud.handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            keymap = {pygame.K_1: self.hud.btn_move, pygame.K_2: self.hud.btn_melee,
                      pygame.K_3: self.hud.btn_ranged, pygame.K_4: self.hud.btn_potion,
                      pygame.K_5: self.hud.btn_end, pygame.K_SPACE: self.hud.btn_end,
                      pygame.K_RETURN: self.hud.btn_end}
            btn = keymap.get(event.key)
            if btn:
                btn.activate()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and event.pos[1] < 596:
                self.click_tile(self.proj.tile_at(*event.pos))
            elif event.button == 3 and self._can_act():
                self.set_mode("move")

    def click_tile(self, tile):
        """Acción del jugador sobre una casilla (separado del mouse para poder testearlo)."""
        if not self._can_act() or not self.level.in_bounds(*tile):
            return
        p = self.player
        ent = self.entity_at(tile)
        if self.mode == "move":
            if ent and ent is not p:      # atajo: click en enemigo adyacente = ataque cuerpo a cuerpo
                if manhattan(p.pos, ent.pos) == 1 and p.ap >= p.attacks["melee"].cost:
                    self.script = self._player_action(self._script_attack(p, ent, p.attacks["melee"]))
                else:
                    self.audio.play("denied")
                return
            if tile in self.reach and tile != p.pos:
                path = build_path(self.reach, tile)
                self.script = self._player_action(self._script_walk(p, path))
            else:
                self.audio.play("denied")
        elif self.mode in ("melee", "ranged"):
            if ent in self.targets:
                atk = p.attacks[self.mode]
                self.script = self._player_action(self._script_attack(p, ent, atk))
            else:
                self.audio.play("denied")

    # ================================================================ scripts
    def _noop(self):
        return
        yield

    def _player_action(self, gen, force_end=False):
        yield from gen
        if self.pending_outcome:
            return
        self.set_mode("move")
        if force_end or self.player.ap <= 0:
            if not force_end:
                yield 350
            yield from self._script_enemy_turn()

    def _script_walk(self, ent, path):
        for c, r in path:
            if self.pending_outcome:
                return
            ent.ap -= MOVE_COST
            sx, sy = self.proj.to_screen(ent.fcol, ent.frow)
            ent.step_to(c, r)
            self.audio.play("step", 0.45)
            self.fx.dust(sx, sy)
            yield lambda e=ent: not e.moving
            if ent is self.player:
                self._try_pickup()

    def _try_pickup(self):
        for p in self.pickups:
            if not p.collected and (p.col, p.row) == self.player.pos:
                p.collected = True
                self.player.potions += 1
                self.audio.play("pickup")
                self.fx.sparkle(p.x, p.y - 16)
                self.fx.text(p.x, p.y - 40, "+1 Poción", COL_LOG_GOOD, 22)
                self.log_msg("Encontraste una poción.", COL_LOG_GOOD)

    def _script_potion(self):
        p = self.player
        p.ap -= POTION_COST
        p.potions -= 1
        gained = p.heal(POTION_HEAL)
        self.stats["potions_used"] += 1
        self.audio.play("potion")
        self.fx.sparkle(p.x, p.y - 30)
        self.fx.text(p.x, p.y - 90, f"+{gained} VIDA", COL_LOG_GOOD, 28)
        self.log_msg(f"Usaste una poción: +{gained} de vida.", COL_LOG_GOOD)
        yield 550

    def _roll(self, atk, dist):
        miss = 0.05 if atk.kind == "melee" else 0.06 + 0.04 * (dist - 1)
        if self.rnd.random() < miss:
            return None
        dmg = round(atk.damage * self.rnd.uniform(1 - DAMAGE_VARIANCE, 1 + DAMAGE_VARIANCE))
        crit = self.rnd.random() < CRIT_CHANCE
        if crit:
            dmg = round(dmg * CRIT_MULT)
        return max(1, dmg), crit

    def _script_attack(self, att, tgt, atk):
        is_player = att is self.player
        att.ap -= atk.cost
        att.play_attack(tgt.col, tgt.row)
        col = COL_LOG_PLAYER if is_player else COL_LOG_ENEMY
        self.audio.play("shoot" if atk.kind == "ranged" else "slash")
        if atk.kind == "ranged":
            yield 150
            muzzle = (att.x + (-22 if att.flip else 22), att.y - 50)
            self.fx.projectile(muzzle, (tgt.x, tgt.y - 46))
            yield lambda: not self.fx.projectiles_active()
        else:
            yield 170
        res = self._roll(atk, manhattan(att.pos, tgt.pos))
        cx, cy = tgt.x, tgt.y - 44
        if res is None:
            self.audio.play("miss")
            self.fx.text(cx, cy - 30, "Falló", (210, 210, 220), 24)
            self.log_msg(f"{att.name} falla contra {tgt.name}.", col)
        else:
            dmg, crit = res
            tgt.take_hit(dmg)
            self.audio.play("crit" if crit else "hit")
            self.fx.burst(cx, cy, (255, 90, 70) if tgt is self.player else (255, 180, 80), n=16 if crit else 10)
            self.fx.text(cx, cy - 30, f"¡-{dmg}!" if crit else f"-{dmg}",
                         (255, 220, 70) if crit else (255, 110, 100), 34 if crit else 26)
            self.shake = 10 if crit else 5
            if is_player:
                self.stats["damage_dealt"] += dmg
            else:
                self.stats["damage_taken"] += dmg
            self.log_msg(f"{att.name} golpea a {tgt.name}: {dmg} de daño{' (¡crítico!)' if crit else ''}.", col)
            if isinstance(tgt, Enemy):
                tgt.alerted = True
            if not tgt.alive:
                self.audio.play("death")
                self.fx.burst(tgt.x, tgt.y - 30, (230, 230, 230), n=18, speed=200)
                self.log_msg(f"{tgt.name} cayó.", col)
                if is_player:
                    self.stats["kills"] += 1
                self.check_outcome()
        yield 380
        if not tgt.alive:
            yield 350

    # ----------------------------------------------------------- turno enemigo
    def _script_enemy_turn(self):
        self.turn = "enemy"
        self.mode = "move"
        self.reach, self.targets = {}, []
        self.audio.play("enemy_turn")
        self.turn_banner = 900
        yield 800
        for e in list(self.enemies):
            if not e.alive or self.pending_outcome:
                continue
            e.ap = e.max_ap
            if not e.alerted:
                if manhattan(e.pos, self.player.pos) <= e.aggro:
                    e.alerted = True
                    self.fx.text(e.x, e.y - 110, "!", (255, 90, 80), 40)
                    self.log_msg(f"¡{e.name} te vio!", COL_LOG_ENEMY)
                    yield 450
                else:
                    continue
            self.active_enemy = e
            yield 250
            guard = 0
            while e.alive and self.player.alive and guard < 24 and not self.pending_outcome:
                guard += 1
                decision = self._enemy_decide(e)
                if decision is None:
                    break
                kind, data = decision
                if kind == "attack":
                    yield from self._script_attack(e, self.player, e.attack)
                else:
                    yield from self._script_walk(e, data)
                    yield 60
            self.active_enemy = None
            yield 160
        self.active_enemy = None
        if not self.pending_outcome:
            self.start_player_turn()

    def _enemy_decide(self, e):
        p = self.player
        atk = e.attack
        d = manhattan(e.pos, p.pos)

        def can_hit_from(tile):
            return manhattan(tile, p.pos) <= atk.range and (atk.range == 1 or self.los(tile, p.pos))

        if e.ap >= atk.cost and can_hit_from(e.pos):
            return ("attack", None)
        if e.ap < MOVE_COST:
            return None
        blocked = lambda c, r: self.blocked(c, r, ignore=e)  # noqa: E731
        near = reachable(blocked, e.pos, e.ap // MOVE_COST)
        best = None
        for tile, (cost, _) in near.items():
            if tile == e.pos or not can_hit_from(tile):
                continue
            if e.ap - cost * MOVE_COST >= atk.cost:
                key = (cost, -manhattan(tile, p.pos))
                if best is None or key < best[0]:
                    best = (key, tile)
        if best:
            return ("move", build_path(near, best[1]))
        # no llega a atacar este turno: se acerca por el camino más corto a una casilla de ataque
        far = reachable(blocked, e.pos, 60)
        goal = None
        for tile, (cost, _) in far.items():
            if can_hit_from(tile):
                if goal is None or cost < goal[0]:
                    goal = (cost, tile)
        if goal is None:
            # sin camino (bloqueado por otros): acercarse en línea recta lo que se pueda
            cand = min(near.items(), key=lambda kv: manhattan(kv[0], p.pos))[0]
            return ("move", build_path(near, cand)) if cand != e.pos else None
        path = build_path(far, goal[1])
        path = path[: e.ap // MOVE_COST]
        return ("move", path) if path else None

    # ------------------------------------------------------------- fin de nivel
    def _script_outcome(self):
        self.ending = True
        self.reach, self.targets = {}, []
        if self.pending_outcome == "lose":
            yield 1300
            self.fade_target = 255
            yield lambda: self.fade >= 255
            self.game.shared["stats"] = self.stats
            self.game.change_scene("gameover", level_index=self.level_index)
            return
        # victoria del nivel
        yield 700
        last = self.level_index >= level_count() - 1
        self.audio.play("victory" if last else "level_up")
        self.banner = dict(title="¡Nivel completado!" if not last else "¡Yermo liberado!",
                           sub="", t=0, short=True)
        yield 1700
        self.fade_target = 255
        yield lambda: self.fade >= 255
        if last:
            self.game.shared["stats"] = self.stats
            self.game.change_scene("victory")
            return
        p = self.player
        heal = int(p.max_hp * 0.5)
        self.checkpoint = dict(hp=min(p.max_hp, p.hp + heal), potions=p.potions + 1)
        self.load_level(self.level_index + 1)
        self.log_msg("Descansaste un poco: recuperaste vida y hallaste una poción.", COL_LOG_GOOD)

    # ================================================================== update
    def _drive_script(self, dt):
        if self.script is None:
            return
        if self._wait_ms > 0:
            self._wait_ms -= dt
            return
        if self._wait_fn is not None:
            if not self._wait_fn():
                return
            self._wait_fn = None
        for _ in range(30):
            try:
                y = next(self.script)
            except StopIteration:
                self.script = None
                return
            if callable(y):
                self._wait_fn = y
                return
            if y and y > 0:
                self._wait_ms = y
                return

    def update(self, dt):
        self.t += dt
        if self.paused:
            for b in self.pause_buttons:
                b.update(dt)
            return
        # fundido
        step = dt * 0.45
        if self.fade < self.fade_target:
            self.fade = min(self.fade_target, self.fade + step)
        elif self.fade > self.fade_target:
            self.fade = max(self.fade_target, self.fade - step)
        if self.banner:
            self.banner["t"] += dt
            if self.banner["t"] > (2300 if not self.banner.get("short") else 2000):
                self.banner = None
        self.turn_banner = max(0, self.turn_banner - dt)

        self.player.update(dt)
        for e in self.enemies:
            e.update(dt)
        self.enemies = [e for e in self.enemies if not e.gone]
        for p in self.pickups:
            p.update(dt)
        self.pickups = [p for p in self.pickups if not p.collected]
        self.fx.update(dt)
        self.shake = max(0.0, self.shake - dt * 0.03)

        if self.script is None and self.pending_outcome and not self.ending:
            self.script = self._script_outcome()
        self._drive_script(dt)
        if self.hud:
            self.hud.update(dt)

    # =================================================================== draw
    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        off = (0, 0)
        if self.shake > 0.5:
            off = (self.rnd.uniform(-self.shake, self.shake), self.rnd.uniform(-self.shake, self.shake))
        lv = self.level
        ts = self.tileset

        # 1) suelo (de atrás hacia adelante)
        for r in range(lv.rows):
            for c in range(lv.cols):
                cx, cy = self.proj.to_screen(c, r)
                ts.draw_floor(surface, lv.floor[r][c], int(cx + off[0]), int(cy + off[1]))

        # 2) resaltados de la grilla
        self._draw_overlays(surface, off)

        # 3) sombras
        for e in self.enemies:
            e.draw_shadow(surface, off)
        self.player.draw_shadow(surface, off)

        # 4) objetos con ordenamiento por profundidad (col + row)
        drawables = []
        for r in range(lv.rows):
            for c in range(lv.cols):
                b = lv.blocks[r][c]
                if b:
                    drawables.append((c + r, c, "block", (b, c, r)))
        for p in self.pickups:
            drawables.append((p.sort_key() + 0.1, p.col, "obj", p))
        for e in self.enemies:
            drawables.append((e.sort_key(), e.fcol, "obj", e))
        drawables.append((self.player.sort_key(), self.player.fcol, "obj", self.player))
        drawables.sort(key=lambda d: (d[0], d[1]))
        # personajes vivos: si un bloque que se dibuja DESPUÉS los tapa, se hace translúcido
        actors = [(e.sort_key(), pygame.Rect(e.x - 22, e.y - 80, 44, 84)) for e in [self.player] + self.enemies if e.alive]
        for depth, _, kind, data in drawables:
            if kind == "block":
                name, c, r = data
                cx, cy = self.proj.to_screen(c, r)
                cx, cy = int(cx + off[0]), int(cy + off[1])
                rect = ts.block_rect(name, cx, cy)
                ghost = any(ad < depth and rect.colliderect(ar) for ad, ar in actors)
                ts.draw_block(surface, name, cx, cy, ghost)
            else:
                data.draw(surface, off)

        # 5) efectos, barras de vida, indicador de turno
        self._draw_overhead(surface, off)
        self.fx.draw(surface, off)
        self._draw_banners(surface)
        self.hud.draw(surface)

        if self.fade > 1:
            veil = pygame.Surface(surface.get_size())
            veil.set_alpha(int(self.fade))
            surface.blit(veil, (0, 0))
        if self.paused:
            self._draw_pause(surface)

    def _fill_tile(self, ov, tile, fill, border=None, shrink=1.0, width=2):
        pts = self.proj.diamond(tile[0], tile[1], shrink)
        pygame.draw.polygon(ov, fill, pts)
        if border:
            pygame.draw.polygon(ov, border, pts, width)

    def _draw_overlays(self, surface, off):
        ov = self.overlay
        ov.fill((0, 0, 0, 0))
        p = self.player
        if self.turn == "player" and self.script is None and not self.pending_outcome:
            if self.mode == "move":
                for t in self.reach:
                    if t != p.pos:
                        self._fill_tile(ov, t, (70, 160, 255, 70), (140, 205, 255, 150))
                if self.hover_tile in self.reach and self.hover_tile != p.pos:
                    path = build_path(self.reach, self.hover_tile)
                    for t in path:
                        self._fill_tile(ov, t, (130, 220, 255, 120), None, 3)
                    self._fill_tile(ov, path[-1], (130, 220, 255, 150), (255, 255, 255, 230), 1, 3)
            elif self.mode in ("melee", "ranged"):
                atk = p.attacks[self.mode]
                for r in range(self.level.rows):
                    for c in range(self.level.cols):
                        if (c, r) != p.pos and not self.level.is_solid(c, r) and manhattan(p.pos, (c, r)) <= atk.range:
                            self._fill_tile(ov, (c, r), (255, 170, 60, 38), (255, 190, 90, 90), 1, 1)
                for e in self.targets:
                    self._fill_tile(ov, e.pos, (255, 70, 60, 120), (255, 120, 100, 230), 1, 3)
            self._fill_tile(ov, p.pos, (255, 220, 90, 60), (255, 220, 90, 230), 2, 3)
        if self.active_enemy and self.active_enemy.alive:
            self._fill_tile(ov, self.active_enemy.pos, (255, 60, 60, 70), (255, 90, 80, 230), 2, 3)
        if self.hover_tile and not self.level.is_solid(*self.hover_tile):
            self._fill_tile(ov, self.hover_tile, (255, 255, 255, 26), (255, 255, 255, 140), 1, 2)
        surface.blit(ov, off)

    def _draw_overhead(self, surface, off):
        ents = [self.player] + self.enemies
        for e in sorted(ents, key=lambda e: e.sort_key()):
            if not e.alive or e.gone:
                continue
            hx, hy = e.head_pos()
            hx += off[0]
            hy += off[1] - 4
            w = 44
            ratio = e.hp / e.max_hp
            r = pygame.Rect(int(hx - w / 2), int(hy), w, 7)
            pygame.draw.rect(surface, (12, 8, 12), r.inflate(4, 4), border_radius=3)
            pygame.draw.rect(surface, (60, 24, 28), r, border_radius=2)
            col = (110, 214, 120) if e is self.player else (232, 84, 76)
            if ratio < 0.34 and e is self.player:
                col = (240, 180, 60)
            fr = r.copy()
            fr.width = max(0, int(w * ratio))
            pygame.draw.rect(surface, col, fr, border_radius=2)
        # flecha de "turno activo"
        active = self.player if self.turn == "player" else self.active_enemy
        if active and active.alive and not self.pending_outcome:
            hx, hy = active.head_pos()
            bounce = abs(((self.t // 5) % 120) - 60) / 60.0 * 8
            tip = (hx + off[0], hy + off[1] - 12 - bounce)
            pts = [(tip[0], tip[1] + 14), (tip[0] - 10, tip[1]), (tip[0] + 10, tip[1])]
            color = (255, 220, 90) if active is self.player else (255, 96, 84)
            pygame.draw.polygon(surface, (16, 8, 12), [(x, y + 2) for x, y in pts])
            pygame.draw.polygon(surface, color, pts)

    def _draw_banners(self, surface):
        W = surface.get_width()
        if self.banner:
            t = self.banner["t"]
            alpha = 255
            if t < 350:
                alpha = int(255 * t / 350)
            elif t > 1700:
                alpha = max(0, int(255 * (2300 - t) / 600))
            band = pygame.Surface((W, 150), pygame.SRCALPHA)
            band.fill((8, 4, 14, int(185 * alpha / 255)))
            surface.blit(band, (0, 250))
            draw_text(surface, self.banner["title"], self.f_banner, THEME["accent"], (W // 2, 300), "center", alpha=alpha)
            if self.banner["sub"]:
                draw_text(surface, self.banner["sub"], self.f_sub, THEME["text"], (W // 2, 352), "center", alpha=alpha)
        elif self.turn_banner > 0 and not self.pending_outcome:
            alpha = min(255, int(255 * self.turn_banner / 400))
            if self.turn == "player":
                draw_text(surface, "TU TURNO", self.f_banner, THEME["good"], (W // 2, 150), "center", alpha=alpha)
            else:
                draw_text(surface, "TURNO ENEMIGO", self.f_banner, THEME["bad"], (W // 2, 150), "center", alpha=alpha)

    def _draw_pause(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((6, 4, 12, 170))
        surface.blit(veil, (0, 0))
        self.pause_panel.draw(surface)
        draw_text(surface, "PAUSA", self.f_banner, THEME["accent"], (640, 230), "center")
        for b in self.pause_buttons:
            b.draw(surface)
