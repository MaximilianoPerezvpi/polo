# ESTADO DE POLO — mapa del proyecto

> Dejá este archivo en la raíz del proyecto. Sirve para que Claude Code (y vos)
> tengan el contexto completo de qué es POLO, cómo está hecho y qué falta.

## Qué es

POLO es un asistente personal con IA, tipo Jarvis, construido desde cero en
Python con **arquitectura hexagonal** (puertos y adaptadores). Corre con cerebro
**local** (Ollama) o **en la nube** (NVIDIA NIM), intercambiable por config.
Es un proyecto de **portafolio** para conseguir trabajo.

## Reglas de oro (no romper)

- El núcleo (`src/polo/core/`) NO importa librerías externas ni adaptadores.
- Todo cambio debe pasar: `uv run ruff check .`, `uv run ruff format .`,
  `uv run mypy`, `uv run pytest`.
- Hay **155 tests** y deben seguir en verde.
- El `.env` tiene las API keys: **NUNCA subirlo a git** (ya está en `.gitignore`).
- Cada capacidad es un adaptador intercambiable. Degradación elegante en todo
  (si la nube falla, cae a local; si la voz falla, cae a texto).

## Cómo correr

```
uv sync --extra cloud --extra gui --extra nimvoice --extra spotify
uv run polo         # terminal
uv run polo-web     # interfaz web futurista (127.0.0.1:8000)
```

## Capacidades actuales

- Conversación (cerebro local Ollama o nube NIM, con respaldo)
- Memoria de largo plazo (SQLite + vectores propios)
- Herramientas (~20): hora, cálculo, clima, búsqueda web, leer/escribir archivos,
  visión, tareas (agregar/listar/completar), YouTube, abrir sitios web, conversor
  de monedas, resumen del día, control de PC (volumen, apps, música), Spotify
- Voz: habla (pyttsx3 / Kokoro / Magpie-nube) y escucha (Whisper)
- Visión (modelo multimodal)
- Plugins (carga .py de una carpeta)
- Seguridad (bloqueo de archivos sensibles; confirmación para acciones riesgosas)
- GUI web "centro de comando": esfera de partículas animada, panel HUD (fecha,
  pendientes, clima), reloj, voz en el navegador

## Estructura

```
src/polo/
├── core/          # núcleo puro (ports/, orchestrator, models, security, registry)
├── adapters/      # llm, embedding, memory, speech, vision, tools, plugins, tasks
├── interfaces/    # cli/ y web/
├── bootstrap.py   # construcción compartida (CLI + web)
└── config.py      # configuración por entorno (.env)
```

## Lo que falta / próximos pasos

- [ ] CONSOLIDAR: confirmar los 155 tests y subir todo a GitHub
      (repo: MaximilianoPerezvpi/polo). Cuidar de NO subir el .env.
- [ ] Probar en máquina real: Spotify, voz Magpie, visión (partes que se
      construyeron sin poder testear).
- [ ] Sacar un GIF/demo de la GUI para el README.
- [ ] Posibles mejoras futuras: briefings proactivos (resumen automático a la
      mañana), Google Calendar (OAuth), streaming de respuestas, cámara en vivo,
      wake-word ("Hey POLO"), versión móvil.

## Nota sobre el modelo

Con ~20 herramientas, conviene un modelo capaz para el tool-calling. En el `.env`,
`POLO_NIM_MODEL=meta/llama-3.3-70b-instruct` (o un Nemotron) anda mejor que el 8B
para decidir herramientas y no marearse con saludos.
