#!/usr/bin/env python3
"""
Script para suscribirse a notificaciones SNS por email.
"""

import json
import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_REGION", "us-east-1")
PROJECT_ROOT = Path(__file__).parent.parent

sns_client = boto3.client("sns", region_name=REGION)

# Cargar configuración de despliegue
config_file = PROJECT_ROOT / "infra" / "deployment.json"

if not config_file.exists():
    print("✗ Archivo deployment.json no encontrado.")
    sys.exit(1)

with open(config_file, "r") as f:
    config = json.load(f)

TOPIC_ARN = config["sns_topic_arn"]

def main():
    print("\n" + "="*60)
    print("SUSCRIPCIÓN A NOTIFICACIONES SNS")
    print("="*60)
    print(f"\nTema SNS: {TOPIC_ARN}")
    
    email = input("\nIngresa tu dirección de email para recibir alertas: ").strip()
    
    if not email or "@" not in email:
        print("✗ Email inválido")
        sys.exit(1)
    
    try:
        response = sns_client.subscribe(
            TopicArn=TOPIC_ARN,
            Protocol="email",
            Endpoint=email
        )
        
        subscription_arn = response["SubscriptionArn"]
        
        print("\n" + "="*60)
        print("✓ SUSCRIPCIÓN INICIADA")
        print("="*60)
        print(f"\nID de suscripción: {subscription_arn}")
        print(f"\n📧 Se ha enviado un email de confirmación a {email}")
        print("Por favor, confirma tu suscripción haciendo clic en el enlace del email.")
        print("\nUna vez confirmado, recibirás alertas cuando el stock sea bajo (<50).")
        
    except ClientError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
