import unittest

from scripts.check_s3 import PUBLIC_ACCESS_FLAGS, check_public_access

class PublicAccessTests(unittest.TestCase):
    def setUp(self):
        self.secure = {
            flag: True
            for flag in PUBLIC_ACCESS_FLAGS
        }

    def test_all_flags_enabled(self):
        checks = check_public_access(self.secure)
        self.assertTrue(all(checks.values()))

    def test_each_disabled_flag_is_detected(self):
        for flag in PUBLIC_ACCESS_FLAGS:
            with self.subTest(flag=flag):
                configuration = self.secure.copy()
                configuration[flag] = False
                checks = check_public_access(configuration)
                self.assertFalse(checks[flag])
                self.assertEqual(sum(checks.values()), 3)
    
    def test_each_missing_flag_is_detected(self):
        for flag in PUBLIC_ACCESS_FLAGS:
            with self.subTest(flag=flag):
                configuration = self.secure.copy()
                del configuration[flag]
                checks = check_public_access(configuration)
                self.assertFalse(checks[flag])
                
    def test_strings_are_not_accepted_as_boolean(self):
        configuration = {
            flag: "true"
            for flag in PUBLIC_ACCESS_FLAGS
        }
        checks = check_public_access(configuration)
        self.assertFalse(any(checks.values()))

if __name__ == "__main__":
    unittest.main()