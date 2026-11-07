"""Tempo logico verificato senza sleep, display o audio."""

import unittest

from game_state import SimulationClock


class SimulationClockTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.clock = SimulationClock(lambda: self.now)

    def test_pause_excludes_wall_time_and_resume_has_no_jump(self):
        self.now += 350
        self.assertEqual(self.clock.elapsed_ms, 350)
        self.clock.pause()
        self.now += 120_000
        self.assertEqual(self.clock.elapsed_ms, 350)
        self.clock.resume()
        self.assertEqual(self.clock.elapsed_ms, 350)
        self.now += 25
        self.assertEqual(self.clock.elapsed_ms, 375)

    def test_repeated_pause_and_resume_are_idempotent(self):
        self.now += 100
        self.clock.pause()
        self.now += 1000
        self.clock.pause()
        self.clock.resume()
        self.now += 50
        self.clock.resume()
        self.assertEqual(self.clock.elapsed_ms, 150)
        self.clock.pause()
        self.now += 5000
        self.clock.resume()
        self.now += 30
        self.assertEqual(self.clock.elapsed_ms, 180)

    def test_reset_starts_new_level_at_zero_and_unpauses(self):
        self.clock.pause()
        self.now += 5000
        self.clock.reset()
        self.assertEqual(self.clock.elapsed_ms, 0)
        self.now += 17
        self.assertEqual(self.clock.elapsed_ms, 17)

    def test_backwards_or_invalid_source_is_rejected(self):
        for value in (999, -1, 1000.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.now = value
                self.clock.elapsed_ms
