# Generador de carga: t3.micro en la subred pública, detenida cuando no se usa.
# Sin puerto 22 (security group sin ingreso): se entra por SSM Session Manager.

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "loadgen" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.loadgen.id]
  iam_instance_profile        = aws_iam_instance_profile.loadgen.name
  associate_public_ip_address = true # sin NAT, la IP pública es la salida a SSM y a CloudFront

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 obligatorio
  }

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "parlache-loadgen" }

  lifecycle {
    # La AMI "latest" cambia con el tiempo; no se reemplaza la instancia por eso.
    ignore_changes = [ami]
  }
}

# Terraform la deja detenida. scripts/run-loadtest.sh la enciende, corre k6 y la vuelve a detener.
resource "aws_ec2_instance_state" "loadgen" {
  instance_id = aws_instance.loadgen.id
  state       = "stopped"
}
