"""Scoperta MP3 e shuffle a sacchetto, indipendenti dal RNG della fisica."""

from collections import deque
from pathlib import Path
import random
from time import monotonic_ns

import pygame


class MenuMusic:
    """Stream del menu con inviluppo aggiornato nei frame, senza attese.

    Possiede mixer.music soltanto finché active è True. La campagna può
    acquisire lo stream dopo il completamento del fade-out, mai in parallelo.
    La sorgente monotona è indipendente da tick fisici e RNG della partita.
    """

    def __init__(self, path, *, volume, fade_in_ms, fade_out_ms, time_source=None):
        self.path = Path(path)
        self.volume = volume
        self.fade_in_ms = fade_in_ms
        self.fade_out_ms = fade_out_ms
        self._time = time_source if time_source is not None else lambda: monotonic_ns() // 1_000_000
        self.active = False
        self._gain = self._target = 0.0
        self._duration = 0

    def start(self):
        if self.active:
            self.update()
            if self.active:
                if self._target == 0:
                    self._fade_to(1.0, self.fade_in_ms)
                return
        if not pygame.mixer.get_init():
            return
        try:
            pygame.mixer.music.load(str(self.path))
            pygame.mixer.music.set_volume(0)
            pygame.mixer.music.play(loops=-1)
            self.active = True
            self._gain = 0.0
            self._fade_to(1.0, self.fade_in_ms)
        except (pygame.error, OSError) as exc:
            print(f'Menu music unavailable ({self.path}): {exc}')
            self.stop()

    def _fade_to(self, target, duration):
        self._from = self._gain
        self._target = target
        self._started = self._time()
        self._duration = duration
        if not duration or self._from == target:
            self._gain = target
            if target == 0:
                self.stop()
            else:
                pygame.mixer.music.set_volume(self.volume * self._gain)

    def fade_out(self):
        if self.active and self._target != 0:
            self.update()  # Parte dal volume realmente raggiunto, anche durante il fade-in.
            if self.active:
                self._fade_to(0.0, self.fade_out_ms)

    def update(self):
        if not self.active:
            return
        if not pygame.mixer.get_init():
            self.active = False
            return
        fraction = min(1.0, max(0, self._time() - self._started) / self._duration) if self._duration else 1.0
        self._gain = self._from + (self._target - self._from) * fraction
        if fraction == 1 and self._target == 0:
            self.stop()
        else:
            pygame.mixer.music.set_volume(self.volume * self._gain)

    def stop(self):
        if self.active and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.active = False
        self._gain = 0.0


class MusicShuffle:
    def __init__(self, directory, *, rng=None, extensions=('.mp3',)):
        allowed = {value.lower() for value in extensions}
        try:
            self.tracks = tuple(sorted((path for path in Path(directory).iterdir()
                                        if path.is_file() and path.suffix.lower() in allowed),
                                       key=lambda path: (path.name.casefold(), path.name)))
        except OSError as exc:
            print(f'Music directory unavailable ({directory}): {exc}')
            self.tracks = ()
        self.rng = rng if rng is not None else random.Random()
        self._bag = deque()
        self.last = None

    def _refill(self):
        batch = list(self.tracks)
        self.rng.shuffle(batch)
        # Evita anche A -> A alla giunzione fra due giri, se possibile.
        if len(batch) > 1 and batch[0] == self.last:
            batch[0], batch[1] = batch[1], batch[0]
        self._bag.extend(batch)

    def next_track(self):
        if not self.tracks:
            return None
        if not self._bag:
            self._refill()
        self.last = self._bag.popleft()
        return self.last

    def mark_played(self, path):
        """Conta anche la traccia obbligatoria nel giro, evitando di ripeterla subito."""
        path = Path(path)
        if path not in self.tracks:
            return
        if not self._bag:
            self._refill()
        self._bag = deque(track for track in self._bag if track != path)
        self.last = path


class MusicPlayer:
    """Un solo stream; fine naturale gestita dal frame loop, mai dal tick."""

    def __init__(self, directory, *, volume, extensions=('.mp3',), rng=None):
        self.shuffle = MusicShuffle(directory, rng=rng, extensions=extensions)
        self.volume = volume
        self.current = None
        self.enabled = False
        self._fixed_track = None

    def play_level(self, level, first_level_track):
        """Il livello 1 ripete il tema dedicato; tutti gli altri usano lo shuffle."""
        if level == 1:
            path = Path(first_level_track)
            if self.enabled and self._fixed_track == path:
                return
            self._fixed_track = path
            self.enabled = True
            if self._play_track(path, loops=-1):
                self.shuffle.mark_played(path)
                return
            # Un file rimosso o corrotto non impedisce di giocare.
            self._fixed_track = None
            self._play_next()
        else:
            if self._fixed_track is not None:
                self._fixed_track = None
                self.enabled = False
            self.ensure_playing()

    def _play_track(self, path, *, loops=0):
        if not pygame.mixer.get_init():
            return False
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.volume)
            if loops:
                pygame.mixer.music.play(loops=loops)
            else:
                pygame.mixer.music.play()
            self.current = path
            return True
        except (pygame.error, OSError) as exc:
            print(f'Music unavailable ({path}): {exc}')
            return False

    def ensure_playing(self):
        if not self.enabled:
            self.enabled = True
            self._play_next()

    def _play_next(self):
        self.current = None
        if not pygame.mixer.get_init():
            self.enabled = False
            return
        attempted = set()
        while len(attempted) < len(self.shuffle.tracks):
            path = self.shuffle.next_track()
            if path in attempted:
                continue
            attempted.add(path)
            if self._play_track(path):
                return
        self.enabled = False  # Cartella vuota o nessun file riproducibile.

    def update(self, *, paused=False):
        if self.enabled and not paused and pygame.mixer.get_init() and not pygame.mixer.music.get_busy():
            if self._fixed_track is None or not self._play_track(self._fixed_track, loops=-1):
                self._fixed_track = None
                self._play_next()

    def stop(self):
        self.enabled = False
        self.current = None
        self._fixed_track = None
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
