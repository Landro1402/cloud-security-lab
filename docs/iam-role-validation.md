# IAM Reader Role: Design and Live Validation

[Back to the project overview](../README.md) · [Setup](setup.md) · [Initial simulation](iam-least-privilege.md)

## Problem

A document consumer needs to retrieve known training objects. It has no
requirement to read private documents, modify objects or discover object keys.
The lab turns this requirement into a restricted role and tests its behaviour.

## Identity and authorization design

| Element | Purpose |
| --- | --- |
| Existing operator role | Deploys infrastructure, prepares fixtures and performs cleanup |
| Reader trust policy | Allows the existing `AccountFullAccessRole` to assume the reader role |
| Reader inline policy | Allows `s3:GetObject` only on the lab bucket's `training/*` |
| STS session | Supplies temporary reader credentials used for permission tests |
| Local CLI profiles | Select credential sources and the role to assume; names do not grant permissions |

Terraform reads the operator's actual IAM ARN, including its path, and creates
`cloud-security-lab-training-reader` plus its inline policy. The operator is
not created or restricted by this configuration.

The local source profile obtains operator credentials and uses them to request
a reader session. Requests made using the reader session have the reader's
permissions, not the union of reader and operator permissions.

## Decisions and trade-offs

- Prefix-scoped reads meet the consumer's requirement. Any new object under
  `training/*` enters that scope, including sensitive content mistakenly placed there.
- Omitting `ListBucket` avoids unnecessary discovery of object names. Known
  or guessed keys can still be read if they fall within the allowed prefix.
- Upload and deletion are not granted. In the tested configuration, those
  operations lack an applicable Allow; there is no explicit reader Deny.
- Temporary credentials avoid creating permanent IAM user keys, but stolen
  reader credentials remain useful during their validity unless blocked.
- An inline policy keeps permissions attached to one dedicated lab role.
  Other applicable policies could change effective permissions.
- Human role assumption demonstrates the boundary. A deployed application
  would need a dedicated workload identity and appropriate trust relationship.

## Recorded manual validation: 8 October 2026

The operator created synthetic objects at `training/iam-test.txt` and
`private/iam-test.txt`. STS GetCallerIdentity confirmed the reader session
before testing. The downloaded training content matched the original.

| Reader request | Observed result |
| --- | --- |
| GetObject on the training fixture | Allowed |
| GetObject on the private fixture | AccessDenied |
| PutObject under the training prefix | AccessDenied |
| DeleteObject on the training fixture | AccessDenied |
| ListObjectsV2 on the bucket | AccessDenied |

Manual fixtures were removed after the first experiment. Later standalone
checker exercises recreated them; the automated runner does not remove those
older keys. Inspect the bucket rather than assuming it is currently empty.

## Automated experiment

Run after completing [setup](setup.md), from the repository root:

```bash
LAB_ACCOUNT_ID=$(terraform -chdir=terraform output -raw authenticated_account)
LAB_BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

python3 scripts/run_iam_lab.py \
  --bucket "$LAB_BUCKET" \
  --account "$LAB_ACCOUNT_ID" \
  --operator-profile lab-operator \
  --reader-profile lab-reader
```

No manual uploads are required for this runner.

1. Check the operator account, expected reader role and versioning response.
2. Generate a UUID and create unique training/private fixture keys.
3. Upload both fixtures as the operator using the shared `TEST_CONTENT` bytes.
4. Invoke `check_iam_access.py` to verify identity, training content, private
   read denial and bucket-listing denial.
5. Attempt an upload and a deletion using reader credentials.
6. Attempt operator cleanup of all three possible keys in a `finally` block.

The reader's attempted deletion targets only this run's synthetic training
object. The upload target is also included in cleanup in case upload
unexpectedly succeeds. Temporary local files are removed automatically.

### Recorded automated result: 8 October 2026

Run `4d33e46b1ad14e48bfa781da00f75047` returned `0`. Fixture creation succeeded,
the reader checks matched expectations, upload and deletion were denied,
and cleanup requests succeeded for all three possible keys.

These are observations from the reported run. The runner does not independently
list or HEAD the keys after cleanup, so its cleanup messages establish successful
delete requests rather than a separate verification of the final bucket state.

### Independent cleanup verification

On 8 October 2026, separate operator ListObjectsV2 requests inspected
`training/iam-check-` and `private/iam-check-`.

Both returned `KeyCount: 0` and `IsTruncated: false`, confirming no current
objects remained under the runner's fixture prefixes at verification time.

This does not establish that the entire bucket was empty. Earlier manual
fixtures use different keys.

### Exit codes and failure interpretation

| Code | Meaning |
| --- | --- |
| `0` | All implemented checks passed and cleanup requests succeeded |
| `1` | An operation expected to be denied succeeded, or downloaded content differed |
| `2` | Preflight failure, a required operation failed, execution error or cleanup error |

A training read failure currently returns `2`, even if its cause is AccessDenied:
it is treated as failure of a required operation. Expected negative checks pass
only when the CLI stderr contains `(AccessDenied)`; other errors are not passes.
A cleanup error overrides an earlier result with `2` and prints the affected key.

## Test coverage

The repository has 32 passing local tests, including four tests for the S3 bucket policy baseline check.
Configuration and result-classification tests cover expected settings,
negative policy scenarios, unexpected successes and operational errors.

Five tests in `tests/test_iam_runner.py` verify:
- Successful execution uses the reader profile and cleans up the run's keys.
- A partial fixture upload failure still triggers cleanup.
- A cleanup failure returns an error while remaining keys are still attempted.
- Unexpected reader upload permission returns exit code 1 and triggers cleanup.
- Unexpected reader deletion permission returns exit code 1 and triggers cleanup.

AWS requests and the child checker are mocked. These tests verify runner
control flow without contacting AWS. Timeouts, interrupted execution and
additional preflight failures are not yet covered by these runner tests.

## Boundaries and failure scenarios

- The operator retains broad access. Compromise of its credentials can bypass
  the reader boundary or modify the infrastructure.
- The experiment checks selected requests in the current configuration; it
  does not prove absence of every other AWS permission.
- The operator preflight checks its account, not a complete permission inventory.
- The runner accepts an empty successful GetBucketVersioning response as an
  empty configuration. Enabled and Suspended status both stop the experiment.
- Cleanup targets the run's exact keys, leaving other objects alone. It is
  attempted after handled failures but may fail after credential expiry,
  connectivity loss or forced process termination.
- SSE-S3 is part of the current baseline. The tests do not address permissions
  and additional failure modes introduced by customer-managed KMS keys.

For leftover fixtures and resource removal, follow [teardown](setup.md#teardown).
