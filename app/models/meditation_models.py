
from pydantic import BaseModel, Field

class MeditationRequest(BaseModel):
    """
    Modelo para la solicitud de generación de meditación.
    Define los datos que el cliente debe enviar.
    """
    nombre_usuario: str = Field(
        ..., 
        description="Nombre del usuario para personalizar la meditación.",
        json_schema_extra={"example": "Elena"}
    )
    emocion_reconocida: str = Field(
        ..., 
        description="Emoción o estado actual del usuario.",
        json_schema_extra={"example": "ansiedad por el futuro"}
    )
    objetivo_meditacion: str = Field(
        ..., 
        description="El objetivo que el usuario quiere alcanzar con la meditación.",
        json_schema_extra={"example": "encontrar calma y aceptación en el presente"}
    )
    duracion_minutos: int = Field(
        ..., 
        gt=0, 
        description="Duración deseada de la meditación en minutos.",
        json_schema_extra={"example": 10}
    )

class MeditationResponse(BaseModel):
    """
    Modelo para la respuesta de la API tras generar la meditación.
    """
    message: str
    audio_url: str
    audio_file_path: str
    script_url: str
    script_file_path: str
