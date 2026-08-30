# Recordatorios con hora — diseño

## Contexto y objetivo

POLO ya tiene una lista de tareas (`TaskStore`) sin noción de tiempo. El
objetivo de esta feature es que el usuario pueda decirle a POLO "avisame a
las 15hs que salga a buscar el pedido" y que, llegado el momento, POLO se lo
recuerde por voz (y visualmente) — el primer paso hacia un asistente estilo
Jarvis que actúa de forma proactiva, no solo reactiva.

Es la primera de varias piezas identificadas para esa meta más grande
("super Jarvis"); las demás (wake-word, Google Calendar, briefings
proactivos, streaming de respuestas, cámara en vivo) quedan fuera de este
spec y se abordan como sub-proyectos independientes más adelante.

## Alcance (decidido con el usuario)

- Los recordatorios avisan **solo si POLO está abierto** (CLI o GUI web) en
  el momento en que vencen. No hace falta que corra como servicio de fondo
  del sistema operativo.
- El aviso es **hablado (TTS)** además de visual.
- Funciona en **ambas interfaces**: CLI y GUI web.
- Solo **recordatorios únicos** en esta versión (sin recurrencia).
- Explícitamente fuera de esta versión: recurrencia, avisos con POLO
  cerrado, notificaciones nativas del navegador.

## Arquitectura

Sigue el patrón ya establecido por `TaskStore`/`SpotifyPlayTool`/etc.: una
feature nueva es un adaptador + una o dos herramientas, conectados en el
composition root (`cli/app.py`, `interfaces/web/server.py` vía
`bootstrap.py`). **Ni `core/` ni `Orchestrator` se tocan.**

```
                    ┌─────────────────────┐
   agregar_recordatorio ─▶│   ReminderStore      │◀─── listar_recordatorios
   (herramienta, SAFE)    │  (JSON + lock, como  │     (herramienta, SAFE)
                          │   TaskStore)          │
                          └──────────┬───────────┘
                                     │ pop_due(ahora)
                                     ▼
                          ┌─────────────────────┐
                          │  ReminderScheduler   │
                          │  (hilo en 2do plano, │
                          │   poll cada ~15s)    │
                          └──────────┬───────────┘
                                     │ on_due(recordatorio)
                        ┌────────────┴────────────┐
                        ▼                          ▼
                  CLI: speaker.speak()      Web: encola en memoria;
                  + print                   GET /api/recordatorios/pendientes
                                             lo entrega (con audio) al
                                             polling del frontend
```

## Componentes nuevos

### `ReminderStore` (`adapters/tasks/reminder_store.py`)

Igual que `TaskStore` (JSON + `threading.Lock`, misma carpeta
`adapters/tasks/`), pero cada entrada tiene hora:

```python
@dataclass(frozen=True)
class Reminder:
    id: str          # uuid4
    mensaje: str
    cuando: datetime  # naive, hora local — igual criterio que ClockTool.run()
    creado: datetime  # ídem
```

Métodos:
- `add(mensaje: str, cuando: datetime) -> Reminder`
- `list() -> list[Reminder]` — pendientes, ordenados por `cuando`.
- `pop_due(ahora: datetime) -> list[Reminder]` — remueve y devuelve los
  vencidos (`cuando <= ahora`). Recibe `ahora` como argumento (no usa
  `datetime.now()` internamente) para que sea determinista en tests.

Igual manejo de corrupción que `TaskStore`: JSON inválido → lista vacía, no
excepción.

### `ReminderScheduler` (`adapters/tasks/scheduler.py`)

```python
class ReminderScheduler:
    def __init__(
        self,
        store: ReminderStore,
        on_due: Callable[[Reminder], None],
        interval_seconds: float = 15.0,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None: ...

    def start(self) -> None:  # spawnea un hilo daemon con el loop
    def stop(self) -> None:   # para tests / apagado limpio
    def _tick(self) -> None:  # una pasada: pop_due + on_due por cada uno
```

- `_tick()` es el método testeable sin hilos reales ni `sleep()`.
- `on_due` se llama dentro de un `try/except` por recordatorio: si uno
  falla (p. ej. el hablante tira una excepción), no debe tumbar el loop ni
  perder los demás recordatorios de esa pasada. Degradación elegante,
  mismo criterio que el resto de POLO.
- `clock` inyectable por la misma razón que `pop_due` recibe `ahora`.

### Herramientas (`adapters/tools/reminders.py`)

- **`agregar_recordatorio`** — argumentos `mensaje` (str) y `cuando_iso`
  (str, ISO 8601, **sin timezone** — hora local naive, mismo formato que
  devuelve `hora_actual`, p. ej. `2026-08-30T15:00:00`). Risk `SAFE`,
  `final=True` (como `agregar_tarea`). La herramienta NO interpreta
  lenguaje natural ("mañana a las 9", "en 20 minutos"): el modelo ya sabe
  usar `hora_actual` para saber la fecha/hora actual y calcular el ISO
  absoluto él mismo, igual que hoy hace cálculos con la calculadora. La
  descripción de la herramienta le indica explícitamente ese formato. Si
  `cuando_iso` no parsea (`datetime.fromisoformat` falla) o trae
  timezone, la herramienta devuelve un mensaje de error amigable, no una
  excepción.
- **`listar_recordatorios`** — sin argumentos, simétrica a
  `listar_tareas`. Risk `SAFE`, `final=True`.

## Entrega por interfaz

### CLI (`cli/app.py`)

En `main()`, junto a la creación del `speaker`/`listener` existentes: se
crea el `ReminderStore` (mismo `settings.data_dir`, archivo
`recordatorios.json`) y el `ReminderScheduler`, con `on_due` que:
1. Si hay `speaker`, `speaker.speak(recordatorio.mensaje)`.
2. Llama un método nuevo `CLIChat.mostrar_recordatorio(mensaje)` (panel de
   rich, mismo estilo que `mostrar_error`).

Se arranca con `scheduler.start()` antes de entrar al loop de conversación.

**Limitación conocida y aceptada**: como el hilo del scheduler imprime de
forma asíncrona mientras el hilo principal puede estar bloqueado en
`cli.receive()` (esperando que el usuario escriba), el aviso puede
interrumpir visualmente la línea de input. No se resuelve en esta versión
(YAGNI: es cosmético, no rompe funcionalidad).

### GUI web (`interfaces/web/server.py`)

El callback del scheduler para la web no habla directo (no hay conexión
persistente con el navegador): encola el recordatorio en una estructura en
memoria protegida por lock, propia del servidor.

Nuevo endpoint:

```
GET /api/recordatorios/pendientes
→ { "recordatorios": [ { "mensaje": str, "audio": "data:audio/wav;base64,..." | null } ] }
```

Vacía la cola al leerla (igual que `pop_due` vacía el store). Si `tts` está
configurado, genera el audio con `synthesize_wav` + base64, mismo patrón
que ya usa `/api/chat`; si falla la síntesis, se manda igual sin audio (la
degradación ya existente: sin audio, la GUI puede usar la voz del
navegador si quiere, o simplemente mostrar el texto).

Frontend (`index.html`): un `setInterval` nuevo (cada ~10s, independiente
del polling de 60s que ya tiene el dashboard) que llama a este endpoint;
por cada recordatorio recibido, lo agrega como mensaje de POLO en el chat
(con un ícono distintivo, p. ej. 🔔) y reproduce el audio si vino.

## Testing

Mismo criterio que el resto del proyecto: todo lo que depende de tiempo
real o hilos reales se inyecta.

- `tests/adapters/test_reminder_store.py` — `add`/`list`/`pop_due` con
  fechas fijas pasadas a mano (sin `datetime.now()` real), corrupción de
  archivo, orden por `cuando`.
- `tests/adapters/test_scheduler.py` — `_tick()` llamado manualmente con un
  `clock` fijo y un `store`/`on_due` falsos; un `on_due` que tira excepción
  no debe impedir que se procesen los demás recordatorios vencidos de la
  misma pasada.
- `tests/adapters/test_reminders.py` — la herramienta: agregar con ISO
  válido, ISO inválido (mensaje de error, no excepción), listar vacío y con
  contenido.
- `tests/interfaces/test_web.py` — casos nuevos para
  `GET /api/recordatorios/pendientes`: vacío, con uno pendiente (con y sin
  `tts`), y que vaciar la cola funciona (dos llamadas seguidas, la segunda
  no repite lo ya entregado).

No se agregan tests de integración con hilos reales ni con `sleep()`: se
mantiene la misma filosofía que ya usa el proyecto (adaptadores con
dependencias inyectables, sin tocar hardware/red/reloj real en los tests).

## Fuera de alcance (explícito)

- Recurrencia ("todos los días a las 8", "cada lunes").
- Avisar con POLO cerrado (requeriría un servicio de fondo del SO, bandeja
  del sistema, arranque con Windows — otro sub-proyecto si se decide más
  adelante).
- Notificaciones nativas del navegador (`Notification` API) — se podría
  sumar después reusando el mismo endpoint de polling.
- Editar o cancelar un recordatorio ya creado (por ahora solo agregar y
  listar, simétrico a cómo arrancaron las tareas).
