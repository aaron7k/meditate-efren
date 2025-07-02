
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

class Settings(BaseSettings):
    """
    Configuraciones de la aplicación, cargadas desde variables de entorno.
    """
    # Clave de API de Google para el modelo Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # Clave de API de ElevenLabs
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

    # (Opcional) ID de la voz de ElevenLabs que deseas usar
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

    # Directorio donde se guardarán los audios y scripts generados
    GENERATED_MEDIA_DIR: str = "generated_media"

    # URL del webhook para notificar la finalización de la generación de audio
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

    # Configuraciones de MinIO S3
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "meditation-audios")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Crear una instancia de la configuración para ser usada en la aplicación
settings = Settings()
