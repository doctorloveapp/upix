"""Contorni e collisioni della scossa senza Pygame e senza timer reali."""

import unittest
from collections import Counter
import random

from collisions import AABB
from perimeter_threat import PerimeterRoute, PerimeterThreat, build_perimeters


def finish(builder):
    while True:
        try:
            next(builder)
        except StopIteration as done:
            return done.value


def bordered(cols, rows):
    return [[int(x in (0, cols - 1) or y in (0, rows - 1))
             for y in range(rows)] for x in range(cols)]


class PerimeterTests(unittest.TestCase):
    def setUp(self):
        self.square = PerimeterRoute(((0, 0), (20, 0), (20, 20), (0, 20)))

    def test_initial_border_compresses_to_four_segments(self):
        routes = finish(build_perimeters(bordered(12, 10), 2))
        self.assertEqual(len(routes), 1)
        self.assertEqual(len(routes[0].vertices), 4)
        self.assertEqual(set(routes[0].vertices), {(2, 2), (22, 2), (22, 18), (2, 18)})
        self.assertEqual(routes[0].length, 72)

    def test_captured_region_changes_route_without_crossing_safe_interior(self):
        cells = bordered(10, 10)
        for x in range(1, 5):
            for y in range(5, 9):
                cells[x][y] = 1
        route, = finish(build_perimeters(cells, 1))
        self.assertEqual(len(route.vertices), 6)
        self.assertIn((5, 5), route.vertices)
        self.assertEqual(route.project((2, 7))[0], 4)  # bordo y=5, non taglio interno
        self.assertEqual(route.length, 32)

    def test_diagonal_regions_have_distinct_closed_routes_and_stable_order(self):
        cells = [[1] * 4 for _ in range(4)]
        cells[1][1] = cells[2][2] = 0
        first = finish(build_perimeters(cells, 2, chunk_edges=1))
        second = finish(build_perimeters(cells, 2, chunk_edges=128))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        self.assertEqual([r.length for r in first], [8, 8])

    def test_safe_island_keeps_both_boundaries_and_spawn_chooses_nearest(self):
        cells = bordered(12, 12)
        for x in (5, 6):
            for y in (5, 6):
                cells[x][y] = 1
        routes = finish(build_perimeters(cells, 1))
        self.assertEqual(len(routes), 2)
        threat = PerimeterThreat.spawn(routes, (5.5, 5), speed_per_tick=1, body_size=(2, 2))
        self.assertEqual(threat.route.length, 8)
        self.assertIsNone(PerimeterThreat.spawn((), (0, 0), speed_per_tick=1, body_size=(2, 2)))

    def test_empty_boundary_and_invalid_open_boundary(self):
        self.assertEqual(finish(build_perimeters([[1] * 3 for _ in range(3)], 1)), ())
        with self.assertRaises(ValueError):
            finish(build_perimeters([[1, 0], [0, 0]], 1))

    def test_builder_yields_before_result_and_does_not_mutate_grid(self):
        cells = bordered(40, 30)
        original = [column.copy() for column in cells]
        builder = build_perimeters(cells, 2)
        for _ in range(40):
            self.assertIsNone(next(builder))
        self.assertEqual(len(finish(builder)), 1)
        self.assertEqual(cells, original)

    def test_fragmented_contours_cover_each_boundary_edge_exactly_once(self):
        rng = random.Random(1989)
        for _ in range(25):
            cells = bordered(15, 12)
            for x in range(1, 14):
                for y in range(1, 11):
                    cells[x][y] = int(rng.random() < .4)
            expected = Counter()
            for x in range(1, 14):
                for y in range(1, 11):
                    if cells[x][y]:
                        continue
                    for neighbor, a, b in (
                            ((x, y - 1), (x, y), (x + 1, y)),
                            ((x + 1, y), (x + 1, y), (x + 1, y + 1)),
                            ((x, y + 1), (x + 1, y + 1), (x, y + 1)),
                            ((x - 1, y), (x, y + 1), (x, y))):
                        if cells[neighbor[0]][neighbor[1]]:
                            expected[a, b] += 1
            actual = Counter()
            for route in finish(build_perimeters(cells, 2)):
                vertices = tuple((int(x / 2), int(y / 2)) for x, y in route.vertices)
                for a, b in zip(vertices, vertices[1:] + vertices[:1]):
                    dx = (b[0] > a[0]) - (b[0] < a[0])
                    dy = (b[1] > a[1]) - (b[1] < a[1])
                    while a != b:
                        end = a[0] + dx, a[1] + dy
                        actual[a, end] += 1
                        a = end
            self.assertEqual(actual, expected)

    def test_spawn_is_antipodal_and_shortest_pursuit_stays_on_segments(self):
        threat = PerimeterThreat.spawn((self.square,), (10, 0),
                                       speed_per_tick=3, body_size=(2, 2))
        self.assertEqual(threat.position, (10, 20))
        self.assertFalse(threat.advance((10, 0)))
        self.assertEqual(threat.position, (7, 20))  # parità: verso iniziale positivo
        self.assertFalse(threat.advance((20, 20)))
        self.assertEqual(threat.position, (10, 20))  # cambio verso più breve

    def test_collision_sweeps_all_segments_at_high_speed(self):
        threat = PerimeterThreat(self.square, 18, speed_per_tick=50, body_size=(2, 2))
        player = AABB(19, 6, 21, 8)
        self.assertTrue(threat.advance((20, 10), player))
        # Nessun falso urto nella diagonale che NON è stata percorsa.
        self.assertFalse(threat.advance((20, 10), AABB(14, 4, 16, 6)))
        self.assertEqual(threat.position, (20, 10))

    def test_reverse_crosses_origin_and_detects_border_player(self):
        threat = PerimeterThreat(self.square, 2, speed_per_tick=20, body_size=(2, 2))
        self.assertTrue(threat.advance((0, 10), AABB(-1, 5, 1, 7)))
        self.assertFalse(threat.advance((0, 10)))
        self.assertEqual(threat.position, (0, 10))
        self.assertEqual(threat.direction, -1)

    def test_initial_overlap_and_player_away_from_border(self):
        threat = PerimeterThreat(self.square, 10, speed_per_tick=3, body_size=(2, 2))
        self.assertTrue(threat.advance((10, 0), AABB(9, 0, 11, 2)))
        self.assertFalse(threat.advance((10, 10), AABB(9, 9, 11, 11)))
        self.assertEqual(threat.position, (10, 0))  # niente scorciatoie nell'interno

    def test_invalid_geometry_and_parameters(self):
        for vertices in (((0, 0), (1, 1), (2, 0), (1, -1)), ((0, 0),) * 4):
            with self.assertRaises(ValueError):
                PerimeterRoute(vertices)
        for speed in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                PerimeterThreat(self.square, 0, speed_per_tick=speed, body_size=(2, 2))


if __name__ == '__main__':
    unittest.main()
