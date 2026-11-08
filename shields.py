"""Inventario scudi, ricompensa singolo taglio e protezione a tick fissi."""

import math


class Shields:
    def __init__(self, config, simulation_hz):
        self.config = config
        self.hz = simulation_hz
        self.charges = 0
        self.active = False
        self.grace_ticks = 0
        self.notice_ticks = 0
        self.earned_this_level = 0

    def start_level(self):
        self.active = False
        self.grace_ticks = self.notice_ticks = self.earned_this_level = 0

    def advance(self):
        self.grace_ticks = max(0, self.grace_ticks - 1)
        self.notice_ticks = max(0, self.notice_ticks - 1)

    def award(self, captured_cells, total_cells):
        if captured_cells * 100 < total_cells * self.config['capture_percent']:
            return False
        self.charges += 1
        self.earned_this_level += 1
        self.notice_ticks = math.ceil(self.config['notice_ms'] * self.hz / 1000)
        return True

    def activate(self):
        if self.charges and not self.active:
            self.active = True
            return True
        return False

    def absorb(self):
        if self.grace_ticks:
            return True
        if not self.active:
            return False
        self.active = False
        self.charges -= 1
        self.grace_ticks = math.ceil(self.config['contact_grace_ms'] * self.hz / 1000)
        return True

    def on_death(self):
        self.active = False
        self.grace_ticks = 0
