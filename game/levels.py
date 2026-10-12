"""
Niveles del juego. Cada mapa es una matriz de texto:

    #  muro            c  caja          b  barril       k  cactus      r  roca
    .  arena           :  tierra        +  suelo agrietado             =  concreto
    P  jugador         p  poción
    R  Saqueador (cuerpo a cuerpo)      G  Pistolero (a distancia)
    B  Bruto (pesado)                   W  Caudillo (jefe)
"""
from dataclasses import dataclass, field

BLOCKS = {"#": "wall", "c": "crate", "b": "barrel", "k": "cactus", "r": "rock"}
FLOORS = {":": "dirt", "+": "cracked", "=": "concrete"}
ENEMY_CODES = {"R": "raider", "G": "gunner", "B": "brute", "W": "warlord"}

LEVEL_DATA = [
    dict(name="Las Afueras", hint="Un puñado de saqueadores merodea la entrada del yermo.", rows=[
        "##############",
        "#P...:::.....#",
        "#..c...:..k..#",
        "#....##...r..#",
        "#.k..#.....R.#",
        "#....#..c....#",
        "#..:.....#...#",
        "#.r......#.G.#",
        "#..p..R..#...#",
        "#...c....==..#",
        "#.k.....b=p..#",
        "##############",
    ]),
    dict(name="Ruinas del Peaje", hint="Hay pistoleros apostados entre las ruinas. Usá las coberturas.", rows=[
        "################",
        "#P..:.....c....#",
        "#...:..##..b.R.#",
        "#.k.:..#.....k.#",
        "#..c...#...==..#",
        "#......#...=G..#",
        "#.r..==...##...#",
        "#....=....#..r.#",
        "#.p..=..c.....B#",
        "#.....##..:....#",
        "#..k..#...:.G..#",
        "#.b...#.p.:..R.#",
        "################",
    ]),
    dict(name="Fortín del Caudillo", hint="El Caudillo y su banda te esperan. Es ahora o nunca.", rows=[
        "################",
        "#P.....:::.....#",
        "#.k..c.....c.k.#",
        "#....##...##...#",
        "#..r.#..W..#.r.#",
        "#....#.....#...#",
        "#.p.....G.....p#",
        "#..:::.....:::.#",
        "#....#.....#...#",
        "#.b..#.R.R.#.b.#",
        "#....##...##...#",
        "#.k..c.....c.k.#",
        "#.....G.p..p...#",
        "################",
    ]),
]


@dataclass
class Level:
    index: int
    name: str
    hint: str
    cols: int
    rows: int
    floor: list = field(default_factory=list)      # floor[row][col] -> nombre de tile
    blocks: list = field(default_factory=list)     # blocks[row][col] -> nombre o None
    solid: list = field(default_factory=list)      # solid[row][col] -> bool (matriz de colisión)
    player_start: tuple = (1, 1)
    enemies: list = field(default_factory=list)    # (tipo, col, fila)
    potions: list = field(default_factory=list)    # (col, fila)

    def in_bounds(self, c, r):
        return 0 <= c < self.cols and 0 <= r < self.rows

    def is_solid(self, c, r):
        return (not self.in_bounds(c, r)) or self.solid[r][c]


def parse_level(index):
    data = LEVEL_DATA[index]
    rows = data["rows"]
    width = len(rows[0])
    for r, line in enumerate(rows):
        if len(line) != width:
            raise ValueError(f"Nivel {index + 1}: la fila {r} mide {len(line)} y debería medir {width}")
    lv = Level(index, data["name"], data["hint"], width, len(rows))
    for r, line in enumerate(rows):
        frow, brow, srow = [], [], []
        for c, ch in enumerate(line):
            floor = FLOORS.get(ch, f"sand_{(c * 7 + r * 13 + c * r) % 4}")
            block = BLOCKS.get(ch)
            frow.append(floor)
            brow.append(block)
            srow.append(block is not None)
            if ch == "P":
                lv.player_start = (c, r)
            elif ch in ENEMY_CODES:
                lv.enemies.append((ENEMY_CODES[ch], c, r))
            elif ch == "p":
                lv.potions.append((c, r))
        lv.floor.append(frow)
        lv.blocks.append(brow)
        lv.solid.append(srow)
    return lv


def level_count():
    return len(LEVEL_DATA)
