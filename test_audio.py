import os
import io
from pydub import AudioSegment
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

# Asegúrate de que estas variables estén en tu .env
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

# Configurar rutas de FFmpeg y FFprobe para pydub
os.environ["FFMPEG_PATH"] = "/opt/homebrew/bin/ffmpeg"
os.environ["FFPROBE_PATH"] = "/opt/homebrew/bin/ffprobe"

if not ELEVENLABS_API_KEY:
    print("Error: ELEVENLABS_API_KEY no está configurada en el archivo .env")
    exit()

print("Iniciando prueba de generación de audio...")

try:
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    text_to_generate = "Hola, esta es una prueba de audio desde ElevenLabs."
    
    audio_stream = client.text_to_speech.convert(
        text=text_to_generate,
        voice_id=ELEVENLABS_VOICE_ID,
        output_format="mp3_44100_128",
        model_id="eleven_multilingual_v2",
    )
    
    audio_data = b"".join(list(audio_stream))
    
    # Guardar el audio
    output_file = "test_output.mp3"
    AudioSegment.from_file(io.BytesIO(audio_data), format="mp3").export(output_file, format="mp3")
    
    print(f"Audio de prueba generado exitosamente en: {output_file}")

except Exception as e:
    print(f"Ocurrió un error durante la generación de audio: {e}")
