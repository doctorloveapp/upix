"""Regressioni del punteggio: area, suddivisioni e scadenza del bonus."""

from dataclasses import replace
import unittest

from scoring import LevelScore, ScoreConfig


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.config = ScoreConfig(bonus_time_limit_ms=10000)
        self.score = LevelScore(self.config, total_cells=1000)

    def test_known_capture_awards_base_and_quadratic_area_bonus(self):
        self.score.capture(100)
        self.assertEqual(self.score.base_points, 1000)
        self.assertEqual(self.score.bonus(0), 100)
        self.assertEqual(self.score.total(0), 1100)
        self.assertEqual(self.score.total(5000), 1050)

    def test_single_large_cut_beats_equal_area_split_into_small_cuts(self):
        self.score.capture(100)
        split = LevelScore(self.config, total_cells=1000)
        split.capture(50)
        split.capture(50)
        self.assertEqual(split.base_points, self.score.base_points)
        self.assertEqual(split.bonus(0), 50)
        self.assertGreater(self.score.total(0), split.total(0))

    def test_bonus_decays_for_all_captures_and_expires_without_losing_base(self):
        self.score.capture(100)
        self.score.capture(200)
        self.assertEqual(self.score.total(0), 3500)
        self.assertEqual(self.score.total(9999), 3000)  # Arrotondamento intero.
        self.assertEqual(self.score.total(10000), 3000)
        self.assertEqual(self.score.total(999999), 3000)
        self.score.capture(100)  # Una cattura tardiva non riavvia il bonus.
        self.assertEqual(self.score.total(10000), 4000)

    def test_zero_area_and_disabled_bonus_preserve_base_rules(self):
        self.score.capture(0)
        self.assertEqual(self.score.total(0), 0)
        score = LevelScore(replace(self.config, area_bonus_percent=0), 1000)
        score.capture(100)
        self.assertEqual(score.total(0), 1000)
        self.assertEqual(score.total(10000), 1000)

    def test_reads_are_pure_and_use_integer_rounding(self):
        self.score.capture(333)
        self.assertEqual(self.score.base_points, 3330)
        self.assertEqual(self.score.bonus_pool, 1108)
        first = self.score.total(1234)
        self.assertEqual(self.score.total(1234), first)
        self.assertIsInstance(first, int)
        self.assertEqual(self.score.total(0), 4438)

    def test_invalid_inputs_are_rejected(self):
        for changes in ({'points_per_cell': 0}, {'points_per_cell': True},
                        {'area_bonus_percent': -1}, {'area_bonus_percent': 1.5},
                        {'bonus_time_limit_ms': 0}, {'bonus_time_limit_ms': float('inf')}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.config, **changes)
        for cells in (0, -1, True, 100.5):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                LevelScore(self.config, cells)
        for area in (-1, 1001, True, 1.5):
            with self.subTest(area=area), self.assertRaises(ValueError):
                self.score.capture(area)
        for elapsed in (-1, 1.5, True):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                self.score.total(elapsed)
