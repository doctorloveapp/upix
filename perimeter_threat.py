"""Confini ortogonali e scossa: nessuna BFS, SDL, RNG o lettura dell'orologio."""

from bisect import bisect_right
from dataclasses import dataclass, field
import math

from collisions import AABB


@dataclass(frozen=True, slots=True)
class PerimeterRoute:
    """Contorno chiuso, compresso in segmenti assiali, in pixel logici."""

    vertices: tuple[tuple[float, float], ...]
    cumulative: tuple[float, ...] = field(init=False)

    def __post_init__(self):
        if len(self.vertices) < 4:
            raise ValueError('Contorno troppo corto')
        lengths = [0.0]
        for a, b in zip(self.vertices, self.vertices[1:] + self.vertices[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            if not all(math.isfinite(v) for v in (*a, *b)) or (dx == 0) == (dy == 0):
                raise ValueError('Il contorno richiede segmenti assiali non nulli')
            lengths.append(lengths[-1] + abs(dx) + abs(dy))
        object.__setattr__(self, 'cumulative', tuple(lengths))

    @property
    def length(self):
        return self.cumulative[-1]

    def point(self, distance):
        distance %= self.length
        index = min(bisect_right(self.cumulative, distance) - 1, len(self.vertices) - 1)
        a, b = self.vertices[index], self.vertices[(index + 1) % len(self.vertices)]
        fraction = ((distance - self.cumulative[index]) /
                    (self.cumulative[index + 1] - self.cumulative[index]))
        return a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction

    def project(self, point):
        """Punto più vicino, con parità risolta dall'ordine stabile dei segmenti."""
        best = None
        for index, a in enumerate(self.vertices):
            b = self.vertices[(index + 1) % len(self.vertices)]
            x = max(min(a[0], b[0]), min(max(a[0], b[0]), point[0]))
            y = max(min(a[1], b[1]), min(max(a[1], b[1]), point[1]))
            squared = (x - point[0]) ** 2 + (y - point[1]) ** 2
            distance = (self.cumulative[index] + abs(x - a[0]) + abs(y - a[1])) % self.length
            candidate = squared, distance
            if best is None or candidate < best:
                best = candidate
        return best  # distanza euclidea al quadrato, coordinata sul contorno

    def travel(self, start, displacement):
        """Spezza esattamente a ogni angolo, anche attraversando l'origine."""
        direction = 1 if displacement >= 0 else -1
        remaining = abs(displacement)
        distance = start % self.length
        while remaining > 0:
            if direction > 0:
                index = bisect_right(self.cumulative, distance) - 1
                available = self.cumulative[index + 1] - distance
            else:
                # Alla giunzione si imbocca il segmento precedente.
                if distance == 0:
                    distance = self.length
                index = bisect_right(self.cumulative, distance) - 1
                if self.cumulative[index] == distance:
                    index -= 1
                available = distance - self.cumulative[index]
            step = min(remaining, available)
            end = distance + direction * step
            yield self.point(distance), self.point(end)
            remaining -= step
            distance = end % self.length


def build_perimeters(cells, cell_size, filled=1, *, chunk_edges=128):
    """Generatore cooperativo: scandisce interfacce FILLED/non-FILLED.

    Un yield per colonna e ogni chunk di lati percorsi. I contorni vengono
    costruiti solo al caricamento/commit, mai nel tick fisico. Si percorrono
    lati orientati con area libera a destra; la svolta destra separa due regioni
    libere che si toccano soltanto in un vertice. Non visita regioni con BFS.
    """
    if not cells or not cells[0] or cell_size <= 0 or chunk_edges < 1:
        raise ValueError('Griglia o budget contorni non valido')
    cols, rows = len(cells), len(cells[0])
    if any(len(column) != rows for column in cells):
        raise ValueError('Griglia non rettangolare')
    edges, outgoing, seeds = {}, {}, []

    def add(a, b):
        edge = a, b
        edges[edge] = None
        seeds.append(edge)
        outgoing.setdefault(a, []).append(b)

    for x in range(cols):
        for y in range(rows):
            if cells[x][y] == filled:
                continue
            if y > 0 and cells[x][y - 1] == filled:
                add((x, y), (x + 1, y))
            if x + 1 < cols and cells[x + 1][y] == filled:
                add((x + 1, y), (x + 1, y + 1))
            if y + 1 < rows and cells[x][y + 1] == filled:
                add((x + 1, y + 1), (x, y + 1))
            if x > 0 and cells[x - 1][y] == filled:
                add((x, y + 1), (x, y))
        yield

    routes = []
    directions = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}
    turn_order = {1: 0, 0: 1, 3: 2, 2: 3}
    count = 0
    for a, b in seeds:
        # Ordine lineare stabile: non ricominciare la scansione di un dict
        # contenente molti lati cancellati dopo ogni piccola regione.
        count += 1
        if count % chunk_edges == 0:
            yield
        if (a, b) not in edges:
            continue
        start = a
        corners = [a]
        previous_direction = None
        while True:
            del edges[a, b]
            direction = directions[b[0] - a[0], b[1] - a[1]]
            if previous_direction is not None and previous_direction != direction:
                corners.append(a)
            previous_direction = direction
            count += 1
            if count % chunk_edges == 0:
                yield
            if b == start:
                break
            candidates = [end for end in outgoing.get(b, ()) if (b, end) in edges]
            if not candidates:
                raise ValueError('Confine aperto: il campo deve avere un bordo sicuro chiuso')
            end = min(candidates, key=lambda p: turn_order[
                (directions[p[0] - b[0], p[1] - b[1]] - direction) % 4])
            a, b = b, end
        # L'origine di scansione può cadere nel mezzo di un segmento.
        if (corners[-1][0] == corners[0][0] == corners[1][0]
                or corners[-1][1] == corners[0][1] == corners[1][1]):
            corners.pop(0)
        routes.append(PerimeterRoute(tuple((x * cell_size, y * cell_size) for x, y in corners)))
        yield
    return tuple(routes)


class PerimeterThreat:
    """Insegue la proiezione del player lungo un solo contorno, a tempo fisso.

    Collisioni continue per segmento assiale: nessun tunnel ai corner o con
    velocità elevate. La scelta antioraria avviene solo se strettamente più
    corta; in parità viene mantenuto il verso precedente.
    """

    def __init__(self, route, distance, *, speed_per_tick, body_size, fixed_direction=None):
        if (not math.isfinite(distance) or not math.isfinite(speed_per_tick) or speed_per_tick <= 0
                or len(body_size) != 2
                or any(not math.isfinite(v) or v <= 0 for v in body_size)):
            raise ValueError('Parametri scossa non validi')
        if fixed_direction not in (None, -1, 1):
            raise ValueError('Verso scossa non valido')
        self.route = route
        self.distance = distance % route.length
        self.speed_per_tick = speed_per_tick
        self.body_size = tuple(body_size)
        self.direction = 1
        self.fixed_direction = fixed_direction
        self.velocity = (1.0, 0.0)

    @classmethod
    def spawn(cls, routes, target, **kwargs):
        if not routes:
            return None
        candidates = []
        for index, route in enumerate(routes):
            squared, projected = route.project(target)
            candidates.append((squared, index, route, projected))
        _, _, route, projected = min(candidates)
        return cls(route, projected + route.length / 2, **kwargs)

    @property
    def position(self):
        return self.route.point(self.distance)

    @property
    def body(self):
        return AABB.from_center(*self.position, *self.body_size)

    def advance(self, target, player=None):
        if player is not None and self.body.overlaps(player):
            return True
        if self.fixed_direction is not None:
            self.direction = self.fixed_direction
            movement = min(self.speed_per_tick, self.route.length)
        else:
            projected = self.route.project(target)[1]
            forward = (projected - self.distance) % self.route.length
            backward = (self.distance - projected) % self.route.length
            if forward < backward:
                self.direction = 1
            elif backward < forward:
                self.direction = -1
            movement = min(self.speed_per_tick, forward if self.direction > 0 else backward)
        for a, b in self.route.travel(self.distance, movement * self.direction):
            dx, dy = b[0] - a[0], b[1] - a[1]
            self.velocity = (dx, dy)
            body = AABB.from_center(*a, *self.body_size)
            if player is not None and body.swept_bounds(dx, dy).overlaps(player):
                return True
        self.distance = (self.distance + movement * self.direction) % self.route.length
        return False
