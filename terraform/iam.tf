# Read the existing operator role, including its actual IAM path.
data "aws_iam_role" "lab_operator" {
  name = "AccountFullAccessRole"
}

# A restricted role that the operator can assume for testing.
resource "aws_iam_role" "training_reader" {
  name        = "cloud-security-lab-training-reader"
  description = "Read-only access to training objects in the S3 security lab"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLabOperatorToAssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = data.aws_iam_role.lab_operator.arn
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Permissions granted to sessions using the restricted role.
resource "aws_iam_role_policy" "training_reader" {
  name = "read-training-objects-only"
  role = aws_iam_role.training_reader.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadTrainingObjectsOnly"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.lab.arn}/training/*"
      }
    ]
  })
}

output "training_reader_role_arn" {
  description = "ARN of the restricted S3 training reader role"
  value       = aws_iam_role.training_reader.arn
}
