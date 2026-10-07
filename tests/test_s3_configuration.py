import unittest

from scripts.check_s3 import check_encryption,check_ownership


class OwnershipTests(unittest.TestCase):
    def test_owner_enforced_passess(self):
        response = {
            "OwnershipControls": {
                "Rules": [
                    {"ObjectOwnership": "BucketOwnerEnforced"}
                ]
            }
        }
        self.assertTrue(check_ownership(response))

    def test_other_ownership_fails(self):
        response = {
            "OwnershipControls": {
                "Rules": [
                    {"ObjectOwnership": "ObjectWriter"}
                ]
            }
        }
        self.assertFalse(check_ownership(response))
    
    def test_missing_configuration_fails(self):
        self.assertFalse(check_ownership({}))   
    
class EncryptionTests(unittest.TestCase):
    def response_with_algorithm(self, algorithm):
        return {
            "ServerSideEncryptionConfiguration": {
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": algorithm
                        }
                    }
                ]
            }
        }
    def test_aes256_passes(self):
        self.assertTrue(
            check_encryption(self.response_with_algorithm("AES256"))
        )
    def test_kms_does_not_match_this_baseline(self):
        self.assertFalse(
            check_encryption(self.response_with_algorithm("aws:kms"))
        )
    def test_missing_configuration_fails(self):
        self.assertFalse(check_encryption({}))

if __name__ == "__main__":
    unittest.main()
    