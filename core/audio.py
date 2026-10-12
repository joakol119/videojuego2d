"""AudioManager: efectos de sonido y música, con degradación elegante sin audio."""
import pygame

from .paths import asset_path


class AudioManager:
    def __init__(self, sfx_volume=0.7, music_volume=0.35):
        self.enabled = False
        self.muted = False
        self.sfx_volume = sfx_volume
        self.music_volume = music_volume
        self.sounds = {}
        self.current_music = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
        except pygame.error as exc:  # sin placa de sonido: el juego sigue andando
            print(f"[audio] desactivado: {exc}")
            return
        self._load_all()

    def _load_all(self):
        folder = asset_path("sounds")
        for wav in sorted(folder.glob("*.wav")):
            if wav.stem.startswith("music_"):
                continue
            try:
                self.sounds[wav.stem] = pygame.mixer.Sound(str(wav))
            except pygame.error as exc:
                print(f"[audio] no se pudo cargar {wav.name}: {exc}")

    def play(self, name, volume=1.0):
        if not self.enabled or self.muted:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(max(0.0, min(1.0, self.sfx_volume * volume)))
            snd.play()

    def play_music(self, name):
        if not self.enabled or name == self.current_music:
            return
        self.current_music = name
        try:
            pygame.mixer.music.load(str(asset_path("sounds", f"{name}.wav")))
            pygame.mixer.music.set_volume(0 if self.muted else self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=600)
        except pygame.error as exc:
            print(f"[audio] música no disponible: {exc}")

    def stop_music(self, fade_ms=400):
        if self.enabled:
            pygame.mixer.music.fadeout(fade_ms)
        self.current_music = None

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled:
            pygame.mixer.music.set_volume(0 if self.muted else self.music_volume)
        return self.muted
