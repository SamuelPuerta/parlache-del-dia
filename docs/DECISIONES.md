# Decisiones de diseño

Registro de decisiones y supuestos. Se añade una entrada cada vez que el plan era ambiguo o se eligió la opción más simple y barata.

| # | Decisión | Motivo |
|---|---|---|
| D1 | Sin dominio propio: se usa `*.cloudfront.net` | No es posible registrar un dominio; CloudFront da HTTPS sin costo. Limitación: no se puede fijar la versión mínima de TLS. |
| D2 | Un solo origen: CloudFront sirve `/*` desde S3 y `/api/*` hacia API Gateway | Evita CORS y oculta el endpoint de la API. |
| D3 | El intento se valida solo por formato (5 letras) | No hay lista abierta y confiable de palabras válidas en español. |
| D4 | Palabra del día aleatoria y guardada, no calculada | Una fórmula en un repo público permitiría predecir las palabras futuras. |
| D5 | Alarmas por errores y DLQ, no por ausencia de métrica | Los periodos de las alarmas se alinean a UTC, no a medianoche de Bogotá. |
| D6 | Terraform en lugar de Serverless Framework | Herramienta distinta a la de otros laboratorios y muy pedida en vacantes. |
| D7 | Los archivos de variables (`*.tfvars`) no se versionan; se incluye `terraform.tfvars.example` | Evita publicar el correo de alertas. |
| D8 | El origen `api` de CloudFront se añade en la fase 2 junto con `apigw.tf` | La API Gateway no existe todavía en la fase 1. |
| D9 | El frontend se sube con `aws s3 sync` y no con recursos `aws_s3_object` | Evita conflictos entre el estado de Terraform y `sync --delete`. |
| D10 | Las pruebas de lógica pura no dependen de moto ni boto3 | Se pueden ejecutar en cualquier entorno; las de flujo con DynamoDB usarán moto. |
| D11 | Se permiten insultos y palabras despectivas o vulgares en `words.json`, sin censurar significados | Decisión del equipo (reemplaza la regla del plan 6.5 de evitar vulgaridades). Conviene un aviso de contenido en el frontend. |
| D12 | Si el CSV trae "No especificado en la fuente" como ejemplo, `words.json` lo deja vacío y el frontend oculta el ejemplo | No se inventan ejemplos ni se muestra texto de relleno. La v2 del CSV ya trae ejemplo en todas. |
| D13 | `words.json` (216 palabras de la v2 del CSV) se genera con `scripts/csv_to_words.py` desde `backend/data/colombianismos_5_letras.csv` | El CSV es la fuente editable; el script valida con la misma regla que usará el importador. |
| D14 | La lógica de negocio vive en `common/logic.py` y no importa boto3; `common/db.py` es el único código que habla con DynamoDB | Permite probar todo el flujo con un almacén en memoria (`tests/fakes.py`) y deja una sola prueba de integración con moto. |
| D15 | `today` y `guess` invocan a `picker` de forma síncrona solo si aún no existe la palabra de hoy | Respaldo por si el Scheduler falló; solo `picker` tiene permisos de escritura sobre `words`. |
| D16 | `picker` e `importer` propagan los errores en lugar de devolver 200 | Cuentan como error de la Lambda (alarma de la fase 5) y el Scheduler reintenta o usa la DLQ. Con S3 el evento se reintenta 2 veces. |
| D17 | El nombre `parlache-picker` se escribe literal en el entorno y en la política IAM | Evita un ciclo de dependencias en Terraform (todas las funciones comparten entorno). |
| D18 | `ranking` se implementó en la fase 2 (el plan lo situaba en la 4) | Es corto y la ruta ya existe en API Gateway. Falta la prueba con datos reales y el frontend. |
