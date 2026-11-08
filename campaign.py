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
    cycle: int = 1
    extra_life: int = 0
    shields_earned: int = 0

    @property
    def score(self):
        return self.base + self.bonus


class RunScore:
    def __init__(self):
        self._results: dict[tuple[int, int], LevelResult] = {}
        self._banked = 0
        self._elapsed_ms = 0

    @property
    def results(self):
        return tuple(self._results.values())

    @property
    def banked(self):
        return self._banked

    @property
    def elapsed_ms(self):
        return self._elapsed_ms

    @property
    def completed_count(self):
        return len(self._results)

    def complete(self, result: LevelResult):
        if (type(result.level) is not int or result.level < 1
                or any(type(value) is not int or value < 0 for value in
                       (result.base, result.bonus, result.elapsed_ms, result.lives,
                        result.extra_life, result.shields_earned))
                or type(result.cycle) is not int or result.cycle < 1
                or not 0 <= result.percent <= 100):
            raise ValueError('Risultato di livello non valido')
        key = result.cycle, result.level
        if key not in self._results:
            self._results[key] = result
            self._banked += result.score
            self._elapsed_ms += result.elapsed_ms
        return self._results[key]

    def has_result(self, level, cycle=1):
        return (cycle, level) in self._results

    def total(self, level, live_score, cycle=1):
        return self.banked + (0 if self.has_result(level, cycle) else live_score)
