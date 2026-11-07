"""Geometria float e interrogazioni della griglia, senza dipendenze da Pygame.

Geometria e solver a substep. Il modulo restituisce nuovi valori senza mutare
entità o griglia, e non legge orologi, input o generatori casuali.
"""

from collections.abc import Sequence
from dataclasses import dataclass
import math

MAX_SUBSTEPS_PER_TICK = 4096
MAX_CONTACTS_PER_AXIS_STEP = 4096


def _require_finite(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Le coordinate e le dimensioni devono essere finite")


@dataclass(frozen=True, slots=True)
class AABB:
    """Rettangolo [left, right) × [top, bottom) con estensione positiva.

    Una tangenza fra bordi non è sovrapposizione. Nessun arrotondamento o epsilon
    viene applicato alla geometria della simulazione.
    """

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        _require_finite(self.left, self.top, self.right, self.bottom,
                        self.width, self.height)
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Un'AABB deve avere larghezza e altezza positive")

    @classmethod
    def from_center(cls, x: float, y: float, width: float, height: float) -> "AABB":
        _require_finite(x, y, width, height)
        if width <= 0 or height <= 0:
            raise ValueError("Larghezza e altezza devono essere positive")
        return cls(x - width / 2, y - height / 2,
                   x + width / 2, y + height / 2)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def overlaps(self, other: "AABB") -> bool:
        return (self.left < other.right and other.left < self.right
                and self.top < other.bottom and other.top < self.bottom)

    def contains(self, other: "AABB") -> bool:
        """Contenimento inclusivo ai bordi: il corpo può essere tangente."""
        return (self.left <= other.left and other.right <= self.right
                and self.top <= other.top and other.bottom <= self.bottom)

    def translated(self, dx: float, dy: float) -> "AABB":
        _require_finite(dx, dy)
        return AABB(self.left + dx, self.top + dy,
                    self.right + dx, self.bottom + dy)

    def swept_bounds(self, dx: float, dy: float) -> "AABB":
        """Inviluppo conservativo del percorso, non un test di impatto continuo.

        Sui movimenti per un solo asse copre esattamente il volume attraversato.
        In diagonale può includere celle mai toccate: il futuro solver deve
        calcolare il primo contatto, non interpretare l'inviluppo come un urto.
        """
        destination = self.translated(dx, dy)
        return AABB(min(self.left, destination.left),
                    min(self.top, destination.top),
                    max(self.right, destination.right),
                    max(self.bottom, destination.bottom))


@dataclass(frozen=True, slots=True)
class CollisionGrid:
    """Vista di sola lettura su una griglia rettangolare cells[x][y].

    Il chiamante conserva la proprietà dei dati: celle aggiornabili fra query,
    forma invariata per la durata della vista, nessuna mutazione durante una
    query. Le celle con valore solid_value sono solide; l'esterno è bloccato.
    Le celle candidate vengono esaminate per riga, poi per colonna.
    """

    cells: Sequence[Sequence[int]]
    cell_size: float
    solid_value: int = 1

    def __post_init__(self) -> None:
        _require_finite(self.cell_size)
        if self.cell_size <= 0:
            raise ValueError("cell_size deve essere positivo")
        if not self.cells or not self.cells[0]:
            raise ValueError("La griglia non può essere vuota")
        if any(len(column) != len(self.cells[0]) for column in self.cells):
            raise ValueError("La griglia deve essere rettangolare")
        # Valida anche che le dimensioni fisiche siano rappresentabili.
        _require_finite(len(self.cells) * self.cell_size,
                        len(self.cells[0]) * self.cell_size)

    @property
    def bounds(self) -> AABB:
        return AABB(0.0, 0.0, len(self.cells) * self.cell_size,
                    len(self.cells[0]) * self.cell_size)

    def overlapping_solid_cells(self, body: AABB) -> tuple[tuple[int, int], ...]:
        """Celle solide interne che penetrano il corpo, in ordine stabile.

        L'esterno non è una cella enumerabile: usare is_blocked per includere
        il controllo dei confini. Il clipping precede la divisione in celle.
        """
        hits = []
        for x, y in self.candidate_cells(body):
            if self.cells[x][y] == self.solid_value and body.overlaps(self.cell_bounds(x, y)):
                hits.append((x, y))
        return tuple(hits)

    def cell_bounds(self, x: int, y: int) -> AABB:
        return AABB(x * self.cell_size, y * self.cell_size,
                    (x + 1) * self.cell_size, (y + 1) * self.cell_size)

    def candidate_cells(self, bounds: AABB, *, touching: bool = False):
        """Broad phase locale, con bordi inclusivi per i contatti del solver."""
        world = self.bounds
        left, top = max(bounds.left, 0), max(bounds.top, 0)
        right, bottom = min(bounds.right, world.right), min(bounds.bottom, world.bottom)
        if left > right or top > bottom:
            return
        if touching:
            first_x, first_y = math.ceil(left / self.cell_size) - 1, math.ceil(top / self.cell_size) - 1
            last_x, last_y = math.floor(right / self.cell_size), math.floor(bottom / self.cell_size)
        else:
            first_x, first_y = math.floor(left / self.cell_size), math.floor(top / self.cell_size)
            last_x, last_y = math.ceil(right / self.cell_size) - 1, math.ceil(bottom / self.cell_size) - 1
        for y in range(max(0, first_y), min(len(self.cells[0]) - 1, last_y) + 1):
            for x in range(max(0, first_x), min(len(self.cells) - 1, last_x) + 1):
                yield x, y

    def is_blocked(self, body: AABB) -> bool:
        return (not self.bounds.contains(body)
                or bool(self.overlapping_solid_cells(body)))


class PhysicsStateError(ValueError):
    """Stato invalido o lavoro non rappresentabile: non accettare un movimento."""


@dataclass(frozen=True, slots=True)
class MotionResult:
    body: AABB
    reflected_x: bool = False
    reflected_y: bool = False
    locked_x: bool = False
    locked_y: bool = False
    hit: str | None = None
    substeps: int = 0


@dataclass(frozen=True, slots=True)
class _Contact:
    distance: float
    kind: str
    face: float


def _axis_contact(body: AABB, obstacle: AABB, axis: int, delta: float,
                  kind: str) -> _Contact | None:
    if axis == 0:
        transverse_overlap = body.top < obstacle.bottom and obstacle.top < body.bottom
        front, face = ((body.right, obstacle.left) if delta > 0
                       else (body.left, obstacle.right))
    else:
        transverse_overlap = body.left < obstacle.right and obstacle.left < body.right
        front, face = ((body.bottom, obstacle.top) if delta > 0
                       else (body.top, obstacle.bottom))
    distance = face - front if delta > 0 else front - face
    if transverse_overlap and 0 <= distance <= abs(delta):
        return _Contact(distance, kind, face)
    return None


def _first_axis_contact(grid: CollisionGrid, body: AABB, axis: int, delta: float,
                        trail: frozenset[tuple[int, int]], player: AABB | None) -> _Contact | None:
    world = grid.bounds
    if axis == 0:
        distance, face = ((world.right - body.right, world.right) if delta > 0
                          else (body.left, 0.0))
    else:
        distance, face = ((world.bottom - body.bottom, world.bottom) if delta > 0
                          else (body.top, 0.0))
    best = _Contact(distance, "wall", face) if distance <= abs(delta) else None
    priority = {"wall": 0, "trail": 1, "player": 2}

    def consider(contact):
        nonlocal best
        if contact is not None and (best is None or
                (contact.distance, priority[contact.kind]) < (best.distance, priority[best.kind])):
            best = contact

    envelope = body.swept_bounds(delta if axis == 0 else 0, delta if axis == 1 else 0)
    for x, y in grid.candidate_cells(envelope, touching=True):
        solid = grid.cells[x][y] == grid.solid_value
        if solid or (x, y) in trail:
            consider(_axis_contact(body, grid.cell_bounds(x, y), axis, delta,
                                   "wall" if solid else "trail"))
    if player is not None:
        consider(_axis_contact(body, player, axis, delta, "player"))
    return best


def _at_contact(body: AABB, axis: int, positive: bool, face: float) -> AABB:
    # Il bordo di contatto è esatto: niente epsilon che potrebbe saltare celle.
    if axis == 0:
        return AABB(face - body.width if positive else face, body.top,
                    face if positive else face + body.width, body.bottom)
    return AABB(body.left, face - body.height if positive else face,
                body.right, face if positive else face + body.height)


def _move_axis(grid: CollisionGrid, body: AABB, axis: int, delta: float,
               trail: frozenset[tuple[int, int]], player: AABB | None
               ) -> tuple[AABB, bool, bool, str | None]:
    remaining, positive, reflected = abs(delta), delta > 0, False
    contacts = 0
    while remaining > 0:
        signed = remaining if positive else -remaining
        contact = _first_axis_contact(grid, body, axis, signed, trail, player)
        if contact is None:
            return body.translated(signed if axis == 0 else 0,
                                   signed if axis == 1 else 0), reflected, False, None
        body = _at_contact(body, axis, positive, contact.face)
        if contact.kind != "wall":
            return body, reflected, False, contact.kind
        remaining -= contact.distance
        positive = not positive
        reflected = not reflected
        contacts += 1
        if remaining > 0 and contact.distance == 0:
            opposite = _first_axis_contact(grid, body, axis,
                                           remaining if positive else -remaining, trail, player)
            if opposite is not None and opposite.kind == "wall" and opposite.distance == 0:
                # Corridoio esattamente largo quanto il corpo: asse vincolato.
                return body, reflected, True, None
        if contacts > MAX_CONTACTS_PER_AXIS_STEP:
            raise PhysicsStateError("Troppi contatti nello stesso substep")
    return body, reflected, False, None


def _substep_count(grid: CollisionGrid, body: AABB, dx: float, dy: float,
                    max_axis_step: float | None = None) -> int:
    """Unico contratto di validazione e budget per boss e proiettili."""
    _require_finite(dx, dy)
    body.translated(dx, dy)
    step = grid.cell_size / 2 if max_axis_step is None else max_axis_step
    _require_finite(step)
    if not 0 < step <= grid.cell_size / 2:
        raise ValueError("Il substep deve essere positivo e <= metà cella")
    ratio = max(abs(dx), abs(dy)) / step
    if not math.isfinite(ratio) or ratio > MAX_SUBSTEPS_PER_TICK:
        raise PhysicsStateError(f"Spostamento oltre il budget di {MAX_SUBSTEPS_PER_TICK} substep")
    return max(1, math.ceil(ratio))


def move_body(grid: CollisionGrid, body: AABB, dx: float, dy: float, *,
              trail: frozenset[tuple[int, int]] = frozenset(), player: AABB | None = None,
              max_axis_step: float | None = None) -> MotionResult:
    """Movimento per tick, X poi Y; restituisce posizione e riflessioni.

    Scansione del percorso su ogni asse, residuo consumato dopo il rimbalzo.
    Un asse senza spazio di manovra viene bloccato esplicitamente. Non altera
    griglia, scia, velocità del chiamante o vite. Input invalidi non vengono
    corretti con teletrasporti. I limiti di lavoro rifiutano il tick intero.
    """
    count = _substep_count(grid, body, dx, dy, max_axis_step)
    if grid.is_blocked(body):
        raise PhysicsStateError("Il corpo iniziale interseca terreno solido o confini")
    if any((x, y) in trail and grid.cells[x][y] != grid.solid_value
           and body.overlaps(grid.cell_bounds(x, y)) for x, y in grid.candidate_cells(body)):
        return MotionResult(body, hit="trail")
    if player is not None and body.overlaps(player):
        return MotionResult(body, hit="player")

    motion = [dx, dy]
    reflected, locked = [False, False], [False, False]
    for index in range(count):
        for axis in (0, 1):
            if motion[axis] == 0:
                continue
            body, bounce, lock, hit = _move_axis(grid, body, axis, motion[axis] / count, trail, player)
            reflected[axis] ^= bounce
            locked[axis] |= lock
            if lock:
                motion[axis] = 0
            elif bounce:
                motion[axis] *= -1
            if hit is not None:
                return MotionResult(body, reflected_x=reflected[0], reflected_y=reflected[1],
                                    locked_x=locked[0], locked_y=locked[1],
                                    hit=hit, substeps=index + 1)
    if grid.is_blocked(body):
        raise PhysicsStateError("Il movimento ha prodotto una penetrazione")
    return MotionResult(body, reflected_x=reflected[0], reflected_y=reflected[1],
                        locked_x=locked[0], locked_y=locked[1], substeps=count)


def _sweep_fraction(body: AABB, obstacle: AABB, dx: float, dy: float) -> float | None:
    """Primo contatto sul segmento rettilineo, tramite intervalli su entrambi gli assi."""
    entry, exit_time = -math.inf, math.inf
    for start, end, near, far, delta in (
            (body.left, body.right, obstacle.left, obstacle.right, dx),
            (body.top, body.bottom, obstacle.top, obstacle.bottom, dy)):
        if delta == 0:
            if end <= near or start >= far:
                return None
            continue
        first, last = (near - end) / delta, (far - start) / delta
        entry = max(entry, min(first, last))
        exit_time = min(exit_time, max(first, last))
    # Un punto di sola tangenza o un contatto da cui ci si allontana non penetra.
    if entry <= 1 and exit_time > max(entry, 0):
        return max(entry, 0)
    return None


def move_projectile(grid: CollisionGrid, body: AABB, dx: float, dy: float, *,
                    trail: frozenset[tuple[int, int]] = frozenset(),
                    player: AABB | None = None) -> MotionResult:
    """Proiettile AABB: substep rettilinei e assorbimento al primo impatto.

    Condivide griglia, geometria e limiti del solver del boss. Non rimbalza:
    hit='wall' assorbe il proiettile, trail/player produce un evento al chiamante.
    Il percorso diagonale è verificato geometricamente, non con il solo inviluppo.
    """
    count = _substep_count(grid, body, dx, dy)
    # Può essere nato dentro una zona appena conquistata: viene assorbito.
    if grid.is_blocked(body):
        return MotionResult(body, hit="wall")
    for x, y in grid.candidate_cells(body):
        if (x, y) in trail and body.overlaps(grid.cell_bounds(x, y)):
            return MotionResult(body, hit="trail")
    if player is not None and body.overlaps(player):
        return MotionResult(body, hit="player")

    sx, sy = dx / count, dy / count
    priority = {"wall": 0, "trail": 1, "player": 2}
    world = grid.bounds
    for index in range(count):
        best_fraction, best_kind = math.inf, None

        def consider(fraction: float | None, kind: str) -> None:
            nonlocal best_fraction, best_kind
            if fraction is not None and (best_kind is None or
                    (fraction, priority[kind]) < (best_fraction, priority[best_kind])):
                best_fraction, best_kind = fraction, kind

        for delta, front, boundary in (
                (sx, body.right if sx > 0 else body.left, world.right if sx > 0 else 0),
                (sy, body.bottom if sy > 0 else body.top, world.bottom if sy > 0 else 0)):
            if delta:
                fraction = (boundary - front) / delta
                if 0 <= fraction <= 1:
                    consider(fraction, "wall")
        for x, y in grid.candidate_cells(body.swept_bounds(sx, sy), touching=True):
            solid = grid.cells[x][y] == grid.solid_value
            if solid or (x, y) in trail:
                consider(_sweep_fraction(body, grid.cell_bounds(x, y), sx, sy),
                         "wall" if solid else "trail")
        if player is not None:
            consider(_sweep_fraction(body, player, sx, sy), "player")
        if best_kind is not None:
            return MotionResult(body.translated(sx * best_fraction, sy * best_fraction),
                                hit=best_kind, substeps=index + 1)
        body = body.translated(sx, sy)
    if grid.is_blocked(body):
        raise PhysicsStateError("Il proiettile ha attraversato terreno solido")
    return MotionResult(body, substeps=count)
