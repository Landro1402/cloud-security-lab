# Setup and Deployment

[Back to the project overview](../README.md)

Run commands from the repository root. Examples use `lab-operator` for the
operator login, `lab-terraform` for the credential-process bridge and
`lab-reader` for reader sessions. These are arbitrary local profile
names, not AWS permissions or account identities.

## 1. Check prerequisites

```bash
terraform version
python3 --version
aws --version
```

The Terraform configuration requires version `>= 1.5, < 2.0` and AWS provider
`>= 6.0, < 7.0`. The committed lock file pins the selected provider version.
Python scripts use only the standard library. This authentication walkthrough
requires an AWS CLI v2 release supporting `aws login` and credential export.

The account must already contain the IAM role `AccountFullAccessRole`.
`terraform/iam.tf` looks it up by name and uses its actual ARN, including its
path, in the reader's trust policy. The operator needs permissions to inspect
that role, provision the lab's S3 and IAM resources, and assume the reader role.

If your account uses another operator role, adapt the data source in
`terraform/iam.tf` and review the resulting trust policy before deployment.
The role name is currently hardcoded; this is a portability limitation.

## 2. Authenticate the operator

```bash
aws login --profile lab-operator
aws sts get-caller-identity --profile lab-operator --no-cli-pager

aws iam get-role \
  --role-name AccountFullAccessRole \
  --profile lab-operator \
  --query 'Role.{Name:RoleName,Arn:Arn}' \
  --output json \
  --no-cli-pager
```

Complete the browser login using the intended account and operator role.
Check both the account number and role. Console access alone does not establish
an authenticated CLI session. Do not put session credentials in the repository.

Configure the bridge used by Terraform and by role assumption:

```bash
aws configure set credential_process \
  "aws configure export-credentials --profile lab-operator --format process" \
  --profile lab-terraform

aws configure set region eu-north-1 --profile lab-terraform
```

The bridge executes the AWS CLI to obtain temporary credentials from the login
profile. It does not create an IAM identity or grant additional permissions.

## 3. Configure local Terraform inputs

Create `terraform/terraform.tfvars` locally:

```hcl
aws_profile         = "lab-terraform"
expected_account_id = "YOUR_12_DIGIT_ACCOUNT_ID"
bucket_prefix       = "cloud-security-lab-"
```

When adapting an existing deployment, preserve its original bucket prefix in the ignored local inputs to avoid planning a bucket replacement.

Replace the account placeholder with the account verified in step 2.
This file is ignored by Git. The provider's `allowed_account_ids` setting
restricts deployment to that account; it does not replace IAM authorization.
State, saved plans and local configuration are also ignored. Ignoring files
prevents ordinary staging; it does not encrypt them on disk.

## 4. Review and deploy

```bash
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -out=lab.tfplan
```

For an empty Terraform state with the required operator role already present,
the current configuration should plan seven creations: five S3 resources,
the reader role and its inline policy. Existing infrastructure/state may
produce a different plan; inspect every action.

```bash
terraform -chdir=terraform apply lab.tfplan
```

Applying a saved plan does not ask for another confirmation. Review it first.
Do not apply an old plan after editing the configuration; generate a new plan.

## 5. Configure the reader profile

```bash
READER_ROLE_ARN=$(terraform -chdir=terraform output -raw training_reader_role_arn)

aws configure set role_arn "$READER_ROLE_ARN" --profile lab-reader
aws configure set source_profile lab-terraform --profile lab-reader
aws configure set role_session_name lab-reader-session --profile lab-reader
aws configure set region eu-north-1 --profile lab-reader
aws configure set output json --profile lab-reader

aws sts get-caller-identity --profile lab-reader --no-cli-pager
```

The ARN must identify an assumed session of
`cloud-security-lab-training-reader` in the intended account.
The source profile obtains operator credentials; AWS STS issues a separate
reader session. Administrative permissions are not added to that reader session.

This is equivalent to using a separate reader-source bridge pointing at the
same login profile. No additional bridge is required for this walkthrough.

## 6. Validate

```bash
LAB_ACCOUNT_ID=$(terraform -chdir=terraform output -raw authenticated_account)
LAB_BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

python3 -m unittest discover -s tests -v

python3 scripts/check_s3.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --profile lab-operator \
  --region eu-north-1

python3 scripts/run_iam_lab.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --operator-profile lab-operator \
  --reader-profile lab-reader
```

Check `echo $?` immediately after each checker or runner. Offline tests should
pass; the configuration checker should print seven PASS results. The runner
should print fixture creation, reader identity/content/access checks, upload
and deletion denials, and successful cleanup requests before returning `0`.

The runner prepares its own fixtures. The standalone `check_iam_access.py`
requires existing synthetic objects matching `TEST_CONTENT`; use the runner
for the normal end-to-end workflow.

## Troubleshooting

| Symptom | Interpretation and next step |
| --- | --- |
| Expired login session | Run `aws login --profile lab-operator`, then check the operator identity and retry |
| Wrong reader identity | Inspect the reader profile's role ARN and source profile; use GetCallerIdentity |
| Unknown option `--formatprocess` | Correct the bridge command to `--format process` |
| Empty versioning response | The runner accepts successful blank GetBucketVersioning output as an empty configuration; it does not accept blank identity responses |
| Content mismatch in standalone checker | Confirm fixtures contain the exact shared TEST_CONTENT bytes; the runner creates them consistently |
| Versioning Enabled or Suspended | The runner stops before creating fixtures; it does not support version-aware cleanup |
| Cleanup error | Note the printed exact keys, restore operator access, and delete only the identified synthetic objects |

## Teardown

First inspect any objects left by manual tests or interrupted runs:

```bash
aws s3api list-objects-v2 \
  --bucket "$LAB_BUCKET" \
  --expected-bucket-owner "$LAB_ACCOUNT_ID" \
  --profile lab-operator \
  --region eu-north-1 \
  --output json \
  --no-cli-pager
```

Remove only reviewed lab objects, one exact key at a time:

```bash
aws s3api delete-object \
  --bucket "$LAB_BUCKET" \
  --key "EXACT_SYNTHETIC_OBJECT_KEY" \
  --expected-bucket-owner "$LAB_ACCOUNT_ID" \
  --profile lab-operator \
  --region eu-north-1 \
  --no-cli-pager
```

Do not pass a local output filename to DeleteObject. Repeat the listing to
verify the final state. The runner's cleanup targets its own unique keys;
it does not remove earlier `training/iam-test.txt` or `private/iam-test.txt`.

Then review and remove the infrastructure:

```bash
terraform -chdir=terraform plan -destroy
terraform -chdir=terraform destroy
```

Review the confirmation prompt. This removes the Terraform-managed bucket,
S3 configurations, reader role and inline policy. It does not delete the
pre-existing operator role or local CLI profiles. `force_destroy = false`
prevents Terraform from automatically deleting stored objects.
