"""Parametri immutabili dei livelli: nessuna dipendenza dal motore o da Pygame."""

from dataclasses import dataclass
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
    music: str
    hint: str
    fuse: FuseConfig = FuseConfig()
    scoring: ScoreConfig = ScoreConfig()
    primary: str = ''
    cover: str = ''
    boss_max_size: tuple[int, int] = tuple(MANIFEST['levels'][0]['boss_max_size'])
    boss_render_scale: float = 1.0

    def __post_init__(self):
        if not all(math.isfinite(value) for value in
                   (self.boss_speed, self.missile_speed, self.direction_jitter,
                    self.pursuit_weight, self.victory_percent, self.boss_render_scale)):
            raise ValueError("Parametri di livello non finiti")
        if (self.boss_speed <= 0 or self.missile_speed <= 0 or self.direction_jitter < 0
                or not 0 <= self.pursuit_weight <= 1 or not 0 < self.victory_percent <= 100
                or self.boss_render_scale <= 0):
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
MUSIC_TRACKS = tuple(dict.fromkeys(item.music for item in LEVEL_CONFIGS))


def get_level_config(level: int) -> LevelConfig:
    if type(level) is not int or not 1 <= level <= len(LEVEL_CONFIGS):
        raise ValueError("Livello non configurato")
    return LEVEL_CONFIGS[level - 1]
