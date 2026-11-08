"""Scoperta MP3 e shuffle a sacchetto, indipendenti dal RNG della fisica."""

from collections import deque
from pathlib import Path
import random

import pygame


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

    def next_track(self):
        if not self.tracks:
            return None
        if not self._bag:
            batch = list(self.tracks)
            self.rng.shuffle(batch)
            # Evita anche A -> A alla giunzione fra due giri, se possibile.
            if len(batch) > 1 and batch[0] == self.last:
                batch[0], batch[1] = batch[1], batch[0]
            self._bag.extend(batch)
        self.last = self._bag.popleft()
        return self.last


class MusicPlayer:
    """Un solo stream; fine naturale gestita dal frame loop, mai dal tick."""

    def __init__(self, directory, *, volume, extensions=('.mp3',), rng=None):
        self.shuffle = MusicShuffle(directory, rng=rng, extensions=extensions)
        self.volume = volume
        self.current = None
        self.enabled = False

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
            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()  # Una sola esecuzione, poi il prossimo brano.
                self.current = path
                return
            except (pygame.error, OSError) as exc:
                print(f'Music unavailable ({path}): {exc}')
        self.enabled = False  # Cartella vuota o nessun file riproducibile.

    def update(self, *, paused=False):
        if self.enabled and not paused and pygame.mixer.get_init() and not pygame.mixer.music.get_busy():
            self._play_next()

    def stop(self):
        self.enabled = False
        self.current = None
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
