# Parlache del día

Juego web diario. Cada día hay una palabra colombiana de 5 letras; el jugador tiene 6 intentos para adivinarla y recibe pistas por color. Al terminar se revela el significado, un ejemplo y la región. *Parlache* es el argot urbano de Medellín.

Proyecto Final – Proyecto Cloud Integral · Cloud Computing · UdeA 2026.

## Estado

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Estructura del repo, `.gitignore`, documentación base | Hecha |
| 1 | Infraestructura base (VPC, S3, CloudFront, DynamoDB) | Escrita, pendiente de `terraform apply` |
| 2 | Backend (lógica común lista y probada; handlers pendientes) | En curso |
| 3–7 | Frontend, ranking, observabilidad, costos, documento y video | Pendiente |

El plan completo está en `PLAN_IMPLEMENTACION_PARLACHE_DEL_DIA.md`.

## Estructura

```
backend/    Lambdas en Python 3.12 (solo biblioteca estándar + boto3) y pruebas
frontend/   HTML + CSS + JS puro, sin build
infra/      Terraform (us-east-1)
loadtest/   Script de k6
scripts/    Despliegue del frontend e importación de palabras
docs/       Documento técnico, decisiones, diagrama y capturas
```

## Requisitos previos

AWS CLI v2 con credenciales de trabajo (SSO o usuario IAM con MFA, nunca el usuario raíz), Terraform ≥ 1.6, Python 3.12 y Git.

## Pruebas del backend

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests
```

## Despliegue de la infraestructura

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # editar alert_email
terraform init
terraform fmt && terraform validate
terraform plan
terraform apply
```

Después de aplicar: `./scripts/deploy-frontend.sh` sube el frontend y invalida la caché de CloudFront.
