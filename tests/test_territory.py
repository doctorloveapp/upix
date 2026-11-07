"""Conquiste pianificate senza mutazioni parziali o boss murati."""

import unittest
from collections import deque
import random

from collisions import AABB, CollisionGrid, PhysicsStateError
from territory import CaptureContactError, CapturePlanner, plan_capture


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

    def test_chunk_sizes_produce_identical_plans_without_any_grid_writes(self):
        before = [column[:] for column in self.cells]
        reference = plan_capture(self.grid, self.trail, self.boss)
        for budget in (1, 17, 128, 4096):
            planner = CapturePlanner(self.grid, self.trail, self.boss)
            frames = 1
            while not planner.advance(budget):
                frames += 1
                self.assertEqual(self.cells, before)
            self.assertEqual(planner.result, reference)
            self.assertEqual(planner.result.cell_count, len(list(planner.result.cells)))
            self.assertEqual(self.cells, before)
            if budget == 1:
                self.assertGreater(frames, 100)

    def test_scanline_matches_independent_bfs_on_seeded_fragmented_boards(self):
        rng = random.Random(1989)
        for case in range(25):
            cells = board()
            for x in range(2, 48):
                for y in range(2, 38):
                    if x != 30 and (x, y) != (10, 20) and rng.random() < 0.15:
                        cells[x][y] = 1
            grid = CollisionGrid(cells, 2)
            boss = AABB.from_center(21, 41, 2, 2)
            wall = set(self.trail)
            reached = {(10, 20)}
            queue = deque(reached)
            while queue:
                x, y = queue.popleft()
                for cell in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                    nx, ny = cell
                    if (0 <= nx < 50 and 0 <= ny < 40 and not cells[nx][ny]
                            and cell not in wall and cell not in reached):
                        reached.add(cell)
                        queue.append(cell)
            expected = {(x, y) for x in range(50) for y in range(40)
                        if not cells[x][y] and (x, y) not in reached}
            plan = plan_capture(grid, self.trail, boss)
            with self.subTest(case=case):
                self.assertEqual(set(plan.cells), expected)
                self.assertEqual(plan.area_count, len(expected - wall))

    def test_chunk_budget_must_be_positive_integer(self):
        planner = CapturePlanner(self.grid, self.trail, self.boss)
        for budget in (0, -1, 1.5, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                planner.advance(budget)
