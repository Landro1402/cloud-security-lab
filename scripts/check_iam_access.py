import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

TEST_CONTENT = b"Synthetic data for IAM least-privilege testing.\n"

def run_aws(arguments, profile, region):
    return subprocess.run(
        [
            "aws", *arguments,
            "--profile", profile,
            "--region", region,
            "--no-cli-pager",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def check_result(name, result, expect_denied=False):
    if expect_denied:
        if result.returncode == 0:
            print(f"FAIL: {name} — request unexpectedly succeeded")
            return False

        if "(AccessDenied)" in result.stderr:
            print(f"PASS: {name} — access denied")
            return True

        raise RuntimeError(
            f"{name}: request failed for another reason:\n"
            f"{result.stderr.strip()}"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"{name}: expected request to succeed:\n"
            f"{result.stderr.strip()}"
        )

    print(f"PASS: {name}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Verify the lab reader's S3 read and list permissions."
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="eu-north-1")
    parser.add_argument("--training-key", default="training/iam-test.txt")
    parser.add_argument("--private-key", default="private/iam-test.txt")
    args = parser.parse_args()

    try:
        identity = run_aws(
            [
                "sts", "get-caller-identity",
                "--query", "Arn",
                "--output", "text",
            ],
            args.profile,
            args.region,
        )

        if identity.returncode != 0:
            raise RuntimeError(identity.stderr.strip())

        expected_prefix = (
            f"arn:aws:sts::{args.account}:assumed-role/"
            "cloud-security-lab-training-reader/"
        )

        if not identity.stdout.strip().startswith(expected_prefix):
            raise RuntimeError(
                "Unexpected identity. Use the lab reader role profile."
            )

        print("PASS: Expected reader identity")

        bucket_arguments = [
            "--bucket", args.bucket,
            "--expected-bucket-owner", args.account,
        ]

        with tempfile.TemporaryDirectory(prefix="cloudsec-iam-") as directory:
            training_file = Path(directory) / "training.txt"
            private_file = Path(directory) / "private.txt"

            training = run_aws(
                [
                    "s3api", "get-object",
                    *bucket_arguments,
                    "--key", args.training_key,
                    str(training_file),
                ],
                args.profile,
                args.region,
            )

            checks = [
                check_result("Training object readable", training)
            ]

            content_matches = (
                training_file.read_bytes() == TEST_CONTENT
            )
            print(
                f"{'PASS' if content_matches else 'FAIL'}: "
                "Training object content matches"
            )
            checks.append(content_matches)

            private = run_aws(
                [
                    "s3api", "get-object",
                    *bucket_arguments,
                    "--key", args.private_key,
                    str(private_file),
                ],
                args.profile,
                args.region,
            )
            checks.append(
                check_result(
                    "Private object read blocked",
                    private,
                    expect_denied=True,
                )
            )

            listing = run_aws(
                [
                    "s3api", "list-objects-v2",
                    *bucket_arguments,
                    "--max-keys", "1",
                    "--no-paginate",
                ],
                args.profile,
                args.region,
            )
            checks.append(
                check_result(
                    "Bucket listing blocked",
                    listing,
                    expect_denied=True,
                )
            )

        return 0 if all(checks) else 1

    except (
        OSError,
        subprocess.TimeoutExpired,
        RuntimeError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
