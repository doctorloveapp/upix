"""Contratti del tutorial e curva di difficoltà dei dodici livelli."""

from dataclasses import FrozenInstanceError, replace
import unittest

from level_config import LEVEL_CONFIGS, get_level_config
from shock_system import ShockSystem


class LevelConfigTests(unittest.TestCase):
    def test_first_three_levels_have_distinct_sprite_and_progression(self):
        tutorial, missiles, aggressive = (get_level_config(level) for level in (1, 2, 3))
        self.assertEqual([config.boss_sprite for config in (tutorial, missiles, aggressive)],
                         ['boss1.png', 'boss2.png', 'boss3.png'])
        self.assertEqual([config.missile_interval_ms for config in (tutorial, missiles, aggressive)],
                         [2400, 2250, 2100])
        self.assertEqual([config.missile_speed for config in (tutorial, missiles, aggressive)],
                         [2.0, 2.3, 2.6])
        self.assertLess(tutorial.boss_speed, missiles.boss_speed)
        self.assertLess(missiles.boss_speed, aggressive.boss_speed)
        self.assertLess(aggressive.direction_interval_ms, missiles.direction_interval_ms)
        self.assertEqual(missiles.pursuit_weight, 0)
        self.assertGreater(aggressive.pursuit_weight, 0)
        self.assertEqual([config.victory_percent for config in (tutorial, missiles, aggressive)],
                         [70, 72, 74])

    def test_campaign_difficulty_increases_at_every_level_without_tutorial_cliff(self):
        for previous, current in zip(LEVEL_CONFIGS, LEVEL_CONFIGS[1:]):
            with self.subTest(target=current.victory_percent):
                self.assertGreater(current.boss_speed, previous.boss_speed)
                self.assertLessEqual(current.boss_speed - previous.boss_speed, 0.401)
                self.assertGreater(current.missile_speed, previous.missile_speed)
                self.assertLess(current.missile_interval_ms, previous.missile_interval_ms)
                self.assertGreater(current.victory_percent, previous.victory_percent)
                self.assertLessEqual(current.victory_percent - previous.victory_percent, 2)
                self.assertLessEqual(current.direction_interval_ms, previous.direction_interval_ms)
                self.assertGreaterEqual(current.pursuit_weight, previous.pursuit_weight)
                self.assertLess(current.shock.activation_ms, previous.shock.activation_ms)
        self.assertEqual(LEVEL_CONFIGS[-1].victory_percent, 86)
        self.assertEqual(LEVEL_CONFIGS[-1].missile_speed, 5.3)
        self.assertEqual(LEVEL_CONFIGS[-1].missile_interval_ms, 750)

    def test_campaign_contains_twelve_valid_configs_and_rejects_unknown_levels(self):
        self.assertEqual(len(LEVEL_CONFIGS), 12)
        for level in range(1, 13):
            self.assertIs(get_level_config(level), LEVEL_CONFIGS[level - 1])
        for level in (0, -1, 13, 1.5, True):
            with self.subTest(level=level), self.assertRaises(ValueError):
                get_level_config(level)

    def test_each_level_shock_activates_on_first_tick_at_or_after_its_threshold(self):
        for level, config in enumerate(LEVEL_CONFIGS, 1):
            with self.subTest(level=level):
                shock = ShockSystem(config.shock)
                ticks = (config.shock.activation_ms * 60 + 999) // 1000
                for _ in range(ticks - 1):
                    shock.advance(safe=True)
                self.assertTrue(shock.warning)
                self.assertFalse(shock.active)
                shock.advance(safe=True)
                self.assertTrue(shock.active)
                self.assertEqual(shock.shot_interval(config.missile_interval_ms),
                                 config.missile_interval_ms // 2)

    def test_configs_are_immutable_and_invalid_parameters_are_rejected(self):
        config = get_level_config(1)
        with self.assertRaises(FrozenInstanceError):
            config.boss_speed = 10
        for changes in ({'boss_speed': 0}, {'boss_speed': float('nan')},
                        {'missile_interval_ms': 0}, {'pursuit_weight': 2},
                        {'victory_percent': 101}, {'direction_interval_ms': None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)
