import subprocess
import unittest
from unittest.mock import patch

from scripts.check_iam_access import check_result


def aws_result(returncode, stderr=""):
    return subprocess.CompletedProcess(
        args=["aws"],
        returncode=returncode,
        stdout="",
        stderr=stderr,
    )


class IAMResultTests(unittest.TestCase):
    def setUp(self):
        printer = patch("builtins.print")
        printer.start()
        self.addCleanup(printer.stop)

    def test_expected_success_passes(self):
        result = aws_result(0)
        self.assertTrue(check_result("Allowed read", result))

    def test_access_denied_passes_when_expected(self):
        result = aws_result(
            254,
            "An error occurred (AccessDenied) "
            "when calling the GetObject operation",
        )
        self.assertTrue(
            check_result("Blocked read", result, expect_denied=True)
        )

    def test_unexpected_success_fails(self):
        result = aws_result(0)
        self.assertFalse(
            check_result("Blocked read", result, expect_denied=True)
        )

    def test_other_errors_are_not_permission_passes(self):
        errors = (
            "Your session has expired. Please reauthenticate.",
            "Could not connect to the endpoint URL.",
            "An error occurred (NoSuchKey) "
            "when calling the GetObject operation",
        )

        for message in errors:
            with self.subTest(message=message):
                result = aws_result(254, message)
                with self.assertRaises(RuntimeError):
                    check_result(
                        "Blocked read",
                        result,
                        expect_denied=True,
                    )

    def test_denied_expected_read_is_an_error(self):
        result = aws_result(
            254,
            "An error occurred (AccessDenied) "
            "when calling the GetObject operation",
        )
        with self.assertRaises(RuntimeError):
            check_result("Allowed read", result)


if __name__ == "__main__":
    unittest.main()
