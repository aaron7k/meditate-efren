
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Ajustar la ruta de importación para que funcione con la nueva estructura
from app.main import app

# Crear un cliente de prueba para la aplicación FastAPI
client = TestClient(app)

@pytest.fixture
def mock_generate_meditation():
    """
    Fixture de Pytest para simular (mock) la función de generación de audio.
    Esto evita llamadas reales a las APIs de Google y ElevenLabs durante las pruebas.
    """
    # El decorador @patch intercepta la llamada a la función especificada
    # y la reemplaza con un objeto "mock".
    with patch("app.main.generar_meditacion_personalizada") as mock_function:
        # Configuramos el mock para que devuelva valores de ejemplo.
        # Esto simula un resultado exitoso de la función original.
        mock_function.return_value = (
            "/path/to/fake/audio.mp3",
            "/path/to/fake/script.txt"
        )
        # 'yield' pasa el control al test que usa este fixture.
        # El código después de yield se ejecuta al final del test (limpieza).
        yield mock_function

def test_generar_meditacion_success(mock_generate_meditation):
    """
    Prueba el endpoint /generar-meditacion/ para un caso de éxito.
    Verifica que la API responde correctamente cuando la solicitud es válida.
    """
    # Datos de ejemplo para la solicitud a la API
    test_payload = {
        "nombre_usuario": "TestUser",
        "emocion_reconocida": "testing",
        "objetivo_meditacion": "verificar la API",
        "duracion_minutos": 1
    }

    # Realizar una solicitud POST al endpoint de la API usando el cliente de prueba
    response = client.post("/generar-meditacion/", json=test_payload)

    # --- Verificaciones (Asserts) ---

    # 1. Verificar que el código de estado de la respuesta es 201 (Created)
    assert response.status_code == 201

    # 2. Verificar que la función simulada fue llamada exactamente una vez
    mock_generate_meditation.assert_called_once()

    # 3. Verificar que la función simulada fue llamada con los argumentos correctos
    mock_generate_meditation.assert_called_with(
        nombre_usuario="TestUser",
        emocion_reconocida="testing",
        objetivo_meditacion="verificar la API",
        duracion_minutos=1
    )

    # 4. Verificar que el cuerpo de la respuesta JSON contiene los datos esperados
    response_data = response.json()
    assert response_data["message"] == "Audio y script de meditación generados exitosamente."
    assert "audio_url" in response_data
    assert "script_url" in response_data

def test_generar_meditacion_invalid_payload():
    """
    Prueba el endpoint con datos inválidos para asegurar que la validación de Pydantic funciona.
    """
    # Datos inválidos (falta el campo "nombre_usuario")
    invalid_payload = {
        "emocion_reconocida": "testing",
        "objetivo_meditacion": "verificar la validación",
        "duracion_minutos": 1
    }

    # Realizar la solicitud con datos inválidos
    response = client.post("/generar-meditacion/", json=invalid_payload)

    # Verificar que la API responde con un código de estado 422 (Unprocessable Entity),
    # que es el código estándar de FastAPI para errores de validación.
    assert response.status_code == 422
