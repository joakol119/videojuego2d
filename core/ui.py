"""Widgets de UI. Button/Panel/Bar heredan de GameObject (clase base del motor)."""
import pygame

from .game_object import GameObject

THEME = {
    "bg": (24, 18, 30),
    "panel": (36, 28, 44),
    "panel_light": (58, 44, 66),
    "border": (232, 150, 62),
    "border_dim": (110, 78, 62),
    "text": (246, 232, 208),
    "text_dim": (170, 154, 150),
    "accent": (255, 190, 80),
    "good": (110, 214, 120),
    "bad": (232, 84, 76),
    "info": (96, 178, 240),
}

_FONT_CACHE = {}
_FONT_CANDIDATES = "segoeui,helveticaneue,arial,dejavusans,liberationsans,freesans,verdana"


def get_font(size, bold=False):
    key = (size, bold)
    if key not in _FONT_CACHE:
        try:
            font = pygame.font.SysFont(_FONT_CANDIDATES, size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, int(size * 1.15))
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


_TEXT_CACHE = {}


def render_text(text, font, color):
    key = (text, id(font), color)
    surf = _TEXT_CACHE.get(key)
    if surf is None:
        if len(_TEXT_CACHE) > 600:
            _TEXT_CACHE.clear()
        surf = font.render(text, True, color)
        _TEXT_CACHE[key] = surf
    return surf


def draw_text(surface, text, font, color, pos, anchor="topleft", shadow=True, alpha=255):
    img = render_text(text, font, color)
    rect = img.get_rect(**{anchor: pos})
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    if shadow:
        sh = render_text(text, font, (10, 6, 12))
        if alpha < 255:
            sh = sh.copy()
            sh.set_alpha(alpha)
        surface.blit(sh, rect.move(2, 2))
    surface.blit(img, rect)
    return rect


class Panel(GameObject):
    """Panel rectangular con borde (fondo semitransparente)."""

    def __init__(self, rect, alpha=225, border=None, radius=10):
        super().__init__(rect[0], rect[1])
        self.rect = pygame.Rect(rect)
        self.alpha = alpha
        self.border = border or THEME["border_dim"]
        self.radius = radius

    def draw(self, surface, offset=(0, 0)):
        surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*THEME["panel"], self.alpha), surf.get_rect(), border_radius=self.radius)
        pygame.draw.rect(surf, self.border, surf.get_rect(), 2, border_radius=self.radius)
        surface.blit(surf, self.rect.move(offset))


class Bar(GameObject):
    """Barra de progreso (vida, etc.)."""

    def __init__(self, rect, color, back=(40, 24, 28)):
        super().__init__(rect[0], rect[1])
        self.rect = pygame.Rect(rect)
        self.color = color
        self.back = back
        self.value = 1.0
        self.ghost = 1.0  # barra "fantasma" que baja despacio al recibir daño

    def set_value(self, v):
        self.value = max(0.0, min(1.0, v))

    def update(self, dt, action=None):
        if self.ghost > self.value:
            self.ghost = max(self.value, self.ghost - dt * 0.0006)
        else:
            self.ghost = self.value

    def draw(self, surface, offset=(0, 0)):
        r = self.rect.move(offset)
        pygame.draw.rect(surface, (14, 8, 12), r.inflate(4, 4), border_radius=4)
        pygame.draw.rect(surface, self.back, r, border_radius=3)
        if self.ghost > self.value:
            g = r.copy()
            g.width = max(0, int(r.width * self.ghost))
            pygame.draw.rect(surface, (240, 220, 200), g, border_radius=3)
        f = r.copy()
        f.width = max(0, int(r.width * self.value))
        if f.width:
            pygame.draw.rect(surface, self.color, f, border_radius=3)
            hl = pygame.Rect(f.x, f.y, f.width, max(1, f.height // 3))
            pygame.draw.rect(surface, tuple(min(255, c + 50) for c in self.color), hl, border_radius=3)


class Button(GameObject):
    """Botón con feedback visual y sonoro (hover + click)."""

    def __init__(self, rect, text, callback, audio=None, hotkey=None, subtext="",
                 font_size=22, primary=False, enabled=True):
        super().__init__(rect[0], rect[1])
        self.rect = pygame.Rect(rect)
        self.text = text
        self.subtext = subtext
        self.callback = callback
        self.audio = audio
        self.hotkey = hotkey
        self.enabled = enabled
        self.selected = False
        self.primary = primary
        self.hover = False
        self.pressed = False
        self.font = get_font(font_size, bold=True)
        self.small = get_font(max(12, font_size - 8))
        self.t = 0

    def activate(self):
        if not self.enabled:
            if self.audio:
                self.audio.play("denied")
            return
        if self.audio:
            self.audio.play("click")
        if self.callback:
            self.callback()

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            inside = self.rect.collidepoint(event.pos)
            if inside and not self.hover and self.enabled and self.audio:
                self.audio.play("hover")
            self.hover = inside
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self.pressed
            self.pressed = False
            if was and self.rect.collidepoint(event.pos):
                self.activate()
                return True
        return False

    def update(self, dt, action=None):
        self.t += dt

    def draw(self, surface, offset=(0, 0)):
        r = self.rect.move(offset)
        if self.pressed:
            r = r.move(0, 2)
        if not self.enabled:
            fill, border, tcol = (40, 34, 44), (80, 66, 70), THEME["text_dim"]
        elif self.selected:
            fill, border, tcol = (110, 62, 36), THEME["accent"], (255, 244, 220)
        elif self.hover:
            fill, border, tcol = (88, 64, 80), THEME["accent"], (255, 244, 220)
        elif self.primary:
            fill, border, tcol = (132, 66, 40), THEME["border"], (255, 244, 220)
        else:
            fill, border, tcol = THEME["panel_light"], THEME["border_dim"], THEME["text"]
        pygame.draw.rect(surface, (12, 8, 14), r.move(0, 3), border_radius=9)
        pygame.draw.rect(surface, fill, r, border_radius=9)
        top = pygame.Rect(r.x + 3, r.y + 3, r.width - 6, r.height // 2 - 2)
        hl = pygame.Surface(top.size, pygame.SRCALPHA)
        pygame.draw.rect(hl, (255, 255, 255, 22), hl.get_rect(), border_radius=7)
        surface.blit(hl, top)
        width = 3 if (self.selected or self.hover) and self.enabled else 2
        pygame.draw.rect(surface, border, r, width, border_radius=9)
        cy = r.centery - (8 if self.subtext else 0)
        draw_text(surface, self.text, self.font, tcol, (r.centerx, cy), "center")
        if self.subtext:
            draw_text(surface, self.subtext, self.small, THEME["accent"] if self.enabled else THEME["text_dim"],
                      (r.centerx, r.centery + 14), "center")
        if self.hotkey:
            k = self.small.render(str(self.hotkey), True, THEME["text_dim"])
            surface.blit(k, (r.x + 8, r.y + 4))
