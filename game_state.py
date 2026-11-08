"""Stati, tempo simulato e schedulazione indipendenti da rendering e mixer."""

from collections.abc import Callable
from enum import Enum, auto
from time import monotonic_ns
from manifest import MANIFEST

SIMULATION_HZ = MANIFEST['engine']['simulation_hz']
MAX_STEPS_PER_FRAME = MANIFEST['engine']['max_steps_per_frame']


class GameState(Enum):
    MENU = auto()
    DEBUG_MENU = auto()
    HIGHSCORES = auto()
    TUTORIAL = auto()
    NAME_ENTRY = auto()
    CAMPAIGN_COMPLETE = auto()
    PLAYING = auto()
    DYING = auto()
    CAPTURING = auto()
    PAUSED = auto()
    LEVEL_CLEAR = auto()
    GAME_OVER = auto()
    PHYSICS_ERROR = auto()


class SimulationClock:
    """Tempo autorevole del livello: avanza esclusivamente di un tick fisso."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.ticks = 0
        self._paused = False

    def advance(self) -> None:
        if not self._paused:
            self.ticks += 1

    @property
    def elapsed_ms(self) -> int:
        return self.ticks * 1000 // SIMULATION_HZ

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False


class FixedTimestep:
    """Accumula millisecondi reali e invoca step a 60 Hz, senza dt variabile.

    Il credito usa unità intere (ms * Hz): un tick costa esattamente 1000,
    senza sommare approssimazioni float di 1/60. Oltre il budget si scarta
    soltanto il debito di tick interi, conservando la frazione; il gioco
    rallenta sotto sovraccarico anziché saltare controlli fisici.

    reset() svuota il credito e interrompe anche un recupero in corso:
    pausa, stati terminali e cambio livello non ereditano tick arretrati.
    La sorgente monotona iniettabile restituisce millisecondi interi.
    """

    def __init__(self, source: Callable[[], int] | None = None):
        self._source = source if source is not None else lambda: monotonic_ns() // 1_000_000
        self._last_real_ms = None
        self._generation = 0
        self.dropped_ticks = 0
        self.reset()

    def _read(self) -> int:
        value = self._source()
        if type(value) is not int or value < 0:
            raise ValueError("La sorgente temporale deve restituire millisecondi interi non negativi")
        if self._last_real_ms is not None and value < self._last_real_ms:
            raise ValueError("La sorgente temporale non è monotona")
        return value

    def reset(self) -> None:
        self._last_real_ms = self._read()
        self._credit = 0
        self._generation += 1

    def advance(self, step: Callable[[], None]) -> int:
        current = self._read()
        self._credit += (current - self._last_real_ms) * SIMULATION_HZ
        self._last_real_ms = current
        due = self._credit // 1000
        if due > MAX_STEPS_PER_FRAME:
            dropped = due - MAX_STEPS_PER_FRAME
            self._credit -= dropped * 1000
            self.dropped_ticks += dropped
        generation = self._generation
        steps = 0
        while self._credit >= 1000 and generation == self._generation:
            self._credit -= 1000
            step()
            steps += 1
        return steps
