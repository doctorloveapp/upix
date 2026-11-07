"""Miccia deterministica: pressione per permanenza in territorio sicuro."""

from dataclasses import dataclass

from game_state import SIMULATION_HZ


@dataclass(frozen=True, slots=True)
class FuseConfig:
    enabled: bool = True
    warning_ms: int = 8000
    activation_ms: int = 12000
    shot_interval_percent: int = 50

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise ValueError("enabled deve essere booleano")
        if (type(self.warning_ms) is not int or type(self.activation_ms) is not int
                or not 0 <= self.warning_ms < self.activation_ms):
            raise ValueError("Soglie Miccia non valide")
        if (type(self.shot_interval_percent) is not int
                or not 1 <= self.shot_interval_percent <= 100):
            raise ValueError("Percentuale intervallo Miccia non valida")


class Fuse:
    """Conta solo i tick sicuri. Uscire dal bordo sospende, senza disinnescare.

    Il chiamante avanza una volta per tick PLAYING e resetta a conquista/morte.
    Nessun timer reale, input, RNG o dipendenza dal rendering.
    """

    def __init__(self, config: FuseConfig):
        self.config = config
        self.reset()

    def reset(self) -> None:
        self.safe_ticks = 0

    def advance(self, *, safe: bool) -> None:
        if self.config.enabled and safe and not self.active:
            self.safe_ticks += 1

    @property
    def elapsed_ms(self) -> int:
        return self.safe_ticks * 1000 // SIMULATION_HZ

    @property
    def active(self) -> bool:
        return self.config.enabled and self.elapsed_ms >= self.config.activation_ms

    @property
    def warning(self) -> bool:
        return self.config.enabled and self.elapsed_ms >= self.config.warning_ms

    def shot_interval(self, base_ms: int | None) -> int | None:
        if base_ms is None or not self.active:
            return base_ms
        return max(1, base_ms * self.config.shot_interval_percent // 100)
