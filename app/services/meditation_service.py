import os
import io
import time
import re
from typing import Dict
import httpx # Importar httpx para solicitudes HTTP
from minio import Minio # Importar el cliente Minio
from minio.error import S3Error

from pydub import AudioSegment
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings

# Configuración de la voz de ElevenLabs para un tono de meditación
VOICE_SETTINGS = VoiceSettings(
    stability=0.20,
    similarity_boost=0.75,
    style=0.05,
    use_speaker_boost=True
)

# Diccionario de duraciones de pausa en milisegundos
PAUSE_DURATIONS: Dict[str, int] = {
    "COMMA_PAUSE": 2000,  # 2 segundos para comas
    "PERIOD_PAUSE": 3000, # 3 segundos para puntos
    "NEWLINE_PAUSE": 4000 # 4 segundos para saltos de línea
}

def estimate_speech_duration(text: str) -> float:
    """
    Estima la duración del habla de un texto en segundos.
    Basado en una velocidad promedio de 130 palabras por minuto (aprox. 2.17 palabras/segundo).
    """
    words = len(text.split())
    return words / 2.17

async def generar_meditacion_personalizada(
    nombre_usuario: str,
    emocion_reconocida: str,
    objetivo_meditacion: str,
    duracion_minutos: int = 15,
    task_id: str = ""
):
    """
    Genera un audio de meditación personalizado de forma iterativa y envía el resultado a un webhook.
    """
    if not settings.ELEVENLABS_API_KEY or not settings.GOOGLE_API_KEY:
        error_msg = "Las claves API (ELEVENLABS_API_KEY, GOOGLE_API_KEY) deben estar configuradas como variables de entorno."
        print(f"Error de configuración: {error_msg}")
        await send_webhook_notification(task_id, "failed", error_msg)
        return

    if not settings.WEBHOOK_URL:
        error_msg = "WEBHOOK_URL no está configurado en las variables de entorno. No se enviará notificación."
        print(f"Advertencia: {error_msg}")
        # No se envía webhook si no hay URL, pero la generación puede continuar si es solo una advertencia

    # Inicializar cliente MinIO
    minio_client = None
    if settings.MINIO_ENDPOINT and settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY:
        try:
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            # Asegurarse de que el bucket existe
            if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
                minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
                print(f"Bucket '{settings.MINIO_BUCKET_NAME}' creado en MinIO.")
        except S3Error as e:
            error_msg = f"Error al conectar o configurar MinIO S3: {e}"
            print(error_msg)
            await send_webhook_notification(task_id, "failed", error_msg)
            return
        except Exception as e:
            error_msg = f"Error inesperado al inicializar MinIO S3: {e}"
            print(error_msg)
            await send_webhook_notification(task_id, "failed", error_msg)
            return
    else:
        error_msg = "Las variables de entorno de MinIO S3 no están completamente configuradas. No se guardarán archivos en S3."
        print(f"Advertencia: {error_msg}")
        # Si MinIO no está configurado, la generación puede continuar, pero los archivos no se guardarán en S3.
        # En un entorno de producción, esto debería ser un error crítico.

    client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    output_parser = StrOutputParser()

    full_script_meditacion = []
    current_duration_ms = 0
    target_duration_ms = duracion_minutos * 60 * 1000
    
    meditation_stages = [
        {"stage": "Bienvenida y Acomodación", "instruction": "Comienza con un saludo cálido y guía al usuario a encontrar una postura cómoda."},
        {"stage": "Anclaje en la Respiración", "instruction": "Guía al usuario a centrar su atención en la respiración, con detalles sobre la sensación del aire."},
        {"stage": "Desarrollo del Objetivo (Parte 1)", "instruction": "Inicia el cuerpo principal de la meditación, enfocado en el objetivo específico. Sé muy descriptivo, usa metáforas y visualizaciones."},
        {"stage": "Desarrollo del Objetivo (Parte 2)", "instruction": "Continúa profundizando en el objetivo de la meditación con más detalles y visualizaciones."},
        {"stage": "Desarrollo del Objetivo (Parte 3)", "instruction": "Avanza en la visualización o el proceso de la meditación."},
        {"stage": "Integración y Retorno Suave", "instruction": "Guía una transición suave para que el usuario integre la experiencia y comience a volver al estado de alerta."},
        {"stage": "Cierre", "instruction": "Finaliza con un mensaje positivo y de agradecimiento."}
    ]

    try:
        for i, stage_info in enumerate(meditation_stages):
            if current_duration_ms >= target_duration_ms and i > 0:
                break

            stage_prompt = ChatPromptTemplate.from_messages([
                ("system", '''
Eres un guía de meditación experto, con una voz calmada y compasiva. Tu tarea es generar el guion para una meditación guiada.
El guion debe ser detallado, evocador y lo suficientemente extenso para que, combinado con las pausas, la duración total se aproxime a los {duracion_minutos} minutos. Incluye descripciones ricas y pasos pequeños para guiar al usuario.

El guion debe seguir una estructura clara:
1.  **Bienvenida y Acomodación:** Saludo cálido y personalizado, invitando a encontrar una postura cómoda.
2.  **Anclaje en la Respiración:** Guía para centrar la atención en la respiración, con detalles sobre la sensación del aire.
3.  **Desarrollo del Objetivo:** El cuerpo principal de la meditación, enfocado en el objetivo específico. Sé muy descriptivo, usa metáforas, visualizaciones, y guía al usuario a través de cada paso de la experiencia. Este debe ser el segmento más largo y detallado.
4.  **Integración y Retorno Suave:** Transición para que el usuario integre la experiencia y comience a volver al estado de alerta.
5.  **Cierre:** Un mensaje final positivo y de agradecimiento.

Utiliza un lenguaje sencillo, directo y evocador. Las comas, puntos y saltos de línea generarán pausas automáticamente. Para pausas explícitas de duración específica, usa el formato `[Xsec]`, donde X es la duración en segundos (ej. `[5sec]`).

IMPORTANTE: Responde únicamente con el texto del guion. No incluyas títulos, encabezados, ni explicaciones adicionales. Cada párrafo debe estar separado por un doble salto de línea.
                '''),
                ("human", f"Para {nombre_usuario}, quien siente {emocion_reconocida} y busca {objetivo_meditacion}. Genera la etapa '{stage_info['stage']}'.")
            ])
            chain = stage_prompt | llm | output_parser

            try:
                segment_text = chain.invoke({
                    "nombre_usuario": nombre_usuario,
                    "emocion_reconocida": emocion_reconocida,
                    "objetivo_meditacion": objetivo_meditacion,
                    "duracion_minutos": duracion_minutos
                })
                full_script_meditacion.append(segment_text)
                
                segment_speech_duration = estimate_speech_duration(segment_text) * 1000
                segment_pause_duration = 0
                # No necesitamos estimar pausas de puntuación aquí, solo las explícitas
                explicit_pause_matches = re.findall(r'\[(\d+)sec\]', segment_text)
                for sec in explicit_pause_matches:
                    segment_pause_duration += int(sec) * 1000
                
                current_duration_ms += segment_speech_duration + segment_pause_duration
                print(f"Etapa {i+1} generada. Duración estimada: {(segment_speech_duration + segment_pause_duration)/1000:.2f}s. Acumulado: {current_duration_ms/1000:.2f}s / {target_duration_ms/1000:.2f}s")

            except Exception as e:
                print(f"Error al generar etapa {stage_info['stage']}: {e}. Deteniendo la generación.")
                raise RuntimeError(f"Fallo al generar el guion con la IA: {e}")

        final_script = "\n\n".join(full_script_meditacion)

        timestamp = int(time.time())
        nombre_base_archivo = f"meditacion_{nombre_usuario.lower().replace(' ', '_')}_{timestamp}"
        
        # --- Subir script a MinIO S3 ---
        script_object_name = f"{nombre_base_archivo}.txt"
        script_data = final_script.encode('utf-8')
        script_data_stream = io.BytesIO(script_data)
        script_data_length = len(script_data)
        
        script_s3_url = ""
        if minio_client:
            try:
                minio_client.put_object(
                    settings.MINIO_BUCKET_NAME,
                    script_object_name,
                    script_data_stream,
                    script_data_length,
                    content_type="text/plain"
                )
                script_s3_url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{script_object_name}"
                print(f"Script subido a MinIO S3: {script_s3_url}")
            except S3Error as e:
                error_msg = f"Error al subir script a MinIO S3: {e}"
                print(error_msg)
                await send_webhook_notification(task_id, "failed", error_msg)
                return
            except Exception as e:
                error_msg = f"Error inesperado al subir script a MinIO S3: {e}"
                print(error_msg)
                await send_webhook_notification(task_id, "failed", error_msg)
                return
        else:
            print("MinIO S3 no configurado, el script no se subirá a S3.")

        print("Generando audio con ElevenLabs...")
        final_audio = AudioSegment.silent(duration=0)
        
        # Dividir el script en segmentos (párrafos y pausas explícitas [Xsec])
        # Usar una expresión regular para dividir por saltos de línea dobles o por marcadores de pausa [Xsec]
        # Capturamos los delimitadores para poder procesarlos
        segments_and_delimiters = re.split(r'(\n\n|\[\d+sec\])', final_script.strip())

        for item in segments_and_delimiters:
            if not item or item.isspace(): # Ignorar elementos vacíos o solo espacios
                continue

            # Manejar pausas explícitas [Xsec]
            match_explicit_pause = re.match(r'\[(\d+)sec\]', item)
            if match_explicit_pause:
                duration_ms = int(match_explicit_pause.group(1)) * 1000
                final_audio += AudioSegment.silent(duration=duration_ms)
                print(f"Añadida pausa explícita: {item} ({duration_ms}ms)")
                continue # Pasar al siguiente elemento

            # Manejar saltos de línea dobles (párrafos)
            if item == "\n\n":
                final_audio += AudioSegment.silent(duration=PAUSE_DURATIONS["NEWLINE_PAUSE"])
                print(f"Añadida pausa por salto de línea doble ({PAUSE_DURATIONS['NEWLINE_PAUSE']}ms)")
                continue # Pasar al siguiente elemento

            # Procesar texto para TTS y pausas de puntuación
            # Dividir el texto por comas y puntos, manteniendo los delimitadores
            parts_with_punctuation = re.split(r'([.,])', item)
            
            for part in parts_with_punctuation:
                if not part.strip():
                    continue

                if part == ",":
                    final_audio += AudioSegment.silent(duration=PAUSE_DURATIONS["COMMA_PAUSE"])
                    print(f"Añadida pausa por coma ({PAUSE_DURATIONS['COMMA_PAUSE']}ms)")
                elif part == ".":
                    final_audio += AudioSegment.silent(duration=PAUSE_DURATIONS["PERIOD_PAUSE"])
                    print(f"Añadida pausa por punto ({PAUSE_DURATIONS['PERIOD_PAUSE']}ms)")
                else:
                    # Limpiar el texto de cualquier marcador de pausa antiguo o espacios extra
                    text_to_speak = re.sub(r'\(PAUSA_[A-Z]+\)', '', part).strip()
                    if not text_to_speak: # Si después de limpiar no queda texto, ignorar
                        continue

                    try:
                        audio_stream = client.text_to_speech.convert(
                            text=text_to_speak,
                            voice_id=settings.ELEVENLABS_VOICE_ID,
                            output_format="mp3_44100_128",
                            model_id="eleven_multilingual_v2",
                        )
                        audio_data = b"".join(list(audio_stream))
                        
                        segmento_audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
                        final_audio += segmento_audio
                        print(f"Generado segmento de habla: '{text_to_speak[:30]}...' ")

                    except Exception as e:
                        print(f"Error al generar audio para el segmento: '{text_to_speak[:30]}...'. Error: {e}")
                        # En caso de error, añadir una pausa de respaldo para no romper el ritmo
                        final_audio += AudioSegment.silent(duration=PAUSE_DURATIONS["PERIOD_PAUSE"])

        # --- Subir audio a MinIO S3 ---
        audio_object_name = f"{nombre_base_archivo}.mp3"
        audio_data_stream = io.BytesIO()
        final_audio.export(audio_data_stream, format="mp3")
        audio_data_stream.seek(0) # Volver al inicio del stream
        audio_data_length = audio_data_stream.getbuffer().nbytes

        audio_s3_url = ""
        if minio_client:
            try:
                minio_client.put_object(
                    settings.MINIO_BUCKET_NAME,
                    audio_object_name,
                    audio_data_stream,
                    audio_data_length,
                    content_type="audio/mpeg"
                )
                audio_s3_url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{audio_object_name}"
                print(f"Audio subido a MinIO S3: {audio_s3_url}")
            except S3Error as e:
                error_msg = f"Error al subir audio a MinIO S3: {e}"
                print(error_msg)
                await send_webhook_notification(task_id, "failed", error_msg)
                return
            except Exception as e:
                error_msg = f"Error inesperado al subir audio a MinIO S3: {e}"
                print(error_msg)
                await send_webhook_notification(task_id, "failed", error_msg)
                return
        else:
            print("MinIO S3 no configurado, el audio no se subirá a S3.")

        # Enviar notificación de éxito al webhook
        await send_webhook_notification(
            task_id,
            "completed",
            "Audio y script de meditación generados exitosamente.",
            audio_url=audio_s3_url,
            script_url=script_s3_url
        )

    except Exception as e:
        error_msg = f"Error inesperado durante la generación de meditación: {e}"
        print(error_msg)
        await send_webhook_notification(task_id, "failed", error_msg)

async def send_webhook_notification(task_id: str, status: str, message: str, **kwargs):
    if not settings.WEBHOOK_URL:
        print("WEBHOOK_URL no configurado. No se enviará notificación.")
        return

    payload = {
        "task_id": task_id,
        "status": status,
        "message": message,
    }
    payload.update(kwargs)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status() # Lanza una excepción para códigos de estado HTTP 4xx/5xx
            print(f"Notificación de webhook enviada exitosamente para task_id {task_id}. Status: {response.status_code}")
    except httpx.RequestError as e:
        print(f"Error al enviar notificación de webhook para task_id {task_id}: {e}")
    except httpx.HTTPStatusError as e:
        print(f"Error de estado HTTP al enviar notificación de webhook para task_id {task_id}: {e.response.status_code} - {e.response.text}")
