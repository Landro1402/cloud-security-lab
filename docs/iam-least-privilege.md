# IAM Least-Privilege Policy Simulation

## Scenario

An application needs to read objects with known keys under the
training/ prefix of an S3 bucket.

It does not need to upload or delete objects, read objects outside
that prefix, or list the bucket contents.

## Policy design

The example identity policy grants only s3:GetObject on:

arn:aws:s3:::YOUR_BUCKET_NAME/training/*

Reading an object and listing a bucket are separate permissions.
An application that knows the object key can request it without
being granted s3:ListBucket.

## Observed simulation results

Tests performed with AWS IAM SimulateCustomPolicy on 7 October 2026.

| Action | Resource | Decision |
|---|---|---|
| s3:GetObject | training/sample.txt | allowed |
| s3:GetObject | private/sample.txt | implicitDeny |
| s3:PutObject | training/sample.txt | implicitDeny |
| s3:DeleteObject | training/sample.txt | implicitDeny |
| s3:ListBucket | Bucket ARN | implicitDeny |

## Interpretation

The policy grants the required read operation within the specified
prefix and does not grant the other tested operations.

implicitDeny means that the evaluated policy does not provide an
applicable Allow. It is not an explicit Deny.

Other policies associated with an identity could grant additional
permissions.

## Limitations

Only the supplied identity policy was evaluated.

The policy was not attached to a dedicated application role.
The simulations did not execute operations against S3.

The bucket policy, other identity policies, permissions boundaries
and organization controls were not included in these simulations.

These results do not establish the effective permissions of the
deployment role or prove least privilege in a live application.

## Next step

Evaluate the policy using a dedicated role and temporary credentials,
then test both permitted and denied operations against real objects.
