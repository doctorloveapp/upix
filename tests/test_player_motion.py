"""Il solver del player non salta celle interne conquistate; AABB completa."""

import unittest

from collisions import AABB, CollisionGrid, move_player, player_cell_allowed, swept_contact


class PlayerMotionTests(unittest.TestCase):
    def setUp(self):
        cells = [[0] * 12 for _ in range(16)]
        for x in range(16):
            for y in range(12):
                if x in (0, 15) or y in (0, 11) or (5 <= x <= 9 and 3 <= y <= 8):
                    cells[x][y] = 1
        self.grid = CollisionGrid(cells, 2)

    def test_frontier_and_outer_border_allowed_interior_forbidden(self):
        self.assertTrue(player_cell_allowed(self.grid, 5, 5))
        self.assertFalse(player_cell_allowed(self.grid, 6, 5))
        self.assertTrue(player_cell_allowed(self.grid, 0, 5))
        self.assertTrue(player_cell_allowed(self.grid, 4, 5))

    def test_fast_motion_stops_before_one_cell_deep_interior(self):
        result = move_player(self.grid, (3, 5), (26, 30), 10, 0)
        self.assertEqual(result.cells, ((4, 5), (5, 5)))
        self.assertTrue(result.blocked)
        self.assertEqual((result.body.width, result.body.height), (26, 30))
        self.assertEqual((result.body.left + 13, result.body.top + 15), (11, 11))

    def test_movement_along_frontier_and_into_free_space(self):
        result = move_player(self.grid, (5, 3), (26, 30), 0, 5)
        self.assertFalse(result.blocked)
        self.assertEqual(result.cells[-1], (5, 8))
        result = move_player(self.grid, (5, 5), (26, 30), -4, 0)
        self.assertEqual(result.cells[-1], (1, 5))

    def test_swept_full_sprite_detects_thin_obstacle_between_endpoints(self):
        body = AABB.from_center(20, 20, 26, 30)
        self.assertTrue(swept_contact(body, AABB(45, 10, 46, 30), 50, 0))
        self.assertFalse(swept_contact(body, AABB(45, 40, 46, 50), 50, 0))

    def test_safe_frontier_turns_around_corner_without_entering_free_field(self):
        cells = [[1] * 9 for _ in range(9)]
        for x in range(3, 6):
            for y in range(3, 6): cells[x][y] = 0
        grid = CollisionGrid(cells, 2)
        first = move_player(grid, (2, 3), (26, 30), 0, -1)
        self.assertEqual(first.cells, ((2, 2),))
        second = move_player(grid, first.cells[-1], (26, 30), 1, 0)
        self.assertEqual(second.cells, ((3, 2),))
        self.assertFalse(player_cell_allowed(grid, 1, 2))
        self.assertFalse(player_cell_allowed(grid, 0, 4))  # cornice profonda non navigabile

    def test_invalid_diagonal_or_start_inside_capture_is_rejected(self):
        for cell, dx, dy in (((4, 5), 1, 1), ((6, 5), 1, 0)):
            with self.assertRaises(ValueError):
                move_player(self.grid, cell, (26, 30), dx, dy)
