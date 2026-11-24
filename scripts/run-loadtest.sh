#!/usr/bin/env bash
# Enciende la EC2, corre k6 contra CloudFront por SSM Run Command y la vuelve a detener.
# Uso: scripts/run-loadtest.sh            (lee los datos de terraform output)
# Requiere: AWS CLI v2 con credenciales válidas y Terraform ya aplicado.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="terraform -chdir=$ROOT/infra/terraform"
REGION="${AWS_REGION:-us-east-1}"

INSTANCE_ID="$($TF output -raw loadgen_instance_id)"
DOMAIN="$($TF output -raw cloudfront_domain)"
BASE_URL="https://${DOMAIN}"

# Pase lo que pase, la instancia termina detenida.
trap 'echo "Deteniendo la instancia..."; aws ec2 stop-instances --region "$REGION" --instance-ids "$INSTANCE_ID" >/dev/null' EXIT

echo "Encendiendo $INSTANCE_ID..."
aws ec2 start-instances --region "$REGION" --instance-ids "$INSTANCE_ID" >/dev/null
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

echo "Esperando a que SSM la vea en línea..."
for _ in $(seq 1 60); do
  STATUS="$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"
  [ "$STATUS" = "Online" ] && break
  sleep 5
done
[ "$STATUS" = "Online" ] || { echo "SSM no respondió en 5 minutos" >&2; exit 1; }

SCRIPT_B64="$(base64 < "$ROOT/loadtest/k6-script.js" | tr -d '\n')"
PARAMS="$(mktemp)"
cat > "$PARAMS" <<JSON
{"commands": [
  "set -e",
  "command -v k6 >/dev/null || { dnf install -y https://dl.k6.io/rpm/repo.rpm && dnf install -y k6; }",
  "echo '$SCRIPT_B64' | base64 -d > /tmp/k6-script.js",
  "k6 run --no-color -e BASE_URL=$BASE_URL /tmp/k6-script.js"
]}
JSON

echo "Ejecutando k6 contra $BASE_URL (unos 2 a 4 minutos)..."
COMMAND_ID="$(aws ssm send-command --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name AWS-RunShellScript \
  --timeout-seconds 900 \
  --parameters "file://$PARAMS" \
  --query 'Command.CommandId' --output text)"
rm -f "$PARAMS"

while true; do
  STATUS="$(aws ssm get-command-invocation --region "$REGION" \
    --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" \
    --query 'Status' --output text 2>/dev/null || echo Pending)"
  case "$STATUS" in
    Pending|InProgress|Delayed) sleep 10 ;;
    *) break ;;
  esac
done

echo "Estado: $STATUS"
aws ssm get-command-invocation --region "$REGION" --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" \
  --query 'StandardOutputContent' --output text
if [ "$STATUS" != "Success" ]; then
  aws ssm get-command-invocation --region "$REGION" --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" \
    --query 'StandardErrorContent' --output text >&2
  exit 1
fi
