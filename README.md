# AWS Cloud Security Lab

A hands-on lab for deploying a secure S3 baseline and verifying a restricted
IAM reader role with Terraform, AWS CLI and Python.

The application scenario is deliberately small: a consumer needs to download
known training documents, without reading private documents, changing objects
or browsing the bucket. The project connects that requirement to permissions,
configuration checks and live authorization tests.

## What is implemented

| Component | Behaviour |
| --- | --- |
| S3 baseline | Bucket-level public access blocks, disabled ACLs, default SSE-S3 encryption and a policy denying insecure transport |
| IAM reader role | Allows `s3:GetObject` only on the lab bucket's `training/*` prefix |
| Configuration checker | Reads and checks seven S3 configuration settings |
| Authorization checker | Confirms the reader identity, downloads a known fixture and checks private-read and listing denials |
| Experiment runner | Creates unique fixtures, runs all five permission scenarios and attempts cleanup |
| Local tests | Test configuration interpretation and AWS result classification without contacting AWS |

The lab region is `eu-north-1` (Stockholm). The current Terraform configuration
manages **seven resources**: five S3 resources, one IAM role and its inline policy.
The existing operator role is read through a data source, not created by this lab.

## Design in brief

The operator deploys and inspects infrastructure, prepares fixtures and cleans
up test objects. The reader receives temporary STS credentials and performs
only the requests whose permissions are being tested.

A trust policy controls who may assume the reader role. A separate permissions
policy grants access to training objects. CLI profile names are local labels;
AWS authorizes requests using credentials and policies.

| Reader request | Expected result in the lab configuration |
| --- | --- |
| Download a training object | Allowed |
| Download a private object | AccessDenied |
| Upload an object | AccessDenied |
| Delete an object | AccessDenied |
| List objects in the bucket | AccessDenied |

Reading a known object and listing object keys are separate permissions.
The unwanted actions have no applicable Allow in the tested configuration;
the reader policy does not explicitly deny them.

## Getting started

Requirements: Terraform `>= 1.5, < 2.0`, Python 3, AWS CLI v2 and suitable AWS
permissions. Python scripts use only the standard library.

**Start with [setup and deployment](docs/setup.md).** It covers authentication,
the existing operator-role prerequisite, local variables and the reader profile.
The current configuration is tailored to an account containing
`AccountFullAccessRole`; it is not a drop-in deployment for every AWS account.

Once deployed and authenticated, run these commands from the repository root:

```bash
LAB_ACCOUNT_ID=$(terraform -chdir=terraform output -raw authenticated_account)
LAB_BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

# Read-only S3 configuration verification; use an inspection-capable profile.
python3 scripts/check_s3.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --profile cloud-fabio \
  --region eu-north-1

# Live experiment: creates and deletes synthetic objects.
python3 scripts/run_iam_lab.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --operator-profile cloud-fabio \
  --reader-profile cloud-fabio-reader
```

The profile names above are examples matching the documented setup. Use your
own names consistently if you change them. Shell variables must be recreated
in each new terminal session. `authenticated_account` is read from local
Terraform state; the runner separately checks the operator's live account.

## Local tests

```bash
python3 -m unittest discover -s tests -v
```

The reviewed revision has 23 passing unit tests. They cover S3 baseline checks
and IAM result interpretation. They do not yet cover the full runner's
orchestration and cleanup paths. Local tests do not validate a deployed account.

## Exit codes

| Code | Configuration checker | IAM checker / runner |
| --- | --- | --- |
| `0` | All implemented checks passed | All checks passed; the runner's cleanup requests also succeeded |
| `1` | A setting differs from the baseline | An expected denial succeeded, or downloaded content differed |
| `2` | Checks could not complete | Wrong identity, failed required operation, execution error or runner cleanup error |

An expired session or connection failure is an execution error, not proof of
an authorization denial. The IAM checks classify `(AccessDenied)` in CLI stderr;
this is a practical lab check, not a general structured AWS error parser.

## Repository guide

| Path | Purpose |
| --- | --- |
| `terraform/` | S3 and IAM configuration; committed provider lock file |
| `scripts/check_s3.py` | Read-only S3 configuration checks |
| `scripts/check_iam_access.py` | Read/list checks against existing synthetic fixtures |
| `scripts/run_iam_lab.py` | Fixture preparation, authorization experiment and cleanup |
| `tests/` | Offline unit tests |
| `policies/` | Example policy for the historical IAM simulation |
| `docs/` | Setup, design decisions, recorded results and limitations |

## Evidence and documentation

- [Setup and deployment](docs/setup.md): reproduce the current lab.
- [S3 baseline](docs/s3-baseline.md): control rationale and validation recorded on 7 October 2026.
- [IAM simulation](docs/iam-least-privilege.md): the initial supplied-policy experiment.
- [Live IAM validation](docs/iam-role-validation.md): role design, manual checks and automated experiment recorded on 8 October 2026.

Recorded results describe specific runs, not a guarantee about the account's
current state. Rerun the checks to establish current behaviour.

## Scope and limitations

- This is a learning lab, not a complete production security assessment.
- The operator retains broad permissions; the reader role does not protect
  against compromise of administrative credentials.
- Reader sessions can access any object whose key they know or guess under
  `training/*`. New content placed there enters the permitted scope.
- S3 configuration checks are distinct from live authorization tests. The HTTPS
  check inspects a particular deny pattern; no actual HTTP rejection test is implemented.
- The AES256 check matches this SSE-S3 baseline. SSE-KMS is not inherently insecure.
- Versioning, recovery, access logging, customer-managed KMS and a deployed
  application's identity mechanism are outside the implemented scope.
- The runner requires a bucket that has never had versioning enabled. Cleanup
  is attempted, but forced termination, expired credentials or connectivity
  failures can leave fixtures behind.

## Costs and teardown

Live checks make AWS API requests. The runner temporarily stores small objects;
free-plan eligibility, credits and charges depend on the account. No EC2
instances, NAT gateways or customer-managed KMS keys are provisioned here.

For fixture cleanup, verification and infrastructure removal, follow the
[teardown instructions](docs/setup.md#teardown). The bucket uses
`force_destroy = false`; Terraform will not automatically empty it.

## Next work

- Test runner failure handling and cleanup with mocked AWS responses.
- Run offline checks in continuous integration.
- Add structured validation reports and independently verified cleanup results.
