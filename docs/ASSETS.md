# Lista de assets y fuentes

**Todos los assets de este proyecto fueron generados por código** con [`tools/generate_assets.py`](../tools/generate_assets.py) (usando solo `pygame` y la librería estándar de Python). No se usaron imágenes, sonidos ni fuentes de terceros, por lo que no hay licencias ni atribuciones pendientes.

Para regenerarlos: `python tools/generate_assets.py`.

## Sprites (`assets/sprites/`)

Hojas de sprites PNG con su JSON de animaciones (`idle`, `walk`, `attack`, `hurt`, `dead`).

| Archivo | Descripción | Fuente |
|---|---|---|
| `player.png/.json` | Superviviente (jugador) | Generado por código |
| `raider.png/.json` | Saqueador | Generado por código |
| `gunner.png/.json` | Pistolero | Generado por código |
| `brute.png/.json` | Bruto | Generado por código |
| `warlord.png/.json` | Caudillo (jefe) | Generado por código |
| `potion.png/.json` | Poción de curación | Generado por código |

## Tiles isométricos (`assets/tiles/`, 64×32 px)

`sand_0..3`, `dirt`, `cracked`, `concrete` (suelos) · `wall`, `crate`, `barrel`, `cactus`, `rock` (bloques con altura) · `tiles.json` (índice). Fuente: generado por código.

## Interfaz (`assets/ui/`)

- `menu_bg.png`: fondo del menú y de las pantallas de fin (atardecer, dunas y ruinas). Generado por código.

## Sonido (`assets/sounds/`, WAV mono 22050 Hz)

Sintetizados por código (ondas seno, cuadrada, sierra, triángulo y ruido):

- Interfaz: `click`, `hover`, `confirm`, `back`, `denied`
- Combate: `slash`, `shoot`, `hit`, `crit`, `miss`, `death`, `step`
- Items y turnos: `potion`, `pickup`, `turn`, `enemy_turn`, `level_up`
- Jingles: `victory`, `gameover`
- Música (loop): `music_menu`, `music_combat`

## Tipografía

Se usan fuentes del sistema (por orden de preferencia: Segoe UI, Helvetica Neue, Arial, DejaVu Sans, Liberation Sans, FreeSans, Verdana) a través de `pygame.font.SysFont`, con la fuente por defecto de Pygame como respaldo. No se distribuyen archivos de fuentes.

## Librerías

- [Pygame](https://www.pygame.org) — licencia LGPL.
