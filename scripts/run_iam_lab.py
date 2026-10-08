import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

if __package__:
    from .check_iam_access import TEST_CONTENT, check_result, run_aws
else:
    from check_iam_access import TEST_CONTENT, check_result, run_aws

ERRORS = (
    OSError,
    subprocess.TimeoutExpired,
    RuntimeError,
    ValueError,
)


def read_json(arguments, profile, region):
    operation = " ".join(arguments[:2])

    result = run_aws(
        [*arguments, "--output", "json"],
        profile,
        region,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{operation} failed:\n{result.stderr.strip()}"
        )

    output = result.stdout.strip()

    if not output:
        if arguments[:2] == ["s3api", "get-bucket-versioning"]:
            return {}

        raise RuntimeError(
            f"{operation} succeeded but returned no JSON."
        )

    try:
        response = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"{operation} returned invalid JSON: {error}"
        ) from error

    if not isinstance(response, dict):
        raise RuntimeError(
            f"{operation} returned an unexpected response structure."
        )

    return response

def main():
    parser = argparse.ArgumentParser(
        description="Prepare, validate and clean up the IAM lab."
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--operator-profile", required=True)
    parser.add_argument("--reader-profile", required=True)
    parser.add_argument("--region", default="eu-north-1")
    args = parser.parse_args()

    bucket_arguments = [
        "--bucket", args.bucket,
        "--expected-bucket-owner", args.account,
    ]

    run_id = uuid4().hex
    training_key = f"training/iam-check-{run_id}/sample.txt"
    private_key = f"private/iam-check-{run_id}/sample.txt"
    upload_key = f"training/iam-check-{run_id}/upload.txt"
    cleanup_keys = [training_key, private_key, upload_key]

    cleanup_needed = False
    exit_code = 2

    try:
        operator = read_json(
            ["sts", "get-caller-identity"],
            args.operator_profile,
            args.region,
        )

        if operator.get("Account") != args.account:
            raise RuntimeError("Operator is using the wrong account.")

        reader = read_json(
            ["sts", "get-caller-identity"],
            args.reader_profile,
            args.region,
        )

        expected_prefix = (
            f"arn:aws:sts::{args.account}:assumed-role/"
            "cloud-security-lab-training-reader/"
        )

        if not str(reader.get("Arn", "")).startswith(expected_prefix):
            raise RuntimeError("Unexpected reader identity.")

        versioning = read_json(
            [
                "s3api", "get-bucket-versioning",
                *bucket_arguments,
            ],
            args.operator_profile,
            args.region,
        )

        if versioning.get("Status") is not None:
            raise RuntimeError(
                "This runner requires a bucket that has never "
                "had versioning enabled."
            )

        print(f"Run ID: {run_id}", flush=True)

        with tempfile.TemporaryDirectory(
            prefix="cloudsec-iam-"
        ) as directory:
            fixture = Path(directory) / "sample.txt"
            fixture.write_bytes(TEST_CONTENT)

            # A timed-out upload may still have stored an object.
            cleanup_needed = True

            for key in [training_key, private_key]:
                result = run_aws(
                    [
                        "s3api", "put-object",
                        *bucket_arguments,
                        "--key", key,
                        "--body", str(fixture),
                    ],
                    args.operator_profile,
                    args.region,
                )
                check_result(f"Fixture created: {key}", result)

            checker = Path(__file__).with_name(
                "check_iam_access.py"
            )

            result = subprocess.run(
                [
                    sys.executable, str(checker),
                    "--bucket", args.bucket,
                    "--account", args.account,
                    "--profile", args.reader_profile,
                    "--region", args.region,
                    "--training-key", training_key,
                    "--private-key", private_key,
                ],
                timeout=300,
            )

            if result.returncode not in (0, 1):
                raise RuntimeError(
                    "Read/list checker could not complete."
                )

            checks_passed = result.returncode == 0

            operations = [
                (
                    "put-object",
                    upload_key,
                    ["--body", str(fixture)],
                    "Reader upload blocked",
                ),
                (
                    "delete-object",
                    training_key,
                    [],
                    "Reader deletion blocked",
                ),
            ]

            for operation, key, extra, name in operations:
                result = run_aws(
                    [
                        "s3api", operation,
                        *bucket_arguments,
                        "--key", key,
                        *extra,
                    ],
                    args.reader_profile,
                    args.region,
                )

                passed = check_result(
                    name,
                    result,
                    expect_denied=True,
                )
                checks_passed = passed and checks_passed

            exit_code = 0 if checks_passed else 1

    except ERRORS as error:
        print(f"ERROR: {error}", file=sys.stderr)
        exit_code = 2

    finally:
        if cleanup_needed:
            for key in cleanup_keys:
                try:
                    result = run_aws(
                        [
                            "s3api", "delete-object",
                            *bucket_arguments,
                            "--key", key,
                        ],
                        args.operator_profile,
                        args.region,
                    )

                    check_result(
                        f"Cleanup completed: {key}",
                        result,
                    )

                except ERRORS as error:
                    print(
                        f"ERROR: Cleanup failed for {key}: {error}",
                        file=sys.stderr,
                    )
                    exit_code = 2

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
