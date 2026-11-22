variable "region" {
  description = "Región única del proyecto (las métricas de facturación solo existen en us-east-1)."
  type        = string
  default     = "us-east-1"
}

variable "alert_email" {
  description = "Correo que recibe las alarmas y las alertas de presupuesto."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Presupuesto mensual en USD para AWS Budgets."
  type        = number
  default     = 5
}

variable "epoch_date" {
  description = "Fecha del día #1 del juego (YYYY-MM-DD)."
  type        = string
  default     = "2026-11-25"
}
