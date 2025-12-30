"""
Lambda C: notify_low_stock
Lee eventos de DynamoDB Streams y envía notificaciones por SNS
cuando el stock está bajo (Count < 50).
"""

import json
import os
from decimal import Decimal
import boto3

sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN = os.environ["TOPIC_ARN"]
REGION = os.environ.get("REGION", "eu-west-1")

LOW_STOCK_THRESHOLD = 50


def lambda_handler(event, context):
    """
    Procesa eventos de DynamoDB Streams.
    Envía notificación por SNS cuando el stock está bajo.
    """
    print(f"Event: {json.dumps(event, default=str)}")
    
    try:
        records = event.get("Records", [])
        print(f"Total registros recibidos: {len(records)}")
        
        notified_count = 0
        
        for i, record in enumerate(records):
            # Obtener el tipo de evento
            event_name = record["eventName"]  # INSERT, MODIFY, REMOVE
            
            print(f"\n[Registro {i+1}] Tipo de evento: {event_name}")
            
            # Obtener los datos nuevos/antiguos
            if event_name in ["INSERT", "MODIFY"]:
                new_image = record.get("dynamodb", {}).get("NewImage", {})
                
                # Convertir DynamoDB format a Python
                store = new_image.get("Store", {}).get("S", "Unknown")
                item = new_image.get("Item", {}).get("S", "Unknown")
                count = int(new_image.get("Count", {}).get("N", 0))
                
                print(f"  Store: {store}, Item: {item}, Stock: {count}")
                
                # Verificar stock bajo
                if count < LOW_STOCK_THRESHOLD:
                    message = f"""
⚠️ ALERTA DE STOCK BAJO

Tienda: {store}
Artículo: {item}
Stock actual: {count}
Umbral: {LOW_STOCK_THRESHOLD}

Por favor, reabastecer inmediatamente.
                    """
                    
                    subject = f"[ALERTA] Stock bajo: {item} en {store}"
                    
                    try:
                        sns.publish(
                            TopicArn=TOPIC_ARN,
                            Subject=subject,
                            Message=message
                        )
                        print(f"  ✓ Notificación SNS enviada para {item}")
                        notified_count += 1
                    except Exception as e:
                        print(f"  ✗ Error al enviar SNS: {e}")
                else:
                    print(f"  ℹ Stock OK ({count} >= {LOW_STOCK_THRESHOLD}), sin notificación")
            elif event_name == "REMOVE":
                print(f"  ℹ Evento REMOVE ignorado (sin notificación)")
            else:
                print(f"  ⚠ Tipo de evento desconocido: {event_name}")
        
        print(f"\n✓ Resumen: {notified_count} notificaciones enviadas")
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Eventos procesados, {notified_count} notificaciones enviadas"})
        }
    
    except Exception as e:
        print(f"✗ Error procesando eventos: {e}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
