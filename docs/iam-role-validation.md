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
