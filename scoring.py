"""Punti di conquista e bonus temporaneo, con sola aritmetica intera."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreConfig:
    points_per_cell: int = 10
    area_bonus_percent: int = 100
    bonus_time_limit_ms: int = 180000

    def __post_init__(self):
        if (type(self.points_per_cell) is not int or self.points_per_cell <= 0
                or type(self.area_bonus_percent) is not int or self.area_bonus_percent < 0
                or type(self.bonus_time_limit_ms) is not int or self.bonus_time_limit_ms <= 0):
            raise ValueError("Parametri punteggio non validi")


class LevelScore:
    """Base permanente; bonus quadratico per singolo taglio, decrescente nel tempo.

    Il tempo è quello attivo del livello, fornito dal chiamante. Il bonus di
    TUTTE le catture scende insieme: aspettare dopo un taglio non lo congela.
    Scia e bordo iniziale non assegnano punti.
    """

    def __init__(self, config: ScoreConfig, total_cells: int):
        if type(total_cells) is not int or total_cells <= 0:
            raise ValueError("Il campo deve contenere un numero positivo di celle")
        self.config = config
        self.total_cells = total_cells
        self.base_points = 0
        self.bonus_pool = 0

    def capture(self, area_cells: int) -> None:
        if type(area_cells) is not int or not 0 <= area_cells <= self.total_cells:
            raise ValueError("Area conquistata non valida")
        base = area_cells * self.config.points_per_cell
        self.base_points += base
        self.bonus_pool += (base * area_cells * self.config.area_bonus_percent
                            // (self.total_cells * 100))

    def bonus(self, elapsed_ms: int) -> int:
        if type(elapsed_ms) is not int or elapsed_ms < 0:
            raise ValueError("Tempo del livello non valido")
        remaining = max(0, self.config.bonus_time_limit_ms - elapsed_ms)
        return self.bonus_pool * remaining // self.config.bonus_time_limit_ms

    def total(self, elapsed_ms: int) -> int:
        return self.base_points + self.bonus(elapsed_ms)
