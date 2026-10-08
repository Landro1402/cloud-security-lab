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

def check_https_policy(policy,bucket):
    bucket_arn = f"arn:aws:s3:::{bucket}"
    required_resources = {bucket_arn, f"{bucket_arn}/*"}

    statements = policy.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]

    for statement in statements:
        if not isinstance(statement, dict):
            continue
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        resources = statement.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]

        principal = statement.get("Principal")
        condition = statement.get("Condition")
        expected_condition = {
            "Bool": {"aws:SecureTransport": "false"}
        }
        boolean_condition = {
            "Bool": {"aws:SecureTransport": False}
        }
        
        if (
            statement.get("Effect") == "Deny"
            and principal in ("*", {"AWS": "*"})
            and ("s3:*" in actions or "*" in actions)
            and required_resources.issubset(set(resources))
            and condition in (expected_condition, boolean_condition)
            and "NotAction" not in statement
            and "NotResource" not in statement
            and "NotPrincipal" not in statement
        ):
            return True
        
    return False


def check_bucket_policy_baseline(policy, bucket):
    if not isinstance(policy, dict):
        return False
    if policy.get("Version") != "2012-10-17":
        return False

    statements = policy.get("Statement")
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list) or len(statements) != 1:
        return False

    statement = statements[0]
    if not isinstance(statement, dict):
        return False

    allowed_fields = {
        "Sid", "Effect", "Principal", "Action", "Resource", "Condition"
    }
    if set(statement) - allowed_fields:
        return False
    if statement.get("Action") not in ("s3:*", ["s3:*"]):
        return False

    resources = statement.get("Resource")
    if not isinstance(resources, list):
        return False
    if any(not isinstance(resource, str) for resource in resources):
        return False

    bucket_arn = f"arn:aws:s3:::{bucket}"
    if set(resources) != {bucket_arn, f"{bucket_arn}/*"}:
        return False

    return check_https_policy(policy, bucket)

def main():
    parser = argparse.ArgumentParser(
        description="Check an S3 bucket against the lab security baseline."
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
        
        policy_response = read_configuration("get-bucket-policy")
        policy_text = policy_response.get("Policy")
        if not isinstance(policy_text, str):
            raise ValueError("Missing or invalid bucket policy response.")

        policy = json.loads(policy_text)
        if not isinstance(policy, dict):
            raise ValueError("Unexpected bucket policy structure.")
        
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
        checks["HTTPSRequired"] = check_https_policy(
            policy, args.bucket
        )
        checks["BucketPolicyMatchesBaseline"] = check_bucket_policy_baseline(
            policy, args.bucket
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
