"""Geometria del Passo 1A: nessuna dipendenza da display, tempo o casualità."""

import math
import random
from pathlib import Path
import subprocess
import sys
import unittest

from collisions import AABB, CollisionGrid, PhysicsStateError, move_body, move_projectile


class AABBTests(unittest.TestCase):
    def test_body_keeps_requested_dimensions_and_fractional_position(self):
        body = AABB.from_center(184.25, 100.75, 30, 30)
        self.assertEqual((body.left, body.top, body.right, body.bottom),
                         (169.25, 85.75, 199.25, 115.75))
        self.assertEqual((body.width, body.height), (30, 30))

    def test_touching_edges_and_corners_do_not_overlap(self):
        body = AABB(0, 0, 30, 30)
        for other in (AABB(30, 0, 40, 30), AABB(-10, 0, 0, 30),
                      AABB(0, 30, 30, 40), AABB(0, -10, 30, 0),
                      AABB(30, 30, 40, 40)):
            with self.subTest(other=other):
                self.assertFalse(body.overlaps(other))
                self.assertFalse(other.overlaps(body))

    def test_smallest_representable_penetration_is_not_rounded_away(self):
        body = AABB(0, 0, 30, 30)
        other = AABB(math.nextafter(30.0, 0.0), 10, 40, 20)
        self.assertTrue(body.overlaps(other))
        self.assertTrue(other.overlaps(body))

    def test_containment_allows_tangency(self):
        world = AABB(0, 0, 40, 40)
        self.assertTrue(world.contains(AABB(0, 0, 40, 40)))
        self.assertFalse(world.contains(AABB(-0.25, 0, 30, 30)))

    def test_translation_preserves_input_and_allows_negative_coordinates(self):
        body = AABB.from_center(10.25, 12.5, 30, 30)
        moved = body.translated(-2.5, 4.25)
        self.assertEqual(moved, AABB(-7.25, 1.75, 22.75, 31.75))
        self.assertEqual(body, AABB(-4.75, -2.5, 25.25, 27.5))

    def test_invalid_or_unrepresentable_bounds_are_rejected(self):
        for bounds in ((0, 0, 0, 1), (0, 0, 1, -1),
                       (math.nan, 0, 1, 1), (0, 0, math.inf, 1),
                       (-1e308, 0, 1e308, 1)):
            with self.subTest(bounds=bounds):
                with self.assertRaises(ValueError):
                    AABB(*bounds)
        for size in (0, -1, math.nan, math.inf):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    AABB.from_center(0, 0, size, 30)

    def test_non_finite_displacements_are_rejected(self):
        body = AABB(0, 0, 30, 30)
        for value in (math.nan, math.inf, -math.inf):
            for method in (body.translated, body.swept_bounds):
                with self.subTest(value=value, method=method.__name__):
                    with self.assertRaises(ValueError):
                        method(value, 0)


class CollisionGridTests(unittest.TestCase):
    def setUp(self):
        # Muro di una cella: colonna 100, intervallo fisico [200, 202).
        self.cells = [[0] * 100 for _ in range(200)]
        self.cells[100] = [1] * 100
        self.grid = CollisionGrid(self.cells, cell_size=2)

    def test_wall_200_201_detected_from_valid_start_before_center_reaches_it(self):
        start = AABB.from_center(184, 100, 30, 30)  # Fronte a x=199: libero.
        destination = start.translated(6.6, 0)
        self.assertFalse(self.grid.is_blocked(start))
        # Il vecchio test del solo centro non vedrebbe l'impatto.
        self.assertEqual(self.cells[math.floor(190.6 / 2)][50], 0)
        self.assertTrue(self.grid.is_blocked(destination))
        hits = self.grid.overlapping_solid_cells(destination)
        self.assertEqual(hits, tuple((100, y) for y in range(42, 58)))

    def test_old_center_196_case_already_penetrates_wall_with_30_pixel_body(self):
        body = AABB.from_center(196, 100, 30, 30)
        self.assertEqual(self.cells[98][50], 0)
        self.assertTrue(self.grid.is_blocked(body))
        self.assertTrue(self.grid.is_blocked(body.translated(6.6, 0)))

    def test_wall_detected_from_right_and_tangency_is_free_on_both_sides(self):
        left = AABB.from_center(185, 100, 30, 30)  # right == 200
        right = AABB.from_center(217, 100, 30, 30)  # left == 202
        for body, displacement in ((left, 0.25), (right, -0.25)):
            with self.subTest(body=body):
                self.assertFalse(self.grid.is_blocked(body))
                self.assertTrue(self.grid.is_blocked(body.translated(displacement, 0)))

    def test_horizontal_wall_uses_body_height(self):
        cells = [[0] * 150 for _ in range(100)]
        for column in cells:
            column[100] = 1
        grid = CollisionGrid(cells, 2)
        for center, displacement in ((185, 0.25), (217, -0.25)):
            with self.subTest(center=center):
                body = AABB.from_center(100, center, 30, 30)
                self.assertFalse(grid.is_blocked(body))
                self.assertTrue(grid.is_blocked(body.translated(0, displacement)))

    def test_axis_swept_bounds_find_wall_when_both_endpoints_are_free(self):
        start = AABB.from_center(170, 100, 30, 30)
        end = start.translated(60, 0)
        self.assertFalse(self.grid.is_blocked(start))
        self.assertFalse(self.grid.is_blocked(end))
        envelope = start.swept_bounds(60, 0)
        self.assertTrue(self.grid.overlapping_solid_cells(envelope))
        self.assertEqual(envelope, end.swept_bounds(-60, 0))
        self.assertEqual(start.swept_bounds(0, 0), start)

    def test_diagonal_envelope_is_only_a_conservative_candidate_query(self):
        # La cella in basso a sinistra è nell'inviluppo, fuori dal percorso.
        cells = [[0] * 6 for _ in range(6)]
        cells[0][4] = 1
        grid = CollisionGrid(cells, 1)
        body = AABB(0, 0, 1, 1)
        self.assertFalse(grid.is_blocked(body))
        self.assertFalse(grid.is_blocked(body.translated(4, 4)))
        self.assertEqual(grid.overlapping_solid_cells(body.swept_bounds(4, 4)),
                         ((0, 4),))

    def test_outside_world_is_solid_but_exact_boundary_is_allowed(self):
        world = AABB(0, 0, 8, 8)
        grid = CollisionGrid([[0] * 4 for _ in range(4)], 2)
        self.assertFalse(grid.is_blocked(world))
        for dx, dy in ((-0.25, 0), (0.25, 0), (0, -0.25), (0, 0.25)):
            with self.subTest(dx=dx, dy=dy):
                self.assertTrue(grid.is_blocked(world.translated(dx, dy)))
        outside = AABB(-100, -100, -70, -70)
        self.assertTrue(grid.is_blocked(outside))
        self.assertEqual(grid.overlapping_solid_cells(outside), ())

    def test_fractional_cell_size_row_order_and_queries_do_not_mutate_grid(self):
        cells = [[7, 0], [7, 7]]
        before = [column[:] for column in cells]
        grid = CollisionGrid(cells, 0.5, solid_value=7)
        body = AABB(0, 0, 1, 1)
        self.assertEqual(grid.overlapping_solid_cells(body), ((0, 0), (1, 0), (1, 1)))
        self.assertEqual(cells, before)
        self.assertEqual(grid.overlapping_solid_cells(body),
                         grid.overlapping_solid_cells(body))
        # La vista vede gli aggiornamenti fra query, senza una copia obsoleta.
        cells[1][1] = 0
        self.assertEqual(grid.overlapping_solid_cells(body), ((0, 0), (1, 0)))

    def test_invalid_grid_shape_and_cell_size_are_rejected(self):
        for cells in ([], [[]], [[0], [0, 0]]):
            with self.subTest(cells=cells):
                with self.assertRaises(ValueError):
                    CollisionGrid(cells, 2)
        for size in (0, -1, math.inf, math.nan):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    CollisionGrid([[0]], size)


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.cells = [[0] * 150 for _ in range(200)]
        self.cells[100] = [1] * 150  # Muro [200, 202).
        self.grid = CollisionGrid(self.cells, 2)

    def test_wall_regression_reflects_only_x_and_consumes_residual(self):
        result = move_body(self.grid, AABB.from_center(184, 100, 30, 30), 6.6, 0.75)
        self.assertAlmostEqual(result.body.left + 15, 179.4)
        self.assertAlmostEqual(result.body.top + 15, 100.75)
        self.assertTrue(result.reflected_x)
        self.assertFalse(result.reflected_y)
        self.assertEqual(result.substeps, 7)
        self.assertFalse(self.grid.is_blocked(result.body))

    def test_wall_from_right_and_high_speed_do_not_tunnel(self):
        for x, dx, expected in ((218, -6.6, 222.6), (100, 150, 120)):
            with self.subTest(x=x, dx=dx):
                result = move_body(self.grid, AABB.from_center(x, 100, 30, 30), dx, 0)
                self.assertAlmostEqual(result.body.left + 15, expected)
                self.assertTrue(result.reflected_x)
                self.assertFalse(self.grid.is_blocked(result.body))

    def test_horizontal_wall_and_corner_reflect_correct_axes(self):
        for column in self.cells:
            column[100] = 1
        result = move_body(self.grid, AABB.from_center(184, 184, 30, 30), 6.6, 6.6)
        self.assertAlmostEqual(result.body.left + 15, 179.4)
        self.assertAlmostEqual(result.body.top + 15, 179.4)
        self.assertTrue(result.reflected_x and result.reflected_y)
        self.assertFalse(self.grid.is_blocked(result.body))

    def test_parallel_motion_does_not_stick_to_tangent_wall(self):
        result = move_body(self.grid, AABB.from_center(185, 100, 30, 30), 0, 6.6)
        self.assertAlmostEqual(result.body.top + 15, 106.6)
        self.assertFalse(result.reflected_x or result.reflected_y)

    def test_world_boundaries_are_solid_and_keep_residual(self):
        result = move_body(self.grid, AABB.from_center(16, 100, 30, 30), -10, 0)
        self.assertAlmostEqual(result.body.left + 15, 24)
        self.assertTrue(result.reflected_x)

    def test_many_bounces_preserve_distance_in_narrow_corridor(self):
        grid = CollisionGrid([[0] * 50 for _ in range(18)], 2)
        result = move_body(grid, AABB.from_center(18, 50, 30, 30), 50, 0)
        self.assertAlmostEqual(result.body.left + 15, 20)
        self.assertFalse(result.reflected_x)  # Otto riflessioni.
        self.assertFalse(grid.is_blocked(result.body))

    def test_exact_fit_corridor_locks_only_constrained_axis(self):
        grid = CollisionGrid([[0] * 50 for _ in range(15)], 2)
        result = move_body(grid, AABB.from_center(15, 50, 30, 30), 1, 2)
        self.assertTrue(result.locked_x)
        self.assertFalse(result.locked_y)
        self.assertAlmostEqual(result.body.top + 15, 52)
        self.assertFalse(grid.is_blocked(result.body))

    def test_trail_between_endpoints_causes_single_early_event(self):
        result = move_body(self.grid, AABB.from_center(100, 100, 30, 30), 80, 0,
                           trail=frozenset({(70, 50)}))
        self.assertEqual(result.hit, "trail")
        self.assertAlmostEqual(result.body.right, 140)
        self.assertLess(result.substeps, 80)

    def test_wall_shields_trail_and_player_behind_it(self):
        result = move_body(self.grid, AABB.from_center(184, 100, 30, 30), 80, 0,
                           trail=frozenset({(110, 50)}), player=AABB(220, 100, 222, 102))
        self.assertIsNone(result.hit)
        self.assertFalse(self.grid.is_blocked(result.body))

    def test_player_contact_and_initial_trail_overlap_are_reported(self):
        body = AABB.from_center(100, 100, 30, 30)
        result = move_body(self.grid, body, 80, 0, player=AABB(140, 100, 142, 102))
        self.assertEqual(result.hit, "player")
        self.assertEqual(move_body(self.grid, body, 0, 0,
                                   trail=frozenset({(50, 50)})).hit, "trail")
        self.assertEqual(move_body(self.grid, body, 0, 0).body, body)

    def test_invalid_start_nonfinite_and_budget_rejected_before_mutation(self):
        before = [column[:] for column in self.cells]
        with self.assertRaises(PhysicsStateError):
            move_body(self.grid, AABB.from_center(196, 100, 30, 30), 6.6, 0)
        for dx in (4097, math.inf, math.nan):
            with self.subTest(dx=dx), self.assertRaises(ValueError):
                move_body(self.grid, AABB.from_center(100, 100, 30, 30), dx, 0)
        with self.assertRaises(ValueError):
            move_body(self.grid, AABB.from_center(100, 100, 30, 30), 1, 0, max_axis_step=2)
        self.assertEqual(self.cells, before)

    def test_repeatability_and_substep_density_reference_case(self):
        body = AABB.from_center(184, 100, 30, 30)
        first = move_body(self.grid, body, 6.6, 0.75)
        self.assertEqual(first, move_body(self.grid, body, 6.6, 0.75))
        dense = move_body(self.grid, body, 6.6, 0.75, max_axis_step=0.5)
        self.assertAlmostEqual(first.body.left, dense.body.left)
        self.assertAlmostEqual(first.body.top, dense.body.top)
        self.assertEqual(first.reflected_x, dense.reflected_x)

    def test_diagonal_graze_does_not_turn_envelope_into_a_wall(self):
        cells = [[0] * 8 for _ in range(8)]
        cells[1][4] = 1
        grid = CollisionGrid(cells, 2)
        body = AABB(2, 2, 4, 4)
        result = move_body(grid, body, 4, 4)
        self.assertEqual(result.body, body.translated(4, 4))
        self.assertFalse(result.reflected_x or result.reflected_y)

    def test_contact_at_exact_end_reflects_without_penetration(self):
        result = move_body(self.grid, AABB.from_center(184, 100, 30, 30), 1, 0)
        self.assertEqual(result.body.right, 200)
        self.assertTrue(result.reflected_x)
        self.assertFalse(self.grid.is_blocked(result.body))

    def test_seeded_sequence_preserves_body_invariant(self):
        rng = random.Random(1989)
        body = AABB.from_center(100, 150, 30, 30)
        for _ in range(100):
            result = move_body(self.grid, body, rng.uniform(-25, 25), rng.uniform(-25, 25))
            body = result.body
            self.assertFalse(self.grid.is_blocked(body))
            self.assertAlmostEqual(body.width, 30)
            self.assertAlmostEqual(body.height, 30)


class ProjectileTests(unittest.TestCase):
    def setUp(self):
        self.cells = [[0] * 150 for _ in range(200)]
        self.cells[100] = [1] * 150
        self.grid = CollisionGrid(self.cells, 2)

    def body(self, x, y):
        return AABB.from_center(x, y, 4, 4)

    def test_thin_wall_absorbs_from_both_sides_instead_of_tunnelling(self):
        for x, dx, front in ((196, 20, 200), (208, -20, 202)):
            with self.subTest(x=x):
                result = move_projectile(self.grid, self.body(x, 100), dx, 0)
                self.assertEqual(result.hit, "wall")
                self.assertAlmostEqual(result.body.right if dx > 0 else result.body.left, front)
                self.assertFalse(result.reflected_x)

    def test_high_speed_and_horizontal_wall_stop_at_first_impact(self):
        result = move_projectile(self.grid, self.body(100, 100), 250, 0)
        self.assertEqual(result.hit, "wall")
        self.assertAlmostEqual(result.body.right, 200)
        for column in self.cells:
            column[100] = 1
        result = move_projectile(self.grid, self.body(100, 100), 0, 150)
        self.assertEqual(result.hit, "wall")
        self.assertAlmostEqual(result.body.bottom, 200)

    def test_diagonal_contact_keeps_straight_trajectory(self):
        result = move_projectile(self.grid, self.body(196, 100), 6.6, 2.4)
        self.assertEqual(result.hit, "wall")
        self.assertAlmostEqual(result.body.right, 200)
        self.assertAlmostEqual(result.body.top + 2, 100 + 2 / 6.6 * 2.4)

    def test_diagonal_graze_does_not_collide_with_unused_envelope(self):
        cells = [[0] * 8 for _ in range(8)]
        cells[1][4] = 1
        body = AABB(2, 2, 4, 4)
        result = move_projectile(CollisionGrid(cells, 2), body, 4, 4)
        self.assertIsNone(result.hit)
        self.assertEqual(result.body, body.translated(4, 4))

    def test_tangent_parallel_and_away_are_free_but_towards_wall_hits(self):
        body = self.body(198, 100)
        self.assertIsNone(move_projectile(self.grid, body, 0, 5).hit)
        self.assertIsNone(move_projectile(self.grid, body, -5, 0).hit)
        self.assertEqual(move_projectile(self.grid, body, 0.1, 0).hit, "wall")

    def test_trail_or_player_before_wall_wins_and_wall_shields_behind_it(self):
        body = self.body(100, 100)
        first = move_projectile(self.grid, body, 180, 0, trail=frozenset({(80, 50)}))
        self.assertEqual(first.hit, "trail")
        self.assertAlmostEqual(first.body.right, 160)
        first = move_projectile(self.grid, body, 180, 0, player=AABB(160, 100, 162, 102))
        self.assertEqual(first.hit, "player")
        shielded = move_projectile(self.grid, body, 180, 0,
                                   trail=frozenset({(110, 50)}), player=AABB(220, 100, 222, 102))
        self.assertEqual(shielded.hit, "wall")
        tie = move_projectile(self.grid, body, 180, 0, trail=frozenset({(100, 50)}))
        self.assertEqual(tie.hit, "wall")

    def test_initial_solid_or_world_boundary_absorbs_without_physics_failure(self):
        self.assertEqual(move_projectile(self.grid, self.body(201, 100), 5, 0).hit, "wall")
        self.assertEqual(move_projectile(self.grid, self.body(-10, 100), 5, 0).hit, "wall")
        result = move_projectile(self.grid, self.body(3, 100), -20, 0)
        self.assertEqual(result.hit, "wall")
        self.assertAlmostEqual(result.body.left, 0)

    def test_zero_and_fractional_motion_are_repeatable_and_inputs_stay_unchanged(self):
        body = self.body(100, 100)
        self.assertEqual(move_projectile(self.grid, body, 0, 0).body, body)
        first = move_projectile(self.grid, body, 3.7, -1.2)
        self.assertEqual(first, move_projectile(self.grid, body, 3.7, -1.2))
        self.assertAlmostEqual(first.body.left, body.left + 3.7)
        self.assertAlmostEqual(first.body.top, body.top - 1.2)
        self.assertEqual(body, self.body(100, 100))
        for value in (math.inf, math.nan, 4097):
            with self.subTest(value=value), self.assertRaises(ValueError):
                move_projectile(self.grid, body, value, 0)


class IndependenceTests(unittest.TestCase):
    def test_collision_module_imports_without_pygame(self):
        result = subprocess.run(
            [sys.executable, "-c", "import collisions, sys; "
             "assert 'pygame' not in sys.modules"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
