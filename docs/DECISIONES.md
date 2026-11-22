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
