# AWS Cloud Security Lab

Hands-on AWS security project combining Infrastructure as Code,
automated configuration checks and documented validation results.

## Objective

Build a reproducible S3 security baseline, verify its configuration
and test basic access behaviour.

The project demonstrates Terraform deployment, AWS CLI operations,
Python automation and security testing.

## Architecture

A single S3 bucket deployed in Europe (Stockholm), `eu-north-1`,
with four security controls:

| Control | Configuration |
|---|---|
| Public access protection | All four bucket-level Block Public Access settings enabled |
| Object ownership | BucketOwnerEnforced, disabling ACLs |
| Encryption at rest | Default SSE-S3 encryption using AES256 |
| Encryption in transit | Bucket policy explicitly denying non-HTTPS requests |

Terraform authenticates through an AWS CLI profile using temporary
credentials. No credentials are stored in the repository.

## Project structure

- `terraform/`: infrastructure configuration and provider lock file.
- `scripts/`: read-only Python configuration checker.
- `tests/`: local unit tests using synthetic configurations.
- `docs/`: validation results, security decisions and limitations.

## Prerequisites

- Terraform >= 1.5 and < 2.0.
- Python 3.
- AWS CLI v2 with an authenticated profile.
- AWS permissions to provision and inspect the lab resources.

The Python checker and tests use only the standard library.

## Deployment

Create a local `terraform/terraform.tfvars` file:

```hcl
aws_profile         = "YOUR_TERRAFORM_AWS_PROFILE"
expected_account_id = "YOUR_12_DIGIT_ACCOUNT_ID"
```

The profile must support authentication by the Terraform AWS provider.
For AWS CLI login sessions, this project uses a credential_process
profile that retrieves temporary credentials through the AWS CLI.

The provider restricts operations to the specified account.
Local variable files, Terraform state and saved plans are excluded
from Git.

From the repository root:

```bash
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -out=s3-baseline.tfplan
```

Review the plan before deploying. For a fresh deployment, the expected
result is five resources to add: one bucket and four associated
configurations.

Apply the reviewed plan:

```bash
terraform -chdir=terraform apply s3-baseline.tfplan
```

Applying a saved plan executes it without an additional confirmation
prompt. AWS usage may consume credits or incur charges, depending on
the account plan.

Retrieve the bucket name:

```bash
terraform -chdir=terraform output -raw bucket_name
```

## Automated configuration checks

The checker reads AWS configuration and verifies:

- BlockPublicAcls is enabled.
- IgnorePublicAcls is enabled.
- BlockPublicPolicy is enabled.
- RestrictPublicBuckets is enabled.
- Object ownership is BucketOwnerEnforced.
- Default encryption uses AES256.
- A bucket policy explicitly denies non-HTTPS requests for both
  the bucket and all its objects.

Run from the repository root:

```bash
LAB_BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

python3 scripts/check_s3.py \
  --bucket "$LAB_BUCKET" \
  --account YOUR_ACCOUNT_ID \
  --profile YOUR_AWS_PROFILE \
  --region eu-north-1
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | All implemented checks passed |
| `1` | At least one configuration does not match the baseline |
| `2` | The checks could not be completed |

AWS request failures, including expired login sessions, are reported
as errors rather than successful checks.

## Local tests

Tests run without AWS credentials or network access:

```bash
python3 -m unittest discover -s tests -v
```

They cover expected configurations and negative scenarios, including:

- Disabled or missing public access block settings.
- Strings incorrectly used in place of boolean values.
- Ownership settings outside the expected baseline.
- Missing encryption settings or a different encryption algorithm.
- An Allow statement instead of the required Deny.
- Missing bucket or object coverage in the HTTPS policy.
- Additional conditions that narrow the transport restriction.
- Limited actions or a policy referencing another bucket.

## Observed results

Validation performed on 7 October 2026:

| Check | Result |
|---|---|
| Terraform validation | Passed |
| AWS deployment | Five resources added |
| Post-deployment Terraform plan | No changes |
| Authenticated object upload | Successful; AES256 confirmed |
| Authenticated object download | Successful; content identical to original |
| Anonymous object download | AccessDenied |
| Test object cleanup | Deleted; bucket confirmed empty |
| Automated configuration checks | Seven PASS results; exit code 0 |
| Local unit tests | Eighteen tests passed |

See [validation results and limitations](docs/s3-baseline.md)
for additional details.

## Scope and limitations

This is a focused configuration baseline, not a complete S3 security
assessment.

The deployment identity uses a broadly privileged role. Successful
authenticated operations do not demonstrate least-privilege access
for an application.

The anonymous access test verifies that the tested object could not
be downloaded anonymously under the tested conditions.

The encryption check expects this project's SSE-S3 baseline.
SSE-KMS does not match that baseline, but is not inherently insecure.

The HTTPS check inspects the explicit deny pattern used by this
project. It does not send HTTP requests or implement a complete IAM
policy evaluator. Equivalent policies expressed differently may
not be recognised.

Versioning, recovery, access logging, customer-managed KMS keys and
application-specific IAM permissions are outside the current scope.

## Cleanup

Remove any test objects before deleting the infrastructure.

The bucket uses `force_destroy = false`, preventing Terraform from
automatically deleting stored objects during cleanup.

Review the destruction plan:

```bash
terraform -chdir=terraform plan -destroy
```

Then remove the lab resources:

```bash
terraform -chdir=terraform destroy
```

Review the resources listed in the confirmation prompt before
approving destruction.

## Next steps

- Design and evaluate a least-privilege S3 application policy.
- Automate local tests through continuous integration.
- Extend the checker with structured reports and additional
  error-handling tests.