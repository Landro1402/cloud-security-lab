# Secure S3 Baseline

## Objective

Deploy a reproducible S3 security baseline with Terraform and verify
its configuration and basic access behaviour.

## Architecture

A single S3 bucket in eu-north-1, with:
- All four bucket-level Block Public Access settings enabled.
- BucketOwnerEnforced object ownership, disabling ACLs.
- Default SSE-S3 encryption using AES256.
- A bucket policy denying requests that do not use HTTPS.

Terraform uses temporary credentials obtained through an AWS CLI
login session. No credentials are stored in the repository.

## Validation results

Tests performed on 7 October 2026.

| Check | Observed result |
|---|---|
| Terraform validation | Configuration valid |
| Deployment | 5 resources added, none changed or destroyed |
| Public access block | All four settings enabled |
| Object ownership | BucketOwnerEnforced |
| Default encryption | AES256 |
| HTTPS policy | Explicit deny for aws:SecureTransport=false |
| Authenticated upload | Successful; response confirmed AES256 |
| Authenticated download | Successful; identical to the original file |
| Anonymous download | AccessDenied |
| Terraform comparison after deployment | No changes |

## Interpretation and limitations

The tested object was readable by the authenticated deployment role
and was not readable anonymously.

The deployment role has broad permissions. These tests do not
demonstrate least-privilege access for an application role.

The HTTPS policy was inspected, but its rejection of HTTP requests
has not yet been tested.

This is a focused baseline, not a complete S3 security assessment.
Logging, versioning, recovery and customer-managed KMS keys are
outside the current scope.

## Cleanup

The synthetic test object was deleted after testing.

To remove the lab infrastructure, empty the bucket and review
`terraform plan -destroy` before running `terraform destroy`.

The bucket uses force_destroy=false to prevent Terraform from
automatically deleting stored objects.

## Automated configuration verification

All seven implemented checks passed against the deployed bucket:
- Four public access block settings.
- BucketOwnerEnforced object ownership.
- Default AES256 encryption.
- An explicit deny of non-HTTPS requests covering the bucket
  and all objects.

The checker returned exit code 0.

Eighteen local unit tests passed. Negative scenarios included
disabled or missing settings, an Allow instead of a Deny,
incomplete resource coverage, limited actions, additional
conditions and a policy referencing a different bucket.

An expired AWS login session caused an error to be reported.
After reauthentication, the live checks completed successfully.

The HTTPS check inspects the policy structure. Rejection of an
actual HTTP request has not been tested. The checker recognises
the project's specific policy pattern and is not a complete
IAM policy evaluator.