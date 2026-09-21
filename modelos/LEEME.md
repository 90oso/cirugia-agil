# Cargar tu propio modelo

Los pesos del modelo viven en Ollama, no dentro de la página web. No se incluyen en el ZIP.

## Modelo que ya tienes en Ollama

1. Ejecuta `ollama list` para ver sus nombres.
2. Abre la aplicación y pulsa **Actualizar**.
3. Selecciona el modelo y pulsa **Probar conexión**.

Puedes fijar uno por defecto en `.env`: `OLLAMA_MODEL=nombre-de-tu-modelo`.

## Un archivo GGUF propio

Necesitas un modelo de instrucciones/chat compatible con Ollama y capaz de devolver JSON.

1. Guarda el archivo, por ejemplo, en `C:/Modelos/mi-modelo.gguf`.
2. Copia `Modelfile.example` como `Modelfile` dentro de esta carpeta.
3. Edita la línea `FROM` con la ruta real. Para evitar problemas, usa una ruta sin espacios.
4. En la terminal, desde la raíz del proyecto:

```powershell
ollama create cirugia-local -f modelos/Modelfile
ollama run cirugia-local
```

Escribe `/bye` para salir del chat. En la aplicación pulsa **Actualizar** y elige `cirugia-local:latest` (o el nombre exacto mostrado por Ollama).

Este proceso importa pesos existentes. No entrena un modelo desde cero. Un archivo `.pt` o cualquier carpeta de pesos no es automáticamente compatible: la arquitectura y el formato deben estar soportados. Ollama también documenta la importación de Safetensors compatibles.

## Cambiar la extracción y las reglas

- Instrucciones para la IA: `app/ai.py`, variable `SYSTEM`.
- Estructura de la respuesta JSON: `app/models.py`.
- Cálculos y decisión preliminar: `app/rules.py`.

Cambiar el prompt no cambia por sí solo los cálculos. Después de modificar reglas, ejecuta las pruebas de `tests`.

Fuentes: [importación de modelos](https://docs.ollama.com/import), [JSON estructurado](https://docs.ollama.com/capabilities/structured-outputs).
