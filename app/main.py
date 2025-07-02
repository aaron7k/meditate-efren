
import os
import time
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from app.models.meditation_models import MeditationRequest
from app.services.meditation_service import generar_meditacion_personalizada
from app.core.config import settings

class InitialResponse(BaseModel):
    message: str
    task_id: str

app = FastAPI(
    title="API de Meditación Personalizada",
    description="Genera audios de meditación guiada usando IA.",
    version="1.0.0"
)

@app.post(
    "/generar-meditacion/",
    response_model=InitialResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inicia la generación de un audio de meditación y notifica vía webhook",
    tags=["Meditación"]
)
async def generar_meditacion_endpoint(request: MeditationRequest, background_tasks: BackgroundTasks):
    """
    Recibe los datos de personalización, inicia la generación en segundo plano
    y devuelve una respuesta inmediata. La notificación de finalización se envía
    a través de un webhook.
    """
    task_id = f"meditation_{int(time.time())}" # Generar un ID único para la tarea
    print(f"Recibida solicitud para generar meditación para: {request.nombre_usuario}. Task ID: {task_id}")
    
    background_tasks.add_task(
        generar_meditacion_personalizada,
        nombre_usuario=request.nombre_usuario,
        emocion_reconocida=request.emocion_reconocida,
        objetivo_meditacion=request.objetivo_meditacion,
        duracion_minutos=request.duracion_minutos,
        task_id=task_id
    )
    
    return {"message": "Generación de meditación iniciada en segundo plano. Se notificará vía webhook al finalizar.", "task_id": task_id}
