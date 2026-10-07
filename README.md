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
access was denied. Automated Python checks are the next step.

See [validation results and limitations](docs/s3-baseline.md).
