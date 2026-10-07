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

def check_ownership(response):
    rules = response.get("OwnershipControls", {}).get("Rules", [])
    return (
        len(rules) == 1
        and rules[0].get("ObjectOwnership") == "BucketOwnerEnforced"
    )

def check_encryption(response):
    rules = response.get(
        "ServerSideEncryptionConfiguration", {}
    ).get("Rules", [])
    return (
        len(rules) == 1
        and rules[0].get(
            "ApplyServerSideEncryptionByDefault", {}
        ).get("SSEAlgorithm") == "AES256"
    )

def main():
    parser = argparse.ArgumentParser(
        description="Check an S3 bucket's public access block settings."
    )

    parser.add_argument("--bucket", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="eu-north-1")
    args = parser.parse_args()

    def read_configuration(operation):
        command = [
            "aws", "s3api", operation,
            "--bucket", args.bucket,
            "--expected-bucket-owner", args.account,
            "--profile", args.profile,
            "--region", args.region,
            "--output", "json",
            "--no-cli-pager",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

        response = json.loads(result.stdout)
        if not isinstance(response, dict):
            raise ValueError("Unexpected AWS response structure.")

        return response

    try:
        public_response = read_configuration("get-public-access-block")
        ownership_response = read_configuration(
            "get-bucket-ownership-controls"
        )
        encryption_response = read_configuration("get-bucket-encryption")

        configuration = public_response.get(
            "PublicAccessBlockConfiguration"
        )
        if not isinstance(configuration, dict):
            raise ValueError("Missing public access block configuration.")

        checks = check_public_access(configuration)
        checks["BucketOwnerEnforced"] = check_ownership(ownership_response)
        checks["DefaultEncryptionAES256"] = check_encryption(
            encryption_response
        )

    except subprocess.CalledProcessError as error:
        print(
            f"ERROR: AWS request failed.\n{error.stderr.strip()}",
            file=sys.stderr,
        )
        return 2
    except (
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
        TypeError,
        AttributeError,
    ) as error:
        print(f"ERROR: Could not complete checks: {error}", file=sys.stderr)
        return 2

    for name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")

    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
