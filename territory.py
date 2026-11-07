"""Pianificazione della conquista, validata prima di modificare campo e canvas."""

from collections import deque
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from collisions import AABB, CollisionGrid, PhysicsStateError


class CaptureContactError(ValueError):
    """Il tracciato tocca il boss: perdita di vita, nessuna conquista."""


@dataclass(frozen=True, slots=True)
class CapturePlan:
    spans: tuple[tuple[int, int, int], ...]  # Colonna, primo y, y escluso.
    area_count: int  # Conserva il punteggio precedente, che non conta la scia.
    cell_count: int

    @property
    def cells(self) -> Iterator[tuple[int, int]]:
        """Compatibilità per query/test, senza allocare una tupla per ogni cella."""
        return ((x, y) for x, first, end in self.spans for y in range(first, end))


class CapturePlanner:
    """Pianificatore cooperativo. Il chiamante mantiene ferma la griglia.

    Ogni unità è una cella/operazione locale; niente accesso a timer o Pygame.
    Budget diversi producono lo stesso piano. Non scrive mai sulla griglia.
    """

    def __init__(self, grid: CollisionGrid, trail: Sequence[tuple[int, int]], boss: AABB):
        self._work = _capture_steps(grid, trail, boss)
        self.result: CapturePlan | None = None

    def advance(self, work_units: int) -> bool:
        if type(work_units) is not int or work_units <= 0:
            raise ValueError("Il budget di cattura deve essere un intero positivo")
        if self.result is not None:
            return True
        for _ in range(work_units):
            try:
                next(self._work)
            except StopIteration as completed:
                self.result = completed.value
                return True
        return False


def plan_capture(grid: CollisionGrid, trail: Sequence[tuple[int, int]], boss: AABB) -> CapturePlan:
    """Wrapper sincrono per strumenti e test; il runtime usa CapturePlanner."""
    planner = CapturePlanner(grid, trail, boss)
    while not planner.advance(4096):
        pass
    return planner.result


def _capture_steps(grid, trail, boss):
    if not grid.bounds.contains(boss):
        raise PhysicsStateError("Boss non valido prima della cattura")
    cols, rows = len(grid.cells), len(grid.cells[0])
    # Flag compatti: 0 libero, 1 frontiera/solido, 2 raggiungibile dal boss.
    flags = bytearray(cols * rows)
    body_cells = set()
    for x, y in grid.candidate_cells(boss):
        if boss.overlaps(grid.cell_bounds(x, y)):
            if grid.cells[x][y] == grid.solid_value:
                raise PhysicsStateError("Boss non valido prima della cattura")
            body_cells.add(x * rows + y)
        yield
    if len(trail) < 3:
        raise PhysicsStateError("Tracciato incompleto o con autointersezioni")
    touches_body = False
    for index, (x, y) in enumerate(trail):
        if not (0 <= x < cols and 0 <= y < rows):
            raise PhysicsStateError("Tracciato fuori dal campo")
        if index and abs(x - trail[index - 1][0]) + abs(y - trail[index - 1][1]) != 1:
            raise PhysicsStateError("Tracciato non continuo sulla griglia")
        is_safe = grid.cells[x][y] == grid.solid_value
        if is_safe != (index == 0 or index == len(trail) - 1):
            raise PhysicsStateError("Il tracciato deve collegare due zone sicure")
        cell = x * rows + y
        if flags[cell]:
            raise PhysicsStateError("Tracciato incompleto o con autointersezioni")
        touches_body |= cell in body_cells
        flags[cell] = 1
        yield
    if touches_body:
        raise CaptureContactError("La nuova frontiera tocca il boss")
    trail_cells = len(trail) - 2
    for x in range(cols):
        for y in range(rows):
            if grid.cells[x][y] == grid.solid_value:
                flags[x * rows + y] = 1
            yield
    seed = (int((boss.left + boss.width / 2) // grid.cell_size),
            int((boss.top + boss.height / 2) // grid.cell_size))
    if flags[seed[0] * rows + seed[1]]:
        raise PhysicsStateError("Seme BFS non libero")
    # Flood fill scanline: espande intervalli verticali e accoda solo l'inizio
    # di ogni intervallo adiacente, evitando tuple/set per 120.000 celle.
    queue = deque([seed])
    while queue:
        x, y = queue.popleft()
        offset = x * rows
        if flags[offset + y]:
            yield
            continue
        while y > 0 and not flags[offset + y - 1]:
            y -= 1
            yield
        left_open = right_open = False
        while y < rows and not flags[offset + y]:
            flags[offset + y] = 2
            left_free = x > 0 and not flags[offset - rows + y]
            right_free = x + 1 < cols and not flags[offset + rows + y]
            if left_free and not left_open:
                queue.append((x - 1, y))
            if right_free and not right_open:
                queue.append((x + 1, y))
            left_open, right_open = left_free, right_free
            y += 1
            yield
    spans = []
    count = 0
    for x in range(cols):
        first = None
        for y in range(rows):
            captured = grid.cells[x][y] != grid.solid_value and flags[x * rows + y] != 2
            if captured:
                if x * rows + y in body_cells:
                    raise PhysicsStateError("La conquista invaderebbe il corpo del boss")
                count += 1
                if first is None:
                    first = y
            elif first is not None:
                spans.append((x, first, y))
                first = None
            yield
        if first is not None:
            spans.append((x, first, rows))
    return CapturePlan(tuple(spans), count - trail_cells, count)
