"""Pianificazione della conquista, validata prima di modificare campo e canvas."""

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from collisions import AABB, CollisionGrid, PhysicsStateError


class CaptureContactError(ValueError):
    """Il tracciato tocca il boss: perdita di vita, nessuna conquista."""


@dataclass(frozen=True, slots=True)
class CapturePlan:
    cells: tuple[tuple[int, int], ...]
    area_count: int  # Conserva il punteggio precedente, che non conta la scia.


def plan_capture(grid: CollisionGrid, trail: Sequence[tuple[int, int]], boss: AABB) -> CapturePlan:
    """BFS inversa senza scritture, con corpo e seme necessariamente validi."""
    if grid.is_blocked(boss):
        raise PhysicsStateError("Boss non valido prima della cattura")
    cols, rows = len(grid.cells), len(grid.cells[0])
    if len(trail) < 3 or len(set(trail)) != len(trail):
        raise PhysicsStateError("Tracciato incompleto o con autointersezioni")
    for index, (x, y) in enumerate(trail):
        if not (0 <= x < cols and 0 <= y < rows):
            raise PhysicsStateError("Tracciato fuori dal campo")
        if index and abs(x - trail[index - 1][0]) + abs(y - trail[index - 1][1]) != 1:
            raise PhysicsStateError("Tracciato non continuo sulla griglia")
        is_safe = grid.cells[x][y] == grid.solid_value
        if is_safe != (index == 0 or index == len(trail) - 1):
            raise PhysicsStateError("Il tracciato deve collegare due zone sicure")
    wall = frozenset(trail)
    body_cells = frozenset(cell for cell in grid.candidate_cells(boss)
                           if boss.overlaps(grid.cell_bounds(*cell)))
    if body_cells & wall:
        raise CaptureContactError("La nuova frontiera tocca il boss")
    seed = (int((boss.left + boss.width / 2) // grid.cell_size),
            int((boss.top + boss.height / 2) // grid.cell_size))
    if grid.cells[seed[0]][seed[1]] == grid.solid_value or seed in wall:
        raise PhysicsStateError("Seme BFS non libero")
    visited = {seed}
    queue = deque([seed])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (0 <= nx < cols and 0 <= ny < rows
                    and grid.cells[nx][ny] != grid.solid_value
                    and (nx, ny) not in wall and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append((nx, ny))
    captured = []
    area_count = 0
    for x in range(cols):
        for y in range(rows):
            if grid.cells[x][y] != grid.solid_value and (x, y) not in visited:
                if (x, y) in body_cells:
                    raise PhysicsStateError("La conquista invaderebbe il corpo del boss")
                captured.append((x, y))
                area_count += (x, y) not in wall
    return CapturePlan(tuple(captured), area_count)
