# AWS Cloud Security Lab

Hands-on project for learning and demonstrating AWS security controls,
Infrastructure as Code and automated security verification.

## First lab: secure S3 baseline

Lab scope:
- Provision an S3 bucket with Terraform.
- Block public access and disable ACLs.
- Configure server-side encryption.
- Require HTTPS through a bucket policy.
- Verify the configuration with Python and AWS CLI.
- Document security decisions, test results and cleanup procedures.

## Project structure

- terraform/: AWS infrastructure configuration
- scripts/: security verification scripts
- tests/: automated tests
- docs/: architecture, evidence and lessons learned

## Status

S3 baseline deployed and manually verified on AWS.
Authenticated upload and download succeeded; anonymous object
access was denied. The public access block check is automated in Python and covered by local tests.

See [validation results and limitations](docs/s3-baseline.md).

## Automated public access check

Requires Python 3 and an authenticated AWS CLI profile.

```bash
python3 scripts/check_s3.py \
  --bucket YOUR_BUCKET_NAME \
  --account YOUR_ACCOUNT_ID \
  --profile YOUR_AWS_PROFILE \
  --region eu-north-1
```

Exit codes:
- `0`: all four public access block settings are enabled.
- `1`: at least one setting is disabled or missing.
- `2`: the check could not be completed.

This check reads bucket configuration. It does not perform a complete
assessment of effective permissions.

## Local tests

No AWS credentials or external Python packages are required.

```bash
python3 -m unittest discover -s tests -v
```
