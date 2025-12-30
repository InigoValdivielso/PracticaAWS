#!/usr/bin/env python3
"""
Script de despliegue programático para arquitectura serverless AWS.
Crea S3 buckets, DynamoDB, Lambdas, IAM roles, API Gateway, y SNS.
"""

import json
import os
import sys
import uuid
import zipfile
import shutil
import tempfile
import time
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Configuración
REGION = os.getenv("AWS_REGION", "us-east-1")

# Usar sufijo fijo para reutilizar recursos en AWS Academy (evita crear nuevos buckets)
deployment_file = Path(__file__).parent / "deployment.json"
EXISTING_SNS_ARN = None  # Para reutilizar SNS si ya existe

if deployment_file.exists():
    with open(deployment_file, 'r') as f:
        existing_config = json.load(f)
        SUFFIX = existing_config.get("suffix")
        EXISTING_SNS_ARN = existing_config.get("sns_topic_arn")
        print(f"[*] Reutilizando sufijo existente: {SUFFIX}")
        if EXISTING_SNS_ARN:
            print(f"[*] Reutilizando SNS tema: {EXISTING_SNS_ARN}")
else:
    # Sufijo fijo para evitar crear nuevos buckets en AWS Academy
    SUFFIX = "inventory-main"
    print(f"[*] Usando sufijo fijo: {SUFFIX}")

PROJECT_ROOT = Path(__file__).parent.parent

# Obtener ID de cuenta
sts_client = boto3.client("sts", region_name=REGION)
ACCOUNT_ID = sts_client.get_caller_identity()["Account"]

print(f"[*] Región: {REGION}")
print(f"[*] Sufijo de despliegue: {SUFFIX}")

# Clientes de AWS
s3_client = boto3.client("s3", region_name=REGION)
dynamodb_client = boto3.client("dynamodb", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)
iam_client = boto3.client("iam", region_name=REGION)
apigateway_client = boto3.client("apigatewayv2", region_name=REGION)
sns_client = boto3.client("sns", region_name=REGION)

# Nombres de recursos
BUCKET_UPLOADS = f"inventory-uploads-{SUFFIX}"
BUCKET_WEB = f"inventory-web-{SUFFIX}"
TABLE_NAME = "Inventory"
LAMBDA_LOAD_NAME = "load_inventory"
LAMBDA_API_NAME = "get_inventory_api"
LAMBDA_NOTIFY_NAME = "notify_low_stock"
IAM_ROLE_LAMBDA = f"lambda-inventory-role-{SUFFIX}"
SNS_TOPIC_NAME = "low-stock-inventory-main"  # Nombre FIJO para evitar crear múltiples temas

# ===== S3 =====
def create_s3_buckets():
    """Verifica y reutiliza buckets S3 existentes, o los crea si no existen."""
    print("\n[*] Verificando buckets S3...")
    
    for bucket_name in [BUCKET_UPLOADS, BUCKET_WEB]:
        bucket_exists = False
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            bucket_exists = True
            print(f"    ℹ Bucket {bucket_name} ya existe (reutilizando)")
        except ClientError:
            pass  # Bucket no existe, se intentará crear
        
        if not bucket_exists:
            try:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": REGION} if REGION != "us-east-1" else {}
                )
                print(f"    ✓ Bucket {bucket_name} creado")
            except ClientError as e:
                if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                    print(f"    ℹ Bucket {bucket_name} ya existe")
                elif "AccessDenied" in str(e) or "explicit deny" in str(e):
                    print(f"    ⚠ No se puede crear {bucket_name} (AWS Academy). Verifica deployment.json.")
                    raise
                else:
                    raise
        
        # Habilitar versionado en bucket de uploads
        if bucket_name == BUCKET_UPLOADS:
            try:
                s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={"Status": "Enabled"}
                )
                print(f"    ✓ Versionado habilitado en {bucket_name}")
            except:
                pass  # Ya puede estar habilitado

# ===== DynamoDB =====
def create_dynamodb_table():
    """Crea tabla DynamoDB con Streams habilitados."""
    print("\n[*] Creando tabla DynamoDB...")
    
    try:
        response = dynamodb_client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "Store", "KeyType": "HASH"},
                {"AttributeName": "Item", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "Store", "AttributeType": "S"},
                {"AttributeName": "Item", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            }
        )
        print(f"    ✓ Tabla {TABLE_NAME} creada")
        
        # Esperar a que la tabla esté activa
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f"    ✓ Tabla {TABLE_NAME} lista")
        
        return response["TableDescription"]["TableArn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"    ℹ Tabla {TABLE_NAME} ya existe")
            response = dynamodb_client.describe_table(TableName=TABLE_NAME)

            # Si la tabla existía sin streams, habilitarlos para permitir eventos INSERT/MODIFY
            stream_spec = response["Table"].get("StreamSpecification", {})
            if not stream_spec.get("StreamEnabled"):
                print("    ℹ Habilitando Streams en tabla existente...")
                dynamodb_client.update_table(
                    TableName=TABLE_NAME,
                    StreamSpecification={
                        "StreamEnabled": True,
                        "StreamViewType": "NEW_AND_OLD_IMAGES"
                    }
                )
                # Esperar a que la actualización termine
                waiter = dynamodb_client.get_waiter("table_exists")
                waiter.wait(TableName=TABLE_NAME)
                response = dynamodb_client.describe_table(TableName=TABLE_NAME)
                print("    ✓ Streams habilitados en tabla existente")

            return response["Table"]["TableArn"]
        else:
            raise

# ===== IAM =====
def create_iam_role():
    """Usa el rol LabRole existente en AWS Academy (no puede crear roles personalizados)."""
    print("\n[*] Buscando rol IAM existente...")
    
    # AWS Academy Learner Lab usa el rol LabRole preconfigurado
    try:
        response = iam_client.get_role(RoleName="LabRole")
        role_arn = response["Role"]["Arn"]
        print(f"    ✓ Usando rol existente: LabRole")
        print(f"    ℹ ARN: {role_arn}")
        return role_arn
    except ClientError as e:
        print(f"    ⚠ No se encontró LabRole, intentando crear rol personalizado...")
        
        # Fallback: intentar crear rol personalizado (funcionará en cuentas no-Academy)
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = iam_client.create_role(
                RoleName=IAM_ROLE_LAMBDA,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description="Rol para Lambdas de inventario"
            )
            role_arn = response["Role"]["Arn"]
            print(f"    ✓ Rol {IAM_ROLE_LAMBDA} creado")
            
            # Adjuntar política AWS managed para Lambda
            iam_client.attach_role_policy(
                RoleName=IAM_ROLE_LAMBDA,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
            print(f"    ✓ Política básica adjuntada")
            
            return role_arn
        except ClientError as create_error:
            print(f"    ✗ Error: {create_error}")
            raise

# ===== Lambda =====
def zip_lambda(source_dir, output_zip):
    """Crea un archivo ZIP con el código Lambda."""
    if output_zip.exists():
        output_zip.unlink()
    
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in Path(source_dir).rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(source_dir)
                zf.write(file_path, arcname)
    
    return output_zip

def create_lambda(name, source_dir, role_arn, handler, timeout=30, memory=256, environment=None):
    """Crea o actualiza una función Lambda."""
    print(f"\n[*] Desplegando Lambda {name}...")
    
    # Crear ZIP en directorio temporal del sistema
    temp_dir = tempfile.gettempdir()
    zip_path = Path(temp_dir) / f"{name}.zip"
    zip_lambda(source_dir, zip_path)
    
    with open(zip_path, "rb") as f:
        zip_content = f.read()
    
    try:
        # Intentar crear
        response = lambda_client.create_function(
            FunctionName=name,
            Runtime="python3.11",
            Role=role_arn,
            Handler=handler,
            Code={"ZipFile": zip_content},
            Timeout=timeout,
            MemorySize=memory,
            Environment={"Variables": environment or {}}
        )
        print(f"    ✓ Lambda {name} creada")
        return response["FunctionArn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            # Función existe, esperar a que termine actualizaciones previas
            print(f"    ℹ Lambda {name} ya existe, esperando a que esté lista...")
            
            # Esperar hasta 60 segundos a que la función esté activa
            for attempt in range(12):
                try:
                    response = lambda_client.get_function(FunctionName=name)
                    state = response["Configuration"]["State"]
                    if state == "Active":
                        break
                    print(f"    ⏳ Estado: {state}, esperando...")
                    time.sleep(5)
                except:
                    time.sleep(5)
            
            # Actualizar código
            try:
                lambda_client.update_function_code(
                    FunctionName=name,
                    ZipFile=zip_content
                )
                print(f"    ✓ Código actualizado")
                
                # Esperar a que termine la actualización del código
                time.sleep(3)
                
                # Actualizar configuración
                lambda_client.update_function_configuration(
                    FunctionName=name,
                    Timeout=timeout,
                    MemorySize=memory,
                    Environment={"Variables": environment or {}}
                )
                print(f"    ✓ Lambda {name} actualizada")
            except ClientError as update_error:
                if "ResourceConflictException" in str(update_error):
                    print(f"    ℹ Lambda en actualización, usando versión existente")
                else:
                    raise
            
            response = lambda_client.get_function(FunctionName=name)
            return response["Configuration"]["FunctionArn"]
        else:
            raise

# ===== SNS =====
def create_sns_topic():
    """Crea o reutiliza tema SNS para alertas de stock bajo.
    
    Siempre usa 'low-stock-inventory-main' como nombre para evitar duplicados.
    """
    print("\n[*] Verificando tema SNS...")
    
    # El nombre del tema debe ser fijo (sin sufijo) para evitar crear múltiples temas
    fixed_topic_name = "low-stock-inventory-main"
    
    # 1. Intentar buscar el tema por nombre fijo
    try:
        response = sns_client.list_topics()
        for topic in response["Topics"]:
            if fixed_topic_name in topic["TopicArn"]:
                print(f"    ✓ Tema SNS {fixed_topic_name} encontrado (reutilizando)")
                print(f"    ℹ ARN: {topic['TopicArn']}")
                return topic["TopicArn"]
    except ClientError:
        pass
    
    # 2. Si no existe, crear nuevo con nombre fijo
    try:
        response = sns_client.create_topic(Name=fixed_topic_name)
        topic_arn = response["TopicArn"]
        print(f"    ✓ Tema SNS {fixed_topic_name} creado")
        print(f"    ℹ ARN: {topic_arn}")
        return topic_arn
    except ClientError as e:
        print(f"    ✗ Error al crear tema SNS: {e}")
        raise

# ===== API Gateway =====
def create_api_gateway(lambda_api_arn):
    """Crea HTTP API Gateway con CORS habilitado."""
    print("\n[*] Creando API Gateway...")
    
    api_name = f"inventory-api-{SUFFIX}"
    
    # Buscar APIs existentes con el mismo nombre y eliminarlas
    try:
        existing_apis = apigateway_client.get_apis()
        for api in existing_apis.get("Items", []):
            if api["Name"] == api_name:
                print(f"    ℹ Eliminando API existente {api['ApiId']}...")
                apigateway_client.delete_api(ApiId=api["ApiId"])
    except:
        pass
    
    # Crear API
    response = apigateway_client.create_api(
        Name=api_name,
        ProtocolType="HTTP",
        CorsConfiguration={
            "AllowOrigins": ["*"],
            "AllowMethods": ["GET", "POST", "PUT", "DELETE"],
            "AllowHeaders": ["Content-Type"],
            "MaxAge": 300
        }
    )
    api_id = response["ApiId"]
    print(f"    ✓ API Gateway {api_name} creada")
    
    # Crear integración Lambda
    integration_response = apigateway_client.create_integration(
        ApiId=api_id,
        IntegrationType="AWS_PROXY",
        IntegrationMethod="POST",
        IntegrationUri=lambda_api_arn,
        PayloadFormatVersion="2.0"
    )
    integration_id = integration_response["IntegrationId"]
    
    # Crear rutas
    routes = [
        {"RouteKey": "GET /items", "Target": f"integrations/{integration_id}"},
        {"RouteKey": "GET /items/{store}", "Target": f"integrations/{integration_id}"}
    ]
    
    for route in routes:
        apigateway_client.create_route(
            ApiId=api_id,
            RouteKey=route["RouteKey"],
            Target=route["Target"]
        )
        print(f"    ✓ Ruta {route['RouteKey']} creada")
    
    # Dar permiso a API Gateway para invocar Lambda
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_API_NAME,
            StatementId=f"AllowApiGateway-{api_id}",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*"
        )
    except ClientError as e:
        if "ResourceConflictException" not in str(e):
            raise
    
    # Crear stage
    stage_response = apigateway_client.create_stage(
        ApiId=api_id,
        StageName="prod",
        AutoDeploy=True
    )
    
    api_endpoint = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    print(f"    ✓ Endpoint: {api_endpoint}")
    
    return api_id, api_endpoint

# ===== S3 Event Trigger =====
def add_s3_trigger_to_lambda(lambda_name):
    """Agrega trigger de S3 PutObject a Lambda."""
    print(f"\n[*] Agregando trigger S3 a {lambda_name}...")
    
    # Dar permiso a S3 para invocar Lambda
    try:
        lambda_client.add_permission(
            FunctionName=lambda_name,
            StatementId=f"AllowS3-{BUCKET_UPLOADS}",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{BUCKET_UPLOADS}"
        )
    except ClientError as e:
        if "ResourceConflictException" not in str(e):
            raise
    
    # Configurar notificación en S3
    lambda_arn = lambda_client.get_function(FunctionName=lambda_name)["Configuration"]["FunctionArn"]
    
    try:
        s3_client.put_bucket_notification_configuration(
            Bucket=BUCKET_UPLOADS,
            NotificationConfiguration={
                "LambdaFunctionConfigurations": [
                    {
                        "LambdaFunctionArn": lambda_arn,
                        "Events": ["s3:ObjectCreated:*"]
                    }
                ]
            }
        )
        print(f"    ✓ Trigger S3 configurado")
    except ClientError as e:
        print(f"    ⚠ Error configurando trigger: {e}")

# ===== DynamoDB Streams =====
def add_stream_trigger_to_lambda(lambda_name):
    """Agrega DynamoDB Stream como source para Lambda notify."""
    print(f"\n[*] Agregando DynamoDB Stream a {lambda_name}...")
    
    # Obtener ARN del stream
    table_response = dynamodb_client.describe_table(TableName=TABLE_NAME)
    stream_arn = table_response["Table"]["LatestStreamArn"]
    
    if not stream_arn:
        print("    ⚠ Stream no habilitado en tabla")
        return
    
    # Primero, eliminar event source mappings anteriores si existen
    try:
        existing_mappings = lambda_client.list_event_source_mappings(
            FunctionName=lambda_name,
            EventSourceArn=stream_arn
        )
        for mapping in existing_mappings.get("EventSourceMappings", []):
            print(f"    ℹ Eliminando event source mapping anterior: {mapping['UUID']}")
            lambda_client.delete_event_source_mapping(UUID=mapping["UUID"])
    except ClientError:
        pass
    
    # Crear event source mapping con TRIM_HORIZON para procesar eventos desde el inicio
    try:
        response = lambda_client.create_event_source_mapping(
            EventSourceArn=stream_arn,
            FunctionName=lambda_name,
            Enabled=True,
            BatchSize=100,
            StartingPosition="TRIM_HORIZON"
        )
        print(f"    ✓ Event source mapping creado: {response['UUID']}")
        print(f"    ℹ Procesará eventos desde el inicio del stream (TRIM_HORIZON)")
    except ClientError as e:
        if "ResourceConflictException" in str(e):
            print(f"    ℹ Event source mapping podría ya existir")
        else:
            print(f"    ⚠ Error: {e}")

# ===== Upload Web =====
def upload_web_content(api_endpoint):
    """Sube contenido web al bucket web S3 (carpeta website/)."""
    print("\n[*] Subiendo contenido web a S3...")
    
    web_dir = PROJECT_ROOT / "website"
    
    if not web_dir.exists():
        print(f"    ⚠ Carpeta website no encontrada en {web_dir}")
        return None
    
    # Subir todos los archivos recursivamente
    files_uploaded = 0
    for file_path in web_dir.rglob("*"):
        if file_path.is_file():
            # Calcular la clave S3 relativa
            relative_path = file_path.relative_to(web_dir)
            s3_key = str(relative_path).replace("\\", "/")
            
            # Leer contenido
            with open(file_path, "rb") as f:
                content = f.read()
            
            # Si es HTML, reemplazar el endpoint de la API
            if file_path.suffix == ".html":
                try:
                    content_text = content.decode("utf-8")
                    content_text = content_text.replace("REPLACE_WITH_API_ENDPOINT", api_endpoint)
                    content = content_text.encode("utf-8")
                except:
                    pass  # Si no es texto, mantener como está
            
            # Determinar Content-Type
            content_type = "application/octet-stream"
            if file_path.suffix == ".html":
                content_type = "text/html"
            elif file_path.suffix == ".css":
                content_type = "text/css"
            elif file_path.suffix == ".js":
                content_type = "application/javascript"
            elif file_path.suffix in [".jpg", ".jpeg"]:
                content_type = "image/jpeg"
            elif file_path.suffix == ".png":
                content_type = "image/png"
            elif file_path.suffix == ".gif":
                content_type = "image/gif"
            elif file_path.suffix == ".svg":
                content_type = "image/svg+xml"
            
            # Subir a S3
            s3_client.put_object(
                Bucket=BUCKET_WEB,
                Key=s3_key,
                Body=content,
                ContentType=content_type
            )
            files_uploaded += 1
            print(f"    ✓ {s3_key}")
    
    print(f"    ✓ Total archivos subidos: {files_uploaded}")
    
    # Habilitar hosting estático
    website_config = {
        "IndexDocument": {"Suffix": "index.html"},
        "ErrorDocument": {"Key": "index.html"}
    }
    s3_client.put_bucket_website(
        Bucket=BUCKET_WEB,
        WebsiteConfiguration=website_config
    )
    
    # Generar URL del sitio web
    web_url = f"http://{BUCKET_WEB}.s3-website-{REGION}.amazonaws.com"
    
    # Desactivar Block Public Access
    try:
        s3_client.put_public_access_block(
            Bucket=BUCKET_WEB,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        print(f"    ✓ Block Public Access desactivado")
    except ClientError as e:
        print(f"    ⚠ No se pudo desactivar Block Public Access: {e}")
    
    # Intentar hacer bucket público
    try:
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{BUCKET_WEB}/*"
                }
            ]
        }
        s3_client.put_bucket_policy(
            Bucket=BUCKET_WEB,
            Policy=json.dumps(bucket_policy)
        )
        print(f"    ✓ Sitio web público: {web_url}")
    except ClientError as e:
        if "BlockPublicPolicy" in str(e) or "AccessDenied" in str(e):
            print(f"    ⚠ No se puede hacer el bucket público")
            print(f"    ℹ URL (no accesible públicamente): {web_url}")
            print(f"    ℹ Usa la API REST para acceder a los datos")
        else:
            raise
    
    return web_url

# ===== MAIN =====
def main():
    print("\n" + "="*60)
    print("DESPLIEGUE SERVERLESS AWS - INVENTARIO")
    print("="*60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Region: {REGION}")
    print(f"Suffix: {SUFFIX}")
    
    try:
        # 1. Crear buckets S3
        create_s3_buckets()
        
        # 2. Crear tabla DynamoDB
        table_arn = create_dynamodb_table()
        
        # 3. Crear rol IAM
        role_arn = create_iam_role()
        
        # 4. Crear tema SNS
        topic_arn = create_sns_topic()
        
        # 5. Desplegar Lambdas
        lambda_load_arn = create_lambda(
            LAMBDA_LOAD_NAME,
            PROJECT_ROOT / "lambdas" / "load_inventory",
            role_arn,
            "lambda_function.lambda_handler",
            timeout=60,
            memory=512,
            environment={
                "TABLE_NAME": TABLE_NAME,
                "REGION": REGION
            }
        )
        
        lambda_api_arn = create_lambda(
            LAMBDA_API_NAME,
            PROJECT_ROOT / "lambdas" / "get_inventory_api",
            role_arn,
            "lambda_function.lambda_handler",
            timeout=30,
            memory=256,
            environment={
                "TABLE_NAME": TABLE_NAME,
                "REGION": REGION
            }
        )
        
        lambda_notify_arn = create_lambda(
            LAMBDA_NOTIFY_NAME,
            PROJECT_ROOT / "lambdas" / "notify_low_stock",
            role_arn,
            "lambda_function.lambda_handler",
            timeout=60,
            memory=256,
            environment={
                "TABLE_NAME": TABLE_NAME,
                "TOPIC_ARN": topic_arn,
                "REGION": REGION
            }
        )
        
        # 6. Configurar triggers
        add_s3_trigger_to_lambda(LAMBDA_LOAD_NAME)
        add_stream_trigger_to_lambda(LAMBDA_NOTIFY_NAME)
        
        # 7. Crear API Gateway
        api_id, api_endpoint = create_api_gateway(lambda_api_arn)
        
        # 8. Subir contenido web
        web_url = upload_web_content(api_endpoint)
        
        # 9. Guardar configuración
        config = {
            "deployment_time": datetime.now().isoformat(),
            "region": REGION,
            "suffix": SUFFIX,
            "bucket_uploads": BUCKET_UPLOADS,
            "bucket_web": BUCKET_WEB,
            "table_name": TABLE_NAME,
            "lambda_load": LAMBDA_LOAD_NAME,
            "lambda_api": LAMBDA_API_NAME,
            "lambda_notify": LAMBDA_NOTIFY_NAME,
            "api_id": api_id,
            "api_endpoint": api_endpoint,
            "web_url": web_url,
            "sns_topic_arn": topic_arn,
            "iam_role": IAM_ROLE_LAMBDA
        }
        
        config_file = PROJECT_ROOT / "infra" / "deployment.json"
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        print("\n" + "="*60)
        print("✓ DESPLIEGUE COMPLETADO")
        print("="*60)
        print(f"\n📋 CONFIGURACIÓN GUARDADA EN: {config_file}")
        print(f"\n🌐 ACCESO:")
        print(f"   Web: {web_url}")
        print(f"   API: {api_endpoint}")
        print(f"\n💾 RECURSOS:")
        print(f"   Bucket uploads: {BUCKET_UPLOADS}")
        print(f"   Bucket web: {BUCKET_WEB}")
        print(f"   DynamoDB tabla: {TABLE_NAME}")
        print(f"   SNS topic: {topic_arn}")
        print(f"\n📝 PRÓXIMOS PASOS:")
        print(f"   1. Suscribirse a SNS: python infra/subscribe_sns.py")
        print(f"   2. Subir CSV: aws s3 cp sample_inventory.csv s3://{BUCKET_UPLOADS}/")
        print(f"   3. Ver web: {web_url}")
        print(f"   4. Limpiar: python infra/destroy.py")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
