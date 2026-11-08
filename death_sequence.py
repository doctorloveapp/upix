"""Sequenza temporanea di morte: soli tick di presentazione, senza fisica."""

import math


class DeathSequence:
    """Conserva il centro dell'impatto e mostra ogni frame per N tick fissi.

    Il chiamante usa un accumulatore azzerato all'ingresso/uscita da DYING.
    Il clock del livello non viene avanzato, neppure durante una morte finale.
    """

    def __init__(self, frame_count, frame_duration_ms, simulation_hz):
        if any(type(value) is not int or value <= 0
               for value in (frame_count, frame_duration_ms, simulation_hz)):
            raise ValueError('Parametri sequenza di morte non validi')
        self.frame_count = frame_count
        self.ticks_per_frame = math.ceil(frame_duration_ms * simulation_hz / 1000)
        self.total_ticks = frame_count * self.ticks_per_frame
        self.cancel()

    def cancel(self):
        self.active = False
        self.elapsed_ticks = 0
        self.center = None

    def start(self, center):
        if len(center) != 2 or not all(math.isfinite(value) for value in center):
            raise ValueError('Centro sequenza di morte non valido')
        self.center = tuple(center)
        self.elapsed_ticks = 0
        self.active = True

    @property
    def frame_index(self):
        return min(self.frame_count - 1, self.elapsed_ticks // self.ticks_per_frame)

    def advance(self):
        """True una sola volta, quando è terminata anche la durata dell'ultimo frame."""
        if not self.active:
            return False
        self.elapsed_ticks += 1
        if self.elapsed_ticks < self.total_ticks:
            return False
        self.active = False
        return True
