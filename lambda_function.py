"""
AWS Lambda Function – Serverless Architecture Copilot
Inference: Amazon Bedrock (Nova Micro)
Persistence: Amazon DynamoDB (HistorialConsultas)
Trigger: DynamoDB Streams -> SNS Worker
"""

import json
import base64
import uuid
from datetime import datetime, timezone
import boto3
from botocore.config import Config

boto_config = Config(
    region_name="us-east-1",
    retries={"max_attempts": 3, "mode": "adaptive"}
)

bedrock = boto3.client(service_name="bedrock-runtime", config=boto_config)
dynamodb = boto3.resource("dynamodb", config=boto_config)
tabla = dynamodb.Table("HistorialConsultas")


def validate_input(raw: str | None) -> str | None:
    if not raw:
        return None
    sanitized = str(raw).strip()
    return sanitized[:500] if sanitized else None


def extract_prompt_or_user(event: dict) -> tuple[str | None, str]:
    # 1. Query String (GET)
    qs_params = event.get("queryStringParameters") or {}
    raw_qs = qs_params.get("prompt") or qs_params.get("nombre")
    if raw_qs:
        validated = validate_input(raw_qs)
        if validated:
            return validated, "query_string"

    # 2. Body (POST)
    http_method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or ""
    ).upper()

    raw_body = event.get("body")
    if http_method == "POST" and raw_body:
        if event.get("isBase64Encoded", False):
            try:
                raw_body = base64.b64decode(raw_body).decode("utf-8")
            except Exception as exc:
                raise ValueError(f"Error decodificando Base64: {exc}") from exc

        try:
            body_data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Payload JSON invalido: {exc}") from exc

        if isinstance(body_data, dict):
            raw_body_text = body_data.get("prompt") or body_data.get("nombre")
            if raw_body_text:
                validated = validate_input(raw_body_text)
                if validated:
                    return validated, "body"

    return None, "none"


def generar_diagnostico_bedrock(consulta: str | None) -> str:
    prompt_tecnico = (
        "Eres un AWS Principal Solutions Architect evaluando un diseno serverless.\n"
        "Analiza el siguiente requerimiento tecnico y genera un diagnostico conciso, directo y estructurado:\n\n"
        "1. Servicios recomendados: (Menciona 2 a 3 servicios clave de AWS serverless)\n"
        "2. Pilar Well-Architected: (Especifica si aplica a Seguridad, Fiabilidad, Eficiencia o Costos y por que)\n"
        "3. Patron arquitectonico: (Menciona si es sincrono, asincrono o Event-Driven y su ventaja)\n\n"
        "Reglas estrictas: No des introducciones, ni disculpas, ni saludos tipo carta, ni firmes al final. "
        "Ve directo a los puntos numerados en maximo 120 palabras.\n\n"
        f"Requerimiento del cliente: {consulta or 'Diseno de arquitectura serverless escalable y resiliente'}"
    )

    try:
        response = bedrock.converse(
            modelId="amazon.nova-micro-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt_tecnico}]
                }
            ],
            inferenceConfig={
                "maxTokens": 220,
                "temperature": 0.3
            }
        )
        return response["output"]["message"]["content"][0]["text"].strip()
    except Exception as exc:
        print(f"[Bedrock Error] Excepcion en inferencia: {exc}")
        return f"Diagnostico en contingencia operativa: Inferencia no disponible temporalmente ({exc})."


def persistir_evento_dynamodb(consulta: str | None, mensaje: str, fuente: str) -> str:
    registro_id = str(uuid.uuid4())
    fecha_utc = datetime.now(timezone.utc).isoformat()

    item = {
        "id": registro_id,
        "usuario": str(consulta if consulta else "Escenario General"),
        "mensaje_bedrock": str(mensaje),
        "fuente_input": str(fuente),
        "timestamp": fecha_utc,
        "modelo": "amazon.nova-micro-v1:0"
    }

    print(f"[DynamoDB Info] Intentando guardar item con ID: {registro_id}")
    tabla.put_item(Item=item)
    print(f"[DynamoDB Info] Item guardado exitosamente: {registro_id}")
    return registro_id


def build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def lambda_handler(event: dict, context) -> dict:
    print(f"[Handler Info] Evento recibido: {json.dumps(event)}")
    try:
        http_method = (
            event.get("httpMethod")
            or event.get("requestContext", {}).get("http", {}).get("method")
            or ""
        ).upper()

        if http_method == "OPTIONS":
            return build_response(204, {})

        try:
            prompt_input, fuente = extract_prompt_or_user(event)
        except ValueError as exc:
            return build_response(400, {"error": str(exc)})

        print(f"[Handler Info] Prompt extraido: '{prompt_input}' desde fuente: '{fuente}'")

        # 1. Bedrock
        diagnostico_ia = generar_diagnostico_bedrock(prompt_input)
        print(f"[Handler Info] Inferencia completada ({len(diagnostico_ia)} caracteres)")

        # 2. DynamoDB
        registro_id = "sin_registro"
        try:
            registro_id = persistir_evento_dynamodb(prompt_input, diagnostico_ia, fuente)
        except Exception as err_db:
            print(f"[DynamoDB Error] Fallo al persistir: {err_db}")

        return build_response(200, {
            "mensaje": diagnostico_ia,
            "fuente": fuente,
            "servicio_ia": "Amazon Bedrock (Amazon Nova Micro)",
            "registro_id": registro_id
        })

    except Exception as exc:
        print(f"[Unhandled Error] Fallo critico en handler: {exc}")
        return build_response(500, {"error": "Error interno al procesar la solicitud"})