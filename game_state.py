"""Stati e tempo logico indipendenti da rendering e mixer."""

from collections.abc import Callable
from enum import Enum, auto
from time import monotonic_ns


class GameState(Enum):
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_CLEAR = auto()
    GAME_OVER = auto()
    PHYSICS_ERROR = auto()


class SimulationClock:
    """Millisecondi attivi del livello; la pausa non accumula arretrati.

    La sorgente monotona è iniettabile: i test non devono dormire o leggere
    l'orologio di Pygame. La sorgente restituisce millisecondi interi.
    """

    def __init__(self, source: Callable[[], int] | None = None):
        self._source = source if source is not None else lambda: monotonic_ns() // 1_000_000
        self._last_real_ms = None
        self.reset()

    def _read(self) -> int:
        value = self._source()
        if not isinstance(value, int) or value < 0:
            raise ValueError("La sorgente temporale deve restituire millisecondi interi non negativi")
        if self._last_real_ms is not None and value < self._last_real_ms:
            raise ValueError("La sorgente temporale non è monotona")
        return value

    def reset(self) -> None:
        self._last_real_ms = self._read()
        self._elapsed_ms = 0
        self._paused = False

    @property
    def elapsed_ms(self) -> int:
        if not self._paused:
            current = self._read()
            self._elapsed_ms += current - self._last_real_ms
            self._last_real_ms = current
        return self._elapsed_ms

    def pause(self) -> None:
        if not self._paused:
            self._elapsed_ms = self.elapsed_ms
            self._paused = True

    def resume(self) -> None:
        if self._paused:
            self._last_real_ms = self._read()
            self._paused = False
