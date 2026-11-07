"""Tick fissi e accumulatore verificati senza sleep, display o audio."""

import unittest

from game_state import FixedTimestep, MAX_STEPS_PER_FRAME, SimulationClock


class SimulationClockTests(unittest.TestCase):
    def test_time_advances_only_with_ticks_and_has_no_rounding_drift(self):
        clock = SimulationClock()
        for _ in range(60 * 300):
            clock.advance()
        self.assertEqual(clock.ticks, 18_000)
        self.assertEqual(clock.elapsed_ms, 300_000)
        self.assertEqual(clock.elapsed_ms, 300_000)  # Leggere non avanza il tempo.

    def test_pause_resume_and_reset(self):
        clock = SimulationClock()
        clock.advance()
        clock.pause()
        clock.pause()
        for _ in range(100):
            clock.advance()
        self.assertEqual(clock.ticks, 1)
        clock.resume()
        clock.resume()
        clock.advance()
        self.assertEqual(clock.elapsed_ms, 33)
        clock.pause()
        clock.reset()
        clock.advance()
        self.assertEqual(clock.ticks, 1)


class FixedTimestepTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.scheduler = FixedTimestep(lambda: self.now)

    def test_equal_tick_count_at_different_render_rates(self):
        for fps in (30, 60, 75, 120, 144, 240):
            with self.subTest(fps=fps):
                self.now = 1000
                scheduler = FixedTimestep(lambda: self.now)
                ticks = []
                for frame in range(1, fps * 10 + 1):
                    self.now = 1000 + frame * 1000 // fps
                    scheduler.advance(lambda: ticks.append(1))
                self.assertEqual(len(ticks), 600)
                self.assertEqual(scheduler.dropped_ticks, 0)

    def test_fractional_credit_survives_irregular_frame_intervals(self):
        ticks = []
        for delta in (1, 4, 11, 1, 33, 2, 48):
            self.now += delta
            self.scheduler.advance(lambda: ticks.append(1))
        self.assertEqual(len(ticks), 6)
        self.assertEqual(self.scheduler.advance(lambda: ticks.append(1)), 0)

    def test_stall_is_bounded_without_enlarging_physics_steps(self):
        ticks = []
        self.now += 1008
        self.assertEqual(self.scheduler.advance(lambda: ticks.append(1)), MAX_STEPS_PER_FRAME)
        self.assertEqual(self.scheduler.dropped_ticks, 52)
        self.now += 9  # Resta il credito frazionario dei primi 8 ms.
        self.assertEqual(self.scheduler.advance(lambda: ticks.append(1)), 1)
        self.assertEqual(len(ticks), 9)

    def test_reset_discards_elapsed_time_and_partial_credit(self):
        self.now += 16
        self.assertEqual(self.scheduler.advance(lambda: None), 0)
        self.now += 120_000
        self.scheduler.reset()
        self.assertEqual(self.scheduler.advance(lambda: None), 0)
        self.now += 1
        self.assertEqual(self.scheduler.advance(lambda: None), 0)
        self.now += 16
        self.assertEqual(self.scheduler.advance(lambda: None), 1)

    def test_reset_inside_tick_stops_remaining_catchup(self):
        self.now += 100
        self.assertEqual(self.scheduler.advance(self.scheduler.reset), 1)
        self.assertEqual(self.scheduler.advance(lambda: None), 0)

    def test_backwards_or_invalid_source_is_rejected(self):
        for value in (999, -1, 1000.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.now = value
                self.scheduler.advance(lambda: None)
