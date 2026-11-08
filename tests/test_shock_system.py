"""Soglie Scossa verificate per tick, senza timer reali o Pygame."""

from dataclasses import replace
import unittest

from shock_system import ShockSystem, ShockConfig


class ShockSystemTests(unittest.TestCase):
    def setUp(self):
        self.config = ShockConfig(warning_ms=1000, activation_ms=2000)
        self.shock = ShockSystem(self.config)

    def test_warning_and_activation_occur_at_exact_safe_time(self):
        for _ in range(59):
            self.shock.advance(safe=True)
        self.assertFalse(self.shock.warning)
        self.shock.advance(safe=True)
        self.assertTrue(self.shock.warning)
        self.assertFalse(self.shock.active)
        for _ in range(59):
            self.shock.advance(safe=True)
        self.assertFalse(self.shock.active)
        self.shock.advance(safe=True)
        self.assertTrue(self.shock.active)
        self.assertEqual(self.shock.shot_interval(1900), 950)

    def test_open_trail_suspends_count_but_cannot_disarm_pressure(self):
        for _ in range(90):
            self.shock.advance(safe=True)
        for _ in range(600):
            self.shock.advance(safe=False)
        self.assertEqual(self.shock.elapsed_ms, 1500)
        for _ in range(30):
            self.shock.advance(safe=True)
        for _ in range(600):
            self.shock.advance(safe=False)
        self.assertTrue(self.shock.active)
        self.assertEqual(self.shock.safe_ticks, 120)
        self.shock.reset()
        self.assertEqual(self.shock.elapsed_ms, 0)
        self.assertFalse(self.shock.warning)
        self.assertEqual(self.shock.shot_interval(1900), 1900)

    def test_disabled_shock_and_disabled_shooting(self):
        disabled = ShockSystem(replace(self.config, enabled=False))
        for _ in range(300):
            disabled.advance(safe=True)
            self.shock.advance(safe=True)
        self.assertFalse(disabled.active)
        self.assertFalse(disabled.warning)
        self.assertEqual(disabled.safe_ticks, 0)
        self.assertEqual(disabled.shot_interval(1900), 1900)
        self.assertIsNone(self.shock.shot_interval(None))

    def test_non_tick_aligned_threshold_never_activates_early(self):
        shock = ShockSystem(ShockConfig(warning_ms=50, activation_ms=101, shot_interval_percent=1))
        for _ in range(6):
            shock.advance(safe=True)
        self.assertFalse(shock.active)
        shock.advance(safe=True)
        self.assertTrue(shock.active)
        self.assertEqual(shock.shot_interval(1), 1)

    def test_invalid_configs_are_rejected(self):
        for changes in ({'warning_ms': -1}, {'activation_ms': 1000},
                        {'activation_ms': 0}, {'warning_ms': 1.5},
                        {'activation_ms': True}, {'enabled': 1},
                        {'shot_interval_percent': 0}, {'shot_interval_percent': 101},
                        {'shot_interval_percent': float('nan')}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.config, **changes)
