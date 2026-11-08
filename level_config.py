"""Parametri immutabili dei livelli: nessuna dipendenza dal motore o da Pygame."""

from dataclasses import dataclass, replace
import math

from fuse import FuseConfig
from scoring import ScoreConfig
from manifest import MANIFEST


@dataclass(frozen=True, slots=True)
class LevelConfig:
    boss_sprite: str
    boss_speed: float  # Magnitudine in pixel logici per tick a 60 Hz.
    missile_interval_ms: int | None
    missile_speed: float
    direction_interval_ms: int
    direction_jitter: float
    pursuit_weight: float
    victory_percent: float
    hint: str
    fuse: FuseConfig = FuseConfig()
    scoring: ScoreConfig = ScoreConfig()
    primary: str = ''
    cover: str = ''
    boss_max_size: tuple[int, int] = tuple(MANIFEST['levels'][0]['boss_max_size'])
    boss_render_scale: float = 1.0
    perimeter_threat_count: int = 1
    perimeter_speed_px_per_second: float = 150

    def __post_init__(self):
        if not all(math.isfinite(value) for value in
                   (self.boss_speed, self.missile_speed, self.direction_jitter,
                    self.pursuit_weight, self.victory_percent, self.boss_render_scale,
                    self.perimeter_speed_px_per_second)):
            raise ValueError("Parametri di livello non finiti")
        if (self.boss_speed <= 0 or self.missile_speed <= 0 or self.direction_jitter < 0
                or not 0 <= self.pursuit_weight <= 1 or not 0 < self.victory_percent <= 100
                or self.boss_render_scale <= 0 or self.perimeter_speed_px_per_second <= 0
                or type(self.perimeter_threat_count) is not int or self.perimeter_threat_count not in (1, 2)):
            raise ValueError("Parametri di livello fuori intervallo")
        for interval in (self.direction_interval_ms, self.missile_interval_ms):
            if interval is not None and (type(interval) is not int or interval <= 0):
                raise ValueError("Gli intervalli devono essere millisecondi interi positivi")
        if self.direction_interval_ms is None:
            raise ValueError("Intervallo direzione obbligatorio")


LEVEL_CONFIGS = tuple(LevelConfig(
    **{key: value for key, value in item.items()
       if key not in ('number', 'fuse', 'scoring', 'boss_max_size')},
    fuse=FuseConfig(**item['fuse']), scoring=ScoreConfig(**item['scoring']),
    boss_max_size=tuple(item['boss_max_size']),
) for item in MANIFEST['levels'])


def get_level_config(level: int, cycle: int = 1) -> LevelConfig:
    if type(level) is not int or not 1 <= level <= len(LEVEL_CONFIGS):
        raise ValueError("Livello non configurato")
    if type(cycle) is not int or cycle < 1:
        raise ValueError('Ciclo non valido')
    base = LEVEL_CONFIGS[level - 1]
    if cycle == 1:
        return base
    tuning = MANIFEST['progression']['loop']
    # Limiti espliciti: nessuna crescita illimitata del costo del solver.
    speed = min(tuning['max_speed_percent'], 100 + (cycle - 1) * tuning['speed_step_percent']) / 100
    interval = max(tuning['min_interval_percent'], 100 - (cycle - 1) * tuning['interval_step_percent'])
    activation = max(tuning['minimum_fuse_ms'], base.fuse.activation_ms * interval // 100)
    warning = min(activation - 1, base.fuse.warning_ms * activation // base.fuse.activation_ms)
    return replace(base,
        boss_speed=base.boss_speed * speed, missile_speed=base.missile_speed * speed,
        missile_interval_ms=(None if base.missile_interval_ms is None else
                             max(tuning['minimum_shot_ms'], base.missile_interval_ms * interval // 100)),
        perimeter_speed_px_per_second=base.perimeter_speed_px_per_second * speed,
        victory_percent=min(tuning['max_victory_percent'],
                            base.victory_percent + (cycle - 1) * tuning['victory_step_percent']),
        fuse=replace(base.fuse, warning_ms=warning, activation_ms=activation))
