"""
Lambda B: get_inventory_api
Expone datos de DynamoDB vía HTTP API.
Rutas:
  GET /items -> Todos los items
  GET /items/{store} -> Items de una tienda específica
"""

import json
import os
from decimal import Decimal
import boto3

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["TABLE_NAME"]
REGION = os.environ.get("REGION", "eu-west-1")

table = dynamodb.Table(TABLE_NAME)


def decimal_default(obj):
    """Serializar Decimal a float para JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def get_all_items():
    """Obtiene todos los items del inventario."""
    try:
        response = table.scan()
        items = response.get("Items", [])
        
        # Manejar paginación
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "items": items,
                "count": len(items)
            }, default=decimal_default)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def get_items_by_store(store):
    """Obtiene items de una tienda específica."""
    try:
        response = table.query(
            KeyConditionExpression="#store = :store",
            ExpressionAttributeNames={"#store": "Store"},
            ExpressionAttributeValues={":store": store}
        )
        items = response.get("Items", [])
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "store": store,
                "items": items,
                "count": len(items)
            }, default=decimal_default)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def lambda_handler(event, context):
    """
    Maneja solicitudes HTTP desde API Gateway v2.
    
    Rutas soportadas:
    - GET /items -> todos los items
    - GET /items/{store} -> items de una tienda específica
    """
    print(f"Event completo: {json.dumps(event, default=str)}")
    
    # Obtener información de la solicitud
    path = event.get("rawPath", "")
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    
    print(f"Path: {path}")
    print(f"Route Key: {route_key}")
    print(f"Path Parameters: {path_params}")
    
    # Intentar obtener el parámetro store de varias formas
    store = None
    
    # 1. Primero intentar desde pathParameters (lo más confiable)
    if path_params and isinstance(path_params, dict) and "store" in path_params:
        store = path_params.get("store")
        print(f"Store desde pathParameters: {store}")
    
    # 2. Si no, intentar extraer del rawPath (fallback)
    if not store and "/items/" in path:
        parts = path.split("/")
        if len(parts) >= 3:
            store = parts[-1]
            print(f"Store extraído del path: {store}")
    
    # Si tenemos un store, consultar por tienda
    if store:
        print(f"Consultando items para tienda: {store}")
        return get_items_by_store(store)
    
    # Si no hay tienda específica, obtener todos
    elif "/items" in route_key or "/items" in path:
        print(f"Consultando todos los items")
        return get_all_items()
    
    else:
        print(f"Ruta no reconocida")
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"Ruta no encontrada: {path}"})
        }
