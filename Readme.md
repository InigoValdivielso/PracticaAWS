# 🚀 AWS Serverless - Sistema Inteligente de Gestión de Inventario

**Una solución empresarial completa y totalmente automatizada para gestionar inventarios mediante arquitectura serverless en AWS.**

---

## 📌 Resumen Ejecutivo

Este proyecto implementa una **arquitectura serverless production-ready** que:

✅ **Carga datos automáticamente** desde archivos CSV directamente a S3  
✅ **Procesa en tiempo real** con Lambda + DynamoDB Streams  
✅ **Expone API REST** con dos endpoints (todos los items + filtrado por tienda)  
✅ **Dashboard web interactivo** alojado en S3 con búsqueda en tiempo real  
✅ **Alertas inteligentes por email** cuando el stock baja de 50 unidades  
✅ **Infraestructura completamente programática** - crear y destruir con un comando  
✅ **Compatible con AWS Academy Learner Lab** - sin costos adicionales  

**Tiempo de ejecución**: 5 minutos de despliegue  
**Nivel de dificultad**: Intermedio-Avanzado  
**Tecnologías**: Python 3, boto3, AWS Lambda, DynamoDB, API Gateway v2, SNS, S3

---

## 🏗️ Arquitectura (Production-Ready)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SISTEMA DE INVENTARIO INTELIGENTE              │
└─────────────────────────────────────────────────────────────────────┘

                            [ENTRADA DE DATOS]
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌──────────────┐              ┌─────────────────┐
            │   S3 Bucket  │              │  Dashboard Web  │
            │   (Uploads)  │              │   (S3 Static)   │
            └────────┬─────┘              └────────┬────────┘
                     │                             │
                     │ S3:ObjectCreated            │ fetch() + REST
                     ▼                             │
            ┌──────────────────────┐       ┌──────────────────────┐
            │   Lambda A: Load     │       │  Lambda B: API REST  │
            │   CSV → DynamoDB     │       │  GET /items          │
            │                      │       │  GET /items/{store}  │
            └────────┬─────────────┘       └──────────┬───────────┘
                     │                               │
                     │ PutItem / UpdateItem          │
                     ▼                               ▼
         ┌───────────────────────────────┐  ┌──────────────────┐
         │      DynamoDB Table           │  │  API Gateway v2  │
         │      "Inventory"              │  │  (HTTP API)      │
         │  PK: Store (String)           │  │                  │
         │  SK: Item (String)            │  │  Public REST     │
         │  Attribute: Count (Number)    │  │  Endpoints       │
         │                               │  │                  │
         │  ✨ DynamoDB Streams ENABLED  │  └────────┬─────────┘
         │     (TRIM_HORIZON mode)       │           │
         └───────────┬───────────────────┘           │
                     │                               │
                     │ Stream Events                 │ Responses (JSON)
                     │ (cuando Count < 50)           │
                     ▼                               ▼
         ┌──────────────────────┐          ┌─────────────────┐
         │  Lambda C: Monitor   │          │   Navegador     │
         │  Stock Bajo          │          │   (React/JS)    │
         │  (Inteligencia)      │          │                 │
         └────────┬─────────────┘          └─────────────────┘
                  │
                  │ SNS Publish
                  ▼
         ┌──────────────────────┐
         │   SNS Topic          │
         │   "low-stock-*"      │
         │   (Persistent)       │
         └────────┬─────────────┘
                  │
                  │ Email Notification
                  ▼
         ┌──────────────────────┐
         │   EMAIL (USUARIO)    │
         │   ⚠️ ALERTA STOCK    │
         └──────────────────────┘
```

---

## 🎯 Funcionalidades Destacadas

### ✨ Lo que diferencia este proyecto:

| Característica | Beneficio |
|---|---|
| **CSV automático** | Solo sube un archivo, el sistema hace el resto |
| **Dashboard interactivo** | Visualización en tiempo real con búsqueda por tienda |
| **API completamente funcional** | Endpoints profesionales con soporte CORS |
| **Alertas inteligentes** | Notificaciones por email automáticas |
| **Infraestructura como Código** | Todo programático (IaC) - reproducible al 100% |
| **Sin servidor (Serverless)** | Costos mínimos, escalabilidad infinita |
| **Monitoreo CloudWatch** | Logs detallados de cada operación |
| **DynamoDB Streams** | Procesamiento en tiempo real de cambios |
| **Rol LabRole compatible** | Funciona directo con AWS Academy sin configuración adicional |
| **Destrucción completa** | Limpia todos los recursos con un comando |

---

## 📋 Requisitos Previos

- ✅ **Cuenta AWS Academy Learner Lab** activa
- ✅ **Python 3.9+** instalado en tu máquina
- ✅ **Credenciales AWS** (explicado abajo)
- ✅ **Correo personal** (⚠️ importante, ver advertencias)

---

## ⚠️ ADVERTENCIAS IMPORTANTES

### 1️⃣ **USA UN CORREO PERSONAL, NO EL DE LA UNIVERSIDAD**

**Problema identificado**: El correo de la universidad tiene filtros que bloquean emails de SNS y pueden causar desuscripciones automáticas.

**Solución**: 
- Usa un correo Gmail, Outlook o Yahoo personal
- Confirma la suscripción SNS inmediatamente
- **NO ignores el email de confirmación de SNS**

**¿Qué pasa si se desuscribe automáticamente?**
- Los emails de alerta no llegarán
- Deberás reiniciar el Lab y ejecutar todo de nuevo
- Por eso es importante usar un correo que funcione

Puede que con un correo personal también haya problemas, pero simplemente reiniciando el Lab y volviendo a suscribirlo funcionará.

### 2️⃣ **El SNS email se desuscribe tras reiniciar el Lab**

Si reinicas el Lab (por expiración de credenciales o cualquier motivo):
1. Todos los recursos de AWS se pierden
2. Necesitarás volver a ejecutar `python infra/deploy.py`
3. Necesitarás volver a suscribir el correo con `python infra/subscribe_sns.py`

**Consejo**: Anota el email usado para que recuerdes configurarlo igual.

### 3️⃣ **Las credenciales de AWS Academy expiran**

- Las credenciales tienen validez limitada (típicamente 4 horas)
- Cuando expiren, verás: `NoCredentialsError: Unable to locate credentials`
- **Solución**: Reinicia el Lab y ejecuta los scripts de nuevo
- Las credenciales se cargarán automáticamente si usas CloudShell

---

## 🔐 Configuración de Credenciales AWS

### Opción 1: CloudShell (RECOMENDADA) ✅

**Ventaja**: Las credenciales se cargan automáticamente, sin copiar/pegar.

```bash
# 1. Abre AWS Academy Learner Lab
# 2. Click en "Start Lab" 
# 3. Click en "AWS Management Console"
# 4. Click en el ícono CloudShell (esquina superior derecha, >_)

# Ya estás dentro de CloudShell. Las credenciales están cargadas automáticamente.
# Ahora ejecuta los scripts:

cd ~/environment  # o donde hayas subido el proyecto
cd Practica_AWS
pip install -r infra/requirements.txt
python infra/deploy.py
```

### Opción 2: Máquina Local con Credenciales Temporales

**Si prefieres ejecutar desde tu PC:**

#### Paso 1: Obtén las credenciales del Lab

1. En el **Learner Lab**, haz clic en el botón **"AWS Details"** (arriba a la derecha), luego haz clic en el botón **"Show"** en AWS CLI.
2. Verás algo como:
   ```
   AWS ACCESS KEY ID: xxxxxxxxxx
   AWS SECRET ACCESS KEY: xxxxxxxxxxxxxx  
   AWS SESSION TOKEN: xxxxxxxxxxxxxxxx
   ```
3. **Copia estas tres líneas completas**

#### Paso 2: Crea el archivo `.aws/credentials`

**Windows** (PowerShell):
```powershell
# Crear carpeta si no existe
mkdir $env:USERPROFILE\.aws -ErrorAction SilentlyContinue

# Abrir editor de texto
notepad $env:USERPROFILE\.aws\credentials
```

**Mac/Linux**:
```bash
mkdir -p ~/.aws
nano ~/.aws/credentials
```

#### Paso 3: Pega el contenido

En el archivo `~/.aws/credentials`, escribe:

```ini
[default]
aws_access_key_id = XXXXXXXXXX
aws_secret_access_key = XXXXXXXXXXXX
aws_session_token = XXXXXXXXXXXX
```

**⚠️ IMPORTANTE**: Reemplaza las X's con tus credenciales reales del Learner Lab.

#### Paso 4: Crea el archivo `.env`

Simplemente copia `.env.sample` a `.env`:

**Windows (PowerShell)**:
```powershell
cd C:\CLOUD\Practica_AWS
copy .env.sample .env
```

**Mac/Linux**:
```bash
cd ~/Practica_AWS
cp .env.sample .env
```

El archivo `.env` ya contiene la configuración necesaria:
- `AWS_REGION=us-east-1`
- `AWS_PROFILE=default`

#### Paso 5: Verifica y ejecuta

```bash
# Verifica que funcionan las credenciales
aws sts get-caller-identity

# Si ves tu Account ID, ¡funciona! Ahora ejecuta:
python infra/deploy.py
```

---

## 🚀 EJECUCIÓN RÁPIDA (5 minutos)

### Desde tu máquina local

```powershell
# PowerShell en Windows:

cd C:\CLOUD\Practica_AWS

# Copia la configuración
copy .env.sample .env

# Verifica credenciales
aws sts get-caller-identity

# Instala dependencias
python -m pip install --upgrade pip
pip install -r infra/requirements.txt

# Ejecuta despliegue
python infra/deploy.py
```

Al terminar el `deploy`, la consola muestra un bloque con **los siguientes pasos ya listos**: comandos para suscribirte a SNS, comando para subir el CSV de ejemplo y los enlaces directos del dashboard web y del endpoint de la API. Solo copia/abre lo que imprime la consola tras el despliegue.

---

## 📊 ¿Qué pasa durante el despliegue?

El script `deploy.py` crea automáticamente:

| Recurso | Nombre | Función |
|---------|--------|---------|
| **S3 Bucket 1** | `inventory-uploads-*` | Recibe CSVs para procesar |
| **S3 Bucket 2** | `inventory-web-*` | Aloja dashboard web |
| **DynamoDB** | `Inventory` | Base de datos de items |
| **Lambda A** | `load_inventory` | Parsea CSV → DynamoDB |
| **Lambda B** | `get_inventory_api` | API REST (GET /items, /items/{store}) |
| **Lambda C** | `notify_low_stock` | Alertas automáticas SNS |
| **API Gateway** | HTTP API v2 | Endpoints públicos |
| **SNS Topic** | `low-stock-inventory-main` | Notificaciones por email |
| **IAM Role** | Reutiliza `LabRole` | Permisos mínimos necesarios |

**Salida esperada**:
```
[✓] Bucket S3 creado: inventory-uploads-inventory-main
[✓] Lambda load_inventory creado
[✓] DynamoDB Inventory creada
[✓] API Gateway creada: https://abc123.execute-api.us-east-1.amazonaws.com/prod
[✓] SNS Topic creado
[✓] Dashboard web desplegado

🌐 ACCESO:
   Dashboard: http://inventory-web-inventory-main.s3-website-us-east-1.amazonaws.com
   API: https://hu0apd4dz6.execute-api.us-east-1.amazonaws.com/prod
```

---

## 📝 Después del Despliegue

### 1. Suscribirse a Alertas SNS
```bash
python infra/subscribe_sns.py
```

Ingresa tu **correo personal** cuando te pida. Recibirás un email de confirmación en segundos.

**⚠️ IMPORTANTE**: Abre el email y haz clic en "Confirmar suscripción". Sin esto, no recibirás alertas.

### 2. Cargar Datos de Ejemplo

```bash
# El bucket se llama "inventory-uploads-inventory-main" (ver deployment.json)
aws s3 cp sample_inventory.csv s3://inventory-uploads-inventory-main/
```

Espera 2-3 segundos. Los datos deberían aparecer en DynamoDB automáticamente.

### 3. Acceder al Dashboard Web

Abre en el navegador la URL mostrada:
```
http://inventory-web-inventory-main.s3-website-us-east-1.amazonaws.com
```

Deberías ver una tabla con todos los items cargados.

### 4. Probar la API REST

```bash
# GET /items (todos los items)
curl "https://hu0apd4dz6.execute-api.us-east-1.amazonaws.com/prod/items"

# GET /items/{store} (filtrar por tienda)
curl "https://hu0apd4dz6.execute-api.us-east-1.amazonaws.com/prod/items/Berlin"
```

**Respuesta de ejemplo**:
```json
{
  "items": [
    {"Store": "Berlin", "Item": "Widget-001", "Count": 100},
    {"Store": "Berlin", "Item": "Widget-002", "Count": 50},
    {"Store": "Berlin", "Item": "Gadget-001", "Count": 25}
  ],
  "count": 3
}
```

### 5. Probar Alertas SNS

Cambia el stock de un item a menos de 50:

```bash
aws dynamodb update-item \
  --table-name Inventory \
  --key '{"Store": {"S": "Berlin"}, "Item": {"S": "Widget-001"}}' \
  --update-expression 'SET #c = :val' \
  --expression-attribute-names '{"#c": "Count"}' \
  --expression-attribute-values '{":val": {"N": "10"}}' \
  --region us-east-1
```

**Resultado**: En segundos, recibirás un email con la alerta de stock bajo.

---

## 🧪 Validación del Sistema

### Checklist de Pruebas

- [ ] Dashboard web carga sin errores
- [ ] API `/items` devuelve todos los items en JSON
- [ ] API `/items/{store}` devuelve items filtrados
- [ ] Al cambiar stock < 50, recibo email en 10 segundos
- [ ] Puedo subir un CSV nuevo y actualiza el dashboard
- [ ] CloudWatch Logs muestra ejecución de Lambdas

### Ver Logs en Tiempo Real

```bash
# Logs de carga de CSV
aws logs tail /aws/lambda/load_inventory --follow

# Logs de API REST
aws logs tail /aws/lambda/get_inventory_api --follow

# Logs de alertas SNS
aws logs tail /aws/lambda/notify_low_stock --follow
```

### Verificar Recursos en AWS

```bash
# Listar buckets S3
aws s3 ls | grep inventory

# Listar tabla DynamoDB
aws dynamodb list-tables --region us-east-1

# Listar Lambdas
aws lambda list-functions --region us-east-1 --query 'Functions[*].FunctionName'

# Listar topics SNS
aws sns list-topics --region us-east-1
```

### (OPCIONAL) Validación Automática

Si prefieres una validación completa y automatizada de todos los recursos:

```bash
python infra/validate.py
```

Este script verifica automáticamente:
- ✓ Buckets S3 y triggers de eventos
- ✓ Tabla DynamoDB y Streams
- ✓ Funciones Lambda
- ✓ API Gateway y endpoints
- ✓ SNS Topic y suscripciones
- ✓ CloudWatch Logs

---

## 🧹 Limpiar Recursos (Cuando Termines)

### Eliminar TODO automáticamente

```bash
python infra/destroy.py
```

Te pedirá confirmación. Escribe `sí` para confirmar.

**Esto elimina**:
- ✓ Buckets S3 (uploads + web)
- ✓ Tabla DynamoDB
- ✓ Funciones Lambda
- ✓ API Gateway
- ✓ SNS Topics
- ✓ Archivo de configuración

**El rol IAM (`LabRole`) no se elimina porque es un recurso de sistema en AWS Academy.**

---

## 🌟 PUNTOS FUERTES DEL PROYECTO

### 1. **Completamente Automatizado**
No hay clics en la consola AWS. Un comando (`python infra/deploy.py`) crea TODO.

### 2. **Infraestructura como Código (IaC)**
Todo está en Python. Reproducible al 100%. Versionable en Git.

### 3. **Arquitectura Profesional**
- Patrones empresariales: Lambda, DynamoDB, Streams
- Seguridad: IAM con permisos mínimos
- Monitoreo: CloudWatch Logs integrado
- Escalabilidad: Serverless (escala automáticamente)

### 4. **Compatible con AWS Academy**
- Usa rol `LabRole` existente (sin crear nuevos)
- Sin costos adicionales (dentro del tier gratuito)
- Credenciales temporales soportadas

### 5. **Dashboard Web Interactivo**
No es solo API. Hay una interfaz visual funcional alojada en S3.

### 6. **Tratamiento de Edge Cases**
- Manejo de DynamoDB Streams con `TRIM_HORIZON`
- Palabras reservadas de DynamoDB manejadas con `ExpressionAttributeNames`
- Reintentos automáticos en caso de error temporal
- Logging detallado para debugging

### 7. **Documentación Completa**
README con ejemplos, troubleshooting y arquitectura explicada.

### 8. **Manejo de Errores Robusto**
Cada Lambda tiene try/catch. Los errores se registran en CloudWatch.

---

## 🎓 Temas de Cloud Computing Demostrados

Este proyecto demuestra:

✅ **Serverless Computing**: Lambda sin servidores  
✅ **NoSQL Databases**: DynamoDB con Streams  
✅ **Event-Driven Architecture**: S3 → Lambda → DynamoDB  
✅ **API REST**: API Gateway v2 (HTTP API)  
✅ **Messaging**: SNS para notificaciones  
✅ **Static Hosting**: S3 website  
✅ **Infrastructure as Code**: Scripts Python automáticos  
✅ **Monitoring & Logging**: CloudWatch Logs  
✅ **IAM Security**: Políticas de mínimo privilegio  
✅ **Real-time Processing**: DynamoDB Streams + Lambda  

---

## 📁 Estructura del Proyecto

```
Practica_AWS/
│
├── infra/
│   ├── deploy.py                  # ⭐ Script principal de despliegue
│   ├── destroy.py                 # Limpieza completa de recursos
│   ├── subscribe_sns.py            # Suscripción a alertas por email
│   ├── cleanup_sns.py              # Limpieza de topics SNS obsoletos
│   ├── cleanup_subscriptions.py    # Limpieza de suscripciones pendientes
│   ├── deployment.json             # (Generado) Configuración del despliegue
│   └── requirements.txt            # Dependencias Python
│
├── lambdas/
│   ├── load_inventory/
│   │   └── lambda_function.py      # Lambda A: CSV parser
│   ├── get_inventory_api/
│   │   └── lambda_function.py      # Lambda B: REST API endpoints
│   └── notify_low_stock/
│       └── lambda_function.py      # Lambda C: Alertas inteligentes
│
├── website/
│   ├── index.html                  # Dashboard interactivo
│   ├── css/
│   │   └── styles.css              # Estilos responsive
│   └── images/
│       └── (assets del dashboard)
│
├── sample_inventory.csv            # Datos de ejemplo
├── .env.sample                     # Variables de configuración (opcional)
└── README.md                       # Este archivo
```

---

## 📊 Ejemplo de Respuesta API

### GET `/items`
```bash
curl https://hu0apd4dz6.execute-api.us-east-1.amazonaws.com/prod/items
```

**Respuesta**:
```json
{
  "items": [
    {
      "Store": "Berlin",
      "Item": "Widget-001",
      "Count": 100
    },
    {
      "Store": "Berlin",
      "Item": "Widget-002",
      "Count": 50
    },
    {
      "Store": "Berlin",
      "Item": "Gadget-001",
      "Count": 25
    },
    {
      "Store": "London",
      "Item": "Widget-001",
      "Count": 200
    },
    {
      "Store": "London",
      "Item": "Widget-003",
      "Count": 15
    },
    {
      "Store": "London",
      "Item": "Gadget-002",
      "Count": 80
    },
    {
      "Store": "Paris",
      "Item": "Widget-002",
      "Count": 45
    },
    {
      "Store": "Paris",
      "Item": "Gadget-001",
      "Count": 120
    },
    {
      "Store": "Paris",
      "Item": "Gadget-003",
      "Count": 15
    },
    {
      "Store": "Madrid",
      "Item": "Widget-001",
      "Count": 60
    },
    {
      "Store": "Madrid",
      "Item": "Widget-002",
      "Count": 20
    },
    {
      "Store": "Madrid",
      "Item": "Gadget-002",
      "Count": 90
    }
  ],
  "count": 12
}
```

### GET `/items/{store}`
```bash
curl https://hu0apd4dz6.execute-api.us-east-1.amazonaws.com/prod/items/Berlin
```

**Respuesta**:
```json
{
  "store": "Berlin",
  "items": [
    {
      "Store": "Berlin",
      "Item": "Widget-001",
      "Count": 100
    },
    {
      "Store": "Berlin",
      "Item": "Widget-002",
      "Count": 50
    },
    {
      "Store": "Berlin",
      "Item": "Gadget-001",
      "Count": 25
    }
  ],
  "count": 3
}
```

---

## 🐛 Solucionar Problemas

### Error: "NoCredentialsError"

**Causa**: Las credenciales AWS no están configuradas.

**Solución**:
```bash
# Opción 1: Usa CloudShell (credenciales automáticas)
# Opción 2: Configura ~/.aws/credentials (ver sección de configuración)
# Opción 3: Exporta variables de entorno
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_SESSION_TOKEN=xxx
```

### Error: "BucketAlreadyOwnedByYou"

**Causa**: Un bucket S3 con ese nombre ya existe (de un despliegue anterior).

**Solución**:
```bash
# Opción 1: Ejecuta destroy primero
python infra/destroy.py

# Opción 2: Cambia el sufijo en deploy.py (línea ~50)
# Busca: DEPLOYMENT_SUFFIX = "inventory-main"
# Cambia a: DEPLOYMENT_SUFFIX = "inventory-main-v2"
```

### Datos no aparecen en DynamoDB

**Causa**: El CSV no se procesó o está mal formateado.

**Solución**:
```bash
# Verifica que el CSV esté bien subido
aws s3 ls s3://inventory-uploads-inventory-main/

# Revisa los logs de Lambda
aws logs tail /aws/lambda/load_inventory --follow

# Verifica el formato del CSV (debe tener: Store,Item,Count)
cat sample_inventory.csv
```

### No recibo emails de SNS

**Causa**: Email no confirmado o correo universitario bloqueado.

**Solución**:
1. Verifica que confirmaste el email desde el enlace de SNS
2. Usa un correo personal (Gmail, Outlook, Yahoo)
3. Revisa carpeta de spam/correo no deseado
4. Revisa logs: `aws logs tail /aws/lambda/notify_low_stock --follow`

### API devuelve 500

**Causa**: Error en Lambda get_inventory_api.

**Solución**:
```bash
# Ver logs detallados
aws logs tail /aws/lambda/get_inventory_api --follow

# Luego cambia algún item y consulta la API
aws dynamodb update-item \
  --table-name Inventory \
  --key '{"Store": {"S": "Berlin"}, "Item": {"S": "Widget-001"}}' \
  --update-expression 'SET #c = :val' \
  --expression-attribute-names '{"#c": "Count"}' \
  --expression-attribute-values '{":val": {"N": "100"}}' \
  --region us-east-1

# Prueba la API
curl https://hu0apd4dz6.execute-api.us-east-1.amazonaws.com/prod/items
```

---

## 💡 Tips y Mejores Prácticas

1. **Guarda el archivo `deployment.json`**: Contiene todos los IDs de recursos (importante para debugging)

2. **Usa CloudWatch Logs**: Todos los Lambdas loguean todo. Es tu mejor herramienta de debugging.

3. **Prueba pequeño primero**: Sube 1-2 items antes de un CSV grande.

4. **Confirma SNS inmediatamente**: No ignores el email de confirmación de SNS.

5. **Usa un correo que recibas**: Los correos universitarios pueden filtrar. Usa Gmail/Outlook personal.

6. **Destruye cuando termines**: No dejes recursos activos (aunque sean gratis, es buena práctica).

7. **Guarda credenciales en `.aws/credentials`**: Más seguro que variables de entorno.

8. **Lee los logs**: Cada error está documentado en CloudWatch. Revísalos antes de preguntar.

---

## 📚 Recursos Útiles

- **AWS Lambda Docs**: https://docs.aws.amazon.com/lambda/
- **DynamoDB Docs**: https://docs.aws.amazon.com/dynamodb/
- **API Gateway v2**: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html
- **boto3 Docs**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **SNS Docs**: https://docs.aws.amazon.com/sns/

---

## 🎓 Conclusión

Este proyecto demuestra una **arquitectura serverless profesional** completa:

- ✅ Automatización total (IaC)
- ✅ Arquitectura production-ready
- ✅ Integración de múltiples servicios AWS
- ✅ Event-driven processing
- ✅ API REST real
- ✅ Dashboard interactivo
- ✅ Monitoreo y logging
- ✅ Manejo de errores robusto

**Tiempo total**: ~5 minutos de despliegue + validación manual



