"""Sequenza nascosta e impostazioni di avvio esclusivamente in memoria."""

from dataclasses import dataclass, replace

from manifest import MANIFEST


class CheatSequence:
    """Riconoscitore di prefissi con recupero delle sequenze sovrapposte."""

    def __init__(self, sequence):
        if not sequence:
            raise ValueError('Sequenza debug vuota')
        self.sequence = tuple(sequence)
        self.prefix = [0] * len(self.sequence)
        matched = 0
        for index in range(1, len(self.sequence)):
            while matched and self.sequence[index] != self.sequence[matched]:
                matched = self.prefix[matched - 1]
            if self.sequence[index] == self.sequence[matched]:
                matched += 1
            self.prefix[index] = matched
        self.reset()

    def reset(self):
        self.matched = 0

    def feed(self, action):
        while self.matched and action != self.sequence[self.matched]:
            self.matched = self.prefix[self.matched - 1]
        if action == self.sequence[self.matched]:
            self.matched += 1
        if self.matched == len(self.sequence):
            self.matched = self.prefix[self.matched - 1]
            return True
        return False


@dataclass(frozen=True, slots=True)
class StartSettings:
    level: int = 1
    lives: int = MANIFEST['engine']['initial_lives']
    shields: int = 0

    def __post_init__(self):
        config = MANIFEST['debug_menu']
        if (type(self.level) is not int or not 1 <= self.level <= len(MANIFEST['levels'])
                or type(self.lives) is not int or not 1 <= self.lives <= config['max_lives']
                or type(self.shields) is not int or not 0 <= self.shields <= config['max_shields']):
            raise ValueError('Impostazioni debug fuori intervallo')

    def adjust(self, field, delta):
        minimum, maximum = {'level': (1, len(MANIFEST['levels'])),
                            'lives': (1, MANIFEST['debug_menu']['max_lives']),
                            'shields': (0, MANIFEST['debug_menu']['max_shields'])}[field]
        return replace(self, **{field: max(minimum, min(maximum, getattr(self, field) + delta))})
