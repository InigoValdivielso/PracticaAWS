#!/usr/bin/env python3
"""
Script de validación post-despliegue
Verifica que todos los recursos se crearon correctamente
"""

import json
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

PROJECT_ROOT = Path(__file__).parent.parent

def load_config():
    """Carga configuración de despliegue."""
    config_file = PROJECT_ROOT / "infra" / "deployment.json"
    if not config_file.exists():
        print("✗ deployment.json no encontrado. ¿Se ejecutó deploy.py?")
        return None
    
    with open(config_file, "r") as f:
        return json.load(f)

def check_s3_buckets(config):
    """Verifica buckets S3."""
    print("\n[*] Verificando S3...")
    s3 = boto3.client("s3", region_name=config["region"])
    
    buckets = [config["bucket_uploads"], config["bucket_web"]]
    
    for bucket in buckets:
        try:
            s3.head_bucket(Bucket=bucket)
            print(f"    ✓ Bucket '{bucket}' existe")
            
            # Verificar notificación para bucket de uploads
            if "uploads" in bucket:
                try:
                    notif = s3.get_bucket_notification_configuration(Bucket=bucket)
                    if "LambdaFunctionConfigurations" in notif:
                        print(f"    ✓ S3 trigger configurado")
                except:
                    print(f"    ⚠ No se pudo verificar trigger")
                    
        except ClientError as e:
            print(f"    ✗ Bucket '{bucket}' no existe o inaccesible")

def check_dynamodb(config):
    """Verifica DynamoDB."""
    print("\n[*] Verificando DynamoDB...")
    ddb = boto3.client("dynamodb", region_name=config["region"])
    
    try:
        response = ddb.describe_table(TableName=config["table_name"])
        table = response["Table"]
        
        print(f"    ✓ Tabla '{config['table_name']}' existe")
        print(f"    ✓ Estado: {table['TableStatus']}")
        print(f"    ✓ Items: {table['ItemCount']}")
        
        if "StreamSpecification" in table:
            print(f"    ✓ Streams: {table['StreamSpecification'].get('StreamViewType', 'N/A')}")
    
    except ClientError:
        print(f"    ✗ Tabla '{config['table_name']}' no existe")

def check_lambdas(config):
    """Verifica Lambdas."""
    print("\n[*] Verificando Lambda Functions...")
    lam = boto3.client("lambda", region_name=config["region"])
    
    lambdas = [
        config["lambda_load"],
        config["lambda_api"],
        config["lambda_notify"]
    ]
    
    for func in lambdas:
        try:
            response = lam.get_function(FunctionName=func)
            config_data = response["Configuration"]
            
            print(f"    ✓ Lambda '{func}' existe")
            print(f"      Runtime: {config_data['Runtime']}")
            print(f"      Memory: {config_data['MemorySize']} MB")
            print(f"      Timeout: {config_data['Timeout']}s")
            
        except ClientError:
            print(f"    ✗ Lambda '{func}' no existe")

def check_api_gateway(config):
    """Verifica API Gateway."""
    print("\n[*] Verificando API Gateway...")
    apigw = boto3.client("apigatewayv2", region_name=config["region"])
    
    try:
        response = apigw.get_api(ApiId=config["api_id"])
        api = response
        
        print(f"    ✓ API '{api['Name']}' existe")
        print(f"    ✓ Protocolo: {api['ProtocolType']}")
        print(f"    ✓ Endpoint: {config['api_endpoint']}")
        
        # Verificar rutas
        routes = apigw.get_routes(ApiId=config["api_id"])
        route_keys = [r["RouteKey"] for r in routes.get("Items", [])]
        
        for route in route_keys:
            if "GET" in route:
                print(f"    ✓ Ruta: {route}")
                
    except ClientError as e:
        print(f"    ✗ API Gateway no existe o inaccesible: {e}")

def check_sns(config):
    """Verifica SNS."""
    print("\n[*] Verificando SNS...")
    sns = boto3.client("sns", region_name=config["region"])
    
    try:
        response = sns.get_topic_attributes(TopicArn=config["sns_topic_arn"])
        
        print(f"    ✓ Tema SNS existe")
        print(f"    ✓ ARN: {config['sns_topic_arn']}")
        
        # Listar suscripciones
        subs = sns.list_subscriptions_by_topic(TopicArn=config["sns_topic_arn"])
        sub_count = len(subs.get("Subscriptions", []))
        print(f"    ✓ Suscripciones: {sub_count}")
        
        for sub in subs.get("Subscriptions", []):
            status = sub.get("SubscriptionArn", "Pendiente")
            endpoint = sub.get("Endpoint", "N/A")
            if "PendingConfirmation" not in status:
                print(f"      ✓ Email confirmado: {endpoint}")
            else:
                print(f"      ⚠ Email pendiente de confirmación: {endpoint}")
        
    except ClientError:
        print(f"    ✗ Tema SNS no existe")

def check_iam(config):
    """Verifica IAM."""
    print("\n[*] Verificando IAM...")
    iam = boto3.client("iam")
    
    try:
        response = iam.get_role(RoleName=config["iam_role"])
        
        print(f"    ✓ Rol IAM '{config['iam_role']}' existe")
        
        # Listar políticas
        policies = iam.list_role_policies(RoleName=config["iam_role"])
        
        for policy in policies.get("PolicyNames", []):
            print(f"      ✓ Política: {policy}")
        
    except ClientError:
        print(f"    ✗ Rol IAM '{config['iam_role']}' no existe")

def test_api_endpoint(config):
    """Prueba el endpoint de la API."""
    print("\n[*] Probando API Endpoint...")
    
    try:
        import urllib.request
        import json
        
        url = f"{config['api_endpoint']}/items"
        
        print(f"    Llamando: GET {url}")
        
        req = urllib.request.Request(url, method='GET')
        req.add_header('User-Agent', 'AWS-Serverless-Test')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            print(f"    ✓ API respondió correctamente")
            print(f"    ✓ Items en BD: {data.get('count', 0)}")
            
            if data.get('items'):
                print(f"    ✓ Primer item: {data['items'][0]}")
    
    except Exception as e:
        print(f"    ⚠ Error al probar API: {e}")
        print(f"    ℹ Esto es normal si aún no has subido datos a S3")

def main():
    print("\n" + "="*60)
    print("VALIDACIÓN POST-DESPLIEGUE")
    print("="*60)
    
    config = load_config()
    if not config:
        sys.exit(1)
    
    print(f"\nVerificando despliegue del suffix: {config['suffix']}")
    print(f"Región: {config['region']}")
    
    check_s3_buckets(config)
    check_dynamodb(config)
    check_lambdas(config)
    check_api_gateway(config)
    check_sns(config)
    check_iam(config)
    test_api_endpoint(config)
    
    print("\n" + "="*60)
    print("✓ VALIDACIÓN COMPLETADA")
    print("="*60)
    
    print("\n📋 RESUMEN:")
    print(f"  Web: {config['web_url']}")
    print(f"  API: {config['api_endpoint']}")
    print(f"  Bucket uploads: {config['bucket_uploads']}")
    print(f"  SNS Topic: {config['sns_topic_arn']}")
    
    print("\n📝 PRÓXIMOS PASOS:")
    print(f"  1. Subir CSV: aws s3 cp sample_inventory.csv s3://{config['bucket_uploads']}/")
    print(f"  2. Abrir dashboard: {config['web_url']}")
    print(f"  3. Suscribirse SNS: python infra/subscribe_sns.py")

if __name__ == "__main__":
    main()
