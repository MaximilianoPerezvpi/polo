# Arquitectura de POLO

## Principio central: Ports & Adapters (hexagonal)

El **núcleo** (`src/polo/core`) contiene la lógica y los contratos. No importa
nada de interfaces, adaptadores ni librerías de proveedores. Solo conoce
abstracciones.

```
   INTERFACES  ───▶   NÚCLEO   ◀───  ADAPTADORES
   (te empujan)     (contratos)    (el núcleo los usa)

   cli/             core/           adapters/  (desde Fase 1)
   (celular)        ├─ models.py    ├─ llm/    (Ollama)
   (máscara)        ├─ ports/       ├─ memory/ (Fase 2)
   (lentes)         └─ orchestrator └─ ...
```

## Las cuatro reglas que no se rompen

1. El núcleo no conoce ninguna interfaz.
2. Todo lo externo es un adaptador reemplazable, conectado por un puerto.
3. Primero capacidades reales, después abstracciones.
4. Costo cero: todo local y open-source.

## Los puertos actuales (Fase 0)

- **`InterfacePort`** — cualquier medio por el que el usuario habla con POLO
  (CLI hoy; celular, máscara y lentes en el futuro). Método `receive()` /
  `present()`.
- **`LLMPort`** — cualquier motor de lenguaje (Ollama local en Fase 1). Método
  `generate()`.

Los puertos de memoria, herramientas, voz y visión se agregarán en sus fases.
No antes: no se diseñan abstracciones para problemas que aún no entendemos.

## Flujo de datos (objetivo, desde Fase 1)

```
UserInput ─▶ InterfacePort.receive() ─▶ Orchestrator.handle()
                                              │
                                              ▼
                                        LLMPort.generate()
                                              │
                                              ▼
AssistantOutput ◀─ InterfacePort.present() ◀──┘
```

## Inyección de dependencias

El `Orchestrator` recibe sus puertos por el constructor. La única capa que
conoce implementaciones concretas es la de arranque (`cli/app.py`, el
"composition root"). Esto mantiene el núcleo puro y testeable con dobles de
prueba.

## Actualizacion Fase 2: memoria de largo plazo

Se agregaron dos puertos y dos adaptadores:

- **`EmbeddingPort`** -> `OllamaEmbedder`: convierte texto en vectores via Ollama.
- **`MemoryPort`** -> `SqliteMemory`: guarda texto + vector en SQLite y busca por
  similitud coseno con numpy (una "base vectorial hecha a mano", suficiente y
  transparente para un solo usuario).

El `Orchestrator` ahora, en cada turno: recupera recuerdos relevantes y los
inyecta como contexto; guarda hechos cuando el usuario lo pide ("recorda que...");
y extrae memoria automaticamente tras cada intercambio (con anti-duplicados).

Decision clave: NO se uso una base vectorial externa. Para el tamano de memoria
de un solo usuario, SQLite + numpy es instantaneo, sin dependencias pesadas, y
totalmente transparente. Si algun dia hiciera falta escalar, se cambia el
adaptador de `MemoryPort` sin tocar el nucleo.

Limite deliberado: la memoria solo AGREGA. No se reescribe ni se borra sola.

## Actualizacion Fase 3: herramientas

Puertos nuevos: `Tool` (una capacidad ejecutable, con nivel de riesgo) y
`ConfirmerPort` (pedir confirmacion sin conocer la interfaz). El puerto `LLMPort`
crecio para aceptar herramientas y devolver `LLMResponse` (texto o peticion de
herramientas).

Piezas nuevas:
- `core/registry.py` (ToolRegistry): cataloga herramientas, las ofrece al modelo,
  y las ejecuta con control de permisos. Es el guardian entre el modelo y las
  capacidades.
- `adapters/tools/`: herramientas concretas (reloj, calculadora). La calculadora
  usa un evaluador seguro con `ast` (NUNCA `eval`).

Flujo (loop de herramientas en el orquestador): el modelo puede PEDIR usar
herramientas; el registro las ejecuta; los resultados vuelven al modelo hasta
que da la respuesta final (con tope de vueltas). El modelo nunca ejecuta nada
por si mismo.

Seguridad: cada herramienta declara RiskLevel (SAFE / CONFIRM). Las CONFIRM
requieren aprobacion del usuario via ConfirmerPort antes de ejecutarse.

## Actualizacion Fase 4: sistema de plugins

Puerto nuevo: `Plugin` (name, version, tools()). Un plugin es un archivo .py
que define un objeto `PLUGIN` cumpliendo ese contrato.

Pieza nueva: `adapters/plugins/loader.py`. Recorre los .py de la carpeta de
plugins (~/.polo/plugins), los importa, valida su objeto PLUGIN, y devuelve los
plugins. Un plugin roto se saltea sin tumbar POLO. El composition root suma las
herramientas de los plugins a las incorporadas.

Decision de CTO: carpeta de plugins en vez de entry points de Python. Menos
ceremonia para un asistente personal (no hay que empaquetar ni instalar cada
plugin). El contrato es el mismo, asi que soportar entry points en el futuro no
requiere rehacer nada.

SEGURIDAD: cargar un plugin ejecuta su codigo con todos los permisos de Python.
NO hay sandbox real (aislar de verdad es un proyecto en si mismo, diferido). El
sistema de permisos a nivel herramienta (RiskLevel + confirmacion) sigue
aplicando a las herramientas de los plugins. Regla: cargar solo plugins de
confianza.

## Actualizacion Fase 5 (Paso A): voz de salida

Puerto nuevo: `SpeechPort` (speak(text)). Adaptador: `PyttsxSpeaker` (voz del
sistema via pyttsx3, SAPI5 en Windows).

La voz es SOLO otra forma de la interfaz: la CLI recibe un SpeechPort opcional y,
si esta presente, present() ademas de mostrar la respuesta la habla. El nucleo,
la memoria, las herramientas y los plugins NO se tocaron: la voz es puramente
una capa de interfaz. Ese es el pago de la arquitectura hexagonal.

Degradacion elegante: si el motor de voz no inicializa (p. ej. sin audio), el
composition root lo captura y POLO sigue en modo texto.

Proximo paso (B): entrada por voz (microfono + STT con faster-whisper).

## Actualizacion Fase 6: vision

Puerto nuevo: `VisionPort` (describe(image_path, question)). Adaptador:
`OllamaVision` (modelo multimodal via Ollama). La vision se expone como una
HERRAMIENTA mas (`VisionTool`, en adapters/tools), asi que se apoya en todo el
sistema de herramientas de la Fase 3: el nucleo y el orquestador no se tocaron.

Ventaja: la vision corre bajo demanda (cuando el usuario pide analizar una
imagen), no en un bucle en tiempo real, asi que la lentitud en CPU molesta menos.

El modelo de vision es un tercer modelo de Ollama (aparte de chat y embeddings),
que se carga solo cuando se usa la herramienta.

## Actualizacion Fase 7: automatizacion

Herramientas nuevas (adapters/tools/automation.py) que interactuan con el SO:
listar_carpeta (SAFE), abrir (CONFIRM, bloquea ejecutables), mover_archivo
(CONFIRM, no sobrescribe). Se apoyan en el sistema de permisos de la Fase 3: lo
riesgoso pide confirmacion via ConfirmerPort.

Seguridad: sin ejecucion de comandos arbitrarios (deliberadamente afuera).
Interruptor maestro POLO_AUTOMATION_ENABLED. Cada accion con efecto se registra
en el log (auditoria). El 'opener' de 'abrir' es inyectable para testear sin
lanzar nada.

Ni el nucleo ni el orquestador se tocaron: la automatizacion son herramientas.

## Control de PC (volumen y apps)

Herramientas nuevas (adapters/tools/pc_control.py), especificas de Windows:
- VolumeTool (SAFE): sube/baja/silencia via teclas multimedia (ctypes).
- OpenAppTool (CONFIRM): abre una app por nombre, SIN shell (evita inyeccion),
  rechazando nombres con caracteres peligrosos.

Ambas con backend inyectable (presser / launcher) para testear sin audio ni
lanzar programas. Gated por POLO_AUTOMATION_ENABLED.

## Seguridad de archivos (inspirado en OpenJarvis)

core/security.py: is_sensitive_path() detecta rutas sensibles (.ssh, .env,
credentials, id_rsa, *.pem, *.key, secretos...) usando coincidencia por
segmento exacto (evita falsos positivos por substring) + globs para extensiones.
Integrado en read_file, listar_carpeta, abrir y mover_archivo: POLO se niega a
leer/listar/abrir/mover cualquier cosa sensible, aunque se lo pidan.

## Voz intercambiable: pyttsx3 <-> Kokoro

SpeechPort tiene ahora dos implementaciones: PyttsxSpeaker (voz del sistema) y
KokoroSpeaker (neuronal, kokoro-onnx). Se eligen por config (voice_engine) sin
tocar el nucleo. El composition root (_crear_speaker) arma una cadena de
degradacion: kokoro -> pyttsx3 -> texto, asi POLO nunca se rompe por un fallo de
audio. Kokoro reproduce via winsound (stdlib de Windows), sin dependencias extra.

## Robustez: chequeo de salud al arrancar

OllamaAdapter.health_check() verifica, antes de entrar al bucle, que Ollama esté
corriendo y que los modelos requeridos (chat + embeddings) estén descargados. Si
algo falta, POLO muestra un mensaje claro y accionable ("ollama pull ...") y sale
con dignidad, en vez de reventar con un stack trace en el primer mensaje. Mejora
clave de UX y una señal de madurez para un proyecto de portafolio.

## Escucha por voz (STT): ListenerPort + WhisperMicListener

Puerto ListenerPort (listen() -> str). Adaptador WhisperMicListener: microfono
(sounddevice, push-to-talk con Enter) + faster-whisper (STT local en CPU).
Grabador y transcriptor inyectables para testear sin hardware ni modelo.

Integracion en la CLI: con listener presente, un Enter vacio graba; texto escrito
funciona igual (permite comandos). Degradacion: si STT falla, POLO sigue con
teclado. Es una capa de INTERFAZ: el nucleo no se entera de que ahora escucha.

## Cerebro intercambiable: Ollama local <-> NIM en la nube

LLMPort tiene ahora dos implementaciones: OllamaAdapter (local) y NimAdapter
(nube, endpoint compatible con OpenAI). Se eligen por config (llm_backend).

NimAdapter traduce el formato de POLO al de OpenAI, incluyendo el enlace de
resultados de herramienta con el tool_call_id que exige NIM (POLO relaciona por
nombre; el adaptador genera y enlaza los ids).

FallbackLLM (patron decorador) envuelve primario+respaldo: intenta NIM y cae a
Ollama local si la nube lanza LLMUnavailableError. Asi POLO no depende de un solo
proveedor. Los embeddings (memoria) siguen en Ollama; se puede mover a la nube a
futuro. El nucleo no se entera de nada de esto: solo ve un LLMPort.

## Velocidad: embeddings en la nube (opcional)

EmbeddingPort tiene ahora dos implementaciones: OllamaEmbedder (local) y
NimEmbedder (nube, OpenAI-compatible). Se eligen por config (embedding_backend).
Con "nim", POLO no genera vectores en CPU -> sin peaje local por mensaje.

SqliteMemory.recall ignora recuerdos cuya dimensión no coincida con la consulta,
así cambiar de modelo de embeddings no rompe la búsqueda (los viejos se ignoran).

El preflight verifica solo lo que se usa: cerebro activo (nim u ollama) y embedder
activo. Con todo en NIM, Ollama queda de puro respaldo (best-effort).

## CI/CD (integración continua)

.github/workflows/ci.yml corre en cada push a main y en cada PR: instala con uv,
y ejecuta ruff (linter), ruff format --check (formato), mypy (tipos estrictos) y
pytest (108 tests). Si algo falla, el push queda marcado en rojo. Los mismos
comandos que corremos localmente, automatizados en la nube de GitHub.

## Interfaz gráfica web (GUI)

Nueva interfaz en interfaces/web/: un servidor FastAPI (server.py) sirve una GUI
futurista (index.html, nucleo animado que reacciona al estado) y expone /api/chat.

Refactor clave: la construccion de POLO se extrajo a bootstrap.py
(build_orchestrator, preflight), compartido entre CLI y web. Cada interfaz pasa su
propio confirmer. La GUI declina acciones riesgosas por ahora (sin UI de permiso).

El servidor se testea con TestClient + un orquestador falso (sirve HTML, responde,
maneja errores) sin navegador ni modelos. FastAPI/uvicorn son dependencia opcional
(extra gui). Comando: polo-web. El nucleo no cambio: la GUI es solo otra interfaz.

## Voz en la nube: NimSpeaker (Magpie TTS de NVIDIA)

Tercera implementacion de SpeechPort: NimSpeaker usa Magpie TTS de NVIDIA (Riva
gRPC) con la misma API key del cerebro. Corre en la nube (no frena la CPU) y da
voces naturales con estilo. voice_engine="nim". Cadena de degradacion:
nim -> kokoro -> pyttsx3 -> texto. Sintesis y reproductor inyectables (testeado
con dobles, sin red ni audio). Dep opcional: extra nimvoice (nvidia-riva-client).

## Voz en la GUI (Web Speech API del navegador)

La interfaz web habla y escucha usando la Web Speech API nativa del navegador:
speechSynthesis (POLO dice sus respuestas, voz en espanol, con boton para
silenciar) y SpeechRecognition (boton de microfono para hablarle). Sin
dependencias nuevas ni audio del servidor. El nucleo animado reacciona: cian al
pensar, cian intenso al hablar, magenta al escuchar. Degrada solo: si el
navegador no soporta la API, oculta los botones y sigue por texto. Funciona en
Chrome/Edge. La voz Magpie del servidor queda como upgrade futuro (streamear
audio de mejor calidad al navegador).

## Integracion: Spotify

Nueva herramienta SpotifyPlayTool (adapters/tools/spotify.py): busca un tema y lo
reproduce via la API oficial de Spotify (spotipy, que maneja el OAuth y cachea el
token). Requiere Premium y un dispositivo activo; si no hay, avisa. El cliente es
inyectable (testeado con un doble, sin red ni credenciales). Se activa con
spotify_enabled y se suma en bootstrap. Dep opcional: extra spotify.

## Optimizacion: herramientas terminales (short-circuit)

Las acciones (reproducir_spotify, abrir_aplicacion, volumen, control_musica)
llevan final=True. Cuando el modelo las llama, el orquestador devuelve el
resultado de la herramienta DIRECTO, sin un segundo viaje al modelo para
redactar. Ahorra latencia en toda accion. Las herramientas informativas
(busqueda, clima) siguen pasando por el modelo para que redacte. El registro
expone is_final(); las tools optan con getattr(tool,"final",False).

## Función: tareas/pendientes

TaskStore (adapters/tasks/) persiste una lista de pendientes en JSON, con candado
(la GUI usa varios hilos). Tres herramientas (agregar_tarea, listar_tareas,
completar_tarea), todas final=True (acciones rápidas sin segundo viaje al modelo).
Sin dependencias ni setup: siempre disponibles. Testeadas de punta a punta.

## Función: YouTube

YouTubePlayTool (adapters/tools/youtube.py): sin API key abre la busqueda de
YouTube en el navegador (cero setup); con una YouTube Data API key busca el
primer video y lo abre directo. Abridor y buscador inyectables (testeado sin red
ni navegador). final=True. Config: youtube_api_key.

## Función: abrir sitios web

OpenWebsiteTool (adapters/tools/website.py): abre sitios por nombre conocido
(gmail, calendario, drive, instagram...), URL o dominio; si no reconoce, busca en
Google. Da acceso liviano a Gmail y Google Calendar sin OAuth. Abridor inyectable
(testeado sin navegador). final=True.

## Optimizaciones de rendimiento

1. Ventana de historial (history_window, default 20): el orquestador solo manda
   los ultimos N mensajes al modelo (ademas del system), acotando costo y
   latencia en charlas largas. Antes crecia sin limite. Config; 0 = sin limite.
2. Cache de tool specs: el registro construye las descripciones de herramientas
   una sola vez (no cambian en runtime) en vez de en cada llamada al modelo.
3. (Previo) Short-circuit de acciones terminales: sin segundo viaje al modelo.
4. (Previo) Recall de memoria se saltea si la memoria esta vacia.

## HUD panel (tablero de la GUI)

La GUI web ahora tiene un panel lateral tipo HUD: fecha, pendientes (del
TaskStore) y clima (si se configura dashboard_city). El servidor expone
/api/dashboard (tareas + clima via _open_meteo). El frontend lo refresca al
cargar, cada 60s, y tras cada mensaje. Layout de dos columnas (panel + main);
en pantallas angostas el panel se oculta. Testeado con TaskStore falso.
