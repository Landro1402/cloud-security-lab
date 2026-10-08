import copy
import unittest

from scripts.check_s3 import check_bucket_policy_baseline, check_https_policy


class BucketPolicyBaselineTests(unittest.TestCase):
    def setUp(self):
        self.bucket = "example-security-lab"
        self.policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [
                    f"arn:aws:s3:::{self.bucket}",
                    f"arn:aws:s3:::{self.bucket}/*",
                ],
                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
            }],
        }

    def test_expected_policy_passes(self):
        self.assertTrue(check_bucket_policy_baseline(self.policy, self.bucket))

    def test_extra_cross_account_allow_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["Statement"].append({
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::111122223333:root"},
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{self.bucket}/*",
        })
        self.assertTrue(check_https_policy(policy, self.bucket))
        self.assertFalse(check_bucket_policy_baseline(policy, self.bucket))

    def test_extra_deny_is_reported_as_baseline_drift(self):
        policy = copy.deepcopy(self.policy)
        policy["Statement"].append({
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:DeleteObject",
            "Resource": f"arn:aws:s3:::{self.bucket}/*",
        })
        self.assertTrue(check_https_policy(policy, self.bucket))
        self.assertFalse(check_bucket_policy_baseline(policy, self.bucket))

    def test_extra_resource_is_reported_as_baseline_drift(self):
        policy = copy.deepcopy(self.policy)
        policy["Statement"][0]["Resource"].append(
            "arn:aws:s3:::another-example-bucket/*"
        )
        self.assertTrue(check_https_policy(policy, self.bucket))
        self.assertFalse(check_bucket_policy_baseline(policy, self.bucket))


if __name__ == "__main__":
    unittest.main()
