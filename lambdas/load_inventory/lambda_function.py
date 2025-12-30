"""
Lambda A: load_inventory
Lee archivos CSV del S3 y carga registros en DynamoDB.
Disparada por eventos PutObject de S3.
"""

import json
import csv
import io
import os
from decimal import Decimal
import boto3

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = os.environ["TABLE_NAME"]
REGION = os.environ.get("REGION", "eu-west-1")

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Procesa archivos CSV subidos a S3.
    
    Formato esperado del CSV:
    Store,Item,Count
    Berlin,Widget-001,100
    Berlin,Widget-002,50
    """
    
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Obtener detalles del objeto S3
        records = event.get("Records", [])
        
        for record in records:
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
            
            print(f"Procesando: s3://{bucket}/{key}")
            
            # Descargar CSV
            response = s3.get_object(Bucket=bucket, Key=key)
            csv_content = response["Body"].read().decode("utf-8")
            
            # Parsear CSV
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            items_inserted = 0
            
            for row in csv_reader:
                try:
                    store = row["Store"].strip()
                    item = row["Item"].strip()
                    count = int(row["Count"])
                    
                    # Insertar en DynamoDB
                    table.put_item(
                        Item={
                            "Store": store,
                            "Item": item,
                            "Count": count
                        }
                    )
                    items_inserted += 1
                    print(f"  ✓ Insertado: {store} - {item} (x{count})")
                
                except Exception as e:
                    print(f"  ✗ Error al insertar fila: {e}")
                    continue
            
            print(f"Total insertados: {items_inserted}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "CSV procesado exitosamente",
                "items_inserted": items_inserted
            })
        }
    
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
