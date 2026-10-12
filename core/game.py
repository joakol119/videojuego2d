"""Game: ventana, bucle principal (INPUT / UPDATE / RENDER) y manejo de escenas."""
import pygame

from .audio import AudioManager


class Game:
    ANCHO = 1280
    ALTO = 720
    FPS = 60
    TITULO = "Cenizas del Yermo — RPG isométrico por turnos"

    def __init__(self, headless=False):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((self.ANCHO, self.ALTO), flags)
        pygame.display.set_caption(self.TITULO)
        self.clock = pygame.time.Clock()
        self.audio = AudioManager()
        self.running = False
        self.scenes = {}
        self.scene = None
        self._pending = None
        self.shared = {}   # datos que viajan entre escenas (estadísticas, etc.)

    # ------------------------------------------------------------- escenas
    def register(self, name, scene_cls):
        self.scenes[name] = scene_cls(self)

    def change_scene(self, name, **kwargs):
        """El cambio se aplica al comienzo del próximo frame (evita cortar un update)."""
        self._pending = (name, kwargs)

    def _apply_pending(self):
        if self._pending:
            name, kwargs = self._pending
            self._pending = None
            if self.scene:
                self.scene.on_exit()
            self.scene = self.scenes[name]
            self.scene.on_enter(**kwargs)

    # --------------------------------------------------------------- bucle
    def step(self, dt, events=None):
        """Un frame completo. Separado de run() para poder testear sin ventana."""
        self._apply_pending()
        for event in (events if events is not None else pygame.event.get()):
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.audio.toggle_mute()
            elif self.scene:
                self.scene.handle_event(event)             # INPUT
        if self.scene:
            self.scene.update(dt)                          # UPDATE
            self.scene.draw(self.screen)                   # RENDER
        pygame.display.flip()

    def run(self, first_scene="menu"):
        self.running = True
        self.change_scene(first_scene)
        while self.running:
            dt = min(self.clock.tick(self.FPS), 50)        # ms; tope para no "saltar" tras un lag
            self.step(dt)
        pygame.quit()
