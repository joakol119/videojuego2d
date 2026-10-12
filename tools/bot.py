"""Jugador automático (solo para pruebas, balance y para grabar el video de demostración)."""
from game.pathfinding import manhattan


class AutoPlayer:
    def __init__(self, aggressive=True):
        self.aggressive = aggressive

    def act(self, sc):
        """Hace UNA acción del jugador si puede. Devuelve True si hizo algo."""
        if not sc._can_act():
            return False
        p = sc.player
        enemies = sc.living_enemies()
        if not enemies:
            return False
        # curarse si está bajo
        if p.hp <= p.max_hp * 0.45 and p.potions > 0 and p.ap >= 1:
            sc.ui_use_potion()
            return True
        melee, ranged = p.attacks["melee"], p.attacks["ranged"]
        adj = [e for e in enemies if manhattan(p.pos, e.pos) == 1]
        if adj and p.ap >= melee.cost:
            tgt = min(adj, key=lambda e: e.hp)
            sc.ui_set_mode("melee")
            sc.click_tile(tgt.pos)
            return True
        if p.ap >= ranged.cost:
            sc.ui_set_mode("ranged")
            if sc.targets:
                tgt = min(sc.targets, key=lambda e: e.hp)
                sc.click_tile(tgt.pos)
                return True
        sc.ui_set_mode("move")
        if p.ap >= 1 and sc.reach:
            tgt = min(enemies, key=lambda e: manhattan(p.pos, e.pos))
            best = min((t for t in sc.reach if t != p.pos),
                       key=lambda t: (manhattan(t, tgt.pos), sc.reach[t][0]), default=None)
            if best and manhattan(best, tgt.pos) < manhattan(p.pos, tgt.pos):
                sc.click_tile(best)
                return True
        sc.ui_end_turn()
        return True
