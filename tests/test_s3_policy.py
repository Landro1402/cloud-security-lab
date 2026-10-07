import copy
import unittest

from scripts.check_s3 import check_https_policy


class HTTPSPolicyTests(unittest.TestCase):
    def setUp(self):
        self.bucket = "example-security-lab"
        self.policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": [
                        f"arn:aws:s3:::{self.bucket}",
                        f"arn:aws:s3:::{self.bucket}/*",
                    ],
                    "Condition": {
                        "Bool": {"aws:SecureTransport": "false"}
                    },
                }
            ],
        }

    def modified_policy(self):
        return copy.deepcopy(self.policy)

    def test_expected_deny_passes(self):
        self.assertTrue(check_https_policy(self.policy, self.bucket))

    def test_allow_does_not_pass(self):
        policy = self.modified_policy()
        policy["Statement"][0]["Effect"] = "Allow"
        self.assertFalse(check_https_policy(policy, self.bucket))

    def test_missing_object_scope_fails(self):
        policy = self.modified_policy()
        policy["Statement"][0]["Resource"].pop()
        self.assertFalse(check_https_policy(policy, self.bucket))

    def test_missing_bucket_scope_fails(self):
        policy = self.modified_policy()
        policy["Statement"][0]["Resource"].pop(0)
        self.assertFalse(check_https_policy(policy, self.bucket))

    def test_extra_condition_fails(self):
        policy = self.modified_policy()
        policy["Statement"][0]["Condition"]["StringEquals"] = {
            "aws:PrincipalAccount": "123456789012"
        }
        self.assertFalse(check_https_policy(policy, self.bucket))

    def test_limited_actions_fail(self):
        policy = self.modified_policy()
        policy["Statement"][0]["Action"] = "s3:GetObject"
        self.assertFalse(check_https_policy(policy, self.bucket))

    def test_wrong_bucket_fails(self):
        self.assertFalse(
            check_https_policy(self.policy, "different-bucket")
        )

    def test_missing_statement_fails(self):
        self.assertFalse(check_https_policy({}, self.bucket))


if __name__ == "__main__":
    unittest.main()