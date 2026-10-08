# IAM Least-Privilege Policy Simulation

[Back to the project overview](../README.md) · [Live role validation](iam-role-validation.md)

## Purpose

This was the first IAM experiment, recorded on 7 October 2026. It evaluated
an identity-policy proposal before creating the reader role. The subsequent
[live experiment](iam-role-validation.md) implements and tests that design.

A document consumer needs known objects under `training/*`, but does not need
private documents, uploads, deletion or bucket listing.

## Policy

The [example JSON](../policies/training-reader-policy.json.example) allows only
`s3:GetObject` on:

```text
arn:aws:s3:::YOUR_BUCKET_NAME/training/*
```

Replace the placeholder before simulation. This example file is illustrative;
Terraform generates the deployed role policy directly in `terraform/iam.tf`.
It does not load or attach the example JSON file.

## Recorded simulation results

AWS IAM SimulateCustomPolicy evaluated the supplied identity policy:

| Action | Resource scope | Decision |
| --- | --- | --- |
| `s3:GetObject` | `training/sample.txt` object ARN | `allowed` |
| `s3:GetObject` | `private/sample.txt` object ARN | `implicitDeny` |
| `s3:PutObject` | `training/sample.txt` object ARN | `implicitDeny` |
| `s3:DeleteObject` | `training/sample.txt` object ARN | `implicitDeny` |
| `s3:ListBucket` | Bucket ARN | `implicitDeny` |

`implicitDeny` means no applicable Allow exists in the evaluated policy.
It is different from an explicit Deny. Another applicable policy could grant
additional access, subject to the other controls evaluated by AWS.

`ListBucket` authorizes listing object keys within a bucket. Listing account
buckets uses a separate permission, `s3:ListAllMyBuckets`.

## What this did and did not establish

The simulation confirmed the intended decisions for the supplied policy and
chosen action/resource combinations. No objects needed to exist for that step.

During this historical experiment, the policy was not attached to an identity
and no S3 operation was executed. The bucket policy, other identity policies,
permissions boundaries and organization controls were not included. The results
therefore did not establish the operator's effective permissions.

The next step is now complete: Terraform provisions a dedicated reader role,
and the [live IAM runner](iam-role-validation.md) tests real requests using its
temporary credentials. Simulation results and live results remain separate evidence.
