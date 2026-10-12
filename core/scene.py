"""Scene: clase base de todas las escenas (menú, juego, game over, victoria)."""


class Scene:
    def __init__(self, game):
        self.game = game

    def on_enter(self, **kwargs):
        """Se llama al activar la escena."""

    def on_exit(self):
        """Se llama al abandonar la escena."""

    def handle_event(self, event):
        """INPUT"""

    def update(self, dt):
        """UPDATE (dt en milisegundos)"""

    def draw(self, surface):
        """RENDER"""
