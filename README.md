# Cirugía Ágil — proyecto local para Visual Studio Code

Prototipo del reto 1: lee una póliza y un informe médico con **tu modelo local**, verifica condiciones y produce una preaprobación preliminar, una solicitud de documentos o una revisión humana. No se ha publicado en internet.

## Empieza aquí (Windows)

Necesitas **Python 3.11 o superior** (recomendado 3.12), **Visual Studio Code** y **Ollama**.

- [Python para Windows](https://www.python.org/downloads/windows/)
- [Visual Studio Code](https://code.visualstudio.com/download)
- [Ollama para Windows](https://ollama.com/download/windows)

1. Extrae todo el ZIP en una carpeta, por ejemplo `C:\Proyectos\cirugia-agil`.
2. En VS Code: **Archivo → Abrir carpeta** y selecciona la carpeta que contiene `run.py`.
3. Abre la terminal de VS Code y ejecuta:

```powershell
.\INSTALAR.bat
```

4. Instala y abre Ollama. Para descargar un modelo inicial, ejecuta:

```powershell
ollama pull qwen3:4b
```

5. Inicia la aplicación:

```powershell
.\INICIAR.bat
```

6. Abre **http://127.0.0.1:8000** en tu navegador. La terminal debe permanecer abierta.
7. Selecciona el modelo y pulsa **Probar conexión**. Esta prueba hace una llamada real al modelo y verifica su JSON.
8. Carga la póliza, el informe y los anexos disponibles; pulsa **Evaluar solicitud**.

También puedes ejecutar los dos `.bat` con doble clic. El instalador no descarga modelos automáticamente, no pide claves y no modifica un `.env` existente. Instala dependencias de Python en `.venv`, dentro del proyecto. La primera instalación y descarga de pesos requieren internet; las evaluaciones con un modelo local ya descargado no necesitan una API de pago.

Se propone `qwen3:4b` como punto de partida pequeño y reemplazable. Sus pesos de catálogo ocupan aproximadamente 2.5 GB; la memoria de ejecución es mayor y depende del contexto. El rendimiento debe comprobarse en tu equipo. No se incluyen pesos en el proyecto. [Ficha del modelo](https://ollama.com/library/qwen3:4b).

## Tu propio modelo

Si ya tienes un modelo en Ollama, aparece en el selector al pulsar **Actualizar**. Para cargar pesos GGUF propios, sigue [modelos/LEEME.md](modelos/LEEME.md). Se incluye un `Modelfile.example` editable.

Este proyecto utiliza la API local de Ollama. **No necesitas OpenAI, una clave de ChatGPT ni entrenar un modelo nuevo.** Tampoco necesitas instalar CUDA Toolkit para ejecutar este código Python; Ollama gestiona su propio motor. Consulta los requisitos de controladores de tu GPU en su [guía de Windows](https://docs.ollama.com/windows).

## Ejecutarlo sin los archivos BAT

Windows, desde la terminal de VS Code:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe run.py
```

No ejecutes `Copy-Item` si ya configuraste `.env`. No es necesario activar el entorno ni cambiar las políticas de PowerShell.

macOS o Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python run.py
```

Para usar F5 en VS Code: instala la extensión Python recomendada, selecciona el intérprete de `.venv` y elige **Cirugía Ágil (local)**. Si prefieres Visual Studio completo, abre esta misma carpeta como proyecto Python; los comandos de terminal son los mismos.

## Qué incluye

- Interfaz en español adaptable a pantallas pequeñas.
- Selector de modelos locales y comprobación real de conexión.
- Lectura de PDF con texto, TXT y Markdown, sin enviar los documentos a un proveedor de IA externo.
- Póliza, informe médico y hasta tres anexos por solicitud.
- Extracción estructurada con citas, documento y página.
- Reglas en Python: identidad, vigencia para la cirugía, cobertura, carencia, documentos y condiciones adicionales.
- Historial SQLite local, conservación de originales, descarga del resultado JSON e impresión.
- Integración opcional con Notion para guardar originales y resultados mediante una acción explícita.

## Cómo decide

1. Lee los archivos sin recortar silenciosamente páginas o texto.
2. Tu modelo extrae hechos y citas mediante un esquema JSON.
3. Se verifica que cada cita exista en el documento y la página señalados. También se comprueba que los valores clave aparezcan en sus citas.
4. Python calcula fechas y aplica las reglas. El texto del modelo no puede emitir directamente una aprobación.
5. Se guarda el resultado con su modelo, duración, extracción y evidencias.

| Estado | Significado |
| --- | --- |
| Preaprobación preliminar | Las comprobaciones implementadas se cumplen. No es autorización definitiva. |
| Documentos o datos pendientes | Falta un requisito identificable y no hay otra incertidumbre que necesite revisión. |
| No procede la preaprobación automática | Hay una condición incumplida, por ejemplo carencia pendiente. No constituye denegación definitiva. |
| Requiere revisión humana | Hay ambigüedad, citas no verificables, contradicciones o reglas que no se pueden resolver. |

La carencia se calcula con días de calendario entre el inicio de cobertura continua del asegurado y la fecha prevista de cirugía. El día de inicio corresponde a 0 días transcurridos. Un plazo de 180 días se cumple en `inicio + 180 días`. No se convierten meses a días arbitrariamente.

Para una preaprobación automática, los nombres del procedimiento extraídos de póliza e informe deben coincidir tras normalizar espacios, signos y acentos. Un sinónimo no se asume equivalente: se deriva a revisión. No hay una lista universal de documentos: se toman los requisitos de la póliza.

Verificar que una cita existe **no demuestra** que el modelo haya interpretado todas las condiciones correctamente. Un modelo pequeño puede omitir o interpretar mal una cláusula. Es una base funcional para demostración y pruebas con datos ficticios, no un sistema validado para decidir cobertura real.

## Notion (opcional durante las pruebas locales)

El reto final exige Notion. El prototipo permite comenzar sin cuenta conectada; sus datos se guardan localmente hasta que tú decidas sincronizar.

1. Crea una conexión interna de Notion con permisos para leer, insertar y actualizar contenido.
2. Crea una página vacía y, en sus conexiones, dale acceso a esa integración.
3. Copia `.env.example` como `.env` si todavía no existe.
4. Configura `NOTION_TOKEN` y `NOTION_PARENT_PAGE_ID` en `.env`. El ID de página es el identificador de 32 caracteres de la URL, no el enlace completo. No compartas el token ni lo pegues en el código o en un repositorio.
5. Ejecuta una sola vez:

```powershell
.\.venv\Scripts\python.exe scripts/setup_notion.py
```

6. El comando crea una base privada y muestra `NOTION_DATA_SOURCE_ID=...`. Copia esa línea a `.env` y reinicia la aplicación con `INICIAR.bat`.
7. Tras evaluar una solicitud, pulsa **Guardar en Notion**. Envía la póliza, el informe, los anexos y el resultado. El historial local permanece disponible aunque falle Notion.

Cada solicitud se guarda como una página en la base, con el estado en el título y las comprobaciones dentro de la página. No se crean columnas extra automáticamente en bases existentes. No vuelvas a ejecutar el instalador de Notion si ya creaste la base: cada ejecución crea una nueva.

Si ya tienes una base compatible, puedes configurar directamente su **ID de fuente de datos**; no lo confundas con el ID del contenedor de la base. Se usa la versión `2025-09-03` de la API. La conexión real requiere tus credenciales y no fue probada contra tu cuenta.

[Guía oficial de conexiones](https://developers.notion.com/guides/get-started/create-a-notion-integration) · [Carga de archivos](https://developers.notion.com/guides/data-apis/uploading-small-files)

## Configuración

| Variable de `.env` | Valor inicial / uso |
| --- | --- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434`; solo servidor local. |
| `OLLAMA_MODEL` | `qwen3:4b`; selección inicial del formulario. |
| `OLLAMA_TIMEOUT_SECONDS` | `300`; espera máxima por llamada al modelo. |
| `OLLAMA_CONTEXT` | `16384`; contexto solicitado al modelo. Aumentarlo consume más memoria. |
| `MAX_TEXT_CHARS` | `18000`; texto total máximo. También se comprueba un presupuesto conservador de contexto. |
| `NOTION_TOKEN` | Vacío; token privado opcional. |
| `NOTION_PARENT_PAGE_ID` | Vacío; usado solo al crear la base con el script. |
| `NOTION_DATA_SOURCE_ID` | Vacío; destino de las solicitudes. |

Reinicia la aplicación después de editar `.env`. Los modelos etiquetados como `cloud` o remotos no aparecen en el selector.

## Límites y soluciones rápidas

- **Ollama sin conexión:** abre Ollama. Si se acaba de instalar, vuelve a abrir VS Code para actualizar el PATH. Comprueba `ollama list`. Usa `ollama serve` solo si no hay un servicio ya escuchando en el puerto 11434.
- **El modelo tarda mucho:** la primera carga tarda más. Cierra programas que consuman RAM/VRAM o usa un modelo menor; para diagnosticar el uso de GPU, consulta `ollama ps`.
- **PDF escaneado:** esta versión no incluye OCR ni visión. Si una página no contiene texto extraíble, se rechaza el archivo completo para no decidir sobre información incompleta. Realiza OCR antes de cargarlo.
- **Texto demasiado largo:** se rechaza sin recortarlo. El límite inicial es de 18 000 caracteres en conjunto; ampliar contexto requiere memoria y soporte del modelo.
- **Carencia en meses o cláusulas ambiguas:** revisión humana, sin aproximar meses a 30 días.
- **Fecha desconocida:** no se supone la fecha actual ni la fecha de emisión del informe. Incluye la fecha de cirugía solicitada.
- **Respuesta JSON inválida:** se intenta una corrección una vez. Si vuelve a fallar, se muestra el error y no se inventa una decisión.
- **Puerto 8000 ocupado:** cierra otra instancia. Puedes cambiar el puerto en `run.py` y abrir la dirección correspondiente.
- **Sin póliza o informe:** todavía no se han incluido los documentos de demostración; se prepararán después de que el proyecto esté listo en tu equipo.

Se aceptan 5 MB y hasta 40 páginas por archivo, sujetos al límite total de texto. Los originales y resultados están en `data/`; el ZIP no incluye datos de usuarios. No publiques este servidor local directamente: la autenticación, las garantías de almacenamiento y la operación pública quedan para la fase de despliegue.

## Estructura para modificarlo

| Archivo | Responsabilidad |
| --- | --- |
| `run.py` | Iniciar el servidor local. |
| `app/main.py` | Rutas, carga de archivos e historial. |
| `app/ai.py` | Prompt, conexión con Ollama y salida JSON. |
| `app/models.py` | Esquema de extracción. |
| `app/rules.py` | Cálculos y reglas de decisión. |
| `app/documents.py` | Lectura de PDF/TXT/MD. |
| `app/storage.py` | SQLite y originales locales. |
| `app/notion.py` | Sincronización opcional. |
| `static/` | HTML, CSS y JavaScript de la interfaz. |
| `tests/` | Pruebas de reglas y API con un servidor de IA simulado. |

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan datos sintéticos y un servidor de Ollama simulado para comprobar transporte, esquema, citas, cálculos, manejo de errores, persistencia y descarga sin instalar pesos. **No miden la precisión clínica o documental de un modelo real.** La prueba de conexión de la interfaz sí invoca tu modelo. La evaluación real de las tres solicitudes de demostración queda para cuando lo ejecutes en tu PC.

La validación del paquete se ejecutó con Python 3.12 en Linux. Los iniciadores de Windows están preparados, pero no se ejecutaron sobre Windows desde este entorno. La interfaz tiene comprobación de sintaxis JavaScript; la revisión visual en navegador no pudo completarse aquí.

## Entrega posterior del reto

El código está listo para importarlo a un repositorio. `.gitignore` excluye datos, secretos, entornos y pesos. No se ha creado un repositorio remoto ni un enlace público. El siguiente paso será preparar una póliza ficticia y tres solicitudes: completa, documentación faltante y carencia pendiente; después conectaremos Notion y revisaremos el despliegue.
