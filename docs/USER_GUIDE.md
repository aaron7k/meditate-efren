# Guía de Usuario: API de Meditación Personalizada

¡Bienvenido/a a la API de Meditación Personalizada! Esta guía te ayudará a entender cómo utilizar nuestro servicio para generar audios de meditación únicos y adaptados a tus necesidades.

## ¿Qué hace esta API?

Nuestra API crea un audio de meditación guiada completamente nuevo cada vez que la usas. Lo hace combinando inteligencia artificial para escribir un guion y para generar una voz que lo narre.

Puedes personalizar la meditación indicando:
-   **Tu nombre**: Para que el audio se dirija a ti directamente.
-   **Tu emoción actual**: ¿Sientes estrés, ansiedad, o simplemente quieres relajarte?
-   **Tu objetivo**: ¿Qué buscas lograr con la meditación? (ej. "dormir mejor", "concentrarme para estudiar", "liberar la tensión del día").
-   **Duración**: El tiempo que deseas que dure la meditación (entre 1 y 60 minutos).

## ¿Cómo se usa?

Para generar un audio, necesitas enviar una solicitud a nuestro endpoint principal. No necesitas ser un programador experto, puedes usar herramientas como [Postman](https://www.postman.com/) o `curl` desde tu terminal.

### Endpoint

-   **URL**: `http://127.0.0.1:8000/generar-meditacion/`
-   **Método**: `POST`

### Datos de la solicitud (Cuerpo/Body)

Debes enviar los datos en formato JSON, con la siguiente estructura:

```json
{
  "nombre_usuario": "Tu Nombre",
  "emocion_reconocida": "La emoción que sientes",
  "objetivo_meditacion": "Lo que quieres lograr",
  "duracion_minutos": 10
}
```

**Ejemplo práctico:**

Supongamos que te llamas "Carlos", te sientes "abrumado por el trabajo" y quieres "despejar la mente para descansar". Quieres una meditación de 15 minutos. Tu solicitud se vería así:

```json
{
  "nombre_usuario": "Carlos",
  "emocion_reconocida": "abrumado por el trabajo",
  "objetivo_meditacion": "despejar la mente para descansar",
  "duracion_minutos": 15
}
```

### ¿Qué recibes a cambio?

La API te responderá inmediatamente con un estado `202 Accepted` indicando que la generación ha comenzado en segundo plano. Una vez que el audio y el script se hayan generado, se enviará una notificación con los detalles a la `WEBHOOK_URL` configurada en el servidor.

**Ejemplo de respuesta inicial (HTTP 202 Accepted):**

```json
{
  "message": "Generación de meditación iniciada en segundo plano. Se notificará vía webhook al finalizar.",
  "task_id": "meditation_1751341245"
}
```

**Ejemplo de Payload del Webhook (POST a `WEBHOOK_URL`):**

```json
{
  "task_id": "meditation_1751341245",
  "status": "completed",
  "message": "Audio y script de meditación generados exitosamente.",
  "audio_url": "/media/meditacion_carlos_1751341245.mp3",
  "audio_file_path": "/ruta/en/el/servidor/generated_media/meditacion_carlos_1751341245.mp3",
  "script_url": "/media/meditacion_carlos_1751341245.txt",
  "script_file_path": "/ruta/en/el/servidor/generated_media/meditacion_carlos_1751341245.txt"
}
```

O en caso de error:

```json
{
  "task_id": "meditation_1751341245",
  "status": "failed",
  "message": "Error inesperado durante la generación de meditación: Fallo al generar el guion con la IA: ..."
}
```

Para escuchar tu meditación, una vez recibida la notificación del webhook, combina la dirección base de la API con la `audio_url` proporcionada. Por ejemplo: `http://127.0.0.1:8000/media/meditacion_carlos_1751341245.mp3`.
