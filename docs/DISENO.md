# Documento de diseño — Cenizas del Yermo

## 1. Concepto

RPG táctico isométrico por turnos ambientado en un yermo postapocalíptico (inspirado en *Wasteland*). El jugador controla a un único superviviente y debe limpiar tres zonas de enemigos. Prioridad: decisiones tácticas claras, partidas cortas (3–6 minutos) y feedback visual y sonoro en cada acción.

**Bucle de juego:** explorar el mapa → elegir posición → atacar / curarse → turno enemigo → repetir hasta eliminar a todos.

## 2. Mecánicas

### 2.1 Turnos y puntos de acción (PA)

- El jugador tiene **6 PA** por turno; los enemigos tienen entre 4 y 5.
- Costos: mover 1 PA por casilla · golpe cuerpo a cuerpo 2 PA · disparo 3 PA · poción 1 PA.
- Cuando el jugador se queda sin PA (o termina el turno) juegan los enemigos, uno por uno. Después empieza una nueva ronda y los PA se restauran.
- Mientras se resuelve una acción (animaciones) el input está bloqueado, así no se pueden encadenar acciones por error.

### 2.2 Atributos

| Entidad | Vida | PA | Ataque (daño / alcance / costo) | Notas |
|---|---|---|---|---|
| Superviviente (jugador) | 70 | 6 | Cuerpo a cuerpo 14 / 1 / 2 PA · Pistola 9 / 5 / 3 PA | Empieza con 2 pociones |
| Saqueador | 28 | 5 | 9 / 1 / 2 PA | Cuerpo a cuerpo |
| Pistolero | 20 | 5 | 8 / 5 / 3 PA | A distancia, requiere línea de visión |
| Bruto | 48 | 4 | 15 / 1 / 3 PA | Lento y resistente |
| Caudillo (jefe) | 80 | 5 | 16 / 1 / 3 PA | Jefe del nivel 3, siempre en alerta |

### 2.3 Combate

- **Daño:** el valor base varía ±15 %. **Crítico:** 12 % de chance, ×1.6.
- **Fallo:** cuerpo a cuerpo 5 %; a distancia 6 % + 4 % por cada casilla de distancia después de la primera.
- **Alcance:** distancia Manhattan sobre la grilla. Los ataques a distancia además necesitan **línea de visión** (Bresenham sobre la matriz): muros, cajas, cactus y rocas bloquean los disparos, lo que vuelve importantes las coberturas.
- **Curación:** poción = +28 de vida (no se puede usar con vida completa).

### 2.4 Enemigos (IA)

- Cada enemigo está **distraído** hasta que el jugador entra en su radio de detección (8–11 casillas, el jefe siempre ve). Al verte pasa a **alerta** y se muestra un "!" sobre él. También se alertan si los atacás.
- En su turno cada enemigo repite: *si puede atacar, ataca; si no, se mueve*. Para moverse busca (BFS) la casilla más cercana desde la que pueda atacar con los PA que le quedan; si no llega este turno, avanza por el camino más corto hacia una casilla de ataque.
- Los enemigos a distancia prefieren la casilla de ataque más lejana del jugador a igual costo.

### 2.5 Niveles y progresión

| Nivel | Nombre | Enemigos |
|---|---|---|
| 1 | Las Afueras | 2 Saqueadores, 1 Pistolero |
| 2 | Ruinas del Peaje | 2 Saqueadores, 2 Pistoleros, 1 Bruto |
| 3 | Fortín del Caudillo | Caudillo, 2 Saqueadores, 2 Pistoleros |

Entre niveles el jugador recupera el 50 % de su vida máxima y encuentra una poción. Las pociones del mapa se recogen caminando sobre ellas.

### 2.6 Condiciones de fin

- **Victoria:** eliminar a todos los enemigos del nivel 3 → pantalla de Victoria.
- **Game Over:** vida del jugador en 0 → pantalla de Game Over con "Reintentar nivel" y "Volver al menú".
- Ambas pantallas muestran estadísticas (turnos, bajas, daño dado y recibido, pociones).

## 3. Implementación técnica de lo isométrico

**Proyección** (`game/iso.py`), con tiles de 64×32 px:

```
iso_x = (col - row) * TILE_W / 2 + origen_x
iso_y = (col + row) * TILE_H / 2 + origen_y
```

La inversa convierte el click del mouse a casilla (`tile_at`). El origen se calcula para centrar cada mapa en pantalla.

**Depth sorting** (de atrás hacia adelante): primero se dibuja todo el suelo; luego muros, props, items y personajes en una sola lista ordenada por `col + row` (los personajes usan su posición interpolada, así que el orden es correcto también mientras caminan). Cuando un bloque que está delante tapa a un personaje se dibuja translúcido para no perderlo de vista.

**Colisiones por matriz:** cada nivel es una matriz de texto (`game/levels.py`) que se convierte en una matriz booleana `solid[fila][col]`. Una casilla está bloqueada si es sólida o si hay una entidad viva en ella. El movimiento, las casillas alcanzables y la IA usan esa misma función.

**Caminos:** BFS en 4 direcciones (`game/pathfinding.py`), con costo = cantidad de casillas = PA gastados.

**Secuencias con generadores:** caminar, atacar, esperar animaciones y pasar el turno están escritos como generadores de Python (`yield` = esperar). Así la lógica de un turno se lee de corrido y el bucle principal nunca se bloquea.

## 4. Arquitectura y herencia del motor de clase

Todas las escenas y objetos del juego heredan de las clases del motor construido en clase (`core/`):

| Clase del motor | Heredan de ella |
|---|---|
| `Scene` | `MenuScene`, `PlayScene`, `EndScreen` → `GameOverScene`, `VictoryScene` |
| `GameObject` (spritesheet + JSON, `update(dt, action)`, `draw`) | `Entity` → `Player`, `Enemy`; `Collectible`; widgets `Button`, `Panel`, `Bar` |
| `Game` (bucle INPUT / UPDATE / RENDER, escenas) | se usa directamente desde `main.py` |

Las animaciones se cargan de un JSON por sprite (`assets/sprites/*.json`) con `spritesheet_path`, la lista de frames por acción (`idle`, `walk`, `attack`, `hurt`, `dead`), la duración de cada frame y el punto de anclaje (los pies).

## 5. Interfaz

- **Menú:** botón **Comenzar Juego**, "Cómo jugar" y "Salir". Fondo y diorama animado.
- **Panel de combate:** botones Mover / Atacar / Disparar / Poción / Terminar turno con su costo en PA, atajos de teclado, barra de vida y puntos de acción.
- **Indicadores:** barra de vida sobre cada personaje, flecha animada sobre quien tiene el turno, cartel "TU TURNO / TURNO ENEMIGO", casillas resaltadas (celeste = mover, rojo = objetivos, naranja = alcance), números de daño flotantes, tarjeta de información del enemigo bajo el cursor y registro de combate.
- **Feedback sonoro:** hover y click de botones, pasos, golpes, críticos, fallos, disparos, pociones, muerte, cambios de turno, fanfarria de victoria y jingle de derrota, más música de menú y de combate.

## 6. Decisiones de diseño

- **Un solo personaje, tácticas ricas:** dos ataques con costos y alcances distintos (golpe barato y fuerte vs. disparo caro y débil) obligan a decidir entre acercarse o mantener distancia.
- **Enemigos distraídos:** permiten "tirar de a uno", una táctica clásica de este género.
- **Coberturas reales:** los props bloquean movimiento y visión, así que el mapa importa.
- **Todo generado por código:** sprites, tiles, fondo y sonido se generan con `tools/generate_assets.py`, lo que evita problemas de licencias y permite iterar rápido.
- **Balance con bot:** se simuló con un bot simple (sin usar coberturas ni kiting) que gana ~40 % de las partidas completas; un jugador humano que use el terreno debería superarlo con holgura.

## 7. Ideas a futuro

Más niveles, inventario con armas, habilidades con enfriamiento, niebla de guerra, guardado de partida y animaciones de 4 direcciones.
