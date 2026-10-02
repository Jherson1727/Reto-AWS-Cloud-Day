import json
import boto3

sns = boto3.client("sns", region_name="us-east-1")
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:279332906930:alertas-consultas-bedrock"


def lambda_handler(event, context):
    print(f"Evento recibido en worker: {json.dumps(event)}")
    records = event.get("Records", [])

    for record in records:
        event_name = record.get("eventName", "")
        # Solo procesamos inserciones nuevas en DynamoDB
        if event_name in ["INSERT", "MODIFY"] or "dynamodb" in record:
            ddb_data = record.get("dynamodb", {})
            new_image = ddb_data.get("NewImage", {})

            # Extracción segura de tipos DynamoDB ({'S': 'valor'})
            item_id = new_image.get("id", {}).get("S", "Desconocido")
            usuario = new_image.get("usuario", {}).get("S", "Consulta Web")
            modelo = new_image.get("modelo", {}).get("S", "Amazon Nova Micro")
            timestamp = new_image.get("timestamp", {}).get("S", "")

            mensaje = (
                "=== ALERTA DE ARQUITECTURA SERVERLESS ===\n\n"
                f"ID Auditoria: {item_id}\n"
                f"Fecha UTC: {timestamp}\n"
                f"Modelo: {modelo}\n\n"
                f"Requerimiento del Usuario:\n{usuario}\n\n"
                "Estado: Procesado por Amazon Bedrock y persistido en DynamoDB."
            )

            try:
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject="Nueva Consulta - Copiloto AWS",
                    Message=mensaje
                )
                print(f"Notificacion SNS enviada para item {item_id}")
            except Exception as exc:
                print(f"Error publicando en SNS: {exc}")

    return {"statusCode": 200, "body": "OK"}