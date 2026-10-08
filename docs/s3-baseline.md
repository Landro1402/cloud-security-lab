# Secure S3 Baseline

[Back to the project overview](../README.md) · [Setup](setup.md)

## Problem and scope

Store lab documents in a private S3 bucket with explicit baseline controls.
Terraform declares the configuration; Python verifies the deployed settings.
Manual object requests provide separate evidence of access behaviour.

## Controls and design decisions

| Control | Intended protection | Boundary or trade-off |
| --- | --- | --- |
| Four bucket-level Block Public Access flags | Restrict public policies and ACL-based exposure | Does not restrict every authenticated identity |
| BucketOwnerEnforced ownership | Disables ACLs; access is managed through policies | Applications requiring ACL-based sharing need another design |
| Default AES256 / SSE-S3 | Encrypts newly stored objects by default using S3-managed keys | No customer-managed KMS key or key-policy exercise |
| Deny insecure transport | Explicitly denies `s3:*` when `aws:SecureTransport` is false, covering bucket and object ARNs | The checker inspects this policy; it does not perform an HTTP request |

`terraform/s3.tf` defines the five S3 resources. IAM role configuration is
separate in `terraform/iam.tf`. The account and credentials come from the
provider configuration in `terraform/main.tf`; the region is `eu-north-1`.

## Recorded validation: 7 October 2026

These observations refer to the initial S3-only deployment, before the two
IAM resources were added.

| Check | Observed result |
| --- | --- |
| Terraform validation | Configuration valid |
| Initial S3 deployment | Five resources added; none changed or destroyed |
| Bucket-level public access block | All four flags true |
| Object ownership | BucketOwnerEnforced |
| Default encryption | AES256 |
| Transport policy | Expected explicit deny pattern present |
| Authenticated upload | Successful; response reported AES256 |
| Authenticated download | Successful; content matched the original |
| Anonymous download of the tested object | AccessDenied |
| Post-deployment Terraform plan | No changes |
| Manual fixture cleanup | Object deleted; bucket confirmed empty at that time |
| Configuration checker | Seven PASS results; exit code 0 |

The initial S3 checks had 18 passing unit tests. The current repository
adds five IAM result-classification tests and five runner tests,
for 28 local tests overall.

## How to reproduce configuration verification

After following [setup](setup.md), run from the repository root:

```bash
LAB_ACCOUNT_ID=$(terraform -chdir=terraform output -raw authenticated_account)
LAB_BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

python3 scripts/check_s3.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --profile cloud-fabio \
  --region eu-north-1
```

The script makes read-only configuration requests. It checks the four public
access flags, ownership, default encryption and HTTPS policy. It does not
upload objects or rerun the historical anonymous-download test.

Exit codes: `0` for all implemented checks passing, `1` for a baseline mismatch,
`2` when checks cannot complete. An expired login session is an error; refresh
the operator login before retrying.

## Interpretation and limitations

- The anonymous result applies to the object and conditions tested. It is not
  an exhaustive public-exposure assessment of the account.
- The initial authenticated requests used a broadly privileged operator.
  Application permission boundaries are tested in the [IAM lab](iam-role-validation.md).
- AES256 is the chosen baseline. SSE-KMS failing this particular check does
  not establish that SSE-KMS is insecure.
- The HTTPS matcher recognises the project's explicit deny structure, not all
  semantically equivalent policies. It is not a complete IAM evaluator.
- Actual HTTP rejection, access logging, recovery, versioning and customer-managed
  KMS keys have not been implemented or validated by these checks.

For object cleanup and resource destruction, use [teardown](setup.md#teardown).
