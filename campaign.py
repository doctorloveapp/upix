"""Registro della campagna: risultati immutabili e consolidamento idempotente."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LevelResult:
    level: int
    base: int
    bonus: int
    elapsed_ms: int
    percent: float
    lives: int

    @property
    def score(self):
        return self.base + self.bonus


class RunScore:
    def __init__(self):
        self._results: dict[int, LevelResult] = {}

    @property
    def results(self):
        return tuple(self._results.values())

    @property
    def banked(self):
        return sum(result.score for result in self._results.values())

    @property
    def elapsed_ms(self):
        return sum(result.elapsed_ms for result in self._results.values())

    def complete(self, result: LevelResult):
        if (type(result.level) is not int or result.level < 1
                or any(type(value) is not int or value < 0 for value in
                       (result.base, result.bonus, result.elapsed_ms, result.lives))
                or not 0 <= result.percent <= 100):
            raise ValueError('Risultato di livello non valido')
        if result.level not in self._results:
            self._results[result.level] = result
        return self._results[result.level]

    def total(self, level, live_score):
        return self.banked + (0 if level in self._results else live_score)
