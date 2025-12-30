#!/usr/bin/env python3
"""
Script para eliminar todos los recursos creados durante el despliegue.
"""

import json
import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_REGION", "us-east-1")
PROJECT_ROOT = Path(__file__).parent.parent

print(f"[*] Región: {REGION}")

# Clientes de AWS
s3_client = boto3.client("s3", region_name=REGION)
dynamodb_client = boto3.client("dynamodb", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)
iam_client = boto3.client("iam", region_name=REGION)
apigateway_client = boto3.client("apigatewayv2", region_name=REGION)
sns_client = boto3.client("sns", region_name=REGION)

# Cargar configuración de despliegue
config_file = PROJECT_ROOT / "infra" / "deployment.json"

if not config_file.exists():
    print("✗ Archivo deployment.json no encontrado. ¿Se ejecutó deploy.py primero?")
    sys.exit(1)

with open(config_file, "r") as f:
    config = json.load(f)

BUCKET_UPLOADS = config["bucket_uploads"]
BUCKET_WEB = config["bucket_web"]
TABLE_NAME = config["table_name"]
LAMBDA_LOAD_NAME = config["lambda_load"]
LAMBDA_API_NAME = config["lambda_api"]
LAMBDA_NOTIFY_NAME = config["lambda_notify"]
API_ID = config["api_id"]
IAM_ROLE = config["iam_role"]
TOPIC_ARN = config["sns_topic_arn"]

def empty_s3_bucket(bucket_name):
    """Vacía completamente un bucket S3, incluidas todas las versiones."""
    print(f"\n[*] Vaciando bucket S3: {bucket_name}...")
    try:
        # Primero, desactivar versionado para facilitar la eliminación
        try:
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={"Status": "Suspended"}
            )
            print(f"    ✓ Versionado suspendido en {bucket_name}")
        except:
            pass
        
        # Eliminar todas las versiones de objetos
        paginator = s3_client.get_paginator("list_object_versions")
        pages = paginator.paginate(Bucket=bucket_name)
        
        delete_markers = []
        objects_to_delete = []
        
        for page in pages:
            # Eliminar versiones de objetos
            if "Versions" in page:
                for version in page["Versions"]:
                    objects_to_delete.append({
                        "Key": version["Key"],
                        "VersionId": version["VersionId"]
                    })
            
            # Eliminar delete markers
            if "DeleteMarkers" in page:
                for marker in page["DeleteMarkers"]:
                    delete_markers.append({
                        "Key": marker["Key"],
                        "VersionId": marker["VersionId"]
                    })
        
        # Realizar eliminaciones en lotes (max 1000 por solicitud)
        all_deletes = objects_to_delete + delete_markers
        for i in range(0, len(all_deletes), 1000):
            batch = all_deletes[i:i+1000]
            if batch:
                s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": batch}
                )
        
        print(f"    ✓ Bucket {bucket_name} vaciado ({len(all_deletes)} objetos eliminados)")
    
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            print(f"    ℹ Bucket {bucket_name} no existe")
        else:
            print(f"    ⚠ Error vaciando bucket (intentando continuar): {e}")
    except Exception as e:
        print(f"    ⚠ Error vaciando bucket (intentando continuar): {e}")

def delete_s3_bucket(bucket_name):
    """Elimina un bucket S3 vacío."""
    print(f"\n[*] Eliminando bucket S3: {bucket_name}...")
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"    ✓ Bucket {bucket_name} eliminado")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            print(f"    ℹ Bucket {bucket_name} no existe")
        else:
            print(f"    ⚠ Error eliminando bucket (continuando...): {e}")

def delete_lambda(function_name):
    """Elimina una función Lambda."""
    print(f"\n[*] Eliminando Lambda: {function_name}...")
    try:
        # Primero eliminar event source mappings (para DynamoDB Streams)
        try:
            response = lambda_client.list_event_source_mappings(
                FunctionName=function_name
            )
            for mapping in response.get("EventSourceMappings", []):
                lambda_client.delete_event_source_mapping(
                    UUID=mapping["UUID"]
                )
                print(f"    ✓ Event source mapping eliminado")
        except:
            pass
        
        lambda_client.delete_function(FunctionName=function_name)
        print(f"    ✓ Lambda {function_name} eliminada")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"    ℹ Lambda {function_name} no existe")
        else:
            print(f"    ✗ Error: {e}")

def delete_api_gateway(api_id):
    """Elimina API Gateway."""
    print(f"\n[*] Eliminando API Gateway: {api_id}...")
    try:
        apigateway_client.delete_api(ApiId=api_id)
        print(f"    ✓ API Gateway {api_id} eliminada")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NotFoundException":
            print(f"    ℹ API Gateway {api_id} no existe")
        else:
            print(f"    ✗ Error: {e}")

def delete_dynamodb_table(table_name):
    """Elimina tabla DynamoDB."""
    print(f"\n[*] Eliminando tabla DynamoDB: {table_name}...")
    try:
        dynamodb_client.delete_table(TableName=table_name)
        print(f"    ✓ Tabla {table_name} marcada para eliminación")
        
        # Esperar a que se elimine
        waiter = dynamodb_client.get_waiter("table_not_exists")
        waiter.wait(TableName=table_name)
        print(f"    ✓ Tabla {table_name} eliminada")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"    ℹ Tabla {table_name} no existe")
        else:
            print(f"    ✗ Error: {e}")

def delete_iam_role(role_name):
    """Elimina rol IAM."""
    print(f"\n[*] Eliminando rol IAM: {role_name}...")
    try:
        # Primero eliminar políticas inline
        try:
            policies = iam_client.list_role_policies(RoleName=role_name)
            for policy_name in policies.get("PolicyNames", []):
                iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                print(f"    ✓ Política {policy_name} eliminada")
        except:
            pass
        
        iam_client.delete_role(RoleName=role_name)
        print(f"    ✓ Rol {role_name} eliminado")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print(f"    ℹ Rol {role_name} no existe")
        else:
            print(f"    ✗ Error: {e}")

def delete_all_low_stock_topics():
    """Elimina todos los topics SNS cuyo nombre contiene 'low-stock'."""
    print("\n[*] Eliminando todos los topics SNS 'low-stock'...")
    response = sns_client.list_topics()
    for topic in response.get("Topics", []):
        arn = topic["TopicArn"]
        if "low-stock" in arn:
            try:
                # Borrar suscripciones primero
                subs = sns_client.list_subscriptions_by_topic(TopicArn=arn)
                for sub in subs.get("Subscriptions", []):
                    try:
                        sns_client.unsubscribe(SubscriptionArn=sub["SubscriptionArn"])
                        print(f"    ✓ Suscripción eliminada: {sub['SubscriptionArn']}")
                    except ClientError:
                        pass
                # Borrar topic
                sns_client.delete_topic(TopicArn=arn)
                print(f"    ✓ Topic eliminado: {arn}")
            except ClientError as e:
                print(f"    ⚠ Error eliminando {arn}: {e}")

def main():
    print("\n" + "="*60)
    print("DESTRUCCIÓN DE RECURSOS SERVERLESS AWS")
    print("="*60)
    print(f"\nEstos recursos serán eliminados:")
    print(f"  - Buckets S3: {BUCKET_UPLOADS}, {BUCKET_WEB}")
    print(f"  - Tabla DynamoDB: {TABLE_NAME}")
    print(f"  - Lambdas: {LAMBDA_LOAD_NAME}, {LAMBDA_API_NAME}, {LAMBDA_NOTIFY_NAME}")
    print(f"  - API Gateway: {API_ID}")
    print(f"  - Rol IAM: {IAM_ROLE}")
    print(f"  - Tema SNS: {TOPIC_ARN}")
    print(f"  - Archivo de configuración: {config_file}")
    
    response = input("\n¿Estás seguro? Escribe 'sí' para confirmar: ").strip().lower()
    
    if response != "sí":
        print("Operación cancelada.")
        return
    
    try:
        # 0. Eliminar archivo de configuración PRIMERO (para evitar inconsistencias)
        print(f"\n[*] Eliminando archivo de configuración...")
        try:
            config_file.unlink()
            print(f"    ✓ Archivo de configuración eliminado")
        except:
            pass
        
        # 1. Eliminar Lambdas
        delete_lambda(LAMBDA_LOAD_NAME)
        delete_lambda(LAMBDA_API_NAME)
        delete_lambda(LAMBDA_NOTIFY_NAME)
        
        # 2. Eliminar API Gateway
        delete_api_gateway(API_ID)
        
        # 3. Eliminar tabla DynamoDB
        delete_dynamodb_table(TABLE_NAME)
        
        # 4. Vaciar y eliminar buckets S3
        empty_s3_bucket(BUCKET_UPLOADS)
        delete_s3_bucket(BUCKET_UPLOADS)
        empty_s3_bucket(BUCKET_WEB)
        delete_s3_bucket(BUCKET_WEB)
        
        # 5. Eliminar rol IAM
        delete_iam_role(IAM_ROLE)
        
        # 6. Eliminar tema SNS
        delete_all_low_stock_topics()
        
        print("\n" + "="*60)
        print("✓ DESTRUCCIÓN COMPLETADA")
        print("="*60)
        print("\nTodos los recursos han sido eliminados exitosamente.")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
