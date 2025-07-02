
import os
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from app.models.meditation_models import MeditationRequest, MeditationResponse
from app.services.meditation_service import generar_meditacion_personalizada
from app.core.config import settings

app = FastAPI(
    title="API de Meditación Personalizada",
    description="Genera audios de meditación guiada usando IA.",
    version="1.0.0"
)

@app.post(
    "/generar-meditacion/",
    response_model=MeditationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Genera un nuevo audio de meditación",
    tags=["Meditación"]
)
async def generar_meditacion_endpoint(request: MeditationRequest):
    """
    Recibe los datos de personalización y genera un archivo de audio MP3.
    """
    try:
        print(f"Recibida solicitud para generar meditación para: {request.nombre_usuario}")
        
        ruta_archivo_audio, ruta_script_txt = generar_meditacion_personalizada(
            nombre_usuario=request.nombre_usuario,
            emocion_reconocida=request.emocion_reconocida,
            objetivo_meditacion=request.objetivo_meditacion,
            duracion_minutos=request.duracion_minutos
        )
        
        nombre_archivo_audio = os.path.basename(ruta_archivo_audio)
        audio_url = f"/media/{nombre_archivo_audio}"

        nombre_script_txt = os.path.basename(ruta_script_txt)
        script_url = f"/media/{nombre_script_txt}"

        print(f"Audio generado con éxito. URL: {audio_url}")
        print(f"Script generado con éxito. URL: {script_url}")

        return {
            "message": "Audio y script de meditación generados exitosamente.",
            "audio_url": audio_url,
            "audio_file_path": ruta_archivo_audio,
            "script_url": script_url,
            "script_file_path": ruta_script_txt
        }

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error de configuración del servicio: {ve}"
        )
    except Exception as e:
        print(f"Error inesperado durante la generación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error interno al generar la meditación: {e}"
        )

os.makedirs(settings.GENERATED_MEDIA_DIR, exist_ok=True)
app.mount(f"/media", StaticFiles(directory=settings.GENERATED_MEDIA_DIR), name="media")

@app.get("/", summary="Verifica el estado de la API", tags=["General"])
async def root():
    return {"status": "API de Meditación funcionando correctamente."}
