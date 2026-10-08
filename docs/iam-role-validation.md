# IAM Least-Privilege Role: Design and Validation

## Problem

A document-consuming application needs to retrieve training files
from an S3 bucket. It does not need access to private documents,
object modification, deletion, or bucket listing.

The objective is to grant only the access required for that task
and verify the resulting permissions with real AWS requests.

## Design

Terraform provisions a dedicated IAM role and an inline permissions
policy allowing `s3:GetObject` on the lab bucket's `training/*` prefix.

The role's trust policy allows the existing lab operator role to
assume it. AWS STS issues temporary credentials for the reader session.

Two AWS CLI profiles separate administrative operations from
restricted reader operations. Profile names are local configuration
labels; AWS authorizes requests using credentials and policies.

## Design Decisions and Trade-Offs

- Prefix-scoped access permits reading training documents while
  excluding objects under other prefixes.
- Bucket listing is omitted because the consumer knows the object keys.
  This prevents discovery through ListObjectsV2 but does not hide known keys.
- Write and delete permissions are omitted because they are unnecessary
  for a read-only consumer.
- Temporary role credentials avoid creating long-lived IAM user keys.
- Terraform makes the intended configuration reproducible and reviewable.
- An inline policy keeps this small lab's permissions attached directly
  to its dedicated role.

## Validation

Synthetic objects were uploaded under both `training/` and `private/`
using the administrative profile.

The reader identity was confirmed using STS GetCallerIdentity before
performing authorization tests.

| Request using the reader role | Observed result |
| --- | --- |
| GetObject on training/iam-test.txt | Allowed |
| GetObject on private/iam-test.txt | AccessDenied |
| PutObject under training/ | AccessDenied |
| DeleteObject on training/iam-test.txt | AccessDenied |
| ListObjectsV2 on the bucket | AccessDenied |

The downloaded training object matched the original local file.

Test objects were removed using the administrative profile after
validation.

## Limitations and Failure Scenarios

- This is a manually validated lab, not a production deployment.
- The operator retains administrative access and can assume the reader role.
- Compromise of reader credentials exposes readable training objects
  during the credentials' validity.
- Compromise of administrative credentials can bypass the reader's
  restrictions or modify the infrastructure.
- New objects under training/ fall within the permission scope.
- Unwanted actions are denied because no applicable Allow grants them
  in the tested configuration, rather than through explicit Deny statements.
- Additional policies or changes to resource policies may alter
  effective permissions.
- The CLI setup demonstrates role assumption by a human operator.
  A deployed workload would need its own appropriate identity mechanism.


## Automated Authorization Experiment

`scripts/run_iam_lab.py` performs a complete live authorization experiment:

1. Verifies the operator account and reader identity.
2. Checks that bucket versioning has never been enabled.
3. Creates synthetic training and private objects with unique keys.
4. Runs the read and list checker.
5. Tests that reader uploads and deletion are denied.
6. Attempts cleanup of all objects belonging to the run.

The uploader and checker share one content definition.

Run from the repository root:

```bash
LAB_ACCOUNT_ID=$(terraform -chdir=terraform output -raw authenticated_account)
LAB_BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

python3 scripts/run_iam_lab.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --operator-profile cloud-fabio \
  --reader-profile cloud-fabio-reader
```

### Results

A complete run returned exit code 0:
- Training download succeeded and its content matched.
- Private reading, listing, upload and deletion returned AccessDenied.
- Cleanup requests succeeded for all three possible object keys.

### Exit Codes

- 0: All checks passed and cleanup requests succeeded.
- 1: A permission or content check failed.
- 2: An execution or cleanup error prevented reliable completion.

### Scope and Limitations

The runner tests selected actions and resources; it is not a complete
evaluation of every possible permission.

Cleanup targets only this run's unique keys. It does not remove fixtures
from earlier manual tests.

Cleanup is attempted after handled failures, but cannot be guaranteed
after forced termination, credential expiry or connectivity loss.

This implementation requires an unversioned bucket. Successful blank
GetBucketVersioning output is normalized to an empty configuration.

Existing unit tests cover checker logic and result interpretation.
The orchestration and cleanup paths do not yet have dedicated unit tests.