"""Búsqueda de caminos (BFS) y línea de visión sobre la matriz del mapa."""
from collections import deque

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reachable(is_blocked, start, max_cost):
    """BFS: devuelve {casilla: (costo, padre)} para todo lo alcanzable con <= max_cost pasos."""
    result = {start: (0, None)}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        cost = result[cur][0]
        if cost >= max_cost:
            continue
        for dc, dr in DIRS:
            nxt = (cur[0] + dc, cur[1] + dr)
            if nxt in result or is_blocked(*nxt):
                continue
            result[nxt] = (cost + 1, cur)
            queue.append(nxt)
    return result


def build_path(parents, goal):
    """Reconstruye el camino (sin incluir el origen) hasta `goal`."""
    path = []
    cur = goal
    while cur is not None and parents[cur][1] is not None:
        path.append(cur)
        cur = parents[cur][1]
    path.reverse()
    return path


def line_of_sight(is_solid, a, b):
    """Bresenham entre dos casillas; la visión se corta si alguna intermedia es sólida."""
    x0, y0 = a
    x1, y1 = b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while (x, y) != (x1, y1):
        if (x, y) != (x0, y0) and is_solid(x, y):
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return True
