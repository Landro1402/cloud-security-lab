import argparse
import json
import subprocess
import sys

PUBLIC_ACCESS_FLAGS = (
    
    "BlockPublicAcls",
    "IgnorePublicAcls",
    "BlockPublicPolicy",
    "RestrictPublicBuckets",    
)

def check_public_access(configuration):
    return {
        flag: configuration.get(flag) is True
        for flag in PUBLIC_ACCESS_FLAGS
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check an S3 bucket's public access block settings."
    )

    parser.add_argument("--bucket", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="eu-north-1")
    args = parser.parse_args()

    command = [
        "aws", "s3api", "get-public-access-block",
        "--bucket", args.bucket,
        "--expected-bucket-owner", args.account,
        "--profile", args.profile,
        "--region", args.region,
        "--output", "json",
        "--no-cli-pager"
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        response = json.loads(result.stdout)
    except subprocess.CalledProcessError as error:
        print(
            f"ERROR: AWS request failed.\n{error.stderr.strip()}",
            file=sys.stderr
        )
        return 2
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2    
    
    configuration = response.get("PublicAccessBlockConfiguration")
    if not isinstance(configuration, dict):
        print("ERROR: Unexpected AWS response.", file=sys.stderr)
        return 2

    checks = check_public_access(configuration)

    for flag,passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {flag}")

    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
