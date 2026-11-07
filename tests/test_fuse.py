"""Soglie Miccia verificate per tick, senza timer reali o Pygame."""

from dataclasses import replace
import unittest

from fuse import Fuse, FuseConfig


class FuseTests(unittest.TestCase):
    def setUp(self):
        self.config = FuseConfig(warning_ms=1000, activation_ms=2000)
        self.fuse = Fuse(self.config)

    def test_warning_and_activation_occur_at_exact_safe_time(self):
        for _ in range(59):
            self.fuse.advance(safe=True)
        self.assertFalse(self.fuse.warning)
        self.fuse.advance(safe=True)
        self.assertTrue(self.fuse.warning)
        self.assertFalse(self.fuse.active)
        for _ in range(59):
            self.fuse.advance(safe=True)
        self.assertFalse(self.fuse.active)
        self.fuse.advance(safe=True)
        self.assertTrue(self.fuse.active)
        self.assertEqual(self.fuse.shot_interval(1900), 950)

    def test_open_trail_suspends_count_but_cannot_disarm_pressure(self):
        for _ in range(90):
            self.fuse.advance(safe=True)
        for _ in range(600):
            self.fuse.advance(safe=False)
        self.assertEqual(self.fuse.elapsed_ms, 1500)
        for _ in range(30):
            self.fuse.advance(safe=True)
        for _ in range(600):
            self.fuse.advance(safe=False)
        self.assertTrue(self.fuse.active)
        self.assertEqual(self.fuse.safe_ticks, 120)
        self.fuse.reset()
        self.assertEqual(self.fuse.elapsed_ms, 0)
        self.assertFalse(self.fuse.warning)
        self.assertEqual(self.fuse.shot_interval(1900), 1900)

    def test_disabled_fuse_and_disabled_shooting(self):
        disabled = Fuse(replace(self.config, enabled=False))
        for _ in range(300):
            disabled.advance(safe=True)
            self.fuse.advance(safe=True)
        self.assertFalse(disabled.active)
        self.assertFalse(disabled.warning)
        self.assertEqual(disabled.safe_ticks, 0)
        self.assertEqual(disabled.shot_interval(1900), 1900)
        self.assertIsNone(self.fuse.shot_interval(None))

    def test_non_tick_aligned_threshold_never_activates_early(self):
        fuse = Fuse(FuseConfig(warning_ms=50, activation_ms=101, shot_interval_percent=1))
        for _ in range(6):
            fuse.advance(safe=True)
        self.assertFalse(fuse.active)
        fuse.advance(safe=True)
        self.assertTrue(fuse.active)
        self.assertEqual(fuse.shot_interval(1), 1)

    def test_invalid_configs_are_rejected(self):
        for changes in ({'warning_ms': -1}, {'activation_ms': 1000},
                        {'activation_ms': 0}, {'warning_ms': 1.5},
                        {'activation_ms': True}, {'enabled': 1},
                        {'shot_interval_percent': 0}, {'shot_interval_percent': 101},
                        {'shot_interval_percent': float('nan')}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.config, **changes)
