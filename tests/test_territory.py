"""Conquiste pianificate senza mutazioni parziali o boss murati."""

import unittest

from collisions import AABB, CollisionGrid, PhysicsStateError
from territory import CaptureContactError, plan_capture


def board(cols=50, rows=40):
    return [[int(x < 2 or x >= cols - 2 or y < 2 or y >= rows - 2)
             for y in range(rows)] for x in range(cols)]


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.cells = board()
        self.grid = CollisionGrid(self.cells, 2)
        self.boss = AABB.from_center(20, 40, 30, 30)
        self.trail = [(30, y) for y in range(1, 39)]

    def test_plan_preserves_boss_region_and_does_not_mutate_input(self):
        before = [col[:] for col in self.cells]
        plan = plan_capture(self.grid, self.trail, self.boss)
        self.assertEqual(self.cells, before)
        self.assertIn((40, 20), plan.cells)
        self.assertNotIn((10, 20), plan.cells)
        self.assertGreater(plan.area_count, 0)
        for x, y in plan.cells:
            self.cells[x][y] = 1
        self.assertFalse(self.grid.is_blocked(self.boss))

    def test_concave_capture_keeps_full_body_free(self):
        trail = ([(35, y) for y in range(1, 21)]
                 + [(x, 20) for x in range(34, 29, -1)]
                 + [(30, y) for y in range(21, 39)])
        plan = plan_capture(self.grid, trail, self.boss)
        for x, y in plan.cells:
            self.cells[x][y] = 1
        self.assertFalse(self.grid.is_blocked(self.boss))
        self.assertEqual(self.cells[40][30], 1)

    def test_line_through_body_rejects_capture_without_writes(self):
        before = [col[:] for col in self.cells]
        with self.assertRaises(CaptureContactError):
            plan_capture(self.grid, [(10, y) for y in range(1, 39)], self.boss)
        self.assertEqual(self.cells, before)

    def test_invalid_seed_or_body_never_reaches_commit(self):
        self.cells[10][20] = 1
        before = [col[:] for col in self.cells]
        with self.assertRaises(PhysicsStateError):
            plan_capture(self.grid, self.trail, self.boss)
        self.assertEqual(self.cells, before)

    def test_invalid_trails_are_rejected_without_writes(self):
        before = [col[:] for col in self.cells]
        for trail in ([], self.trail[:-1], [self.trail[0], self.trail[5], self.trail[-1]],
                      self.trail + [self.trail[0]], [(30, -1)] + self.trail):
            with self.subTest(trail=trail), self.assertRaises(PhysicsStateError):
                plan_capture(self.grid, trail, self.boss)
        self.assertEqual(self.cells, before)
